using System.Globalization;
using System.Text.Json;

namespace Cica.Agent.Service;

/// Parâmetro de um job, como a nuvem o manda: nome, valor JSON e tipo ODBC.
internal sealed record JobParameter(string Name, JsonElement Value, string OdbcType);

/// Parâmetro já conferido contra o contrato e convertido para o tipo que o ODBC espera.
internal sealed record BoundParameter(string Name, string OdbcType, string Type, object Value);

internal sealed class ParameterBindingException(string message) : InvalidOperationException(message);

/// A conversão texto -> valor tipado de um parâmetro de dataset. Existe num lugar só:
/// o serviço (ODBC x64 em processo) e a ponte de 32 bits usam esta mesma função.
internal static class DatasetParameterValue
{
    internal static object Convert(string type, string text) => type switch
    {
        "integer" => int.Parse(text, CultureInfo.InvariantCulture),
        "decimal" => decimal.Parse(text, CultureInfo.InvariantCulture),
        "date" => DateTime.ParseExact(text, DatasetValue.DateFormat, CultureInfo.InvariantCulture),
        "string" => text,
        _ => throw new InvalidOperationException("Tipo de parâmetro não suportado."),
    };
}

/// Liga os parâmetros que a nuvem mandou aos que o contrato declara.
///
/// O vínculo no ODBC é posicional, então o que vale é a ordem do manifesto: mesmos
/// nomes, mesma ordem, mesmo tipo ODBC. Nome trocado ou fora de ordem passaria uma
/// data como código de empresa em silêncio. As mensagens citam só o nome do
/// parâmetro, nunca o valor.
internal static class DatasetParameterBinder
{
    internal static IReadOnlyList<BoundParameter> Bind(
        DatasetDefinition dataset, IReadOnlyList<JobParameter> supplied)
    {
        if (supplied.Count != dataset.Parameters.Count)
            throw new ParameterBindingException("Quantidade de parâmetros divergente do contrato.");

        List<BoundParameter> bound = new(supplied.Count);
        for (int index = 0; index < supplied.Count; index++)
        {
            DatasetParameter expected = dataset.Parameters[index];
            JobParameter given = supplied[index];
            if (!string.Equals(given.Name, expected.Name, StringComparison.Ordinal))
                throw new ParameterBindingException(
                    $"Parâmetro {index} fora de ordem ou com nome divergente (esperado {expected.Name}).");
            if (!string.Equals(given.OdbcType, expected.OdbcType, StringComparison.Ordinal))
                throw new ParameterBindingException(
                    $"Tipo ODBC divergente em {expected.Name} (esperado {expected.OdbcType}).");
            bound.Add(new BoundParameter(
                expected.Name, expected.OdbcType, expected.Type, ConvertValue(expected, given.Value)));
        }
        return bound;
    }

    private static object ConvertValue(DatasetParameter expected, JsonElement value)
    {
        string? text = value.ValueKind switch
        {
            JsonValueKind.String => value.GetString(),
            JsonValueKind.Number when expected.Type is "integer" or "decimal" => value.GetRawText(),
            _ => null,
        };
        if (text is null)
            throw new ParameterBindingException($"Valor de {expected.Name} com formato inválido.");
        try
        {
            return DatasetParameterValue.Convert(expected.Type, text);
        }
        catch (Exception error) when (error is FormatException or OverflowException)
        {
            throw new ParameterBindingException($"Valor de {expected.Name} não é {expected.Type}.");
        }
    }
}
