using System.Data.Odbc;
using System.Security.Cryptography;
using System.Text.Json;
using SharpCompress.Archives;
using SharpCompress.Archives.Zip;
using SharpCompress.Common;
using SharpCompress.Readers;

namespace Cica.Agent.Service;

internal sealed class BackupProcessor(AgentConfig config, AgentClient client)
{
    private const int PageSize = 500;

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
            ExtractBackup(archivePath, key, extracted);
            string database = Directory.EnumerateFiles(extracted, "contabil.db", SearchOption.AllDirectories)
                .FirstOrDefault() ?? throw new InvalidDataException("O backup não contém contabil.db.");
            await SendCompanies(id, database, token);
            await SendAccumulatorCatalog(id, database, token);
            await SendAccumulatorObservations(id, database, token);
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
            $"PWD={config.DatabasePassword};DBF={database};ASTART=YES;ENC=None;CON=CicaBackup";
        var connection = new OdbcConnection(cs);
        connection.Open();
        return connection;
    }

    private async Task SendCompanies(string batch, string database, CancellationToken token)
    {
        const string sql = "SELECT codi_emp, nome_emp, cgce_emp, stat_emp " +
            "FROM bethadba.geempre ORDER BY codi_emp";
        using OdbcConnection connection = Open(database);
        using OdbcCommand command = new(sql, connection) { CommandTimeout = 60 };
        using OdbcDataReader reader = command.ExecuteReader();
        var page = new List<object>(PageSize);
        while (reader.Read())
        {
            page.Add(new { external_key = Convert.ToString(reader[0]), name = Convert.ToString(reader[1]),
                cnpj = Convert.ToString(reader[2]), active = Convert.ToString(reader[3]) == "A" });
            if (page.Count == PageSize) { await SendPage("companies", batch, page, token); page.Clear(); }
        }
        if (page.Count > 0) await SendPage("companies", batch, page, token);
    }

    private async Task SendAccumulatorCatalog(string batch, string database,
        CancellationToken token)
    {
        const string sql = "SELECT CODI_EMP, CODI_ACU, NOME_ACU, " +
            "CASE WHEN DATA_INATIVACAO_ACU IS NULL THEN 1 ELSE 0 END, " +
            "CAST(CODI_EMP AS VARCHAR(64)) || '|' || CAST(CODI_ACU AS VARCHAR(64)) " +
            "FROM bethadba.EFACUMULADOR ORDER BY CODI_EMP, CODI_ACU";
        using OdbcConnection connection = Open(database);
        using OdbcCommand command = new(sql, connection) { CommandTimeout = 120 };
        using OdbcDataReader reader = command.ExecuteReader();
        var page = new List<object>(PageSize);
        while (reader.Read())
        {
            page.Add(new
            {
                company_key = Convert.ToString(reader[0]),
                accumulator_code = Convert.ToString(reader[1]),
                name = Convert.ToString(reader[2]),
                active = Convert.ToInt32(reader[3]) == 1,
                source_identifier = Convert.ToString(reader[4]),
            });
            if (page.Count == PageSize)
            {
                await SendPage("accumulator_catalog", batch, page, token);
                page.Clear();
            }
        }
        if (page.Count > 0) await SendPage("accumulator_catalog", batch, page, token);
    }

    private async Task SendAccounting(string batch, string database, CancellationToken token)
    {
        const string sql = "SELECT CAST(i.CODI_EMP AS VARCHAR(64)) || '|' || " +
            "CAST(i.I_LANCAMENTO AS VARCHAR(64)) || '|' || CAST(i.I_ITEM AS VARCHAR(64)), " +
            "i.CODI_EMP, i.DATA_ITEM, i.HISTORICO, i.VALOR, i.TIPO FROM " +
            "bethadba.CTEXTRATO_BANCARIO_LANCAMENTO_ITEM i ORDER BY i.DATA_ITEM, i.CODI_EMP";
        using OdbcConnection connection = Open(database);
        using OdbcCommand command = new(sql, connection) { CommandTimeout = 120 };
        using OdbcDataReader reader = command.ExecuteReader();
        var page = new List<object>(PageSize);
        while (reader.Read())
        {
            page.Add(new { external_key = Convert.ToString(reader[0]), company_key = Convert.ToString(reader[1]),
                occurred_on = Convert.ToDateTime(reader[2]).ToString("yyyy-MM-dd"),
                description = Convert.ToString(reader[3]), amount = Convert.ToDecimal(reader[4]),
                direction = Convert.ToString(reader[5]) });
            if (page.Count == PageSize) { await SendPage("accounting_entries", batch, page, token); page.Clear(); }
        }
        if (page.Count > 0) await SendPage("accounting_entries", batch, page, token);
    }

    private async Task SendAccumulatorObservations(string batch, string database,
        CancellationToken token)
    {
        const string issuedSql = "SELECT s.codi_emp, s.codi_acu, s.RN_CODIGO_TRIBUTACAO, " +
            "c.cgce_cli, COUNT(*), MAX(COALESCE(s.DATA_SERVICO, s.dser_ser, s.ddoc_ser)) " +
            "FROM bethadba.efservicos s JOIN bethadba.efclientes c " +
            "ON c.codi_emp = s.codi_emp AND c.codi_cli = s.codi_cli " +
            "WHERE s.codi_acu IS NOT NULL GROUP BY s.codi_emp, s.codi_acu, " +
            "s.RN_CODIGO_TRIBUTACAO, c.cgce_cli";
        const string takenSql = "SELECT e.codi_emp, e.codi_acu, NULL, f.cgce_for, COUNT(*), " +
            "MAX(COALESCE(e.DATA_ENTRADA, e.dent_ent, e.ddoc_ent)) " +
            "FROM bethadba.efentradas e JOIN bethadba.effornece f " +
            "ON f.codi_emp = e.codi_emp AND f.codi_for = e.codi_for " +
            "WHERE e.codi_acu IS NOT NULL AND ((e.CHAVE_NFSE_ENT IS NOT NULL " +
            "AND TRIM(e.CHAVE_NFSE_ENT) <> '') OR e.TIPO_SERVICO IS NOT NULL) " +
            "GROUP BY e.codi_emp, e.codi_acu, f.cgce_for";
        using OdbcConnection connection = Open(database);
        await SendObservationQuery(batch, connection, issuedSql, token);
        await SendObservationQuery(batch, connection, takenSql, token);
    }

    private async Task SendObservationQuery(string batch, OdbcConnection connection,
        string sql, CancellationToken token)
    {
        using OdbcCommand command = new(sql, connection) { CommandTimeout = 180 };
        using OdbcDataReader reader = command.ExecuteReader();
        var page = new List<object>(PageSize);
        while (reader.Read())
        {
            string serviceCode = Convert.ToString(reader[2])?.Trim() ?? string.Empty;
            string counterpartyRef = HashCounterparty(Convert.ToString(reader[3]));
            if (serviceCode.Length == 0 && counterpartyRef.Length == 0) continue;
            page.Add(new
            {
                company_key = Convert.ToString(reader[0]),
                accumulator_code = Convert.ToString(reader[1]),
                service_code = serviceCode,
                counterparty_ref = counterpartyRef,
                frequency = Convert.ToInt32(reader[4]),
                last_used_at = Convert.ToDateTime(reader[5]).ToUniversalTime().ToString("O"),
            });
            if (page.Count == PageSize)
            {
                await SendPage("accumulator_observations", batch, page, token);
                page.Clear();
            }
        }
        if (page.Count > 0)
            await SendPage("accumulator_observations", batch, page, token);
    }

    private static string HashCounterparty(string? value)
    {
        string digits = new((value ?? string.Empty).Where(char.IsDigit).ToArray());
        if (digits.Length is not (11 or 14)) return string.Empty;
        byte[] digest = SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(digits));
        return Convert.ToHexString(digest).ToLowerInvariant()[..24];
    }

    private async Task SendPage(string capability, string batch, List<object> rows,
        CancellationToken token) => await client.PostAsync($"api/agent/v2/sync/{capability}",
            new { batch_id = batch, rows }, token);

    private static void ExtractBackup(string archivePath, string key, string extractionRoot)
    {
        Directory.CreateDirectory(extractionRoot);
        string root = Path.GetFullPath(extractionRoot).TrimEnd(
            Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        string allowedPrefix = root + Path.DirectorySeparatorChar;
        using IArchive archive = ZipArchive.OpenArchive(archivePath, new ReaderOptions { Password = key });
        List<IArchiveEntry> entries = archive.Entries.Where(entry => !entry.IsDirectory).ToList();
        if (entries.Count == 0) throw new InvalidDataException("O backup não contém arquivos para extrair.");

        foreach (IArchiveEntry entry in entries)
        {
            string entryPath = (entry.Key ?? string.Empty).Replace('/', Path.DirectorySeparatorChar);
            if (string.IsNullOrWhiteSpace(entryPath)
                || entryPath.IndexOf('\0') >= 0
                || Path.IsPathRooted(entryPath))
                throw new InvalidDataException("O backup contém um caminho de arquivo inválido.");
            string destination = Path.GetFullPath(Path.Combine(root, entryPath));
            if (!destination.StartsWith(allowedPrefix, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("O backup tentou extrair arquivo fora da pasta temporária.");
        }

        foreach (IArchiveEntry entry in entries)
            entry.WriteToDirectory(extractionRoot, new ExtractionOptions
                { ExtractFullPath = true, Overwrite = true, PreserveFileTime = true });
    }

    private static string Friendly(Exception error) => error switch
    {
        InvalidDataException => error.Message,
        OdbcException => "Não foi possível abrir contabil.db. Verifique o SQL Anywhere 16/17 e as credenciais do banco.",
        _ => "O backup não pôde ser processado. Tente novamente ou envie o diagnóstico ao suporte."
    };
}
