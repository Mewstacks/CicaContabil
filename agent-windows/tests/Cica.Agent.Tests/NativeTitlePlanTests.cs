using System.Globalization;
using System.Text;
using System.Text.Json;
using Xunit;

namespace Cica.Agent.Service;

public class NativeTitlePlanTests
{
    private const string Capture = "11111111-1111-1111-1111-111111111111";
    private static Dictionary<string, object> Scope() => new() {
        ["capture_id"] = Capture, ["company_code"] = 212, ["comparison_bank_account_code"] = 8,
        ["period_start"] = "2026-09-01", ["period_end_exclusive"] = "2026-10-01",
        ["expected_counts"] = NativeTitlePlan.Families.ToDictionary(f => f, f => new Dictionary<string, int> {
            ["due_installments"] = 0, ["payments"] = 0, ["accounting_links"] = 0,
        }),
    };
    private static JsonElement Job(Dictionary<string, object>? scope = null, string? hash = null, string? revision = null) =>
        JsonSerializer.SerializeToElement(new {
            id = Capture, version = NativeTitlePlan.Version,
            contract_hash = hash ?? NativeTitlePlan.LocalContractHash,
            scope_revision = revision ?? "d5e2c0b201e29a9a560799ab783caa70396f2761af639bcd91128d0baa8386f5",
            scope = scope ?? Scope(),
        });

    [Fact]
    public void PythonRevisionAndTwelveEmbeddedQueriesAgree()
    {
        var plan = new NativeTitlePlan(Job());
        foreach (string family in NativeTitlePlan.Families)
        foreach (string kind in new[] { "control", "installments", "payments", "accounting_links" }) {
            string name = family + "_" + kind;
            Assert.DoesNotContain(";", plan.Query(name));
            Assert.Equal(plan.Parameters(name).Length, plan.Query(name).Count(c => c == '?'));
            Assert.True(plan.Specification(name).GetProperty("columns").GetArrayLength() > 0);
        }
        Assert.Equal("unproven", plan.Manifest.GetProperty("coverage").GetProperty("bank_linkage").GetString());
        Assert.False(plan.Manifest.GetProperty("coverage").GetProperty("settlements_complete").GetBoolean());
    }
    [Theory]
    [InlineData("company_code", 213)]
    [InlineData("comparison_bank_account_code", 9)]
    [InlineData("period_start", "2026-08-01")]
    [InlineData("capture_id", "22222222-2222-2222-2222-222222222222")]
    public void UnsupportedScopeCannotReachOdbc(string field, object value)
    {
        var scope = Scope(); scope[field] = value;
        Assert.Throws<InvalidDataException>(() => new NativeTitlePlan(Job(scope)));
    }
    [Fact]
    public void ChangedApprovalOrUntrustedContractIsRejected()
    {
        Assert.Throws<InvalidDataException>(() => new NativeTitlePlan(Job(hash: new string('0', 64))));
        Assert.Throws<InvalidDataException>(() => new NativeTitlePlan(Job(revision: new string('0', 64))));
        var scope = Scope(); scope["sql"] = "SELECT unsafe";
        Assert.Throws<InvalidDataException>(() => new NativeTitlePlan(Job(scope)));
    }
    private static JsonElement Column(string name) => new NativeTitlePlan(Job())
        .Specification("entradas_payments").GetProperty("columns").EnumerateArray()
        .Single(c => c.GetProperty("name").GetString() == name);

    [Theory]
    [InlineData("0.00")]
    [InlineData("-2.50")]
    [InlineData("99999999999.99")]
    public void OriginalDecimalsPreserveZerosAndNegativeValuesWithoutRounding(string text)
    {
        decimal amount = decimal.Parse(text, CultureInfo.InvariantCulture);
        Assert.Equal(text, NativeTitlePlan.ReadValue(amount, Column("vpag_entp")));
    }
    [Fact]
    public void BinaryFloatStringsAndExcessPrecisionCannotBecomeMoney()
    {
        var column = Column("vpag_entp");
        foreach (object invalid in new object[] { 1.001m, 100000000000m, 1.0, "1.00", true })
            Assert.Throws<InvalidDataException>(() => NativeTitlePlan.ReadValue(invalid, column));
        Assert.Null(NativeTitlePlan.ReadValue(DBNull.Value, column));
    }
    [Fact]
    public void DriverTinyintsAndLiteralTextArePreserved()
    {
        Assert.Equal(255, NativeTitlePlan.ReadValue((byte)255, Column("tipo_entp")));
        Assert.Throws<InvalidDataException>(() => NativeTitlePlan.ReadValue(true, Column("tipo_entp")));
        Assert.Throws<InvalidDataException>(() => NativeTitlePlan.ReadValue(256, Column("tipo_entp")));
        Assert.Equal("0001/A  ", NativeTitlePlan.ReadValue("0001/A  ", Column("numero_titulo_entp")));
        Assert.Equal("2026-09-12", NativeTitlePlan.ReadValue(new DateTime(2026, 9, 12), Column("pgto_entp")));
        Assert.Throws<InvalidDataException>(() => NativeTitlePlan.ReadValue(new DateTime(2026, 9, 12, 1, 0, 0), Column("pgto_entp")));
    }
    [Fact]
    public void RawBytePayloadHasBoundedBase64WithoutHtmlStringExpansion()
    {
        byte[] content = [251, 255, 255];
        string json = Encoding.UTF8.GetString(JsonSerializer.SerializeToUtf8Bytes(new { content_base64 = content }));
        Assert.Contains("+///", json);
        Assert.DoesNotContain("\\u002B", json);
        using JsonDocument parsed = JsonDocument.Parse(json);
        Assert.Equal(content, parsed.RootElement.GetProperty("content_base64").GetBytesFromBase64());
        Assert.True(((NativeTitlePlan.MaxBytes + 2L) / 3 * 4) + 1024 < 10 * 1024 * 1024);
    }
}
