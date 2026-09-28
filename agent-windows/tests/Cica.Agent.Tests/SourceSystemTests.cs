using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

/// O catálogo carrega os contratos dos dois ERPs, e é ele que decide o que cada
/// conector pode executar. Estes testes provam que o recorte por origem existe
/// mesmo quando o código da consulta é o mesmo nos dois.
public sealed class SourceSystemTests
{
    [Theory]
    [InlineData("dominio")]
    [InlineData("siescon")]
    public void Cada_erp_tem_contratos_proprios(string sourceSystem)
    {
        var contratos = DatasetCatalog.All
            .Where(item => item.SourceSystem == sourceSystem)
            .ToArray();

        Assert.NotEmpty(contratos);
        Assert.All(contratos, item => Assert.Equal(sourceSystem, item.SourceSystem));
    }

    [Fact]
    public void O_contrato_de_folha_do_siescon_esta_validado()
    {
        // É o que o cálculo de custo precisa, e foi por onde o levantamento do
        // Siescon começou. `GetForRun` só devolve contrato validado.
        var folha = DatasetCatalog.GetForRun("siescon", "salaries", "full");

        Assert.True(folha.Validated);
        Assert.Equal("siescon", folha.SourceSystem);
    }

    [Fact]
    public void Contrato_com_parametro_declara_a_ordem_que_o_sql_usa()
    {
        // Os parâmetros são posicionais: a ordem declarada tem de bater com a
        // ordem das interrogações, senão o valor entra na coluna errada.
        foreach (var dataset in DatasetCatalog.All.Where(item => item.Parameters.Count > 0))
        {
            Assert.Equal(
                dataset.Parameters.Count,
                dataset.Sql.Count(character => character == '?'));
            Assert.Equal(
                dataset.Parameters.Select(item => item.Name).Distinct().Count(),
                dataset.Parameters.Count);
        }
    }
}
