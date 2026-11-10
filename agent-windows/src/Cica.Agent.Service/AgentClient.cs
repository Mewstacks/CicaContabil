using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class AgentClient : IDisposable
{
    private readonly AgentConfig config;
    private readonly HttpClient http;
    private string protocol;

    internal AgentClient(AgentConfig config)
    {
        this.config = config;
        protocol = config.SyncScope?.IsPortfolio is true ? AgentSyncScope.Protocol : AgentSyncScope.LegacyProtocol;
        AgentAuthentication.Validate(config.AuthenticationMode, config.AgentId,
            config.SharedSecret, config.CertificatePfxBase64);
        var handler = AgentAuthentication.CreateHandler(config.AuthenticationMode, config.CertificatePfxBase64);
        http = new HttpClient(handler) { BaseAddress = new Uri(config.ServerUrl.TrimEnd('/') + "/") };
        http.Timeout = TimeSpan.FromMinutes(10);
    }

    private HttpRequestMessage Signed(HttpMethod method, string path, byte[] body) =>
        Signed(method, new Uri(path, UriKind.Relative), body);

    // O download recebe a URL absoluta que o servidor devolveu, já conferida por
    // `TrustedDownloadUri`. Sem esta sobrecarga a chamada não compilava, e como o
    // agente Windows não é construído pela integração contínua isso passou.
    private HttpRequestMessage Signed(HttpMethod method, Uri uri, byte[] body)
    {
        long timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        byte[] prefix = Encoding.UTF8.GetBytes(timestamp + ".");
        byte[] signed = new byte[prefix.Length + body.Length];
        Buffer.BlockCopy(prefix, 0, signed, 0, prefix.Length);
        Buffer.BlockCopy(body, 0, signed, prefix.Length, body.Length);
        string signature = Convert.ToHexString(HMACSHA256.HashData(
            Encoding.UTF8.GetBytes(config.SharedSecret), signed)).ToLowerInvariant();
        var request = new HttpRequestMessage(method, uri);
        request.Headers.Add("X-Hub-Agent-Protocol", protocol);
        request.Headers.Add("X-Hub-Agent-ID", config.AgentId);
        request.Headers.Add("X-Hub-Agent-Timestamp", timestamp.ToString());
        request.Headers.Add("X-Hub-Agent-Signature", signature);
        request.Content = new ByteArrayContent(body);
        request.Content.Headers.ContentType = new("application/json");
        return request;
    }

    internal async Task<JsonDocument> PostAsync(string path, object payload, CancellationToken token)
    {
        byte[] body = JsonSerializer.SerializeToUtf8Bytes(payload);
        using var response = await http.SendAsync(Signed(HttpMethod.Post, path, body), token);
        if (response.StatusCode is System.Net.HttpStatusCode.Unauthorized or System.Net.HttpStatusCode.Forbidden)
            throw new AgentAuthorizationException();
        response.EnsureSuccessStatusCode();
        return await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(token), cancellationToken: token);
    }

    internal async Task<(string? ArchiveRoot, AgentSyncScope? Scope, bool CollectionEnabled)> GetConfigurationAsync(CancellationToken token)
    {
        using JsonDocument result = await PostAsync("api/agent/v2/configuration/next", new { }, token);
        string? root = result.RootElement.GetProperty("windows_archive_root").GetString();
        AgentSyncScope? scope = null;
        if (result.RootElement.TryGetProperty("sync_scope", out JsonElement value)
            && value.ValueKind == JsonValueKind.Object && value.EnumerateObject().Any())
        {
            scope = value.Deserialize<AgentSyncScope>()
                ?? throw new InvalidDataException("Recorte financeiro inválido.");
            scope.Validate();
            protocol = scope.IsPortfolio ? AgentSyncScope.Protocol : AgentSyncScope.LegacyProtocol;
        }
        return (string.IsNullOrWhiteSpace(root) ? null : root, scope,
            AgentCollectionGate.IsEnabled(result.RootElement));
    }

    internal async Task DownloadAsync(string absoluteUrl, string output, CancellationToken token)
    {
        Uri requested = TrustedDownloadUri(absoluteUrl);
        string partial = output + ".partial";
        Directory.CreateDirectory(Path.GetDirectoryName(output) ?? throw new InvalidDataException(
            "Destino de download inválido."));
        if (File.Exists(partial)) File.Delete(partial);
        byte[] body = "{}"u8.ToArray();
        try
        {
            using var response = await http.SendAsync(Signed(HttpMethod.Post, requested.PathAndQuery, body),
                HttpCompletionOption.ResponseHeadersRead, token);
            response.EnsureSuccessStatusCode();
            await using var source = await response.Content.ReadAsStreamAsync(token);
            await using (var destination = new FileStream(partial, FileMode.CreateNew, FileAccess.Write,
                FileShare.None, 64 * 1024, FileOptions.Asynchronous | FileOptions.SequentialScan))
            {
                await source.CopyToAsync(destination, token);
                await destination.FlushAsync(token);
            }
            File.Move(partial, output, true);
        }
        finally
        {
            if (File.Exists(partial)) File.Delete(partial);
        }
    }

    private Uri TrustedDownloadUri(string absoluteUrl)
    {
        if (!Uri.TryCreate(absoluteUrl, UriKind.Absolute, out Uri? requested))
            throw new InvalidDataException("A URL de download do servidor é inválida.");
        Uri baseUri = http.BaseAddress ?? throw new InvalidOperationException("Servidor não configurado.");
        if (!string.Equals(requested.Scheme, baseUri.Scheme, StringComparison.OrdinalIgnoreCase)
            || !string.Equals(requested.Host, baseUri.Host, StringComparison.OrdinalIgnoreCase)
            || requested.Port != baseUri.Port
            || !requested.AbsolutePath.StartsWith("/api/agent/v2/", StringComparison.Ordinal))
            throw new InvalidDataException("A URL de download não pertence ao servidor CICA configurado.");
        return requested;
    }

    public void Dispose() => http.Dispose();
}

internal sealed class AgentAuthorizationException : Exception
{
    internal AgentAuthorizationException()
        : base("O servidor CICA recusou a autorização deste agente.") { }
}
