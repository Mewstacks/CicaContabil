using System.Data;
using System.Data.Common;
using System.Data.Odbc;
using System.Globalization;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class NativeLedgerProcessor(AgentConfig config, AgentClient client)
{
    internal async Task<bool> RunOnce(CancellationToken token)
    {
        using JsonDocument response = await client.PostAsync("api/agent/v2/ledger/next", new { version = "1.0.8" }, token);
        var job = response.RootElement.GetProperty("job");
        if (job.ValueKind == JsonValueKind.Null)
            return response.RootElement.TryGetProperty("review_required", out var review) && review.GetBoolean();
        var plan = new NativeLedgerPlan(job);
        byte[] content;
        try
        {
            using var connection = new OdbcConnection(LocalOdbcConnection.Build(config.Dsn!,
                config.DatabaseUser, config.DatabasePassword, config.UseDsnAuthentication));
            connection.ConnectionTimeout = 20;
            await connection.OpenAsync(token);
            byte[] first = await ReadSnapshot(connection, plan, token);
            content = await ReadSnapshot(connection, plan, token);
            if (!first.AsSpan().SequenceEqual(content))
            {
                await Fail(plan, "source_changed", token);
                return true;
            }
        }
        catch (OdbcException)
        {
            await Fail(plan, "source_unavailable", token);
            return true;
        }
        catch (InvalidDataException)
        {
            await Fail(plan, "source_contract", token);
            return true;
        }
        using JsonDocument completed = await client.PostAsync($"api/agent/v2/ledger/{plan.Id}/complete", new {
            scope_revision = plan.Revision, contract_hash = plan.ContractHash,
            content_sha256 = NativeLedgerPlan.Digest(content), content_base64 = Convert.ToBase64String(content),
        }, token);
        return completed.RootElement.GetProperty("state").GetString() != "imported";
    }

    private async Task Fail(NativeLedgerPlan plan, string code, CancellationToken token)
    {
        using JsonDocument _ = await client.PostAsync($"api/agent/v2/ledger/{plan.Id}/failure", new {
            scope_revision = plan.Revision, contract_hash = plan.ContractHash, code,
        }, token);
    }

    private static async Task<byte[]> ReadSnapshot(OdbcConnection connection, NativeLedgerPlan plan, CancellationToken token)
    {
        var lots = await Rows(connection, plan, "lots", 3, r => new Dictionary<string, object?> {
            ["lot_code"] = Integer(r[0]), ["row_count"] = Integer(r[1]), ["type_raw"] = Text(r[2]),
        }, token);
        var records = await Rows(connection, plan, "records", 12, r => new Dictionary<string, object?> {
            ["company_code"] = Integer(r[0]), ["chart_company_code"] = Integer(r[1]),
            ["lot_code"] = Integer(r[2]), ["row_code"] = Integer(r[3]), ["branch_code"] = Integer(r[4]),
            ["occurred_on"] = Day(r[5]), ["debit_account_code"] = Integer(r[6]),
            ["credit_account_code"] = Integer(r[7]), ["amount"] = NativeLedgerPlan.Amount(r[8]),
            ["history"] = Text(r[9]), ["document"] = NullableInteger(r[10]), ["history_code_raw"] = NullableInteger(r[11]),
        }, token);
        var accounts = await Rows(connection, plan, "accounts", 7, r => new Dictionary<string, object?> {
            ["company_code"] = Integer(r[0]), ["account_code"] = Integer(r[1]),
            ["name_raw"] = Text(r[2]), ["classification_raw"] = Text(r[3]),
            ["type_raw"] = Text(r[4]), ["status_raw"] = Text(r[5]),
            ["inactive_date_raw"] = r.IsDBNull(6) ? null : Day(r[6]),
        }, token);
        if (lots.Count != 163 || records.Count != 177 || accounts.Count == 0
            || accounts.Count > 5000 || accounts.Any(a => (int)a["account_code"]! == 0)
            || lots.Sum(l => (int)l["row_count"]!) != records.Count) throw NativeLedgerPlan.Invalid();
        byte[] bytes = JsonSerializer.SerializeToUtf8Bytes(new {
            version = NativeLedgerPlan.Version, scope_revision = plan.Revision, lots, records, accounts,
        });
        if (bytes.Length > NativeLedgerPlan.MaxBytes) throw NativeLedgerPlan.Invalid();
        return bytes;
    }

    private static async Task<List<Dictionary<string, object?>>> Rows(OdbcConnection connection,
        NativeLedgerPlan plan, string name, int fields, Func<DbDataReader, Dictionary<string, object?>> read,
        CancellationToken token)
    {
        using var command = new OdbcCommand(plan.Query(name), connection) { CommandTimeout = 60 };
        foreach (object value in plan.Parameters(name))
        {
            var parameter = command.Parameters.Add("", value is DateTime ? OdbcType.Date : OdbcType.Int);
            parameter.Value = value;
        }
        using var reader = await command.ExecuteReaderAsync(token);
        if (reader.FieldCount != fields) throw NativeLedgerPlan.Invalid();
        var rows = new List<Dictionary<string, object?>>();
        while (await reader.ReadAsync(token))
        {
            if (rows.Count >= 50_000) throw NativeLedgerPlan.Invalid();
            rows.Add(read(reader));
        }
        return rows;
    }
    private static int Integer(object value) => value switch {
        int i when i >= 0 => i, short s when s >= 0 => s,
        long l when l >= 0 && l <= int.MaxValue => (int)l,
        decimal d when d >= 0 && d <= int.MaxValue && decimal.Truncate(d) == d => (int)d,
        _ => throw NativeLedgerPlan.Invalid(),
    };
    private static int? NullableInteger(object value) => value is DBNull ? null : Integer(value);
    private static string? Text(object value) => value switch {
        DBNull => null, string s when s.Length <= 1000 => s, _ => throw NativeLedgerPlan.Invalid(),
    };
    private static string Day(object value) => value is DateTime day && day.TimeOfDay == TimeSpan.Zero
        ? day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) : throw NativeLedgerPlan.Invalid();
}
