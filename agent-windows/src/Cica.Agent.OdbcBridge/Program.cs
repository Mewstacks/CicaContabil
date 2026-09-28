using System.Data;
using System.Data.Odbc;
using System.Globalization;
using System.Text.Json;
using Cica.Agent.Service;

namespace Cica.Agent.OdbcBridge;

/// A ponte de 32 bits, para o único driver que não existe em 64.
///
/// Portada do conector do Lucrums por D-111 e autorizada por D-117. O serviço CICA
/// é x64 e assim permanece; o Pervasive, que o Siescon usa, só publica driver ODBC
/// de 32 bits, e um processo não carrega driver de outra arquitetura. Este
/// executável é a única parte do pacote que roda em x86, e existe só para abrir
/// esse driver.
///
/// Fala por entrada e saída padrão, sem rede e sem arquivo temporário: o pedido
/// chega numa linha de JSON pelo stdin e as linhas saem uma por linha no stdout. A
/// credencial nunca aparece na linha de comando, que é visível para qualquer
/// processo da máquina.
///
/// A conversão de valores vem de `DatasetValue`, a mesma que o serviço usa. No
/// projeto de origem havia duas cópias dessa lógica, uma de cada lado da ponte —
/// e duas cópias de uma regra de conversão concordam até o dia em que alguém
/// corrige uma delas.
internal static class Program
{
    internal static int Main()
    {
        try
        {
            string? linha = Console.In.ReadLine();
            BridgeRequest request = JsonSerializer.Deserialize<BridgeRequest>(linha ?? "")
                ?? throw new InvalidOperationException("Pedido da ponte vazio.");

            using OdbcConnection connection = new(ConnectionString(request));
            connection.ConnectionTimeout = 20;
            connection.Open();

            if (request.Mode == "test")
            {
                using OdbcCommand test = new("SELECT 1", connection) { CommandTimeout = 10 };
                _ = test.ExecuteScalar();
                Console.Out.WriteLine("{\"ok\":true}");
                return 0;
            }
            if (request.Mode != "read")
                throw new InvalidOperationException("Modo de ponte desconhecido.");

            using OdbcCommand command = BuildCommand(connection, request);
            using OdbcDataReader reader = command.ExecuteReader(
                CommandBehavior.SequentialAccess | CommandBehavior.SingleResult);
            WriteRows(reader, request.MaxRows, request.ExpectedColumns);
            return 0;
        }
        catch (Exception error)
        {
            // Só o tipo e a mensagem, nunca o pedido: ele carrega a credencial.
            Console.Error.WriteLine(error.GetType().Name + ": " + error.Message);
            return 1;
        }
    }

    private static string ConnectionString(BridgeRequest request)
    {
        OdbcConnectionStringBuilder builder = new() { Dsn = request.Dsn };
        // O Pervasive relacional aceita usuário em branco quando o banco não tem
        // segurança ligada, e é assim que boa parte das instalações Siescon está.
        if (request.User.Length > 0) builder["UID"] = request.User;
        if (request.Password.Length > 0) builder["PWD"] = request.Password;
        return builder.ConnectionString;
    }

    private static OdbcCommand BuildCommand(OdbcConnection connection, BridgeRequest request)
    {
        OdbcCommand command = new(request.Sql, connection) { CommandTimeout = 30 };
        foreach (BridgeParameter parameter in request.Parameters)
        {
            if (!Enum.TryParse(parameter.OdbcType, ignoreCase: false, out OdbcType odbcType))
                throw new InvalidOperationException("Tipo de parâmetro ODBC inválido.");
            command.Parameters.Add(
                new OdbcParameter(parameter.Name, odbcType) { Value = ParameterValue(parameter) });
        }
        return command;
    }

    internal static object ParameterValue(BridgeParameter parameter) => parameter.Type switch
    {
        "integer" => int.Parse(parameter.Value, CultureInfo.InvariantCulture),
        "decimal" => decimal.Parse(parameter.Value, CultureInfo.InvariantCulture),
        "date" => DateTime.ParseExact(
            parameter.Value, "yyyy-MM-dd", CultureInfo.InvariantCulture),
        "string" => parameter.Value,
        _ => throw new InvalidOperationException("Tipo de parâmetro não suportado."),
    };

    private static void WriteRows(
        OdbcDataReader reader, int maxRows, IReadOnlyList<string> expectedColumns)
    {
        string[] names = Enumerable.Range(0, reader.FieldCount).Select(reader.GetName).ToArray();
        DatasetResultContract.ValidateColumns(expectedColumns, names);
        DatasetValueKind[] kinds = ValueKinds(reader);
        int linhas = 0;
        while (reader.Read())
        {
            if (linhas >= maxRows)
                throw new InvalidOperationException("A consulta excedeu o limite de linhas.");
            Dictionary<string, object?> row = new(StringComparer.Ordinal);
            for (int index = 0; index < names.Length; index++)
                row[names[index]] = DatasetValue.Normalize(
                    reader.IsDBNull(index) ? null : reader.GetValue(index), kinds[index]);
            // Uma linha por linha: o serviço lê em fluxo, e um único JSON gigante
            // exigiria que os dois lados segurassem a consulta inteira na memória.
            Console.Out.WriteLine(JsonSerializer.Serialize(row));
            linhas++;
        }
    }

    internal static DatasetValueKind[] ValueKinds(IDataReader reader)
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

internal sealed class BridgeParameter
{
    public string Name { get; set; } = "";
    public string OdbcType { get; set; } = "";
    public string Type { get; set; } = "";
    public string Value { get; set; } = "";
}

internal sealed class BridgeRequest
{
    public string Mode { get; set; } = "";
    public string Dsn { get; set; } = "";
    public string User { get; set; } = "";
    public string Password { get; set; } = "";
    public string Sql { get; set; } = "";
    public List<BridgeParameter> Parameters { get; set; } = [];
    public int MaxRows { get; set; }
    public string[] ExpectedColumns { get; set; } = [];
}
