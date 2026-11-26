using System.Security.Cryptography;
using System.Text.Json;

namespace Cica.Agent.Service;

/// <summary>
/// Vigia da pasta de entrada do escritório: arquivos estáveis sobem para a quarentena da
/// Triagem; o que subiu vai para <c>_processados</c>, o que o servidor recusou (ou esgotou
/// as tentativas) vai para <c>_quarentena</c> com o motivo ao lado.
/// O estado vive em memória (um agente por máquina); reiniciar o serviço só reabre a espera
/// de estabilidade, e o servidor deduplica pelo hash.
/// </summary>
internal static class InboxWatcher
{
    private static readonly StabilityTracker Stability = new();
    private static readonly Dictionary<string, (int Attempts, DateTime NextUtc)> Retries =
        new(StringComparer.OrdinalIgnoreCase);
    private static FileSystemWatcher? watcher;
    private static string? watchedPath;
    private static int dirty;

    /// <summary>Um ciclo; nunca derruba o ciclo do agente (só autorização e parada propagam).</summary>
    internal static async Task RunOnceAsync(AgentConfig config, AgentClient client, CancellationToken token)
    {
        try
        {
            using JsonDocument configuration = await client.PostAsync(
                "api/agent/v2/configuration/next", new { }, token);
            if (!configuration.RootElement.TryGetProperty("inbox_watch", out JsonElement setting)
                || setting.ValueKind != JsonValueKind.Object
                || !setting.TryGetProperty("enabled", out JsonElement enabled)
                || enabled.ValueKind != JsonValueKind.True)
            {
                Stop();
                return;
            }
            string path = setting.GetProperty("path").GetString() ?? "";
            int stableSeconds = Math.Clamp(setting.GetProperty("stable_seconds").GetInt32(), 5, 3600);
            long maxBytes = setting.GetProperty("max_bytes").GetInt64();
            if (string.IsNullOrWhiteSpace(config.WindowsArchiveRoot)
                || !InboxRules.IsStrictlyUnder(config.WindowsArchiveRoot, path))
            {
                Stop();
                AgentRuntimeStatus.Write("configuration_error",
                    "A pasta de entrada precisa ficar dentro da pasta raiz de arquivos do agente.");
                return;
            }
            path = Path.GetFullPath(path);
            Directory.CreateDirectory(path);
            RejectReparsePoints(config.WindowsArchiveRoot, path);
            Directory.CreateDirectory(Path.Combine(path, InboxRules.ProcessedFolder));
            Directory.CreateDirectory(Path.Combine(path, InboxRules.QuarantineFolder));
            Watch(path);
            await SweepAsync(client, path, stableSeconds, maxBytes, token);
        }
        catch (Exception error) when (error is not OperationCanceledException
                                      and not AgentAuthorizationException)
        {
            // Pasta de rede fora do ar, disco cheio, servidor lento: tenta de novo no próximo ciclo.
            AgentRuntimeStatus.Write("temporary_error",
                "A pasta de entrada não pôde ser lida. O agente tentará novamente.");
        }
    }

    private static void RejectReparsePoints(string configuredRoot, string directory)
    {
        string root = Path.GetFullPath(configuredRoot).TrimEnd(
            Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        for (string? current = directory; current != null && current.Length >= root.Length;
             current = Path.GetDirectoryName(current))
        {
            if (Directory.Exists(current)
                && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("A pasta de entrada contém um redirecionamento não autorizado.");
            if (string.Equals(current, root, StringComparison.OrdinalIgnoreCase)) break;
        }
    }

    private static void Watch(string path)
    {
        if (watcher is not null && string.Equals(watchedPath, path, StringComparison.OrdinalIgnoreCase))
            return;
        Stop();
        watcher = new FileSystemWatcher(path)
        {
            NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite | NotifyFilters.Size,
            IncludeSubdirectories = false,
            EnableRaisingEvents = true,
        };
        // O evento só marca "mexeu": a decisão de estabilidade é sempre da varredura, que
        // também cobre o que o watcher perde (estouro de buffer, pasta de rede).
        watcher.Created += (_, _) => Interlocked.Exchange(ref dirty, 1);
        watcher.Changed += (_, _) => Interlocked.Exchange(ref dirty, 1);
        watcher.Renamed += (_, _) => Interlocked.Exchange(ref dirty, 1);
        watcher.Error += (_, _) => Interlocked.Exchange(ref dirty, 1);
        watchedPath = path;
    }

    private static void Stop()
    {
        watcher?.Dispose();
        watcher = null;
        watchedPath = null;
    }

    private static async Task SweepAsync(AgentClient client, string root, int stableSeconds,
        long maxBytes, CancellationToken token)
    {
        Interlocked.Exchange(ref dirty, 0);
        var present = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (string file in Directory.EnumerateFiles(root))
        {
            token.ThrowIfCancellationRequested();
            string name = Path.GetFileName(file);
            if (InboxRules.IsIgnored(name)) continue;
            FileInfo info = new(file);
            if ((info.Attributes & FileAttributes.ReparsePoint) != 0) continue;
            present.Add(file);
            if (Retries.TryGetValue(file, out var retry) && retry.NextUtc > DateTime.UtcNow) continue;
            if (!Stability.IsStable(file, info.Length, info.LastWriteTimeUtc, DateTime.UtcNow, stableSeconds))
                continue;
            if (info.Length == 0) continue;
            if (info.Length > maxBytes)
            {
                Quarantine(root, file, "Arquivo acima do limite da pasta de entrada.");
                continue;
            }
            await SendAsync(client, root, file, token);
        }
        Stability.Prune(present);
        foreach (string gone in Retries.Keys.Where(key => !present.Contains(key)).ToList())
            Retries.Remove(gone);
    }

    private static async Task SendAsync(AgentClient client, string root, string file, CancellationToken token)
    {
        byte[] content;
        try
        {
            // FileShare.Read recusa o arquivo enquanto o programa que o grava ainda o mantém aberto.
            await using var stream = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.Read);
            using var memory = new MemoryStream();
            await stream.CopyToAsync(memory, token);
            content = memory.ToArray();
        }
        catch (IOException)
        {
            Stability.Forget(file);
            return;
        }
        string sha256 = Convert.ToHexString(SHA256.HashData(content)).ToLowerInvariant();
        (int status, string detail) = await client.UploadInboxAsync(
            Path.GetFileName(file), sha256, content, token);
        if (status is >= 200 and < 300)
        {
            Retries.Remove(file);
            Stability.Forget(file);
            Move(root, file, InboxRules.ProcessedFolder, DateTime.Now.ToString("yyyy-MM-dd"));
            return;
        }
        if (status == 422)
        {
            Quarantine(root, file, detail);
            return;
        }
        int attempts = Retries.TryGetValue(file, out var current) ? current.Attempts + 1 : 1;
        if (attempts >= InboxRules.MaxAttempts)
        {
            Quarantine(root, file, $"Falha após {attempts} tentativas (HTTP {status}).");
            return;
        }
        Retries[file] = (attempts, DateTime.UtcNow + InboxRules.RetryDelay(attempts));
    }

    private static void Quarantine(string root, string file, string reason)
    {
        string destination = Move(root, file, InboxRules.QuarantineFolder, null);
        File.WriteAllText(destination + ".motivo.txt", reason);
        Retries.Remove(file);
        Stability.Forget(file);
    }

    private static string Move(string root, string file, string folder, string? subfolder)
    {
        string directory = subfolder is null
            ? Path.Combine(root, folder) : Path.Combine(root, folder, subfolder);
        Directory.CreateDirectory(directory);
        string name = Path.GetFileName(file);
        string destination = Path.Combine(directory, name);
        for (int copy = 2; File.Exists(destination); copy++)
            destination = Path.Combine(directory,
                $"{Path.GetFileNameWithoutExtension(name)} ({copy}){Path.GetExtension(name)}");
        File.Move(file, destination, false);
        return destination;
    }
}
