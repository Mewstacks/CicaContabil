using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class Worker(ILogger<Worker> logger) : BackgroundService
{
    private static readonly string AgentVersion = typeof(Worker).Assembly.GetName().Version?.ToString(3)
        ?? "0.0.0";

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        TimeSpan retryDelay = TimeSpan.FromMinutes(1);
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                if (!File.Exists(AgentConfig.FilePath))
                {
                    logger.LogInformation("CICA Agent is awaiting local configuration");
                    AgentRuntimeStatus.Write("awaiting_configuration",
                        "Aguardando configuração local no configurador CICA.");
                    await Task.Delay(TimeSpan.FromSeconds(15), stoppingToken);
                    continue;
                }
                AgentConfig config = AgentConfig.Load();
                config.Validate();
                AgentRuntimeStatus.Write("synchronizing", "Sincronização em andamento.");
                using var client = new AgentClient(config);
                using JsonDocument heartbeat = await client.PostAsync("api/agent/v2/heartbeat",
                    new { version = AgentVersion }, stoppingToken);
                string? archiveRoot = await client.GetWindowsArchiveRootAsync(stoppingToken);
                if (!string.Equals(archiveRoot, config.WindowsArchiveRoot, StringComparison.OrdinalIgnoreCase))
                {
                    config = config with { WindowsArchiveRoot = archiveRoot };
                    config.Validate();
                    config.Save();
                    AgentRuntimeStatus.Write("synchronizing", "Configuração de destino atualizada pela CICA.");
                }
                await new DominioLocalProcessor(config, client).RunOnce(stoppingToken);
                await new BackupProcessor(config, client).RunOnce(stoppingToken);
                await new FileArchiveProcessor(config, client).RunOnce(stoppingToken);
                await RenewCertificateIfNeeded(config, client, stoppingToken);
                string serverVersion = heartbeat.RootElement.GetProperty("update").GetString() ?? "";
                if (IsNewerVersion(serverVersion, AgentVersion))
                    AgentRuntimeStatus.Write("update_available",
                        $"Atualização {serverVersion} disponível. Baixe e execute o MSI pelo console CICA.");
                else
                    AgentRuntimeStatus.Write("ready", "Último ciclo concluído com sucesso.");
                retryDelay = TimeSpan.FromMinutes(1);
            }
            catch (Exception error) when (error is not OperationCanceledException)
            {
                logger.LogWarning("CICA agent cycle failed with code {Code}", error.GetType().Name);
                string state = error switch
                {
                    AgentAuthorizationException => "authorization_error",
                    InvalidDataException or CryptographicException => "configuration_error",
                    _ => "temporary_error",
                };
                AgentRuntimeStatus.Write(state, Detail(error));
                await Task.Delay(retryDelay, stoppingToken);
                retryDelay = TimeSpan.FromMinutes(Math.Min(retryDelay.TotalMinutes * 2, 5));
                continue;
            }
            await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
        }
    }

    private static string Detail(Exception error) => error switch
    {
        AgentAuthorizationException => "Este agente foi recusado pela CICA. Verifique se foi revogado ou se o pareamento precisa ser refeito.",
        InvalidDataException => error.Message,
        CryptographicException => "A configuração local não pôde ser aberta neste computador. Execute o configurador novamente.",
        HttpRequestException => "Não foi possível alcançar o servidor CICA. O agente tentará novamente.",
        TaskCanceledException => "A comunicação com a CICA excedeu o tempo limite. O agente tentará novamente.",
        _ => "O ciclo não foi concluído. Consulte o Visualizador de Eventos e o arquivo de diagnóstico.",
    };

    private static async Task<AgentConfig> RenewCertificateIfNeeded(
        AgentConfig config, AgentClient client, CancellationToken token)
    {
        byte[] existingPfx = Convert.FromBase64String(config.CertificatePfxBase64);
        using var identity = new X509Certificate2(existingPfx, (string?)null,
            X509KeyStorageFlags.MachineKeySet | X509KeyStorageFlags.EphemeralKeySet);
        if (identity.NotAfter.ToUniversalTime() > DateTime.UtcNow.AddDays(30)) return config;
        using RSA key = identity.GetRSAPrivateKey()
            ?? throw new CryptographicException("O certificado do agente não possui chave RSA privada.");
        var request = new CertificateRequest(identity.SubjectName, key, HashAlgorithmName.SHA256,
            RSASignaturePadding.Pkcs1);
        string csr = PemEncoding.WriteString("CERTIFICATE REQUEST", request.CreateSigningRequest());
        using JsonDocument result = await client.PostAsync("api/agent/v2/certificate/renew", new { csr }, token);
        string certificatePem = result.RootElement.GetProperty("certificate").GetString()
            ?? throw new InvalidDataException("A CICA não retornou o certificado renovado.");
        using X509Certificate2 renewedPublic = X509Certificate2.CreateFromPem(certificatePem);
        using X509Certificate2 renewedIdentity = renewedPublic.CopyWithPrivateKey(key);
        AgentConfig renewed = config with
        {
            CertificatePfxBase64 = Convert.ToBase64String(renewedIdentity.Export(X509ContentType.Pkcs12)),
        };
        renewed.Save();
        AgentRuntimeStatus.Write("synchronizing", "Certificado do agente renovado localmente.");
        return renewed;
    }

    private static bool IsNewerVersion(string candidate, string installed) =>
        Version.TryParse(candidate, out Version? available)
        && Version.TryParse(installed, out Version? current)
        && available > current;
}
