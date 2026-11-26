using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Cica.Agent.Service;

// Cria pastas de clientes e inventaria a raiz (somente leitura). Nunca move nem apaga arquivo:
// a reorganização destrutiva com backup não faz parte deste processador.
internal sealed class FolderJobProcessor(AgentConfig config, AgentClient client)
{
    private const int MaxEntries = 200;
    private const int MaxCount = 100_000;

    internal async Task RunOnce(CancellationToken token)
    {
        if (string.IsNullOrWhiteSpace(config.WindowsArchiveRoot)) return;
        using JsonDocument result = await client.PostAsync("api/agent/v2/folders/next", new { }, token);
        JsonElement value = result.RootElement.GetProperty("job");
        if (value.ValueKind == JsonValueKind.Null) return;
        string id = value.GetProperty("id").GetString()!;
        string kind = value.GetProperty("kind").GetString()!;
        string expectedRootHash = value.GetProperty("root_sha256").GetString()!;
        try
        {
            string root = Path.GetFullPath(config.WindowsArchiveRoot!)
                .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            string rootHash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(root.ToLowerInvariant())))
                .ToLowerInvariant();
            if (!CryptographicOperations.FixedTimeEquals(
                    Encoding.ASCII.GetBytes(rootHash), Encoding.ASCII.GetBytes(expectedRootHash)))
                throw new InvalidDataException(
                    "A pasta configurada no agente difere da pasta escolhida na Triagem.");
            if (kind == "provision")
            {
                int created = 0;
                foreach (JsonElement entry in value.GetProperty("paths").EnumerateArray())
                {
                    string directory = SafeDirectory(root, entry.GetString()!);
                    if (!Directory.Exists(directory))
                    {
                        RejectReparsePoints(root, Path.GetDirectoryName(directory)!);
                        Directory.CreateDirectory(directory);
                        created++;
                    }
                    else RejectReparsePoints(root, directory);
                }
                await Complete(id, true, $"{created} pastas criadas.", [], token);
            }
            else if (kind == "inventory")
            {
                await Complete(id, true, "Inventário concluído.", Inventory(root), token);
            }
            else throw new InvalidDataException("Tipo de trabalho de pastas desconhecido.");
        }
        catch (Exception error) when (error is not OperationCanceledException)
        {
            string detail = $"{error.GetType().Name}: {error.Message}";
            if (detail.Length > 500) detail = detail[..500];
            await Complete(id, false, detail, [], token);
        }
    }

    private async Task Complete(string id, bool success, string detail, object[] entries,
        CancellationToken token) => await client.PostAsync(
            $"api/agent/v2/folders/{id}/complete", new { success, detail, entries }, token);

    private static object[] Inventory(string root)
    {
        var entries = new List<object>();
        foreach (string directory in Directory.EnumerateDirectories(root).Take(MaxEntries))
        {
            if ((File.GetAttributes(directory) & FileAttributes.ReparsePoint) != 0) continue;
            int dirs = 0, files = 0;
            var options = new EnumerationOptions
            {
                RecurseSubdirectories = true,
                IgnoreInaccessible = true,
                AttributesToSkip = FileAttributes.ReparsePoint,
            };
            foreach (string _ in Directory.EnumerateDirectories(directory, "*", options))
                if (++dirs >= MaxCount) break;
            foreach (string _ in Directory.EnumerateFiles(directory, "*", options))
                if (++files >= MaxCount) break;
            entries.Add(new { path = Path.GetFileName(directory), dirs, files });
        }
        return [.. entries];
    }

    private static string SafeDirectory(string root, string relativePath)
    {
        if (Path.IsPathRooted(relativePath)) throw new InvalidDataException("Destino absoluto recusado.");
        string destination = Path.GetFullPath(Path.Combine(root, relativePath));
        if (!destination.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Destino fora da pasta autorizada.");
        return destination;
    }

    private static void RejectReparsePoints(string root, string directory)
    {
        for (string? current = directory; current != null && current.Length >= root.Length;
             current = Path.GetDirectoryName(current))
        {
            if (Directory.Exists(current)
                && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("A pasta contém um redirecionamento não autorizado.");
            if (string.Equals(current, root, StringComparison.OrdinalIgnoreCase)) break;
        }
    }
}
