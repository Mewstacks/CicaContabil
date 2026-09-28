using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class SourceSystemProfileTests
{
    [Fact]
    public void Dominio_usa_sql_anywhere_de_64_bits()
    {
        SourceSystemProfile profile = SourceSystemProfiles.Get("dominio");

        Assert.False(profile.Uses32BitOdbcBridge);
        Assert.True(profile.RequiresSqlAnywhereDriver);
        Assert.Contains("SQL Anywhere", profile.DsnDriverMarkers);
    }

    [Fact]
    public void Siescon_usa_pervasive_pela_ponte_de_32_bits()
    {
        SourceSystemProfile profile = SourceSystemProfiles.Get("siescon");

        Assert.True(profile.Uses32BitOdbcBridge);
        Assert.False(profile.RequiresSqlAnywhereDriver);
        Assert.Contains("Pervasive", profile.DsnDriverMarkers);
        Assert.Contains("PSQL", profile.DsnDriverMarkers);
    }

    [Fact]
    public void Sistema_desconhecido_e_recusado()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => SourceSystemProfiles.Get("outro"));
    }
}
