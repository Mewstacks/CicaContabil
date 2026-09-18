using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class AgentClient : IDisposable
{
    private readonly AgentConfig config;
    private readonly HttpClient http;

    internal AgentClient(AgentConfig config)
    {
        this.config = config;
        byte[] pfx = Convert.FromBase64String(config.CertificatePfxBase64);
        var certificate = new X509Certificate2(pfx, (string?)null,
            X509KeyStorageFlags.MachineKeySet | X509KeyStorageFlags.EphemeralKeySet);
        var handler = new HttpClientHandler();
        handler.ClientCertificates.Add(certificate);
        http = new HttpClient(handler) { BaseAddress = new Uri(config.ServerUrl.TrimEnd('/') + "/") };
        http.Timeout = TimeSpan.FromMinutes(10);
    }

    private HttpRequestMessage Signed(HttpMethod method, string path, byte[] body)
    {
        long timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        byte[] prefix = Encoding.UTF8.GetBytes(timestamp + ".");
        byte[] signed = new byte[prefix.Length + body.Length];
        Buffer.BlockCopy(prefix, 0, signed, 0, prefix.Length);
        Buffer.BlockCopy(body, 0, signed, prefix.Length, body.Length);
        string signature = Convert.ToHexString(HMACSHA256.HashData(
            Encoding.UTF8.GetBytes(config.SharedSecret), signed)).ToLowerInvariant();
        var request = new HttpRequestMessage(method, path);
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

    internal async Task<string?> GetWindowsArchiveRootAsync(CancellationToken token)
    {
        using JsonDocument result = await PostAsync("api/agent/v2/configuration/next", new { }, token);
        string? root = result.RootElement.GetProperty("windows_archive_root").GetString();
        return string.IsNullOrWhiteSpace(root) ? null : root;
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
            using var response = await http.SendAsync(Signed(HttpMethod.Post, requested, body),
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
