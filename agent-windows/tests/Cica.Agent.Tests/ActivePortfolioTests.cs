using System.Text.Json;
using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class ActivePortfolioTests
{
    // Synthetic codes; this does not approve the meaning of M in the client's ERP.
    private static AgentSyncScope Scope() => new("dominio-portfolio-v2", "", "", "",
        "2026-09-01", "2026-09-30", [], new string('a', 64),
        "bc276e62-27ac-4408-9ea0-339950b257e4", ["companies"],
        new() { ["Z"] = true, ["I"] = false, ["A"] = true }, "active_only");

    [Fact]
    public void SelectionRoundTripsAndNegotiatesANewProtocol()
    {
        var loaded = JsonSerializer.Deserialize<AgentSyncScope>(JsonSerializer.Serialize(Scope()))!;
        loaded.Validate();
        Assert.True(loaded.IsActiveOnly);
        Assert.Equal("scoped-v3", loaded.TransportProtocol);
        var legacy = loaded with { Version = "dominio-portfolio-v1", CompanySelection = null };
        legacy.Validate();
        Assert.Equal("scoped-v2", legacy.TransportProtocol);
    }

    [Fact]
    public void CountAndPageHaveTheSameBoundStatusSelection()
    {
        var plan = PortfolioReadPlan.FromScope(Scope());
        Assert.Equal(new[] { "A", "Z" }, plan.Statuses);
        Assert.Equal("SELECT COUNT(*) FROM bethadba.geempre WHERE stat_emp IN (?,?)", plan.CountSql);
        Assert.Equal("SELECT TOP 500 codi_emp, nome_emp, cgce_emp, stat_emp FROM bethadba.geempre WHERE stat_emp IN (?,?) AND codi_emp > ? ORDER BY codi_emp", plan.PageSql);
        Assert.DoesNotContain("'A'", plan.PageSql);
        Assert.DoesNotContain("'Z'", plan.CountSql);
    }

    [Fact]
    public void SingleStatusAndLegacyQueriesKeepStableNumericPagination()
    {
        var scope = Scope() with { CompanyStatusMap = new() { ["A"] = true, ["I"] = false } };
        var selected = PortfolioReadPlan.FromScope(scope);
        Assert.EndsWith("stat_emp IN (?)", selected.CountSql);
        Assert.EndsWith("stat_emp IN (?) AND codi_emp > ? ORDER BY codi_emp", selected.PageSql);
        var legacy = PortfolioReadPlan.FromScope(scope with { Version = "dominio-portfolio-v1", CompanySelection = null });
        Assert.Empty(legacy.Statuses);
        Assert.Equal("SELECT COUNT(*) FROM bethadba.geempre", legacy.CountSql);
        Assert.DoesNotContain("stat_emp IN", legacy.PageSql);
    }

    [Fact]
    public void ASourceRowOutsideTheSelectedStatesIsNotTransmitted()
    {
        Assert.Throws<InvalidDataException>(() => PortfolioCompany.FromSource(1, "Synthetic", "", "I", Scope()));
        Assert.Equal("A", PortfolioCompany.FromSource(2, "Synthetic", "", "A", Scope()).Status);
    }

    [Fact]
    public void InvalidOrEmptySelectionsCannotEnableReads()
    {
        foreach (var scope in new[] {
            Scope() with { CompanySelection = null }, Scope() with { CompanySelection = "all" },
            Scope() with { CompanyStatusMap = new() { ["I"] = false } },
            Scope() with { CompanyStatusMap = new() { ["A' OR 1=1"] = true } },
            Scope() with { Version = "dominio-portfolio-v1" },
        }) Assert.Throws<InvalidDataException>(() => PortfolioReadPlan.FromScope(scope));
    }
}
