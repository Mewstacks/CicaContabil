using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class NativeTitlePlan
{
    internal const string Version = "dominio-title-snapshot-v1";
    internal const string AutomaticVersion = "dominio-title-snapshot-v2";
    internal const int MaxRows = 50_000;
    internal const int MaxBytes = 4_000_000;
    internal static readonly string[] Families = ["entradas", "saidas", "servicos"];
    internal string Id { get; }
    internal string Revision { get; }
    internal string ContractHash { get; }
    internal JsonElement Manifest { get; }
    private readonly JsonElement counts;
    internal bool AutomaticCounts { get; }
    internal string SnapshotVersion => AutomaticCounts ? AutomaticVersion : Version;
    private int Company { get; }
    private DateTime Start { get; }
    private DateTime End { get; }

    internal static async Task<JsonDocument> NextAutomaticJob(
        Func<bool, CancellationToken, Task<JsonDocument>> next, CancellationToken token)
    {
        try { return await next(true, token); }
        catch (HttpRequestException error) when (error.StatusCode == System.Net.HttpStatusCode.BadRequest)
        { return await next(false, token); }
    }

    internal static async Task<byte[]?> ReadStableSnapshot(
        Func<CancellationToken, Task<byte[]>> read, CancellationToken token)
    {
        byte[] first = await read(token);
        byte[] second = await read(token);
        return first.AsSpan().SequenceEqual(second) ? second : null;
    }

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
            string? version = job.GetProperty("version").GetString();
            if (version != Version && version != AutomaticVersion
                || job.GetProperty("contract_hash").GetString() != LocalContractHash) throw Invalid();
            AutomaticCounts = version == AutomaticVersion;
            Id = job.GetProperty("id").GetString() ?? throw Invalid();
            if (!Guid.TryParseExact(Id, "D", out _) || Id != Id.ToLowerInvariant()) throw Invalid();
            Revision = job.GetProperty("scope_revision").GetString() ?? throw Invalid();
            ContractHash = LocalContractHash;
            var scope = job.GetProperty("scope");
            if (AutomaticCounts)
                Fields(scope, "capture_id", "company_code", "period_start", "period_end_exclusive");
            else
                Fields(scope, "capture_id", "company_code", "comparison_bank_account_code", "period_start", "period_end_exclusive", "expected_counts");
            if (scope.GetProperty("capture_id").GetString() != Id) throw Invalid();
            var company = scope.GetProperty("company_code");
            if (company.ValueKind != JsonValueKind.Number || !company.TryGetInt32(out int companyCode)
                || companyCode <= 0 || company.GetRawText() != companyCode.ToString(CultureInfo.InvariantCulture)) throw Invalid();
            Company = companyCode;
            string? startText = scope.GetProperty("period_start").GetString();
            string? endText = scope.GetProperty("period_end_exclusive").GetString();
            if (!DateTime.TryParseExact(startText, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var start)
                || !DateTime.TryParseExact(endText, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var end)
                || start.Day != 1 || start.Year > 9998 || end != start.AddMonths(1)
                || start.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) != startText
                || end.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) != endText) throw Invalid();
            Start = start; End = end;
            var expected = new SortedDictionary<string, object>(StringComparer.Ordinal) {
                ["capture_id"] = Id, ["company_code"] = Company,
                ["period_start"] = startText!, ["period_end_exclusive"] = endText!,
            };
            if (!AutomaticCounts)
            {
                var bank = scope.GetProperty("comparison_bank_account_code");
                if (Company != 212 || Start != new DateTime(2026, 9, 1)
                    || bank.ValueKind != JsonValueKind.Number || bank.GetRawText() != "8") throw Invalid();
                expected["comparison_bank_account_code"] = 8;
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
                            || number < 0 || number > MaxRows || raw.GetRawText() != number.ToString(CultureInfo.InvariantCulture)) throw Invalid();
                        group[field] = number;
                    }
                    familyCounts[family] = group;
                }
                expected["expected_counts"] = familyCounts;
            }
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
            "company" => (object)Company, "start" => Start, "end" => End, _ => throw Invalid(),
        }).ToArray();
    internal int Expected(string family, string kind) => counts.GetProperty(family).GetProperty(kind).GetInt32();
    internal bool IsDueInPeriod(string value) => string.CompareOrdinal(value, Start.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)) >= 0
        && string.CompareOrdinal(value, End.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)) < 0;

    internal void ValidateObservedCounts(string family, IReadOnlyDictionary<string, object?> control,
        int installments, int payments, int links, int due)
    {
        if (!Families.Contains(family)) throw Invalid();
        foreach (string field in new[] { "due_installments", "selected_installments", "payments", "accounting_links", "missing_headers", "missing_installments" })
            if (!control.TryGetValue(field, out object? value) || value is not int number || number < 0 || number > MaxRows) throw Invalid();
        if (installments < 0 || installments > MaxRows || payments < 0 || payments > MaxRows || links < 0 || links > MaxRows
            || due < 0 || due > installments || (int)control["due_installments"]! != due
            || (int)control["selected_installments"]! != installments || (int)control["payments"]! != payments
            || (int)control["accounting_links"]! != links || (int)control["missing_headers"]! != 0
            || (int)control["missing_installments"]! != 0) throw Invalid();
        if (!AutomaticCounts)
            foreach (string field in new[] { "due_installments", "payments", "accounting_links" })
                if ((int)control[field]! != Expected(family, field)) throw Invalid();
    }

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
