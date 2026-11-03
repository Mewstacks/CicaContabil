using System.Data.Odbc;
using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class LocalOdbcConnectionTests
{
    [Fact]
    public void Dsn_authentication_does_not_override_existing_identity()
    {
        var result = new OdbcConnectionStringBuilder(
            LocalOdbcConnection.Build("test", "unused-user", "unused-password", true));
        Assert.Equal("test", result.Dsn);
        Assert.False(result.ContainsKey("UID"));
        Assert.False(result.ContainsKey("PWD"));
        Assert.Equal("Dsn=test", result.ConnectionString);
    }

    [Fact]
    public void Explicit_credentials_are_preserved_without_connection_string_injection()
    {
        string connectionString = LocalOdbcConnection.Build(
            "test;UID=other", "user;DSN=other", "p;}x;UID=other", false);
        var result = new OdbcConnectionStringBuilder(connectionString);
        Assert.Equal("{test;UID=other}", result.Dsn);
        Assert.Contains("UID={user;DSN=other}", connectionString);
        Assert.Contains("PWD={p;}}x;UID=other}", connectionString);
        Assert.Equal(3, result.Count);
    }

    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    public void Empty_dsn_is_rejected_before_any_connection(string dsn)
    {
        Assert.Throws<InvalidDataException>(() => LocalOdbcConnection.Build(dsn, "", "", true));
    }

    [Fact]
    public void Explicit_mode_does_not_silently_switch_to_dsn_authentication()
    {
        string result = LocalOdbcConnection.Build("test", "", "", false);
        Assert.Contains(";UID=", result);
        Assert.Contains(";PWD=", result);
    }
}
