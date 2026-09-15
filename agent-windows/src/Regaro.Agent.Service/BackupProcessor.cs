using System.Data.Odbc;
using System.Security.Cryptography;
using System.Text.Json;
using SharpCompress.Archives;
using SharpCompress.Archives.Zip;
using SharpCompress.Common;
using SharpCompress.Readers;

namespace Regaro.Agent.Service;

internal sealed class BackupProcessor(AgentConfig config, AgentClient client)
{
    internal async Task RunOnce(CancellationToken token)
    {
        using JsonDocument result = await client.PostAsync("api/agent/v2/backups/next", new { }, token);
        if (result.RootElement.GetProperty("job").ValueKind == JsonValueKind.Null) return;
        JsonElement job = result.RootElement.GetProperty("job");
        string id = job.GetProperty("id").GetString()!;
        string expectedHash = job.GetProperty("sha256").GetString()!;
        string key = job.GetProperty("backup_key").GetString()!;
        string temporary = Path.Combine(AgentConfig.DirectoryPath, "queue", id);
        Directory.CreateDirectory(temporary);
        string archivePath = Path.Combine(temporary, "backup.dom");
        try
        {
            await client.DownloadAsync(job.GetProperty("download_url").GetString()!, archivePath, token);
            await using (FileStream file = File.OpenRead(archivePath))
            {
                string observed = Convert.ToHexString(await SHA256.HashDataAsync(file, token)).ToLowerInvariant();
                if (!CryptographicOperations.FixedTimeEquals(
                    Convert.FromHexString(observed), Convert.FromHexString(expectedHash)))
                    throw new InvalidDataException("O hash do backup recebido não confere.");
            }
            string extracted = Path.Combine(temporary, "extracted");
            using (IArchive archive = ZipArchive.OpenArchive(archivePath, new ReaderOptions { Password = key }))
                foreach (IArchiveEntry entry in archive.Entries.Where(e => !e.IsDirectory))
                    entry.WriteToDirectory(extracted, new ExtractionOptions
                        { ExtractFullPath = true, Overwrite = true, PreserveFileTime = true });
            string database = Directory.EnumerateFiles(extracted, "contabil.db", SearchOption.AllDirectories)
                .FirstOrDefault() ?? throw new InvalidDataException("O backup não contém contabil.db.");
            await SendCompanies(id, database, token);
            await SendAccounting(id, database, token);
            await client.PostAsync("api/agent/v2/sync/complete", new { batch_id = id }, token);
        }
        catch (Exception error) when (error is not OperationCanceledException)
        {
            await client.PostAsync("api/agent/v2/sync/failed", new
                { batch_id = id, code = "backup_processing", detail = Friendly(error) }, token);
        }
        finally
        {
            if (Directory.Exists(temporary)) Directory.Delete(temporary, true);
        }
    }

    private OdbcConnection Open(string database)
    {
        string cs = $"Driver={{{config.SqlAnywhereDriver}}};UID={config.DatabaseUser};" +
            $"PWD={config.DatabasePassword};DBF={database};ASTART=YES;ENC=None;CON=RegaroBackup";
        var connection = new OdbcConnection(cs);
        connection.Open();
        return connection;
    }

    private async Task SendCompanies(string batch, string database, CancellationToken token)
    {
        const string sql = "SELECT TOP 10000 codi_emp, nome_emp, cgce_emp, stat_emp " +
            "FROM bethadba.geempre ORDER BY codi_emp";
        using OdbcConnection connection = Open(database);
        using OdbcCommand command = new(sql, connection) { CommandTimeout = 60 };
        using OdbcDataReader reader = command.ExecuteReader();
        var page = new List<object>(500);
        while (reader.Read())
        {
            page.Add(new { external_key = Convert.ToString(reader[0]), name = Convert.ToString(reader[1]),
                cnpj = Convert.ToString(reader[2]), active = Convert.ToString(reader[3]) == "A" });
            if (page.Count == 500) { await SendPage("companies", batch, page, token); page.Clear(); }
        }
        if (page.Count > 0) await SendPage("companies", batch, page, token);
    }

    private async Task SendAccounting(string batch, string database, CancellationToken token)
    {
        const string sql = "SELECT TOP 100000 CAST(i.CODI_EMP AS VARCHAR(64)) || '|' || " +
            "CAST(i.I_LANCAMENTO AS VARCHAR(64)) || '|' || CAST(i.I_ITEM AS VARCHAR(64)), " +
            "i.CODI_EMP, i.DATA_ITEM, i.HISTORICO, i.VALOR, i.TIPO FROM " +
            "bethadba.CTEXTRATO_BANCARIO_LANCAMENTO_ITEM i ORDER BY i.DATA_ITEM, i.CODI_EMP";
        using OdbcConnection connection = Open(database);
        using OdbcCommand command = new(sql, connection) { CommandTimeout = 120 };
        using OdbcDataReader reader = command.ExecuteReader();
        var page = new List<object>(500);
        while (reader.Read())
        {
            page.Add(new { external_key = Convert.ToString(reader[0]), company_key = Convert.ToString(reader[1]),
                occurred_on = Convert.ToDateTime(reader[2]).ToString("yyyy-MM-dd"),
                description = Convert.ToString(reader[3]), amount = Convert.ToDecimal(reader[4]),
                direction = Convert.ToString(reader[5]) });
            if (page.Count == 500) { await SendPage("accounting_entries", batch, page, token); page.Clear(); }
        }
        if (page.Count > 0) await SendPage("accounting_entries", batch, page, token);
    }

    private async Task SendPage(string capability, string batch, List<object> rows,
        CancellationToken token) => await client.PostAsync($"api/agent/v2/sync/{capability}",
            new { batch_id = batch, rows }, token);

    private static string Friendly(Exception error) => error switch
    {
        InvalidDataException => error.Message,
        OdbcException => "Não foi possível abrir contabil.db. Verifique o SQL Anywhere 16/17 e as credenciais do banco.",
        _ => "O backup não pôde ser processado. Tente novamente ou envie o diagnóstico ao suporte."
    };
}
