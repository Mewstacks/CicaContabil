using System.Globalization;

namespace Cica.Agent.Service;

/// Como um valor lido do ERP vira JSON sem perder o que o servidor precisa.
///
/// Portado do conector do Lucrums. Vive na biblioteca de contratos, e não junto do
/// leitor ODBC, porque é a metade da conversa que o servidor enxerga: a data que
/// sai daqui é a data que o processamento vai comparar com a janela reconciliada,
/// e um formato diferente por ERP faria a mesma linha ser lida de dois jeitos.
///
/// Decimal sai como texto de propósito. Em JSON ele viraria ponto flutuante, e um
/// honorário somado sobre a carteira inteira não sobrevive a isso.
internal static class DatasetValue
{
    internal const string DateFormat = "yyyy-MM-dd";
    internal const string TimeFormat = "HH:mm:ss.fffffff";
    internal const string TimestampFormat = "yyyy-MM-dd'T'HH:mm:ss.fffffff";

    internal static object? Normalize(object? value, DatasetValueKind kind)
    {
        if (value is null or DBNull) return null;
        return kind switch
        {
            DatasetValueKind.Date => value switch
            {
                DateTime date => date.ToString(DateFormat, CultureInfo.InvariantCulture),
                _ => Convert.ToDateTime(value, CultureInfo.InvariantCulture)
                    .ToString(DateFormat, CultureInfo.InvariantCulture),
            },
            DatasetValueKind.Time => value switch
            {
                TimeSpan time => time.ToString(@"hh\:mm\:ss\.fffffff", CultureInfo.InvariantCulture),
                DateTime time => time.ToString(TimeFormat, CultureInfo.InvariantCulture),
                _ => Convert.ToDateTime(value, CultureInfo.InvariantCulture)
                    .ToString(TimeFormat, CultureInfo.InvariantCulture),
            },
            DatasetValueKind.Timestamp => Convert.ToDateTime(value, CultureInfo.InvariantCulture)
                .ToString(TimestampFormat, CultureInfo.InvariantCulture),
            _ => value switch
            {
                decimal number => number.ToString(CultureInfo.InvariantCulture),
                byte[] bytes => Convert.ToBase64String(bytes),
                string or int or long or short or bool => value,
                _ => Convert.ToString(value, CultureInfo.InvariantCulture),
            },
        };
    }
}

internal enum DatasetValueKind
{
    Other,
    Date,
    Time,
    Timestamp,
}
