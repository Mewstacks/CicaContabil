using System.Text.Json;
using Xunit;

namespace Cica.Agent.Service;

public class NativeLedgerAutomaticTests
{
    private const string Capture = "11111111-1111-1111-1111-111111111111";
    private static Dictionary<string, object> Scope() => new() {
        ["company_code"] = 212, ["chart_company_code"] = 212, ["branch_code"] = 212,
        ["bank_account_code"] = 8, ["absent_account_code"] = 0, ["bank_inflow_side"] = "debit",
        ["period_start"] = "2026-09-01", ["period_end_exclusive"] = "2026-10-01",
        ["capture_id"] = Capture,
    };
    private static JsonElement Job(Dictionary<string, object>? scope = null, string? version = null) {
        scope ??= Scope();
        return JsonSerializer.SerializeToElement(new {
            id = Capture, version = version ?? NativeLedgerPlan.AutomaticVersion,
            contract_hash = NativeLedgerPlan.LocalContractHash,
            scope_revision = NativeLedgerPlan.Digest(JsonSerializer.SerializeToUtf8Bytes(
                new SortedDictionary<string, object>(scope, StringComparer.Ordinal))), scope,
        });
    }
    [Fact]
    public void AutomaticScopeHasNoGuessedTotalsAndPreservesEmbeddedQueries() {
        var plan = new NativeLedgerPlan(Job());
        Assert.True(plan.AutomaticCounts);
        Assert.Equal(NativeLedgerPlan.AutomaticVersion, plan.SnapshotVersion);
        plan.ValidateObservedCounts(177, 163, 3, 177, false);
        plan.ValidateObservedCounts(0, 0, 0, 0, false);
        foreach (string query in new[] { "lots", "records", "accounts" }) {
            Assert.DoesNotContain(";", plan.Query(query));
            Assert.Equal(plan.Parameters(query).Length, plan.Query(query).Count(c => c == '?'));
        }
    }
    [Theory]
    [InlineData(177, 163, 3, 176, false)]
    [InlineData(50001, 163, 3, 50001, false)]
    [InlineData(1, 2, 3, 1, false)]
    [InlineData(0, 1, 0, 0, false)]
    [InlineData(177, 163, 5001, 177, false)]
    [InlineData(177, 163, 3, 177, true)]
    public void UnboundedIncompleteOrInvalidResultsAreRejected(int rows, int lots, int accounts, long total, bool zero) =>
        Assert.Throws<InvalidDataException>(() => new NativeLedgerPlan(Job()).ValidateObservedCounts(rows, lots, accounts, total, zero));

    [Fact]
    public void CaptureIdentityCannotBeReusedForAnotherRequest() {
        var scope = Scope(); scope["capture_id"] = "22222222-2222-2222-2222-222222222222";
        Assert.Throws<InvalidDataException>(() => new NativeLedgerPlan(Job(scope)));
        scope = Scope(); scope["expected_source_rows"] = 177;
        Assert.Throws<InvalidDataException>(() => new NativeLedgerPlan(Job(scope)));
        Assert.Throws<InvalidDataException>(() => new NativeLedgerPlan(Job(version: NativeLedgerPlan.Version)));
    }
    [Fact]
    public async Task CapabilityRollsBackOnlyThroughKnownOlderShapes() {
        var attempts = new List<int>();
        using var response = await NativeLedgerPlan.NextAutomaticJob((capability, _) => {
            attempts.Add(capability);
            if (capability > 0) throw new HttpRequestException("older backend", null, System.Net.HttpStatusCode.BadRequest);
            return Task.FromResult(JsonDocument.Parse("{\"job\":null}"));
        }, CancellationToken.None);
        Assert.Equal(new[] { 2, 1, 0 }, attempts);
    }
    [Theory]
    [InlineData(401)] [InlineData(403)] [InlineData(409)] [InlineData(500)]
    public async Task ScopeOrAuthenticationFailuresDoNotDowngrade(int status) {
        int attempts = 0;
        await Assert.ThrowsAsync<HttpRequestException>(() => NativeLedgerPlan.NextAutomaticJob((_, _) => {
            attempts++;
            throw new HttpRequestException("rejected", null, (System.Net.HttpStatusCode)status);
        }, CancellationToken.None));
        Assert.Equal(1, attempts);
    }
    [Theory]
    [InlineData(false)] [InlineData(true)]
    public async Task TwoCompleteReadsMustBeByteIdentical(bool changed) {
        int reads = 0;
        byte[]? result = await NativeLedgerPlan.ReadStableSnapshot(_ => {
            reads++;
            return Task.FromResult(new byte[] { 1, (byte)(changed && reads == 2 ? 3 : 2) });
        }, CancellationToken.None);
        Assert.Equal(2, reads);
        if (changed) Assert.Null(result); else Assert.Equal(new byte[] { 1, 2 }, result);
    }
}
