using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

/// O catálogo é a única coisa entre a nuvem e um SELECT rodando na máquina do
/// escritório. Estes testes provam que ele carrega com os contratos reais e que
/// recusa o que tem de recusar.
public sealed class DatasetCatalogTests
{
    [Fact]
    public void O_catalogo_carrega_e_confere_o_hash_de_toda_consulta()
    {
        // `SelfVerify` percorre o manifesto inteiro: qualquer hash divergente,
        // recurso ausente ou SQL fora do contrato levanta aqui.
        DatasetCatalog.SelfVerify();

        Assert.NotEmpty(DatasetCatalog.All);
        Assert.Equal(64, DatasetCatalog.ManifestSha256.Length);
    }

    [Fact]
    public void Os_dois_erps_convivem_porque_a_chave_carrega_a_origem()
    {
        // `companies` existe nos dois, e são contratos diferentes.
        var dominio = DatasetCatalog.All.Single(
            item => item.SourceSystem == "dominio" && item.Code == "companies");
        var siescon = DatasetCatalog.All.Single(
            item => item.SourceSystem == "siescon" && item.Code == "companies");

        Assert.NotEqual(dominio.QuerySha256, siescon.QuerySha256);
        Assert.NotEqual(DatasetCatalog.Key("dominio", "companies"),
            DatasetCatalog.Key("siescon", "companies"));
    }

    [Fact]
    public void O_conector_so_alcanca_o_contrato_do_proprio_erp()
    {
        // `companies` existe nos dois ERPs. Pedir pelo código não basta: o conector
        // apontado para o Domínio recebe o contrato do Domínio, e nunca o do
        // Siescon, mesmo que a nuvem mande o mesmo nome.
        var escolhido = DatasetCatalog.GetForRun("dominio", "companies", "full");
        var doSiescon = DatasetCatalog.All.Single(
            item => item.SourceSystem == "siescon" && item.Code == "companies");

        Assert.Equal("dominio", escolhido.SourceSystem);
        Assert.NotEqual(doSiescon.Sql, escolhido.Sql);
    }

    [Fact]
    public void Consulta_que_nao_existe_no_catalogo_e_recusada()
    {
        var erro = Assert.Throws<InvalidOperationException>(
            () => DatasetCatalog.GetForRun("dominio", "consulta_inventada", "full"));

        Assert.Contains("desconhecida", erro.Message);
    }

    [Fact]
    public void Consulta_nao_validada_nao_e_despachada()
    {
        // `salaries` do Domínio está no manifesto como ainda não validado.
        var erro = Assert.Throws<InvalidOperationException>(
            () => DatasetCatalog.GetForRun("dominio", "salaries", "full"));

        Assert.Contains("não validada", erro.Message);
    }

    [Fact]
    public void Modo_de_execucao_fora_do_contrato_e_recusado()
    {
        // `companies` é um retrato completo; não existe ciclo incremental dele.
        var erro = Assert.Throws<InvalidOperationException>(
            () => DatasetCatalog.GetForRun("dominio", "companies", "incremental"));

        Assert.Contains("não permitido", erro.Message);
    }

    [Fact]
    public void Toda_consulta_e_um_select_com_os_parametros_que_declara()
    {
        foreach (var dataset in DatasetCatalog.All)
        {
            string inicio = dataset.Sql.TrimStart();
            Assert.True(
                inicio.StartsWith("SELECT", StringComparison.OrdinalIgnoreCase)
                    || inicio.StartsWith("WITH", StringComparison.OrdinalIgnoreCase),
                $"{dataset.Code} não começa com SELECT.");
            Assert.DoesNotContain(";", dataset.Sql);
            Assert.Equal(
                dataset.Parameters.Count,
                dataset.Sql.Count(character => character == '?'));
        }
    }
}
