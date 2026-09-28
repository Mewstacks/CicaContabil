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
    public void Usuario_siescon_fica_bloqueado_ate_confirmar_campo_de_atividade()
    {
        Assert.Throws<InvalidOperationException>(
            () => DatasetCatalog.GetForRun("siescon", "users", "full"));
    }

    [Fact]
    public void Colunas_de_contexto_nao_sao_exigidas_do_select_da_folha()
    {
        var folha = DatasetCatalog.GetForRun("siescon", "salaries", "full");

        Assert.Equal(
            ["i_empregados", "nome", "salario_mais_recente"],
            folha.ResultColumns);
    }

    [Fact]
    public void Desvio_de_colunas_falha_antes_de_transmitir_linhas()
    {
        string[] esperadas = ["codi_emp", "razao_emp", "cgce_emp", "situacao"];
        DatasetResultContract.ValidateColumns(
            esperadas, ["CODI_EMP", "RAZAO_EMP", "CGCE_EMP", "SITUACAO"]);

        Assert.Throws<InvalidOperationException>(() => DatasetResultContract.ValidateColumns(
            esperadas, ["codi_emp", "razao_emp", "cgce_emp"]));
        Assert.Throws<InvalidOperationException>(() => DatasetResultContract.ValidateColumns(
            esperadas, ["codi_emp", "razao_emp", "documento", "situacao"]));
        Assert.Throws<InvalidOperationException>(() => DatasetResultContract.ValidateColumns(
            esperadas, ["codi_emp", "razao_emp", "cgce_emp", "cgce_emp"]));
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
