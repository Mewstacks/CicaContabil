using System.Globalization;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class NativeLedgerPlan
{
    internal const string Version = "dominio-ledger-snapshot-v1";
    internal const int MaxBytes = 2_000_000;
    internal string Id { get; }
    internal string Revision { get; }
    internal string ContractHash { get; }
    internal DateTime Start { get; }
    internal int Company { get; }
    internal int Chart { get; }
    internal int Bank { get; }
    internal int ExpectedRows { get; }
    internal int ExpectedLots { get; }
    internal DateTime End { get; }
    internal JsonElement Manifest { get; }
    private static byte[] Resource(string name)
    {
        using Stream input = typeof(NativeLedgerPlan).Assembly.GetManifestResourceStream("Cica.Ledger." + name)
            ?? throw Invalid();
        using var output = new MemoryStream();
        input.CopyTo(output);
        return output.ToArray();
    }
    internal static string Digest(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));
    internal static string LocalContractHash => Digest(Resource("manifest.json"));
    internal static async Task<JsonDocument> NextJob(
        Func<bool, CancellationToken, Task<JsonDocument>> send, CancellationToken token)
    {
        try { return await send(true, token); }
        catch (HttpRequestException error) when (error.StatusCode == System.Net.HttpStatusCode.BadRequest)
        {
            // Release 86 understands the same fixed pilot, without the capability flag.
            // Never retry authorization, scope, transport or certificate failures.
            return await send(false, token);
        }
    }
    internal static void SelfVerify()
    {
        using JsonDocument document = JsonDocument.Parse(Resource("manifest.json"));
        if (document.RootElement.GetProperty("version").GetString() != Version) throw Invalid();
        string[] names = ["lots", "records", "accounts"];
        var queries = document.RootElement.GetProperty("queries");
        if (queries.EnumerateObject().Count() != names.Length) throw Invalid();
        foreach (string name in names)
        {
            var query = queries.GetProperty(name);
            if (query.GetProperty("file").GetString() != name + ".sql"
                || Digest(Resource(name + ".sql")) != query.GetProperty("sha256").GetString()) throw Invalid();
            string sql = Encoding.UTF8.GetString(Resource(name + ".sql"));
            if (sql.Contains(';') || sql.Count(c => c == '?') != query.GetProperty("parameters").GetArrayLength()) throw Invalid();
        }
    }
    internal NativeLedgerPlan(JsonElement job)
    {
        SelfVerify();
        if (job.GetProperty("version").GetString() != Version
            || job.GetProperty("contract_hash").GetString() != LocalContractHash) throw Invalid();
        Id = job.GetProperty("id").GetString() ?? throw Invalid();
        if (!Guid.TryParseExact(Id, "D", out _)) throw Invalid();
        Revision = job.GetProperty("scope_revision").GetString() ?? throw Invalid();
        ContractHash = LocalContractHash;
        var scope = job.GetProperty("scope");
        string[] fields = ["company_code", "chart_company_code", "branch_code", "bank_account_code",
            "absent_account_code", "bank_inflow_side", "period_start", "period_end_exclusive",
            "expected_source_rows", "expected_lots", "expected_bank_effects"];
        if (scope.EnumerateObject().Count() != fields.Length) throw Invalid();
        var expected = new SortedDictionary<string, object>(StringComparer.Ordinal);
        foreach (string field in fields) {
            var value = scope.GetProperty(field);
            if (field is "period_start" or "period_end_exclusive" or "bank_inflow_side") {
                if (value.ValueKind != JsonValueKind.String) throw Invalid();
                expected[field] = value.GetString() ?? throw Invalid();
            } else {
                if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt32(out int number)
                    || value.GetRawText() != number.ToString(CultureInfo.InvariantCulture)) throw Invalid();
                int minimum = field.StartsWith("expected_") || field == "absent_account_code" ? 0 : 1;
                int maximum = field.StartsWith("expected_") ? 50_000 : int.MaxValue;
                if (number < minimum || number > maximum) throw Invalid();
                expected[field] = number;
            }
        }
        if ((int)expected["absent_account_code"] != 0
            || (string)expected["bank_inflow_side"] is not ("debit" or "credit")) throw Invalid();
        if (!DateTime.TryParseExact((string)expected["period_start"], "yyyy-MM-dd", CultureInfo.InvariantCulture,
            DateTimeStyles.None, out DateTime start)
            || !DateTime.TryParseExact((string)expected["period_end_exclusive"], "yyyy-MM-dd", CultureInfo.InvariantCulture,
            DateTimeStyles.None, out DateTime end)
            || start < new DateTime(2026, 9, 1) || start.Day != 1 || end.Day != 1
            || end != start.AddMonths(1)) throw Invalid();
        Start = start; End = end;
        Company = (int)expected["company_code"]; Chart = (int)expected["chart_company_code"];
        Bank = (int)expected["bank_account_code"];
        ExpectedRows = (int)expected["expected_source_rows"]; ExpectedLots = (int)expected["expected_lots"];
        if (ExpectedLots > ExpectedRows || (ExpectedRows == 0) != (ExpectedLots == 0)
            || (int)expected["expected_bank_effects"] != ExpectedLots) throw Invalid();
        if (Revision != Digest(JsonSerializer.SerializeToUtf8Bytes(expected))) throw Invalid();
        using JsonDocument manifest = JsonDocument.Parse(Resource("manifest.json"));
        Manifest = manifest.RootElement.Clone();
    }
    internal string Query(string name) => Encoding.UTF8.GetString(Resource(name + ".sql"));
    internal object[] Parameters(string name) => Manifest.GetProperty("queries").GetProperty(name)
        .GetProperty("parameters").EnumerateArray().Select(p => p.GetString() switch {
            "company" => (object)Company, "chart" => Chart, "bank" => Bank, "absent" => 0,
            "start" => Start, "end" => End, _ => throw Invalid(),
        }).ToArray();
    internal static InvalidDataException Invalid() => new("Contrato de coleta nativa incompatível; confira a coleta no CICA.");
    internal static string Amount(object value)
    {
        if (value is not decimal amount || amount <= 0 || amount > 999999999999.99m
            || decimal.Truncate(amount * 100) != amount * 100) throw Invalid();
        return amount.ToString("0.00", CultureInfo.InvariantCulture);
    }
}
