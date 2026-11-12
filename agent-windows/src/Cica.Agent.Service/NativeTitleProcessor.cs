using System.Data;
using System.Data.Odbc;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class NativeTitleProcessor(AgentConfig config, AgentClient client)
{
    internal async Task<bool> RunOnce(CancellationToken token)
    {
        using JsonDocument response = await client.PostAsync("api/agent/v2/titles/next", new { version = "1.0.9" }, token);
        var job = response.RootElement.GetProperty("job");
        if (job.ValueKind == JsonValueKind.Null)
            return response.RootElement.GetProperty("review_required").GetBoolean();
        var plan = new NativeTitlePlan(job);
        byte[] content;
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(token);
        deadline.CancelAfter(TimeSpan.FromMinutes(3));
        try
        {
            using var connection = new OdbcConnection(LocalOdbcConnection.Build(config.Dsn!,
                config.DatabaseUser, config.DatabasePassword, config.UseDsnAuthentication));
            connection.ConnectionTimeout = 20;
            await connection.OpenAsync(deadline.Token);
            byte[] first = await ReadSnapshot(connection, plan, deadline.Token);
            content = await ReadSnapshot(connection, plan, deadline.Token);
            if (!first.AsSpan().SequenceEqual(content)) {
                await Fail(plan, "source_changed", token);
                return true;
            }
        }
        catch (OdbcException) { await Fail(plan, "source_unavailable", token); return true; }
        catch (InvalidDataException) { await Fail(plan, "source_contract", token); return true; }
        catch (OperationCanceledException) when (!token.IsCancellationRequested)
        { await Fail(plan, "source_unavailable", token); return true; }
        // byte[] uses the base64 JSON converter, avoiding string-encoder expansion.
        try {
            using JsonDocument completed = await client.PostAsync($"api/agent/v2/titles/{plan.Id}/complete", new {
                scope_revision = plan.Revision, contract_hash = plan.ContractHash,
                content_sha256 = NativeTitlePlan.Digest(content), content_base64 = content,
            }, token);
            return completed.RootElement.GetProperty("result").GetProperty("requires_semantic_review").GetBoolean();
        }
        catch (HttpRequestException error) when (error.StatusCode == System.Net.HttpStatusCode.BadRequest)
        { await Fail(plan, "source_contract", token); return true; }
    }
    private async Task Fail(NativeTitlePlan plan, string code, CancellationToken token)
    {
        using JsonDocument _ = await client.PostAsync($"api/agent/v2/titles/{plan.Id}/failure", new {
            scope_revision = plan.Revision, contract_hash = plan.ContractHash, code,
        }, token);
    }
    private static async Task<byte[]> ReadSnapshot(OdbcConnection connection, NativeTitlePlan plan, CancellationToken token)
    {
        var families = new List<object>();
        foreach (string family in NativeTitlePlan.Families)
        {
            var controls = await Rows(connection, plan, family + "_control", token);
            if (controls.Count != 1) throw NativeTitlePlan.Invalid();
            var control = controls[0];
            foreach (string field in new[] { "due_installments", "payments", "accounting_links" })
                if ((int)control[field]! != plan.Expected(family, field)) throw NativeTitlePlan.Invalid();
            if ((int)control["missing_headers"]! != 0 || (int)control["missing_installments"]! != 0) throw NativeTitlePlan.Invalid();
            var installments = await Rows(connection, plan, family + "_installments", token);
            var payments = await Rows(connection, plan, family + "_payments", token);
            var links = await Rows(connection, plan, family + "_accounting_links", token);
            if ((int)control["selected_installments"]! != installments.Count
                || (int)control["payments"]! != payments.Count || (int)control["accounting_links"]! != links.Count) throw NativeTitlePlan.Invalid();
            families.Add(new { name = family, control, installments, payments, accounting_links = links });
        }
        byte[] content = JsonSerializer.SerializeToUtf8Bytes(new {
            version = NativeTitlePlan.Version, scope_revision = plan.Revision,
            coverage = plan.Manifest.GetProperty("coverage"), families,
        });
        if (content.Length > NativeTitlePlan.MaxBytes) throw NativeTitlePlan.Invalid();
        return content;
    }
    private static async Task<List<Dictionary<string, object?>>> Rows(OdbcConnection connection, NativeTitlePlan plan, string name, CancellationToken token)
    {
        token.ThrowIfCancellationRequested();
        var spec = plan.Specification(name);
        var columns = spec.GetProperty("columns").EnumerateArray().ToArray();
        using var command = new OdbcCommand(plan.Query(name), connection) { CommandTimeout = 20 };
        foreach (object value in plan.Parameters(name)) {
            var parameter = command.Parameters.Add("", value is DateTime ? OdbcType.Date : OdbcType.Int);
            parameter.Value = value;
        }
        using var reader = await command.ExecuteReaderAsync(token);
        if (reader.FieldCount != columns.Length) throw NativeTitlePlan.Invalid();
        var rows = new List<Dictionary<string, object?>>();
        while (await reader.ReadAsync(token)) {
            token.ThrowIfCancellationRequested();
            if (rows.Count >= spec.GetProperty("row_limit").GetInt32()) throw NativeTitlePlan.Invalid();
            var row = new Dictionary<string, object?>();
            for (int i = 0; i < columns.Length; i++)
                row.Add(columns[i].GetProperty("name").GetString()!, NativeTitlePlan.ReadValue(reader.GetValue(i), columns[i]));
            rows.Add(row);
        }
        return rows;
    }
}
