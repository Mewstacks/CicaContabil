using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class PortfolioCompanyTests
{
    private static AgentSyncScope Scope() => new("dominio-portfolio-v1", "", "", "",
        "2026-09-01", "2026-09-30", [], new string('a', 64),
        "bc276e62-27ac-4408-9ea0-339950b257e4", ["companies"], new() { ["A"] = true, ["I"] = false });

    [Fact]
    public void PortfolioValidatesWithoutPilotAccountAndPreservesInactiveSourceStatus()
    {
        AgentSyncScope scope = Scope();
        scope.Validate();
        Assert.True(scope.IsPortfolio);
        PortfolioCompany company = PortfolioCompany.FromSource(501, " Empresa ", "11222333000181", "I", scope);
        Assert.Equal("501", company.Code);
        Assert.Equal("I", company.Status);
        Assert.Equal("11.222.333/0001-81", company.Cnpj);
        Assert.Equal("Empresa", company.Name);
    }

    [Theory]
    [InlineData("1", "Nome", "", "UNKNOWN")]
    [InlineData("01", "Nome", "", "A")]
    [InlineData("0", "Nome", "", "A")]
    [InlineData("1", "", "", "A")]
    [InlineData("1", "Nome", "123", "A")]
    [InlineData("1", "Nome", "CPF 11222333000181", "A")]
    public void InvalidSourceNeverProducesSilentlyTruncatedOrActiveCompany(string code, string name, string document, string status) =>
        Assert.Throws<InvalidDataException>(() => PortfolioCompany.FromSource(code, name, document, status, Scope()));

    [Fact]
    public void UnsupportedSourcesMissingMapAndUnboundOfficeAreRefused()
    {
        foreach (AgentSyncScope scope in new[] {
            Scope() with { Datasets = ["companies", "ledger"] },
            Scope() with { OrganizationId = "" }, Scope() with { CompanyStatusMap = null },
            Scope() with { PeriodEnd = "9999-12-31" },
        }) Assert.Throws<InvalidDataException>(scope.Validate);
    }
}
