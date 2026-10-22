using System.Data;
using System.Data.Common;
using System.Data.Odbc;

namespace Cica.Agent.Service;

/// Fila "pull" do Contraprova: a cada ciclo pede um job à nuvem, lê no Domínio a
/// consulta fixada por hash e devolve as páginas.
///
/// O protocolo e as regras vivem em `ContraprovaJobRunner` (biblioteca de contratos,
/// testável sem Windows). Aqui fica só o que depende do sistema: o cliente assinado
/// e o ODBC x64 em processo, como o `ProfitabilityProcessor`. O Siescon não entra:
/// o contrato é do Domínio e o driver do Siescon exige a ponte de 32 bits.
internal sealed class ContraprovaProcessor(AgentConfig config, AgentClient client)
{
    private const string SourceSystem = "dominio";

    internal async Task RunOnce(CancellationToken token)
    {
        if (string.IsNullOrWhiteSpace(config.Dsn)
            || config.EffectiveSourceSystem != SourceSystem)
            return;

        ContraprovaJobRunner runner = new(
            client.PostAsync,
            new OdbcDominioRowSource(config),
            DatasetCatalog.TryGet,
            SourceSystem);
        await runner.RunOnceAsync(token);
    }
}

/// Lê o contrato pelo ODBC x64 do Domínio. Toda falha do driver vira
/// `DatasetReadException` com mensagem saneada: o texto de um `OdbcException` pode
/// trazer servidor, DSN ou usuário, então só o SQLSTATE sai daqui.
internal sealed class OdbcDominioRowSource(AgentConfig config) : IDatasetRowSource
{
    public async IAsyncEnumerable<Dictionary<string, object?>> ReadAsync(
        DatasetDefinition dataset,
        IReadOnlyList<BoundParameter> parameters,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken token)
    {
        using OdbcConnection connection = new(
            $"DSN={config.Dsn};UID={config.DatabaseUser};PWD={config.DatabasePassword}");
        connection.ConnectionTimeout = 20;
        try
        {
            await connection.OpenAsync(token);
        }
        catch (OdbcException error)
        {
            throw Sanitized(error);
        }

        using OdbcCommand command = new(dataset.Sql, connection) { CommandTimeout = 30 };
        foreach (BoundParameter parameter in parameters)
        {
            if (!Enum.TryParse(parameter.OdbcType, ignoreCase: false, out OdbcType odbcType))
                throw new DatasetReadException("Tipo de parâmetro ODBC inválido no contrato.");
            command.Parameters.Add(
                new OdbcParameter(parameter.Name, odbcType) { Value = parameter.Value });
        }

        DbDataReader reader;
        try
        {
            reader = await command.ExecuteReaderAsync(
                CommandBehavior.SequentialAccess | CommandBehavior.SingleResult, token);
        }
        catch (OdbcException error)
        {
            throw Sanitized(error);
        }

        using (reader)
        {
            string[] names = Enumerable.Range(0, reader.FieldCount).Select(reader.GetName).ToArray();
            try
            {
                DatasetResultContract.ValidateColumns(dataset.ResultColumns, names);
            }
            catch (InvalidOperationException)
            {
                throw new DatasetReadException("Colunas do ERP divergem do contrato.");
            }
            DatasetValueKind[] kinds = ProfitabilityProcessor.ValueKinds(reader);

            while (true)
            {
                try
                {
                    if (!await reader.ReadAsync(token)) yield break;
                }
                catch (OdbcException error)
                {
                    throw Sanitized(error);
                }
                Dictionary<string, object?> row = new(StringComparer.Ordinal);
                for (int index = 0; index < names.Length; index++)
                    row[names[index]] = DatasetValue.Normalize(
                        reader.IsDBNull(index) ? null : reader.GetValue(index), kinds[index]);
                yield return row;
            }
        }
    }

    private static DatasetReadException Sanitized(OdbcException error)
    {
        string state = error.Errors.Count > 0 ? error.Errors[0].SQLState : "";
        return new DatasetReadException(
            string.IsNullOrWhiteSpace(state) ? "Falha ODBC." : $"Falha ODBC (SQLSTATE {state}).");
    }
}
