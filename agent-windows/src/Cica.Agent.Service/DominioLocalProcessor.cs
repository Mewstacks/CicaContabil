using System.Data.Odbc;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class DominioLocalProcessor(AgentConfig config, AgentClient client)
{
    private const int PageSize = 500;
    private const string CompaniesSql = "SELECT TOP 500 codi_emp, nome_emp, cgce_emp " +
        "FROM bethadba.geempre WHERE stat_emp = 'A' AND codi_emp > ? ORDER BY codi_emp";

    internal async Task RunOnce(CancellationToken token)
    {
        if (string.IsNullOrWhiteSpace(config.Dsn)) return;
        using var connection = new OdbcConnection($"DSN={config.Dsn};UID={config.DatabaseUser};PWD={config.DatabasePassword}");
        connection.ConnectionTimeout = 20;
        await connection.OpenAsync(token);
        string cursor = "";
        while (!token.IsCancellationRequested)
        {
            using var command = new OdbcCommand(CompaniesSql, connection) { CommandTimeout = 60 };
            command.Parameters.AddWithValue("@after_company", cursor);
            using var reader = await command.ExecuteReaderAsync(token);
            var page = new List<object>(PageSize);
            while (await reader.ReadAsync(token))
            {
                string code = Convert.ToString(reader[0]) ?? "";
                if (string.IsNullOrWhiteSpace(code)) continue;
                cursor = code;
                page.Add(new { codigo = code, nome = Convert.ToString(reader[1]) ?? "", cnpj_masked = FormatCnpj(Convert.ToString(reader[2])) });
            }
            if (page.Count == 0) return;
            using JsonDocument _ = await client.PostAsync("api/agent/v2/dominio/companies", new { companies = page }, token);
            if (page.Count < PageSize) return;
        }
        await SendBankEntries(token);
    }

    private async Task SendBankEntries(CancellationToken token)
    {
        const string sql = "SELECT TOP 500 CAST(i.CODI_EMP AS VARCHAR(64)) || '|' || CAST(i.I_LANCAMENTO AS VARCHAR(64)) || '|' || CAST(i.I_ITEM AS VARCHAR(64)), i.CODI_EMP, i.DATA_ITEM, i.HISTORICO, i.VALOR, i.TIPO FROM bethadba.CTEXTRATO_BANCARIO_LANCAMENTO_ITEM i WHERE CAST(i.CODI_EMP AS VARCHAR(64)) || '|' || CAST(i.I_LANCAMENTO AS VARCHAR(64)) || '|' || CAST(i.I_ITEM AS VARCHAR(64)) > ? ORDER BY 1";
        using var connection = new OdbcConnection($"DSN={config.Dsn};UID={config.DatabaseUser};PWD={config.DatabasePassword}");
        await connection.OpenAsync(token); string cursor = "";
        while (!token.IsCancellationRequested) {
            using var command = new OdbcCommand(sql, connection); command.Parameters.AddWithValue("@after", cursor);
            using var reader = await command.ExecuteReaderAsync(token); var page = new List<object>(PageSize);
            while (await reader.ReadAsync(token)) { cursor = Convert.ToString(reader[0]) ?? ""; page.Add(new { source_id = cursor, company_code = Convert.ToString(reader[1]) ?? "", occurred_on = Convert.ToDateTime(reader[2]).ToString("yyyy-MM-dd"), description = Convert.ToString(reader[3]) ?? "", amount = Convert.ToDecimal(reader[4]), direction = Convert.ToString(reader[5]) ?? "", is_linked = false }); }
            if (page.Count == 0) return;
            using JsonDocument _ = await client.PostAsync("api/agent/v2/dominio/bank-entries", new { rows = page }, token);
            if (page.Count < PageSize) return;
        }
    }

    private static string FormatCnpj(string? value)
    {
        string digits = new string((value ?? "").Where(char.IsDigit).ToArray());
        return digits.Length == 14 ? $"{digits[..2]}.{digits.Substring(2, 3)}.{digits.Substring(5, 3)}/{digits.Substring(8, 4)}-{digits.Substring(12, 2)}" : "";
    }
}
