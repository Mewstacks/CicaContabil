using System.Globalization;
using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

/// A conversão de valor é onde um ERP e o servidor se desentendem em silêncio:
/// a linha entra, o número está errado, e ninguém percebe até a margem não fechar.
public sealed class DatasetValueTests
{
    [Fact]
    public void Decimal_sai_como_texto_para_nao_virar_ponto_flutuante()
    {
        // Um honorário somado sobre a carteira inteira não sobrevive a float.
        object? convertido = DatasetValue.Normalize(1234.56m, DatasetValueKind.Other);

        Assert.Equal("1234.56", convertido);
        Assert.IsType<string>(convertido);
    }

    [Fact]
    public void Decimal_nao_depende_da_regiao_da_maquina()
    {
        // Numa máquina em português a vírgula viraria separador decimal, e o
        // servidor leria outro número.
        var anterior = CultureInfo.CurrentCulture;
        try
        {
            CultureInfo.CurrentCulture = new CultureInfo("pt-BR");
            Assert.Equal("1234.56", DatasetValue.Normalize(1234.56m, DatasetValueKind.Other));
        }
        finally
        {
            CultureInfo.CurrentCulture = anterior;
        }
    }

    [Fact]
    public void Data_sai_no_formato_que_a_janela_reconciliada_compara()
    {
        Assert.Equal(
            "2026-09-10",
            DatasetValue.Normalize(new DateTime(2026, 9, 10, 14, 30, 0), DatasetValueKind.Date));
    }

    [Fact]
    public void Hora_preserva_os_segundos_e_a_fracao()
    {
        // A duração de uma sessão sai da diferença entre início e fim: truncar
        // segundos mudaria o custo da hora.
        Assert.Equal(
            "09:30:15.0000000",
            DatasetValue.Normalize(new TimeSpan(0, 9, 30, 15), DatasetValueKind.Time));
    }

    [Fact]
    public void Nulo_do_banco_continua_nulo()
    {
        Assert.Null(DatasetValue.Normalize(null, DatasetValueKind.Other));
        Assert.Null(DatasetValue.Normalize(DBNull.Value, DatasetValueKind.Other));
    }

    [Fact]
    public void Binario_vira_base64_em_vez_de_texto_ilegivel()
    {
        Assert.Equal("AQID", DatasetValue.Normalize(new byte[] { 1, 2, 3 }, DatasetValueKind.Other));
    }
}
