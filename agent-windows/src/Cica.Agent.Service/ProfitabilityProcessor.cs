using System.Data;
using System.Data.Common;
using System.Data.Odbc;
using System.Globalization;
using System.Text.Json;

namespace Cica.Agent.Service;

/// Executa os contratos de consulta do módulo Rentabilidade e entrega as linhas.
///
/// Portado do conector do Lucrums por D-108 e D-111, com duas mudanças. A primeira
/// é o transporte: por D-114 vale o do agente da CICA — mTLS com assinatura do
/// corpo —, então não há envelope cifrado nem token próprio aqui. A segunda é o
/// perfil: o Lucrums compilava o ERP dentro do binário e publicava um instalador
/// por sistema; D-80 mantém pacote único na CICA, então o ERP vem da configuração
/// e o mesmo serviço atende os dois.
///
/// O ciclo é o do servidor: perguntar o que rodar, abrir a execução, enviar as
/// páginas, fechar. O que nunca acontece é executar SQL que a nuvem mandou: a
/// nuvem manda o código do contrato, e o SQL sai do catálogo incorporado, cujo
/// hash foi conferido na subida.
internal sealed class ProfitabilityProcessor(AgentConfig config, AgentClient client)
{
    private const int PageSize = 500;

    internal async Task RunOnce(CancellationToken token)
    {
        if (string.IsNullOrWhiteSpace(config.Dsn)) return;

        using JsonDocument commands = await client.PostAsync(
            "api/agent/v2/profitability/datasets",
            new { source_system = config.EffectiveSourceSystem },
            token);
        JsonElement root = commands.RootElement;
        if (!root.TryGetProperty("enabled", out JsonElement enabled) || !enabled.GetBoolean())
            return;

        foreach (JsonElement item in root.GetProperty("datasets").EnumerateArray())
        {
            token.ThrowIfCancellationRequested();
            await RunDataset(item, token);
        }
    }

    private async Task RunDataset(JsonElement command, CancellationToken token)
    {
        string code = command.GetProperty("code").GetString() ?? "";
        int schemaVersion = command.GetProperty("schema_version").GetInt32();
        string runKind = command.GetProperty("allowed_run_kinds")[0].GetString() ?? "full";

        // O SQL vem do catálogo, nunca do comando. O que a nuvem manda é o código,
        // a versão e o hash que ela espera — e o hash é conferido dos dois lados.
        DatasetDefinition dataset = DatasetCatalog.GetForRun(config.EffectiveSourceSystem, code, runKind);
        if (dataset.SchemaVersion != schemaVersion
            || !string.Equals(
                dataset.QuerySha256,
                command.GetProperty("query_sha256").GetString(),
                StringComparison.Ordinal))
            // Servidor e agente estão em versões diferentes do contrato. Executar
            // aqui produziria linhas que o outro lado interpretaria por outro
            // desenho de coluna.
            return;

        // A chave de idempotência inclui o dia: uma reconexão no mesmo dia retoma a
        // execução já aberta, e o dia seguinte começa uma nova.
        string idempotencyKey =
            $"{config.EffectiveSourceSystem}:{code}:v{schemaVersion}:"
            + DateTime.UtcNow.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

        using JsonDocument opened = await client.PostAsync(
            "api/agent/v2/profitability/runs",
            new
            {
                source_system = config.EffectiveSourceSystem,
                dataset_code = code,
                schema_version = schemaVersion,
                run_kind = runKind,
                idempotency_key = idempotencyKey,
                parameters = Array.Empty<object>(),
            },
            token);
        string runId = opened.RootElement.GetProperty("run_id").GetString() ?? "";
        if (string.IsNullOrWhiteSpace(runId)) return;

        try
        {
            int sent = await SendPages(runId, dataset, token);
            using JsonDocument _ = await client.PostAsync(
                $"api/agent/v2/profitability/runs/{runId}/complete",
                new { row_count = sent },
                token);
        }
        catch (Exception erro) when (erro is OdbcException or InvalidOperationException)
        {
            // A falha fica registrada na execução em vez de deixá-la recebendo para
            // sempre — do lado do servidor, uma execução abandonada não distingue
            // "o agente caiu" de "o agente ainda está enviando".
            using JsonDocument _ = await client.PostAsync(
                $"api/agent/v2/profitability/runs/{runId}/failure",
                new { code = erro is OdbcException ? "odbc_failure" : "contract_failure" },
                token);
            throw;
        }
    }

    private async Task<int> SendPages(
        string runId, DatasetDefinition dataset, CancellationToken token)
    {
        int sequence = 0;
        int total = 0;
        List<Dictionary<string, object?>> page = new(PageSize);

        await foreach (Dictionary<string, object?> row in ReadAsync(dataset, token))
        {
            page.Add(row);
            total++;
            if (total > dataset.MaxRowsPerRun)
                throw new InvalidOperationException(
                    "A consulta excedeu o limite de linhas do contrato.");
            if (page.Count < PageSize) continue;
            await SendPage(runId, sequence++, page, token);
            page.Clear();
        }
        if (page.Count > 0) await SendPage(runId, sequence, page, token);
        return total;
    }

    private async Task SendPage(
        string runId,
        int sequence,
        List<Dictionary<string, object?>> rows,
        CancellationToken token)
    {
        using JsonDocument _ = await client.PostAsync(
            $"api/agent/v2/profitability/runs/{runId}/batches",
            new { sequence, rows },
            token);
    }

    private async IAsyncEnumerable<Dictionary<string, object?>> ReadAsync(
        DatasetDefinition dataset,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken token)
    {
        // O Siescon lê pela ponte de 32 bits: o driver Pervasive não existe em 64,
        // e um processo não carrega driver de outra arquitetura.
        if (config.EffectiveSourceSystem == "siescon")
        {
            await foreach (Dictionary<string, object?> row in
                new OdbcBridgeClient(config).ReadAsync(dataset, token))
                yield return row;
            yield break;
        }

        using var connection = new OdbcConnection(
            $"DSN={config.Dsn};UID={config.DatabaseUser};PWD={config.DatabasePassword}");
        connection.ConnectionTimeout = 20;
        await connection.OpenAsync(token);

        using var command = new OdbcCommand(dataset.Sql, connection) { CommandTimeout = 30 };
        // Sem parâmetro não há concatenação: o contrato ou declara parâmetros
        // posicionais, ou a consulta não os tem. Nenhum valor entra no texto do SQL.
        if (dataset.Parameters.Count > 0)
            throw new InvalidOperationException(
                "Contrato com parâmetros ainda não é despachado por este conector.");

        using DbDataReader reader = await command.ExecuteReaderAsync(
            CommandBehavior.SequentialAccess | CommandBehavior.SingleResult, token);
        string[] names = Enumerable.Range(0, reader.FieldCount).Select(reader.GetName).ToArray();
        DatasetValueKind[] kinds = ValueKinds(reader);

        while (await reader.ReadAsync(token))
        {
            Dictionary<string, object?> row = new(StringComparer.Ordinal);
            for (int index = 0; index < names.Length; index++)
                row[names[index]] = DatasetValue.Normalize(
                    reader.IsDBNull(index) ? null : reader.GetValue(index), kinds[index]);
            yield return row;
        }
    }

    private static DatasetValueKind[] ValueKinds(DbDataReader reader)
    {
        DataTable? schema = reader.GetSchemaTable();
        if (schema is null || schema.Rows.Count != reader.FieldCount)
            return Enumerable.Repeat(DatasetValueKind.Other, reader.FieldCount).ToArray();
        return schema.Rows.Cast<DataRow>()
            .Select(row => row["ProviderType"] is int value
                ? (OdbcType)value switch
                {
                    OdbcType.Date => DatasetValueKind.Date,
                    OdbcType.Time => DatasetValueKind.Time,
                    OdbcType.DateTime or OdbcType.SmallDateTime or OdbcType.Timestamp =>
                        DatasetValueKind.Timestamp,
                    _ => DatasetValueKind.Other,
                }
                : DatasetValueKind.Other)
            .ToArray();
    }
}
