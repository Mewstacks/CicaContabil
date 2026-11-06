using System.Text.Json;
using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class AgentSyncScopeTests
{
    private static AgentSyncScope Valid() => new("dominio-pilot-v1",
        "bc276e62-27ac-4408-9ea0-339950b257e4", "1", "001:123",
        "2026-09-01", "2026-09-30", ["10", "11"], new string('a', 64));

    [Fact]
    public void ScopeRoundTripsTheServerContractAndIncludesTheWholeLastDay()
    {
        AgentSyncScope original = Valid();
        string json = JsonSerializer.Serialize(original);
        Assert.Contains("\"statement_ids\"", json);
        AgentSyncScope loaded = JsonSerializer.Deserialize<AgentSyncScope>(json)!;
        loaded.Validate();
        Assert.Equal(new DateTime(2026, 9, 1), loaded.Start);
        Assert.Equal(new DateTime(2026, 10, 1), loaded.EndExclusive);
        Assert.Equal(original.StatementIds, loaded.StatementIds);
    }

    [Theory]
    [InlineData("2026-09-02", "2026-09-30")]
    [InlineData("2026-09-01", "2026-09-29")]
    [InlineData("2026-09-01", "2026-10-31")]
    [InlineData("9999-01-01", "9999-01-31")]
    [InlineData("2026-02-01", "2026-02-30")]
    public void InvalidOrFuturePeriodsNeverEnableReads(string start, string end) =>
        Assert.Throws<InvalidDataException>(() => (Valid() with { PeriodStart = start, PeriodEnd = end }).Validate());

    [Fact]
    public void ScopeRequiresCompanyAccountRevisionAndReviewedStatements()
    {
        foreach (AgentSyncScope invalid in new[] {
            Valid() with { StatementIds = [] }, Valid() with { StatementIds = ["10", "10"] },
            Valid() with { StatementIds = ["10 OR 1=1"] }, Valid() with { CompanyCode = "" },
            Valid() with { AccountReference = "" }, Valid() with { FinancialAccountId = "bad" },
            Valid() with { Revision = "" }, Valid() with { Version = "unknown" },
        }) Assert.Throws<InvalidDataException>(invalid.Validate);
    }
}
