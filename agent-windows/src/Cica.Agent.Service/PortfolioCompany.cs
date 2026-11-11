using System.Globalization;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Cica.Agent.Service;

internal sealed record PortfolioCompany(
    [property: JsonPropertyName("codigo")] string Code,
    [property: JsonPropertyName("nome")] string Name,
    [property: JsonPropertyName("cnpj_masked"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Cnpj,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("registration_raw"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? RegistrationRaw = null,
    [property: JsonPropertyName("registration_type_code"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int? RegistrationTypeCode = null)
{
    internal static PortfolioCompany FromSource(object code, object name, object cnpj, object status,
        AgentSyncScope scope, object? registrationType = null)
    {
        string key = Convert.ToString(code, CultureInfo.InvariantCulture) ?? "";
        string label = Convert.ToString(name, CultureInfo.InvariantCulture)?.Trim() ?? "";
        string rawStatus = Convert.ToString(status, CultureInfo.InvariantCulture)?.Trim() ?? "";
        string document = Convert.ToString(cnpj, CultureInfo.InvariantCulture)?.Trim() ?? "";
        if (!Regex.IsMatch(key, @"\A[1-9][0-9]{0,17}\z") || label.Length is < 1 or > 180
            || scope.CompanyStatusMap?.ContainsKey(rawStatus) is not true
            || (scope.IsActiveOnly && !scope.CompanyStatusMap[rawStatus])
            || (document.Length > 0 && !Regex.IsMatch(document, @"\A[0-9./-]+\z")))
            throw new InvalidDataException("Cadastro inválido ou situação de origem não revisada; carga incompleta.");
        if (scope.IsActiveOnly)
        {
            if (document.Length > 14)
                throw new InvalidDataException("Inscrição de origem excede o limite literal; carga incompleta.");
            int? kind = null;
            if (registrationType is not null and not DBNull)
            {
                if (!int.TryParse(Convert.ToString(registrationType, CultureInfo.InvariantCulture),
                    NumberStyles.None, CultureInfo.InvariantCulture, out int value) || value is < 0 or > 255)
                    throw new InvalidDataException("Tipo de inscrição de origem inválido; carga incompleta.");
                kind = value;
            }
            return new(key, label, null, rawStatus, document, kind);
        }
        string digits = new string(document.Where(char.IsAsciiDigit).ToArray());
        if (document.Length > 0 && digits.Length != 14)
            throw new InvalidDataException("Identificação de empresa fora do contrato; carga incompleta.");
        string formatted = digits.Length == 0 ? "" :
            $"{digits[..2]}.{digits.Substring(2, 3)}.{digits.Substring(5, 3)}/{digits.Substring(8, 4)}-{digits.Substring(12, 2)}";
        return new(key, label, formatted, rawStatus);
    }
}
