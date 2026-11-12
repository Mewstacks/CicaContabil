using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class NativeTitlePlan
{
    internal const string Version = "dominio-title-snapshot-v1";
    internal const int MaxBytes = 4_000_000;
    internal static readonly string[] Families = ["entradas", "saidas", "servicos"];
    internal string Id { get; }
    internal string Revision { get; }
    internal string ContractHash { get; }
    internal JsonElement Manifest { get; }
    private readonly JsonElement counts;
    private static DateTime Start => new(2026, 9, 1);
    private static DateTime End => new(2026, 10, 1);

    private static byte[] Resource(string name)
    {
        using Stream input = typeof(NativeTitlePlan).Assembly.GetManifestResourceStream("Cica.Titles." + name)
            ?? throw Invalid();
        using var output = new MemoryStream();
        input.CopyTo(output);
        return output.ToArray();
    }
    internal static string Digest(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));
    internal static string LocalContractHash => Digest(Resource("manifest.json"));
    internal static InvalidDataException Invalid() => new("Fonte fiscal fora do contrato; confira a captura no CICA.");

    internal static void SelfVerify()
    {
        using JsonDocument document = JsonDocument.Parse(Resource("manifest.json"));
        var root = document.RootElement;
        if (root.GetProperty("version").GetString() != Version || root.GetProperty("maximum_bytes").GetInt32() != MaxBytes)
            throw Invalid();
        var queries = root.GetProperty("queries");
        if (queries.EnumerateObject().Count() != 12) throw Invalid();
        foreach (string family in Families)
        foreach (string kind in new[] { "control", "installments", "payments", "accounting_links" })
        {
            string name = family + "_" + kind;
            var spec = queries.GetProperty(name);
            byte[] sql = Resource(name + ".sql");
            if (spec.GetProperty("file").GetString() != name + ".sql"
                || spec.GetProperty("sha256").GetString() != Digest(sql)
                || Encoding.UTF8.GetString(sql).Contains(';')
                || sql.Count(b => b == (byte)'?') != spec.GetProperty("parameters").GetArrayLength())
                throw Invalid();
        }
    }

    private static void Fields(JsonElement value, params string[] fields)
    {
        if (value.ValueKind != JsonValueKind.Object) throw Invalid();
        var names = value.EnumerateObject().Select(p => p.Name).ToArray();
        if (names.Length != fields.Length || names.Distinct().Count() != names.Length
            || names.Any(n => !fields.Contains(n))) throw Invalid();
    }
    internal NativeTitlePlan(JsonElement job)
    {
        try
        {
            SelfVerify();
            Fields(job, "id", "version", "contract_hash", "scope_revision", "scope");
            if (job.GetProperty("version").GetString() != Version
                || job.GetProperty("contract_hash").GetString() != LocalContractHash) throw Invalid();
            Id = job.GetProperty("id").GetString() ?? throw Invalid();
            if (!Guid.TryParseExact(Id, "D", out _) || Id != Id.ToLowerInvariant()) throw Invalid();
            Revision = job.GetProperty("scope_revision").GetString() ?? throw Invalid();
            ContractHash = LocalContractHash;
            var scope = job.GetProperty("scope");
            Fields(scope, "capture_id", "company_code", "comparison_bank_account_code", "period_start", "period_end_exclusive", "expected_counts");
            if (scope.GetProperty("capture_id").GetString() != Id) throw Invalid();
            var expected = new SortedDictionary<string, object>(StringComparer.Ordinal) {
                ["capture_id"] = Id, ["company_code"] = 212, ["comparison_bank_account_code"] = 8,
                ["period_start"] = "2026-09-01", ["period_end_exclusive"] = "2026-10-01",
            };
            foreach (var pair in expected)
            {
                var value = scope.GetProperty(pair.Key);
                if (pair.Value is int number) {
                    if (value.ValueKind != JsonValueKind.Number || value.GetRawText() != number.ToString(CultureInfo.InvariantCulture)) throw Invalid();
                } else if (value.ValueKind != JsonValueKind.String || value.GetString() != (string)pair.Value) throw Invalid();
            }
            counts = scope.GetProperty("expected_counts").Clone();
            Fields(counts, Families);
            var familyCounts = new SortedDictionary<string, object>(StringComparer.Ordinal);
            foreach (string family in Families)
            {
                var value = counts.GetProperty(family);
                Fields(value, "due_installments", "payments", "accounting_links");
                var group = new SortedDictionary<string, object>(StringComparer.Ordinal);
                foreach (string field in new[] { "due_installments", "payments", "accounting_links" })
                {
                    var raw = value.GetProperty(field);
                    if (raw.ValueKind != JsonValueKind.Number || !raw.TryGetInt32(out int number)
                        || number < 0 || number > 50_000 || raw.GetRawText() != number.ToString(CultureInfo.InvariantCulture)) throw Invalid();
                    group[field] = number;
                }
                familyCounts[family] = group;
            }
            expected["expected_counts"] = familyCounts;
            if (Revision != Digest(JsonSerializer.SerializeToUtf8Bytes(expected))) throw Invalid();
            using JsonDocument manifest = JsonDocument.Parse(Resource("manifest.json"));
            Manifest = manifest.RootElement.Clone();
        }
        catch (Exception error) when (error is KeyNotFoundException or InvalidOperationException or FormatException or OverflowException or JsonException)
        { throw Invalid(); }
    }
    internal JsonElement Specification(string name) => Manifest.GetProperty("queries").GetProperty(name);
    internal string Query(string name) => Encoding.UTF8.GetString(Resource(name + ".sql"));
    internal object[] Parameters(string name) => Specification(name).GetProperty("parameters")
        .EnumerateArray().Select(p => p.GetString() switch {
            "company" => (object)212, "start" => Start, "end" => End, _ => throw Invalid(),
        }).ToArray();
    internal int Expected(string family, string kind) => counts.GetProperty(family).GetProperty(kind).GetInt32();

    internal static object? ReadValue(object value, JsonElement spec)
    {
        if (value is DBNull) {
            if (spec.GetProperty("nullable").GetBoolean()) return null;
            throw Invalid();
        }
        switch (spec.GetProperty("type").GetString())
        {
            case "int":
                long number = value switch {
                    byte b => b, short s => s, int i => i, long l => l,
                    decimal d when d >= long.MinValue && d <= long.MaxValue && decimal.Truncate(d) == d => (long)d,
                    _ => throw Invalid(),
                };
                if (number < spec.GetProperty("minimum").GetInt64() || number > spec.GetProperty("maximum").GetInt64()) throw Invalid();
                return (int)number;
            case "decimal":
                if (value is not decimal amount) throw Invalid();
                int digits = spec.GetProperty("integer_digits").GetInt32();
                int scale = spec.GetProperty("scale").GetInt32();
                if (digits < 1 || digits > 12 || scale != 2) throw Invalid();
                decimal limit = 1m;
                for (int i = 0; i < digits; i++) limit *= 10;
                if (amount <= -limit || amount >= limit || decimal.Truncate(amount * 100) != amount * 100) throw Invalid();
                return amount.ToString("0.00", CultureInfo.InvariantCulture);
            case "date":
                return value is DateTime day && day.TimeOfDay == TimeSpan.Zero
                    ? day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) : throw Invalid();
            case "text":
                return value is string text && text.Length <= spec.GetProperty("maximum_length").GetInt32()
                    ? text : throw Invalid();
            default: throw Invalid();
        }
    }
}
