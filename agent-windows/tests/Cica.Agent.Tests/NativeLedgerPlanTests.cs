using System.Text.Json;
using Xunit;

namespace Cica.Agent.Service;

public class NativeLedgerPlanTests
{
    private static Dictionary<string, object> Scope() => new() {
        ["company_code"] = 212, ["chart_company_code"] = 212, ["branch_code"] = 212,
        ["bank_account_code"] = 8, ["absent_account_code"] = 0, ["bank_inflow_side"] = "debit",
        ["period_start"] = "2026-09-01", ["period_end_exclusive"] = "2026-10-01",
        ["expected_source_rows"] = 177, ["expected_lots"] = 163, ["expected_bank_effects"] = 163,
    };
    private static JsonElement Job(Dictionary<string, object>? scope = null, string? hash = null) =>
        JsonSerializer.SerializeToElement(new {
            id = "11111111-1111-1111-1111-111111111111", version = NativeLedgerPlan.Version,
            contract_hash = hash ?? NativeLedgerPlan.LocalContractHash,
            scope_revision = "eee504f7733095d92e11b5d48a03b3ba910b1e65fd67e09e6a7de9cb840b3ba6", scope = scope ?? Scope(),
        });
    [Fact]
    public void SharedPythonRevisionAndEmbeddedQueryHashesAgree()
    {
        var plan = new NativeLedgerPlan(Job());
        Assert.Equal(5, plan.Parameters("lots").Length);
        Assert.Equal(7, plan.Parameters("records").Length);
        Assert.Equal(9, plan.Parameters("accounts").Length);
        Assert.Equal(new DateTime(2026, 9, 1), plan.Start);
        foreach (string name in new[] { "lots", "records", "accounts" }) {
            Assert.DoesNotContain(";", plan.Query(name));
            Assert.Equal(plan.Parameters(name).Length, plan.Query(name).Count(c => c == '?'));
        }
    }
    [Theory]
    [InlineData("company_code", 213)]
    [InlineData("chart_company_code", 213)]
    [InlineData("branch_code", 1)]
    [InlineData("bank_account_code", 20)]
    [InlineData("expected_source_rows", 178)]
    [InlineData("absent_account_code", 9)]
    public void UnsupportedScopeCannotReachOdbc(string key, int value)
    {
        var scope = Scope(); scope[key] = value;
        Assert.Throws<InvalidDataException>(() => new NativeLedgerPlan(Job(scope)));
    }
    [Fact]
    public void UntrustedContractIsRejected()
    {
        Assert.Throws<InvalidDataException>(() => new NativeLedgerPlan(Job(hash: new string('0', 64))));
    }
    [Theory]
    [InlineData("1.00")]
    [InlineData("999999999999.99")]
    public void ExactSourceDecimalsHaveNoRounding(string amount)
    {
        decimal value = decimal.Parse(amount, System.Globalization.CultureInfo.InvariantCulture);
        Assert.Equal(amount, NativeLedgerPlan.Amount(value));
    }
    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    [InlineData(100)]
    public void NonDecimalDriverValuesAreRejected(int value) =>
        Assert.Throws<InvalidDataException>(() => NativeLedgerPlan.Amount(value));
    [Fact]
    public void ExcessPrecisionAndOverflowAreRejected()
    {
        Assert.Throws<InvalidDataException>(() => NativeLedgerPlan.Amount(1.001m));
        Assert.Throws<InvalidDataException>(() => NativeLedgerPlan.Amount(1000000000000m));
        Assert.Throws<InvalidDataException>(() => NativeLedgerPlan.Amount(-1m));
    }
}
