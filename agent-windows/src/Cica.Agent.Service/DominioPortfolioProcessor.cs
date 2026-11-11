using System.Data.Odbc;
using System.Globalization;
using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class DominioPortfolioProcessor(AgentConfig config, AgentClient client)
{
    internal async Task RunOnce(CancellationToken token)
    {
        AgentSyncScope scope = config.SyncScope
            ?? throw new InvalidDataException("Manifesto de carteira ausente.");
        scope.Validate();
        if (!scope.IsPortfolio) throw new InvalidDataException("Manifesto incompatível.");
        PortfolioReadPlan plan = PortfolioReadPlan.FromScope(scope);
        using var connection = new OdbcConnection(LocalOdbcConnection.Build(
            config.Dsn!, config.DatabaseUser, config.DatabasePassword, config.UseDsnAuthentication));
        connection.ConnectionTimeout = 20;
        await connection.OpenAsync(token);
        int count = await CountCompanies(connection, plan, token);
        using JsonDocument opened = await client.PostAsync("api/agent/v2/dominio/portfolio/companies",
            new { action = "open", scope_revision = scope.Revision, expected_count = count }, token);
        string runId = opened.RootElement.GetProperty("run_id").GetString()!;
        string after = opened.RootElement.GetProperty("after").GetString()!;
        while (!token.IsCancellationRequested)
        {
            using var command = new OdbcCommand(plan.PageSql, connection) { CommandTimeout = 60 };
            AddStatuses(command, plan);
            command.Parameters.Add("@after", OdbcType.Decimal).Value = decimal.Parse(after, CultureInfo.InvariantCulture);
            var page = new List<PortfolioCompany>(500);
            using (var reader = await command.ExecuteReaderAsync(token))
            {
                while (await reader.ReadAsync(token))
                    page.Add(PortfolioCompany.FromSource(reader[0], reader[1], reader[2], reader[3], scope));
            }
            bool complete = page.Count < 500;
            int sourceCount = complete ? await CountCompanies(connection, plan, token) : count;
            using JsonDocument receipt = await client.PostAsync("api/agent/v2/dominio/portfolio/companies",
                new { action = "page", scope_revision = scope.Revision, run_id = runId,
                    after, rows = page, complete, source_count = sourceCount }, token);
            string acknowledged = receipt.RootElement.GetProperty("after").GetString()!;
            string expected = page.Count == 0 ? after : page[^1].Code;
            if (acknowledged != expected || receipt.RootElement.GetProperty("run_id").GetString() != runId
                || receipt.RootElement.GetProperty("complete").GetBoolean() != complete)
                throw new InvalidDataException("Confirmação de página de carteira inconsistente.");
            after = acknowledged;
            if (complete) break;
        }
    }

    private static void AddStatuses(OdbcCommand command, PortfolioReadPlan plan)
    {
        for (int i = 0; i < plan.Statuses.Length; i++)
            command.Parameters.Add("@status" + i, OdbcType.VarChar, 16).Value = plan.Statuses[i];
    }

    private static async Task<int> CountCompanies(OdbcConnection connection, PortfolioReadPlan plan,
        CancellationToken token)
    {
        using var command = new OdbcCommand(plan.CountSql, connection)
            { CommandTimeout = 60 };
        AddStatuses(command, plan);
        long value = Convert.ToInt64(await command.ExecuteScalarAsync(token), CultureInfo.InvariantCulture);
        if (value is < 0 or > 1_000_000)
            throw new InvalidDataException("Carteira excede o limite explícito; carga não iniciada.");
        return (int)value;
    }
}
