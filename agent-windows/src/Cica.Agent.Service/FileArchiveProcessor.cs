using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class FileArchiveProcessor(AgentConfig config, AgentClient client)
{
    internal async Task RunOnce(CancellationToken token)
    {
        if (string.IsNullOrWhiteSpace(config.WindowsArchiveRoot)) return;
        using JsonDocument result = await client.PostAsync("api/agent/v2/files/next", new { }, token);
        JsonElement value = result.RootElement.GetProperty("job");
        if (value.ValueKind == JsonValueKind.Null) return;
        string id = value.GetProperty("id").GetString()!;
        string relativePath = value.GetProperty("relative_path").GetString()!;
        string expectedHash = value.GetProperty("sha256").GetString()!;
        long expectedSize = value.GetProperty("byte_size").GetInt64();
        string expectedRootHash = value.GetProperty("root_sha256").GetString()!;
        string downloadUrl = value.GetProperty("download_url").GetString()!;
        try
        {
            string normalizedRoot = Path.GetFullPath(config.WindowsArchiveRoot!)
                .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
                .ToLowerInvariant();
            string rootHash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(normalizedRoot)))
                .ToLowerInvariant();
            if (!CryptographicOperations.FixedTimeEquals(
                    Encoding.ASCII.GetBytes(rootHash), Encoding.ASCII.GetBytes(expectedRootHash)))
                throw new InvalidDataException(
                    "A pasta configurada no agente difere da pasta escolhida na Triagem.");
            string destination = SafeDestination(config.WindowsArchiveRoot!, relativePath);
            Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
            RejectReparsePoints(config.WindowsArchiveRoot!, Path.GetDirectoryName(destination)!);
            if (File.Exists(destination))
            {
                (string hash, long size) = await Inspect(destination, token);
                if (hash != expectedHash || size != expectedSize)
                    throw new IOException("Já existe outro arquivo no destino aprovado.");
                await Complete(id, true, relativePath, hash, size, "Arquivo já estava íntegro.", token);
                return;
            }
            string temporary = destination + ".cica-" + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                await client.DownloadAsync(downloadUrl, temporary, token);
                (string hash, long size) = await Inspect(temporary, token);
                if (hash != expectedHash || size != expectedSize)
                    throw new InvalidDataException("O download não corresponde ao arquivo aprovado.");
                File.Move(temporary, destination, false);
                await Complete(id, true, relativePath, hash, size, "Arquivo gravado e conferido.", token);
            }
            finally
            {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }
        catch (Exception error) when (error is not OperationCanceledException)
        {
            string detail = $"{error.GetType().Name}: {error.Message}";
            if (detail.Length > 500) detail = detail[..500];
            await Complete(id, false, relativePath, "", -1, detail, token);
        }
    }

    private async Task Complete(string id, bool success, string relativePath, string hash,
        long size, string detail, CancellationToken token) => await client.PostAsync(
            $"api/agent/v2/files/{id}/complete",
            new { success, relative_path = relativePath, sha256 = hash, byte_size = size, detail }, token);

    private static string SafeDestination(string configuredRoot, string relativePath)
    {
        if (Path.IsPathRooted(relativePath)) throw new InvalidDataException("Destino absoluto recusado.");
        string root = Path.GetFullPath(configuredRoot).TrimEnd(Path.DirectorySeparatorChar,
            Path.AltDirectorySeparatorChar);
        string destination = Path.GetFullPath(Path.Combine(root, relativePath));
        if (!destination.StartsWith(root + Path.DirectorySeparatorChar,
                StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Destino fora da pasta autorizada.");
        return destination;
    }

    private static void RejectReparsePoints(string configuredRoot, string destinationDirectory)
    {
        string root = Path.GetFullPath(configuredRoot).TrimEnd(Path.DirectorySeparatorChar,
            Path.AltDirectorySeparatorChar);
        for (string? current = destinationDirectory; current != null && current.Length >= root.Length;
             current = Path.GetDirectoryName(current))
        {
            if (Directory.Exists(current)
                && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("A pasta contém um redirecionamento não autorizado.");
            if (string.Equals(current, root, StringComparison.OrdinalIgnoreCase)) break;
        }
    }

    private static async Task<(string Hash, long Size)> Inspect(string path, CancellationToken token)
    {
        await using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read,
            64 * 1024, FileOptions.Asynchronous | FileOptions.SequentialScan);
        byte[] digest = await SHA256.HashDataAsync(stream, token);
        return (Convert.ToHexString(digest).ToLowerInvariant(), stream.Length);
    }
}
