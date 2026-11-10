using Cica.Agent.Service;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
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

    [WindowsFact]
    public void CertificateIdentityRetainsItsPrivateKeyAndNormalHttpsValidation()
    {
        using RSA key = RSA.Create(2048);
        var request = new CertificateRequest("CN=synthetic-agent", key,
            HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        using var certificate = request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1),
            DateTimeOffset.UtcNow.AddDays(1));
        string pfx = Convert.ToBase64String(certificate.Export(X509ContentType.Pfx));

        using var handler = AgentAuthentication.CreateHandler(AgentAuthentication.Mtls, pfx);
        using var loaded = Assert.Single(handler.ClientCertificates.OfType<X509Certificate2>());
        using RSA loadedKey = loaded.GetRSAPrivateKey()!;
        byte[] data = "synthetic-authentication-check"u8.ToArray();
        byte[] signature = loadedKey.SignData(data, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        Assert.True(key.VerifyData(data, signature, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1));
        Assert.Null(handler.ServerCertificateCustomValidationCallback);
        Assert.False(handler.AllowAutoRedirect);
    }

    [WindowsFact]
    public void InvalidPkcs12IdentityIsRejected()
    {
        string invalidPfx = Convert.ToBase64String("not-a-certificate"u8);
        Assert.Throws<CryptographicException>(() =>
            AgentAuthentication.CreateHandler(AgentAuthentication.Mtls, invalidPfx));
    }

    private sealed class WindowsFactAttribute : FactAttribute
    {
        public WindowsFactAttribute()
        {
            if (!OperatingSystem.IsWindows())
                Skip = "Requires the Windows ephemeral machine-key storage used by the agent.";
        }
    }
}
