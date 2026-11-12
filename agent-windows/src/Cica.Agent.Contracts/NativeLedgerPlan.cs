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
    internal DateTime Start => new(2026, 9, 1);
    internal DateTime End => new(2026, 10, 1);
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
        var expected = new SortedDictionary<string, object>(StringComparer.Ordinal) {
            ["company_code"] = 212, ["chart_company_code"] = 212, ["branch_code"] = 212,
            ["bank_account_code"] = 8, ["absent_account_code"] = 0, ["bank_inflow_side"] = "debit",
            ["period_start"] = "2026-09-01", ["period_end_exclusive"] = "2026-10-01",
            ["expected_source_rows"] = 177, ["expected_lots"] = 163, ["expected_bank_effects"] = 163,
        };
        if (scope.EnumerateObject().Count() != expected.Count) throw Invalid();
        foreach (var pair in expected)
        {
            var value = scope.GetProperty(pair.Key);
            if (pair.Value is int number)
            {
                if (value.ValueKind != JsonValueKind.Number || value.GetRawText() != number.ToString(CultureInfo.InvariantCulture)) throw Invalid();
            }
            else if (value.ValueKind != JsonValueKind.String || value.GetString() != (string)pair.Value) throw Invalid();
        }
        if (Revision != Digest(JsonSerializer.SerializeToUtf8Bytes(expected))) throw Invalid();
        using JsonDocument manifest = JsonDocument.Parse(Resource("manifest.json"));
        Manifest = manifest.RootElement.Clone();
    }
    internal string Query(string name) => Encoding.UTF8.GetString(Resource(name + ".sql"));
    internal object[] Parameters(string name) => Manifest.GetProperty("queries").GetProperty(name)
        .GetProperty("parameters").EnumerateArray().Select(p => p.GetString() switch {
            "company" or "chart" => (object)212, "bank" => 8, "absent" => 0,
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
