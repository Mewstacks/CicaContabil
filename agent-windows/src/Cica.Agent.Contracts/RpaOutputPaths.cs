namespace Cica.Agent.Service;

/// Resolve um arquivo devolvido pelo executor só se ele estiver dentro da pasta de saída aprovada.
internal static class RpaOutputPaths
{
    internal static string Resolve(string root, string candidate)
    {
        if (root.Length == 0 || !Path.IsPathFullyQualified(root))
            throw new InvalidDataException("Pasta de saída do RPA não configurada.");
        if (candidate.Length == 0 || !Path.IsPathFullyQualified(candidate))
            throw new InvalidDataException("Caminho de arquivo inválido.");
        string full = Path.GetFullPath(candidate);
        string rootFull = Path.TrimEndingDirectorySeparator(Path.GetFullPath(root)) + Path.DirectorySeparatorChar;
        if (!full.StartsWith(rootFull, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Arquivo fora da pasta de saída aprovada.");
        // Nenhum trecho do caminho pode ser ponto de reanálise (junção, link simbólico).
        string current = full;
        while (current.Length > rootFull.Length - 1)
        {
            FileSystemInfo item = Directory.Exists(current) ? new DirectoryInfo(current) : new FileInfo(current);
            if (item.Exists && item.Attributes.HasFlag(FileAttributes.ReparsePoint))
                throw new InvalidDataException("Caminho com ponto de reanálise recusado.");
            current = Path.GetDirectoryName(current) ?? "";
            if (current.Length == 0) break;
        }
        if (!File.Exists(full)) throw new FileNotFoundException("Arquivo do executor não existe.");
        return full;
    }
}
