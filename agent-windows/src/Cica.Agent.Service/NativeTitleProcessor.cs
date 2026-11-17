using System.Data;
using System.Data.Odbc;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class NativeTitleProcessor(AgentConfig config, AgentClient client)
{
    internal async Task<NativeCollectionOutcome> RunOnce(CancellationToken token)
    {
        using JsonDocument response = await NativeTitlePlan.NextAutomaticJob((automatic, cancellation) =>
            client.PostAsync("api/agent/v2/titles/next", automatic
                ? (object)new { version = "1.0.9", company_scope = true, automatic_counts = true }
                : new { version = "1.0.9" }, cancellation), token);
        var job = response.RootElement.GetProperty("job");
        if (job.ValueKind == JsonValueKind.Null)
            return NativeCollectionOutcome.Idle(response.RootElement.GetProperty("review_required").GetBoolean());
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
            byte[]? stable = await NativeTitlePlan.ReadStableSnapshot(
                cancellation => ReadSnapshot(connection, plan, cancellation), deadline.Token);
            if (stable is null) {
                await Fail(plan, "source_changed", token);
                return NativeCollectionOutcome.Rejected();
            }
            content = stable;
        }
        catch (OdbcException) { await Fail(plan, "source_unavailable", token); return NativeCollectionOutcome.Rejected(); }
        catch (InvalidDataException) { await Fail(plan, "source_contract", token); return NativeCollectionOutcome.Rejected(); }
        catch (OperationCanceledException) when (!token.IsCancellationRequested)
        { await Fail(plan, "source_unavailable", token); return NativeCollectionOutcome.Rejected(); }
        // byte[] uses the base64 JSON converter, avoiding string-encoder expansion.
        try {
            using JsonDocument completed = await client.PostAsync($"api/agent/v2/titles/{plan.Id}/complete", new {
                scope_revision = plan.Revision, contract_hash = plan.ContractHash,
                content_sha256 = NativeTitlePlan.Digest(content), content_base64 = content,
            }, token);
            return NativeCollectionOutcome.Completed(
                completed.RootElement.GetProperty("result").GetProperty("requires_semantic_review").GetBoolean());
        }
        catch (HttpRequestException error) when (error.StatusCode == System.Net.HttpStatusCode.BadRequest)
        { await Fail(plan, "source_contract", token); return NativeCollectionOutcome.Rejected(); }
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
            var installments = await Rows(connection, plan, family + "_installments", token);
            var payments = await Rows(connection, plan, family + "_payments", token);
            var links = await Rows(connection, plan, family + "_accounting_links", token);
            string dueField = plan.Manifest.GetProperty("families").GetProperty(family).GetProperty("due_field").GetString()!;
            plan.ValidateObservedCounts(family, control, installments.Count, payments.Count, links.Count,
                installments.Count(row => plan.IsDueInPeriod((string)row[dueField]!)));
            families.Add(new { name = family, control, installments, payments, accounting_links = links });
        }
        byte[] content = JsonSerializer.SerializeToUtf8Bytes(new {
            version = plan.SnapshotVersion, scope_revision = plan.Revision,
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
