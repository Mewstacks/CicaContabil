using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class AgentAuthenticationTests
{
    [Fact]
    public void ExplicitHmacNeedsNoCertificateAndKeepsNormalHttpsValidation()
    {
        AgentAuthentication.Validate(AgentAuthentication.Hmac, "synthetic-agent", "synthetic-secret", "");
        using var handler = AgentAuthentication.CreateHandler(AgentAuthentication.Hmac, "");
        Assert.Empty(handler.ClientCertificates);
        Assert.Null(handler.ServerCertificateCustomValidationCallback);
        Assert.False(handler.AllowAutoRedirect);
    }

    [Theory]
    [InlineData("unknown", "agent", "secret", "")]
    [InlineData("hmac", "", "secret", "")]
    [InlineData("hmac", "agent", "", "")]
    [InlineData("mtls", "agent", "secret", "")]
    public void InvalidOrIncompleteIdentityIsNeverAccepted(string mode, string id, string secret, string pfx) =>
        Assert.Throws<InvalidDataException>(() => AgentAuthentication.Validate(mode, id, secret, pfx));

    [Fact]
    public void LegacyCertificateModeNeverFallsBackWhenItsIdentityCannotBeLoaded()
    {
        Assert.Throws<FormatException>(() => AgentAuthentication.CreateHandler(AgentAuthentication.Mtls, "not-a-pfx"));
        Assert.Throws<InvalidDataException>(() => AgentAuthentication.CreateHandler("unknown", ""));
    }
}
