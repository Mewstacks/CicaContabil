using System.Net;
using System.Text.Json;
using Xunit;

namespace Cica.Agent.Service;

public class NativeTitleAutomaticTests
{
    private const string Capture = "11111111-1111-1111-1111-111111111111";
    private static SortedDictionary<string, object> Scope() => new(StringComparer.Ordinal) {
        ["capture_id"] = Capture, ["company_code"] = 37,
        ["period_start"] = "2019-12-01", ["period_end_exclusive"] = "2020-01-01",
    };
    private static JsonElement Job(SortedDictionary<string, object>? scope = null, string? version = null)
    {
        scope ??= Scope();
        return JsonSerializer.SerializeToElement(new {
            id = Capture, version = version ?? NativeTitlePlan.AutomaticVersion,
            contract_hash = NativeTitlePlan.LocalContractHash,
            scope_revision = NativeTitlePlan.Digest(JsonSerializer.SerializeToUtf8Bytes(scope)), scope,
        });
    }
    private static Dictionary<string, object?> Control() => new() {
        ["due_installments"] = 2, ["selected_installments"] = 3, ["payments"] = 5,
        ["accounting_links"] = 4, ["missing_headers"] = 0, ["missing_installments"] = 0,
    };

    [Fact]
    public void HistoricalCompanyScopeMatchesPythonHashAndUsesUnchangedSql()
    {
        var plan = new NativeTitlePlan(Job());
        Assert.True(plan.AutomaticCounts);
        Assert.Equal(NativeTitlePlan.AutomaticVersion, plan.SnapshotVersion);
        Assert.Equal("410c0372edf4a7da552ae4e242e2225b96600c27136208ae0a57c7b8c67b73ec", plan.Revision);
        Assert.Equal(NativeTitlePlan.Version, plan.Manifest.GetProperty("version").GetString());
        foreach (string family in NativeTitlePlan.Families)
        foreach (string kind in new[] { "control", "installments", "payments", "accounting_links" }) {
            string query = family + "_" + kind;
            var values = plan.Parameters(query);
            Assert.Contains(37, values);
            Assert.DoesNotContain(212, values);
            Assert.Equal(plan.Query(query).Count(c => c == '?'), values.Length);
            Assert.Contains(new DateTime(2019, 12, 1), values);
            Assert.Contains(new DateTime(2020, 1, 1), values);
        }
    }

    [Theory]
    [InlineData("0001-01-01", "0001-02-01")]
    [InlineData("2020-02-01", "2020-03-01")]
    [InlineData("9998-12-01", "9999-01-01")]
    public void EntireSupportedMonthlyDateRangeIsAccepted(string start, string end)
    {
        var scope = Scope(); scope["period_start"] = start; scope["period_end_exclusive"] = end;
        var plan = new NativeTitlePlan(Job(scope));
        Assert.True(plan.IsDueInPeriod(start));
        Assert.False(plan.IsDueInPeriod(end));
    }

    [Theory]
    [InlineData("company_code", 0)]
    [InlineData("company_code", -1)]
    [InlineData("company_code", 37.5)]
    [InlineData("company_code", "37")]
    [InlineData("company_code", true)]
    [InlineData("company_code", 2147483648L)]
    [InlineData("period_start", "2019-12-02")]
    [InlineData("period_start", "2019-11-01")]
    [InlineData("period_start", "2019-2-01")]
    [InlineData("period_start", "0000-12-01")]
    [InlineData("period_start", "9999-12-01")]
    [InlineData("period_end_exclusive", "2020-02-01")]
    [InlineData("capture_id", "22222222-2222-2222-2222-222222222222")]
    [InlineData("comparison_bank_account_code", 8)]
    [InlineData("expected_counts", "{}")]
    public void InvalidCompanyOrMonthNeverReachesTheDatabase(string field, object value)
    {
        var scope = Scope(); scope[field] = value;
        Assert.Throws<InvalidDataException>(() => new NativeTitlePlan(Job(scope)));
    }

    [Fact]
    public void CompanyScopeCannotBeDisguisedAsLegacy()
    {
        Assert.Throws<InvalidDataException>(() => new NativeTitlePlan(Job(version: NativeTitlePlan.Version)));
    }

    [Fact]
    public void SourceControlCountsMustMatchObservedRowsWithoutHumanCounts()
    {
        var plan = new NativeTitlePlan(Job());
        plan.ValidateObservedCounts("entradas", Control(), 3, 5, 4, 2);
        foreach (string field in Control().Keys) {
            var changed = Control(); changed[field] = (int)changed[field]! + 1;
            Assert.Throws<InvalidDataException>(() => plan.ValidateObservedCounts("entradas", changed, 3, 5, 4, 2));
        }
        var tooLarge = Control(); tooLarge["payments"] = NativeTitlePlan.MaxRows + 1;
        Assert.Throws<InvalidDataException>(() => plan.ValidateObservedCounts("entradas", tooLarge, 3, NativeTitlePlan.MaxRows + 1, 4, 2));
        var nonInteger = Control(); nonInteger["payments"] = 5.0;
        Assert.Throws<InvalidDataException>(() => plan.ValidateObservedCounts("entradas", nonInteger, 3, 5, 4, 2));
    }

    [Fact]
    public async Task StableReadRequiresTwoIdenticalCompleteSnapshots()
    {
        int reads = 0;
        byte[]? content = await NativeTitlePlan.ReadStableSnapshot(_ => {
            reads++; return Task.FromResult(new byte[] { 1, 2 });
        }, CancellationToken.None);
        Assert.Equal(2, reads); Assert.Equal(new byte[] { 1, 2 }, content);
        reads = 0;
        content = await NativeTitlePlan.ReadStableSnapshot(_ => Task.FromResult(new byte[] { (byte)++reads }), CancellationToken.None);
        Assert.Equal(2, reads); Assert.Null(content);
    }

    [Fact]
    public async Task CapabilityNegotiationFallsBackOnlyForLegacyBadRequest()
    {
        var attempts = new List<bool>();
        using var result = await NativeTitlePlan.NextAutomaticJob((automatic, _) => {
            attempts.Add(automatic);
            if (automatic) throw new HttpRequestException("legacy", null, HttpStatusCode.BadRequest);
            return Task.FromResult(JsonDocument.Parse("{}"));
        }, CancellationToken.None);
        Assert.Equal(new[] { true, false }, attempts);
    }

    [Theory]
    [InlineData(HttpStatusCode.Unauthorized)]
    [InlineData(HttpStatusCode.Forbidden)]
    [InlineData(HttpStatusCode.Conflict)]
    [InlineData(HttpStatusCode.InternalServerError)]
    public async Task AuthenticationAndServerFailuresDoNotDowngrade(HttpStatusCode status)
    {
        int attempts = 0;
        await Assert.ThrowsAsync<HttpRequestException>(() => NativeTitlePlan.NextAutomaticJob((_, _) => {
            attempts++; throw new HttpRequestException("failure", null, status);
        }, CancellationToken.None));
        Assert.Equal(1, attempts);
    }
}
