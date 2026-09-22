using System.Diagnostics;
using System.Text.Json;

namespace Cica.Agent.Service;

/// Conversa com a ponte de 32 bits, quando o ERP configurado exige.
///
/// O pedido vai por stdin e as linhas voltam por stdout, uma por linha. Nada de
/// argumento de linha de comando: ele carrega a credencial do banco e fica visível
/// para qualquer processo da máquina enquanto a ponte roda.
internal sealed class OdbcBridgeClient(AgentConfig config)
{
    private static readonly TimeSpan Timeout = TimeSpan.FromMinutes(30);

    private static string ExecutablePath => Path.Combine(
        Path.GetDirectoryName(Environment.ProcessPath) ?? AppContext.BaseDirectory,
        "Cica.Agent.OdbcBridge.exe");

    internal async IAsyncEnumerable<Dictionary<string, object?>> ReadAsync(
        DatasetDefinition dataset,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken token)
    {
        using Process process = Start();
        await WriteRequest(process, "read", dataset, token);

        while (await process.StandardOutput.ReadLineAsync(token) is { } linha)
        {
            if (linha.Length == 0) continue;
            Dictionary<string, object?>? row =
                JsonSerializer.Deserialize<Dictionary<string, object?>>(linha);
            if (row is not null) yield return row;
        }
        await Finish(process, token);
    }

    internal async Task TestConnectionAsync(CancellationToken token)
    {
        using Process process = Start();
        await WriteRequest(process, "test", dataset: null, token);
        _ = await process.StandardOutput.ReadToEndAsync(token);
        await Finish(process, token);
    }

    private Process Start()
    {
        string caminho = ExecutablePath;
        if (!File.Exists(caminho))
            throw new InvalidOperationException(
                "A ponte ODBC de 32 bits não está instalada junto do serviço.");
        Process? process = Process.Start(new ProcessStartInfo(caminho)
        {
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        });
        return process ?? throw new InvalidOperationException(
            "Não foi possível iniciar a ponte ODBC de 32 bits.");
    }

    private async Task WriteRequest(
        Process process, string mode, DatasetDefinition? dataset, CancellationToken token)
    {
        var pedido = new
        {
            Mode = mode,
            Dsn = config.Dsn ?? "",
            User = config.DatabaseUser,
            Password = config.DatabasePassword,
            Sql = dataset?.Sql ?? "",
            Parameters = Array.Empty<object>(),
            MaxRows = dataset?.MaxRowsPerRun ?? 0,
        };
        await process.StandardInput.WriteLineAsync(
            JsonSerializer.Serialize(pedido).AsMemory(), token);
        await process.StandardInput.FlushAsync(token);
        process.StandardInput.Close();
    }

    private static async Task Finish(Process process, CancellationToken token)
    {
        string erro = await process.StandardError.ReadToEndAsync(token);
        using var limite = CancellationTokenSource.CreateLinkedTokenSource(token);
        limite.CancelAfter(Timeout);
        await process.WaitForExitAsync(limite.Token);
        if (process.ExitCode != 0)
            // A ponte já cuida de não ecoar o pedido; o que chega aqui é tipo e
            // mensagem do erro do driver.
            throw new InvalidOperationException(
                $"A ponte ODBC de 32 bits falhou: {erro.Trim()}");
    }
}
