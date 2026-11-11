namespace Cica.Agent.Service;

/// <summary>The count and page must cover exactly the same reviewed source selection.</summary>
internal sealed record PortfolioReadPlan(string CountSql, string PageSql, string[] Statuses)
{
    internal static PortfolioReadPlan FromScope(AgentSyncScope scope)
    {
        scope.Validate();
        if (!scope.IsPortfolio) throw new InvalidDataException("Manifesto de carteira ausente.");
        string[] statuses = scope.IsActiveOnly
            ? scope.CompanyStatusMap!.Where(pair => pair.Value).Select(pair => pair.Key)
                .Order(StringComparer.Ordinal).ToArray() : [];
        string filter = statuses.Length == 0 ? "" :
            "stat_emp IN (" + string.Join(",", statuses.Select(_ => "?")) + ") AND ";
        string source = "FROM bethadba.geempre";
        string count = "SELECT COUNT(*) " + source +
            (statuses.Length == 0 ? "" : " WHERE " + filter[..^5]);
        string page = "SELECT TOP 500 codi_emp, nome_emp, cgce_emp, stat_emp " + source +
            " WHERE " + filter + "codi_emp > ? ORDER BY codi_emp";
        return new(count, page, statuses);
    }
}
