using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Cica.Agent.Service;

/// O catálogo de consultas do ERP, incorporado no binário e fixado por hash.
///
/// Portado do conector do Lucrums por D-108 e D-111. É o que o agente da CICA não
/// tinha: até aqui o SQL vivia solto no código-fonte, e nada impedia que a consulta
/// executada na máquina do escritório fosse diferente da que a nuvem espera.
///
/// O manifesto e os arquivos SQL vêm de `contracts/datasets/`, os mesmos que o
/// servidor lê. São conferidos na primeira leitura, e uma divergência derruba o
/// serviço em vez de falhar calado no meio de um ciclo noturno: hash de SQL que
/// não confere, manifesto de outra versão, consulta que não começa em SELECT,
/// ponto-e-vírgula no meio ou contagem de parâmetros diferente da declarada.
///
/// Quem decide o sistema de origem é a configuração do conector, nunca o comando
/// que a nuvem manda — um conector apontado para o Domínio não executa consulta do
/// Siescon, mesmo que peçam.
internal sealed record DatasetParameter(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("odbcType")] string OdbcType);

internal sealed record DatasetColumn(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("type")] string Type);

internal sealed record DatasetDefinition(
    string Code,
    string SourceSystem,
    int SchemaVersion,
    string QuerySha256,
    string Sql,
    bool Validated,
    IReadOnlyList<DatasetParameter> Parameters,
    IReadOnlyList<DatasetColumn> Columns,
    IReadOnlyList<string> ContextColumns,
    IReadOnlyList<string> IdentityColumns,
    IReadOnlyList<string> AllowedRunKinds,
    int MaxRowsPerRun)
{
    internal string[] ResultColumns => Columns
        .Select(column => column.Name)
        .Where(name => !ContextColumns.Contains(name, StringComparer.OrdinalIgnoreCase))
        .ToArray();
}

internal static class DatasetResultContract
{
    internal static void ValidateColumns(
        IReadOnlyList<string> expected, IReadOnlyList<string> actual)
    {
        if (expected.Count != actual.Count
            || expected.Distinct(StringComparer.OrdinalIgnoreCase).Count() != expected.Count
            || actual.Distinct(StringComparer.OrdinalIgnoreCase).Count() != actual.Count
            || expected.Where((column, index) =>
                !string.Equals(column, actual[index], StringComparison.OrdinalIgnoreCase)).Any())
            throw new InvalidOperationException(
                "As colunas retornadas pelo ERP divergem do contrato do dataset.");
    }
}

internal static class DatasetCatalog
{
    private const string ResourcePrefix = "Cica.Datasets.";
    private static readonly Lazy<CatalogState> State = new(LoadAndVerify);

    internal static string ManifestSha256 => State.Value.ManifestSha256;

    internal static IReadOnlyCollection<DatasetDefinition> All =>
        State.Value.Definitions.Values.ToArray();

    /// Falha cedo, na subida do serviço, em vez de na primeira consulta.
    internal static void SelfVerify() => _ = State.Value;

    internal static string Key(string sourceSystem, string code) => sourceSystem + ":" + code;

    internal static DatasetDefinition GetForRun(string sourceSystem, string code, string runKind)
    {
        if (!State.Value.Definitions.TryGetValue(
                Key(sourceSystem, code), out DatasetDefinition? value))
            throw new InvalidOperationException("Consulta desconhecida no catálogo incorporado.");
        if (!value.Validated)
            throw new InvalidOperationException("Consulta ainda não validada para despacho.");
        if (!value.AllowedRunKinds.Contains(runKind, StringComparer.Ordinal))
            throw new InvalidOperationException("Modo de execução não permitido pelo catálogo.");
        return value;
    }

    private static CatalogState LoadAndVerify()
    {
        Assembly assembly = typeof(DatasetCatalog).Assembly;
        byte[] manifestBytes = ReadResource(assembly, ResourcePrefix + "manifest.json");
        Manifest manifest = JsonSerializer.Deserialize<Manifest>(manifestBytes)
            ?? throw new InvalidOperationException("Manifesto de consultas vazio.");
        if (manifest.ManifestVersion != 2 || manifest.Datasets.Length == 0)
            throw new InvalidOperationException("Versão ou conteúdo do manifesto inválido.");

        Dictionary<string, DatasetDefinition> definitions = new(StringComparer.Ordinal);
        foreach (ManifestDataset item in manifest.Datasets)
        {
            if (Path.GetFileName(item.SqlFile) != item.SqlFile)
                throw new InvalidOperationException("Nome de recurso SQL inválido.");
            // O sistema de origem entra na chave do catálogo, então precisa ser um
            // identificador simples — nada de ':' ou vazio partindo a chave em dois.
            if (string.IsNullOrEmpty(item.SourceSystem)
                || !item.SourceSystem.All(character =>
                    (character >= 'a' && character <= 'z')
                    || (character >= '0' && character <= '9')
                    || character == '_'))
                throw new InvalidOperationException(
                    $"Sistema de origem inválido para {item.Code}.");

            byte[] sqlBytes = ReadResource(assembly, ResourcePrefix + item.SqlFile);
            string digest = Convert.ToHexString(SHA256.HashData(sqlBytes)).ToLowerInvariant();
            if (!CryptographicOperations.FixedTimeEquals(
                    Convert.FromHexString(digest), Convert.FromHexString(item.QuerySha256)))
                throw new InvalidOperationException($"Hash SQL divergente para {item.Code}.");

            string sql = Encoding.UTF8.GetString(sqlBytes);
            string trimmed = sql.TrimStart();
            if (!(trimmed.StartsWith("SELECT", StringComparison.OrdinalIgnoreCase)
                    || trimmed.StartsWith("WITH", StringComparison.OrdinalIgnoreCase))
                || sql.Contains(';')
                || sql.Count(character => character == '?') != item.Parameters.Length)
                throw new InvalidOperationException($"Contrato SQL inválido para {item.Code}.");

            DatasetDefinition definition = new(
                item.Code,
                item.SourceSystem,
                item.SchemaVersion,
                item.QuerySha256,
                sql,
                item.Validated,
                item.Parameters,
                item.Columns,
                item.ContextColumns ?? [],
                item.IdentityColumns,
                item.AllowedRunKinds,
                item.MaxRowsPerRun);
            if (!definitions.TryAdd(Key(item.SourceSystem, item.Code), definition))
                throw new InvalidOperationException(
                    $"Consulta duplicada: {Key(item.SourceSystem, item.Code)}.");
        }

        return new CatalogState(
            definitions, Convert.ToHexString(SHA256.HashData(manifestBytes)).ToLowerInvariant());
    }

    private static byte[] ReadResource(Assembly assembly, string name)
    {
        using Stream stream = assembly.GetManifestResourceStream(name)
            ?? throw new InvalidOperationException($"Recurso incorporado ausente: {name}.");
        using MemoryStream output = new();
        stream.CopyTo(output);
        return output.ToArray();
    }

    private sealed record CatalogState(
        IReadOnlyDictionary<string, DatasetDefinition> Definitions,
        string ManifestSha256);

    private sealed record Manifest(
        [property: JsonPropertyName("manifestVersion")] int ManifestVersion,
        [property: JsonPropertyName("datasets")] ManifestDataset[] Datasets);

    private sealed record ManifestDataset(
        [property: JsonPropertyName("code")] string Code,
        [property: JsonPropertyName("sourceSystem")] string SourceSystem,
        [property: JsonPropertyName("schemaVersion")] int SchemaVersion,
        [property: JsonPropertyName("sqlFile")] string SqlFile,
        [property: JsonPropertyName("querySha256")] string QuerySha256,
        [property: JsonPropertyName("validated")] bool Validated,
        [property: JsonPropertyName("parameters")] DatasetParameter[] Parameters,
        [property: JsonPropertyName("columns")] DatasetColumn[] Columns,
        [property: JsonPropertyName("contextColumns")] string[]? ContextColumns,
        [property: JsonPropertyName("identityColumns")] string[] IdentityColumns,
        [property: JsonPropertyName("allowedRunKinds")] string[] AllowedRunKinds,
        [property: JsonPropertyName("maxRowsPerRun")] int MaxRowsPerRun);
}
