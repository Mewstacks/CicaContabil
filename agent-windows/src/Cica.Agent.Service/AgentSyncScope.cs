using System.Globalization;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Cica.Agent.Service;

internal sealed record AgentSyncScope(
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("financial_account_id")] string FinancialAccountId,
    [property: JsonPropertyName("company_code")] string CompanyCode,
    [property: JsonPropertyName("account_reference")] string AccountReference,
    [property: JsonPropertyName("period_start")] string PeriodStart,
    [property: JsonPropertyName("period_end")] string PeriodEnd,
    [property: JsonPropertyName("statement_ids")] string[] StatementIds,
    [property: JsonPropertyName("revision")] string Revision,
    [property: JsonPropertyName("organization_id")] string? OrganizationId = null,
    [property: JsonPropertyName("datasets")] string[]? Datasets = null,
    [property: JsonPropertyName("company_status_map")] Dictionary<string, bool>? CompanyStatusMap = null)
{
    internal const string Protocol = "scoped-v2";
    internal const string LegacyProtocol = "scoped-v1";
    internal bool IsPortfolio => Version == "dominio-portfolio-v1";
    internal DateTime Start => DateTime.ParseExact(PeriodStart, "yyyy-MM-dd", CultureInfo.InvariantCulture);
    internal DateTime EndExclusive => DateTime.ParseExact(PeriodEnd, "yyyy-MM-dd", CultureInfo.InvariantCulture).AddDays(1);

    internal void Validate()
    {
        if (IsPortfolio)
        {
            if (!Guid.TryParse(OrganizationId, out _)
                || Datasets is null || !Datasets.SequenceEqual(new[] { "companies" })
                || CompanyStatusMap is null || CompanyStatusMap.Count is < 1 or > 16
                || CompanyStatusMap.Keys.Any(key => !Regex.IsMatch(key, @"\A[A-Z0-9_-]{1,16}\z"))
                || Revision is null || !Regex.IsMatch(Revision, @"\A[0-9a-f]{64}\z")
                || !DateOnly.TryParseExact(PeriodStart, "yyyy-MM-dd", CultureInfo.InvariantCulture,
                    DateTimeStyles.None, out DateOnly portfolioStart)
                || !DateOnly.TryParseExact(PeriodEnd, "yyyy-MM-dd", CultureInfo.InvariantCulture,
                    DateTimeStyles.None, out DateOnly portfolioEnd)
                || portfolioStart > portfolioEnd || portfolioEnd > DateOnly.FromDateTime(DateTime.UtcNow))
                throw new InvalidDataException("Manifesto de carteira inválido ou fonte não implementada.");
            return;
        }
        if (Version != "dominio-pilot-v1" || !Guid.TryParse(FinancialAccountId, out _)
            || string.IsNullOrWhiteSpace(CompanyCode) || !Regex.IsMatch(CompanyCode, @"\A[0-9]{1,18}\z")
            || string.IsNullOrWhiteSpace(AccountReference) || AccountReference.Length > 160
            || StatementIds is null || StatementIds.Length is < 1 or > 500
            || StatementIds.Any(id => id is null || !Regex.IsMatch(id, @"\A[0-9]{1,18}\z"))
            || StatementIds.Distinct(StringComparer.Ordinal).Count() != StatementIds.Length
            || Revision is null || !Regex.IsMatch(Revision, @"\A[0-9a-f]{64}\z"))
            throw new InvalidDataException("O recorte financeiro do piloto está ausente ou inválido.");
        if (!DateOnly.TryParseExact(PeriodStart, "yyyy-MM-dd", CultureInfo.InvariantCulture,
                DateTimeStyles.None, out DateOnly start)
            || !DateOnly.TryParseExact(PeriodEnd, "yyyy-MM-dd", CultureInfo.InvariantCulture,
                DateTimeStyles.None, out DateOnly end)
            || start.Day != 1 || start.Year != end.Year || start.Month != end.Month
            || end.Day != DateTime.DaysInMonth(start.Year, start.Month)
            || end >= DateOnly.FromDateTime(DateTime.UtcNow))
            throw new InvalidDataException("O recorte exige uma competência anterior completa.");
    }
}
