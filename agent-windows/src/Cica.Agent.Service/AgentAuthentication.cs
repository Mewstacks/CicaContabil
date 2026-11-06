using System.Security.Cryptography.X509Certificates;

namespace Cica.Agent.Service;

internal static class AgentAuthentication
{
    internal const string Hmac = "hmac";
    internal const string Mtls = "mtls";

    internal static void Validate(string mode, string agentId, string secret, string pfx)
    {
        if (mode is not (Hmac or Mtls))
            throw new InvalidDataException("Modo de autenticação do agente desconhecido.");
        if (string.IsNullOrWhiteSpace(agentId) || string.IsNullOrWhiteSpace(secret)
            || (mode == Mtls && string.IsNullOrWhiteSpace(pfx)))
            throw new InvalidDataException("O pareamento do agente está incompleto. Execute o configurador novamente.");
    }

    internal static HttpClientHandler CreateHandler(string mode, string pfx)
    {
        if (mode is not (Hmac or Mtls))
            throw new InvalidDataException("Modo de autenticação do agente desconhecido.");
        // Keep the operating system's HTTPS certificate validation. Do not send
        // signed bodies or custom authentication headers to redirect targets.
        var handler = new HttpClientHandler { AllowAutoRedirect = false };
        if (mode == Mtls)
        {
            try
            {
                var certificate = new X509Certificate2(Convert.FromBase64String(pfx), (string?)null,
                    X509KeyStorageFlags.MachineKeySet | X509KeyStorageFlags.EphemeralKeySet);
                handler.ClientCertificates.Add(certificate);
            }
            catch { handler.Dispose(); throw; }
        }
        return handler;
    }
}
