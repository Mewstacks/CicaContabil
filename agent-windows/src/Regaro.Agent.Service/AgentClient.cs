using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;

namespace Regaro.Agent.Service;

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
        response.EnsureSuccessStatusCode();
        return await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(token), cancellationToken: token);
    }

    internal async Task DownloadAsync(string absoluteUrl, string output, CancellationToken token)
    {
        byte[] body = "{}"u8.ToArray();
        using var response = await http.SendAsync(Signed(HttpMethod.Post, absoluteUrl, body),
            HttpCompletionOption.ResponseHeadersRead, token);
        response.EnsureSuccessStatusCode();
        await using var source = await response.Content.ReadAsStreamAsync(token);
        await using var destination = File.Create(output);
        await source.CopyToAsync(destination, token);
    }

    public void Dispose() => http.Dispose();
}
