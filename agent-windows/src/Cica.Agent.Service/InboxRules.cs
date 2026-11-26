namespace Cica.Agent.Service;

/// <summary>
/// Regras puras da pasta de entrada vigiada (sem I/O, testáveis): o que ignorar, quando um
/// arquivo está estável e quando desistir. Portado do orquestrador do HubFedrizzi
/// (TEMPORARIOS, _estavel, backoff 2^(n-1) min limitado a 60).
/// </summary>
internal static class InboxRules
{
    internal const string ProcessedFolder = "_processados";
    internal const string QuarantineFolder = "_quarentena";
    internal const int MaxAttempts = 5;

    private static readonly string[] TemporarySuffixes =
        [".tmp", ".part", ".partial", ".crdownload", ".download", ".cica-partial"];

    internal static bool IsIgnored(string fileName)
    {
        string name = fileName.ToLowerInvariant();
        return name.StartsWith("~$", StringComparison.Ordinal)
            || name.StartsWith('.')
            || name == "thumbs.db"
            || name == "desktop.ini"
            || TemporarySuffixes.Any(suffix => name.EndsWith(suffix, StringComparison.Ordinal));
    }

    /// <summary>
    /// O caminho vigiado vem do servidor, então só vale se ficar ESTRITAMENTE dentro da raiz
    /// de arquivos configurada localmente (mesma raiz de confiança do FileArchiveProcessor).
    /// </summary>
    internal static bool IsStrictlyUnder(string root, string candidate)
    {
        if (string.IsNullOrWhiteSpace(root) || string.IsNullOrWhiteSpace(candidate)
            || !Path.IsPathFullyQualified(candidate))
            return false;
        string fullRoot = Path.GetFullPath(root).TrimEnd(
            Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        string full = Path.GetFullPath(candidate).TrimEnd(
            Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        return full.StartsWith(fullRoot + Path.DirectorySeparatorChar,
            StringComparison.OrdinalIgnoreCase);
    }

    internal static bool IsReservedFolder(string folderName) =>
        string.Equals(folderName, ProcessedFolder, StringComparison.OrdinalIgnoreCase)
        || string.Equals(folderName, QuarantineFolder, StringComparison.OrdinalIgnoreCase);

    /// <summary>Minutos até a próxima tentativa depois da falha de número <paramref name="attempt"/>.</summary>
    internal static TimeSpan RetryDelay(int attempt) =>
        TimeSpan.FromMinutes(Math.Min(Math.Pow(2, Math.Max(attempt - 1, 0)), 60));
}

internal sealed record FileSnapshot(long Size, long ModifiedUtcTicks, DateTime ChangedAtUtc);

/// <summary>
/// Um arquivo só é considerado copiado por inteiro quando tamanho e data de modificação
/// ficam iguais por <c>stableSeconds</c> entre varreduras consecutivas.
/// </summary>
internal sealed class StabilityTracker
{
    private readonly Dictionary<string, FileSnapshot> seen = new(StringComparer.OrdinalIgnoreCase);

    internal bool IsStable(string path, long size, DateTime modifiedUtc, DateTime nowUtc, int stableSeconds)
    {
        long ticks = modifiedUtc.Ticks;
        if (!seen.TryGetValue(path, out FileSnapshot? previous)
            || previous.Size != size || previous.ModifiedUtcTicks != ticks)
        {
            seen[path] = new FileSnapshot(size, ticks, nowUtc);
            return false;
        }
        return (nowUtc - previous.ChangedAtUtc).TotalSeconds >= stableSeconds
            && (nowUtc - modifiedUtc).TotalSeconds >= stableSeconds;
    }

    /// <summary>Esquece o arquivo (movido ou removido) para um novo com o mesmo nome recomeçar.</summary>
    internal void Forget(string path) => seen.Remove(path);

    internal void Prune(IReadOnlySet<string> present)
    {
        foreach (string path in seen.Keys.Where(key => !present.Contains(key)).ToList())
            seen.Remove(path);
    }
}
