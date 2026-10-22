using System.Net;
using System.Text.Json;

namespace Cica.Agent.Service;

/// Manda a execução parar com um código do protocolo. Nunca carrega dado de linha.
internal sealed class JobFailure(string code, string detail) : Exception(detail)
{
    internal string Code { get; } = code;
}

/// A leitura do ERP falhou. A mensagem já vem saneada por quem lê: sem string de
/// conexão, credencial nem valor de linha.
internal sealed class DatasetReadException(string detail) : Exception(detail);

internal interface IDatasetRowSource
{
    IAsyncEnumerable<Dictionary<string, object?>> ReadAsync(
        DatasetDefinition dataset, IReadOnlyList<BoundParameter> parameters, CancellationToken token);
}

internal delegate Task<JsonDocument> PostJson(string path, object payload, CancellationToken token);

/// A fila "pull" do Contraprova, sem nada de ODBC nem de rede concreta: pede um job,
/// confere o contrato, lê, pagina, fecha. Fica na biblioteca de contratos para ser
/// testável sem Windows.
///
/// A nuvem manda o código, a versão e o hash; o SQL sai do catálogo incorporado. Se os
/// três não baterem com o catálogo, nada executa.
internal sealed class ContraprovaJobRunner(
    PostJson post,
    IDatasetRowSource source,
    Func<string, string, DatasetDefinition?> lookup,
    string sourceSystem)
{
    internal const int MaxPageSize = 500;
    private const int MaxDetail = 200;
    private const string Base = "api/agent/v2/contraprova/jobs";

    /// Devolve true quando havia um job (concluído ou fechado com falha).
    internal async Task<bool> RunOnceAsync(CancellationToken token)
    {
        JsonDocument next;
        try
        {
            next = await post($"{Base}/next", new { source_system = sourceSystem }, token);
        }
        catch (HttpRequestException error) when (error.StatusCode == HttpStatusCode.NotFound)
        {
            // Recurso desligado no servidor: sem trabalho.
            return false;
        }

        using (next)
        {
            if (!next.RootElement.TryGetProperty("job", out JsonElement job)
                || job.ValueKind != JsonValueKind.Object)
                return false;
            await Handle(job, token);
            return true;
        }
    }

    private async Task Handle(JsonElement job, CancellationToken token)
    {
        // O id entra na URL: só aceita UUID, nada de segmento de caminho vindo do JSON.
        if (!job.TryGetProperty("id", out JsonElement idElement)
            || idElement.ValueKind != JsonValueKind.String
            || !Guid.TryParse(idElement.GetString(), out Guid parsed))
            throw new InvalidDataException("Job da Contraprova sem id válido.");
        string id = parsed.ToString();

        try
        {
            (int rows, int pages) = await Execute(id, job, token);
            using JsonDocument _ = await post(
                $"{Base}/{id}/complete", new { row_count = rows, pages }, token);
        }
        catch (JobFailure failure)
        {
            await Fail(id, failure.Code, failure.Message, token);
        }
        catch (ParameterBindingException error)
        {
            await Fail(id, "dataset_mismatch", error.Message, token);
        }
        catch (DatasetReadException error)
        {
            await Fail(id, "odbc_error", error.Message, token);
        }
        catch (HttpRequestException error)
        {
            await Fail(id, "agent_error",
                $"Servidor recusou a chamada (HTTP {(int?)error.StatusCode}).", token);
        }
        catch (Exception error) when (
            error is not OperationCanceledException and not AgentAuthorizationException)
        {
            // Só o tipo: a mensagem de uma exceção qualquer pode ecoar dado.
            await Fail(id, "agent_error", error.GetType().Name, token);
        }
    }

    private async Task<(int Rows, int Pages)> Execute(
        string id, JsonElement job, CancellationToken token)
    {
        string code = StringOf(job, "dataset_code");
        DatasetDefinition? dataset = lookup(sourceSystem, code);
        if (dataset is null
            || !job.TryGetProperty("schema_version", out JsonElement version)
            || !version.TryGetInt32(out int schemaVersion)
            || dataset.SchemaVersion != schemaVersion
            || !string.Equals(
                dataset.QuerySha256, StringOf(job, "query_sha256"), StringComparison.Ordinal))
            throw new JobFailure("dataset_mismatch", "Dataset, versão ou hash divergente do catálogo.");
        if (!dataset.Validated)
            throw new JobFailure("dataset_not_validated", "Dataset ainda não validado.");

        IReadOnlyList<BoundParameter> parameters =
            DatasetParameterBinder.Bind(dataset, ReadParameters(job));

        int limit = dataset.MaxRowsPerRun;
        if (job.TryGetProperty("max_rows", out JsonElement maxRows)
            && maxRows.TryGetInt32(out int requested) && requested > 0)
            limit = Math.Min(limit, requested);
        int pageSize = MaxPageSize;
        if (job.TryGetProperty("page_size", out JsonElement size)
            && size.TryGetInt32(out int pageRequested) && pageRequested > 0)
            pageSize = Math.Min(pageRequested, MaxPageSize);

        string[] columns = dataset.ResultColumns;
        List<Dictionary<string, object?>> page = new(pageSize);
        int total = 0;
        int sequence = 0;
        await foreach (Dictionary<string, object?> row in source.ReadAsync(dataset, parameters, token))
        {
            total++;
            if (total > limit)
                throw new JobFailure("row_limit", $"A consulta excedeu o limite de {limit} linhas.");
            page.Add(Shape(row, columns));
            if (page.Count < pageSize) continue;
            await SendPage(id, sequence++, page, token);
            page.Clear();
        }
        if (page.Count > 0) await SendPage(id, sequence++, page, token);
        return (total, sequence);
    }

    private async Task SendPage(
        string id, int sequence, List<Dictionary<string, object?>> rows, CancellationToken token)
    {
        using JsonDocument _ = await post($"{Base}/{id}/batches", new { sequence, rows }, token);
    }

    private async Task Fail(string id, string code, string detail, CancellationToken token)
    {
        string clean = detail.ReplaceLineEndings(" ");
        if (clean.Length > MaxDetail) clean = clean[..MaxDetail];
        using JsonDocument _ = await post(
            $"{Base}/{id}/failure", new { error_code = code, detail = clean }, token);
    }

    /// Só as colunas do contrato, na ordem dele; nulo vira "" e o texto perde o
    /// preenchimento de CHAR que o SQL Anywhere devolve.
    private static Dictionary<string, object?> Shape(
        Dictionary<string, object?> row, string[] columns)
    {
        Dictionary<string, object?> shaped = new(columns.Length, StringComparer.Ordinal);
        foreach (string column in columns)
        {
            row.TryGetValue(column, out object? value);
            shaped[column] = value switch
            {
                null => "",
                string text => text.Trim(),
                _ => value,
            };
        }
        return shaped;
    }

    private static string StringOf(JsonElement job, string name) =>
        job.TryGetProperty(name, out JsonElement value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? ""
            : "";

    private static List<JobParameter> ReadParameters(JsonElement job)
    {
        List<JobParameter> parameters = [];
        if (!job.TryGetProperty("parameters", out JsonElement list)
            || list.ValueKind != JsonValueKind.Array)
            return parameters;
        foreach (JsonElement item in list.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.Object
                || !item.TryGetProperty("value", out JsonElement value))
                throw new ParameterBindingException("Parâmetro do job malformado.");
            parameters.Add(new JobParameter(
                StringOf(item, "name"), value.Clone(), StringOf(item, "odbc_type")));
        }
        return parameters;
    }
}
