using System.Net;
using System.Text.Json;
using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

/// Binder de parâmetros e fila da Contraprova, sem ODBC nem rede: o transporte e a
/// leitura são falsos, o catálogo e o protocolo são os reais.
public sealed class ContraprovaTests
{
    private const string JobId = "11111111-2222-3333-4444-555555555555";

    private static readonly DatasetDefinition Real =
        DatasetCatalog.TryGet("dominio", "fiscal_counterparts")!;

    // O manifesto real mantém o dataset como não validado; os testes de execução usam
    // a mesma definição com `Validated` ligado.
    private static readonly DatasetDefinition Validated = Real with { Validated = true };

    private static string Parameters(string? first = "codi_emp_sai", string type = "Int") => $$"""
        [{"name":"{{first}}","value":123,"odbc_type":"{{type}}"},
         {"name":"start_sai","value":"2026-08-01","odbc_type":"Date"},
         {"name":"end_sai","value":"2026-10-31","odbc_type":"Date"},
         {"name":"codi_emp_ent","value":123,"odbc_type":"Int"},
         {"name":"start_ent","value":"2026-08-01","odbc_type":"Date"},
         {"name":"end_ent","value":"2026-10-31","odbc_type":"Date"}]
        """;

    private static JsonDocument Job(
        string? code = "fiscal_counterparts",
        string? sha = null,
        string? parameters = null,
        int maxRows = 200000,
        int pageSize = 500) => JsonDocument.Parse($$$"""
        {"job":{"id":"{{{JobId}}}","dataset_code":"{{{code}}}","schema_version":1,
         "query_sha256":"{{{sha ?? Real.QuerySha256}}}","parameters":{{{parameters ?? Parameters()}}},
         "max_rows":{{{maxRows}}},"page_size":{{{pageSize}}}}}
        """);

    private sealed class FakeServer(JsonDocument? next, HttpStatusCode? nextStatus = null)
    {
        internal List<(string Path, JsonElement Body)> Calls { get; } = [];
        internal Func<string, Exception?>? Reject { get; set; }

        internal Task<JsonDocument> Post(string path, object payload, CancellationToken token)
        {
            Calls.Add((path, JsonSerializer.SerializeToElement(payload)));
            if (path.EndsWith("/next"))
            {
                if (nextStatus is { } status)
                    throw new HttpRequestException("x", null, status);
                return Task.FromResult(next ?? JsonDocument.Parse("""{"job":null}"""));
            }
            if (Reject?.Invoke(path) is { } error) throw error;
            return Task.FromResult(JsonDocument.Parse("""{"status":"accepted"}"""));
        }

        internal IEnumerable<(string Path, JsonElement Body)> Under(string suffix) =>
            Calls.Where(call => call.Path.EndsWith(suffix));

        internal string FailureCode() =>
            Under("/failure").Single().Body.GetProperty("error_code").GetString()!;
    }

    private sealed class FakeSource(int rows, Exception? error = null) : IDatasetRowSource
    {
        internal int Reads { get; private set; }
        internal IReadOnlyList<BoundParameter>? Bound { get; private set; }

        public async IAsyncEnumerable<Dictionary<string, object?>> ReadAsync(
            DatasetDefinition dataset,
            IReadOnlyList<BoundParameter> parameters,
            [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken token)
        {
            Reads++;
            Bound = parameters;
            await Task.Yield();
            if (error is not null) throw error;
            for (int index = 0; index < rows; index++)
                yield return new Dictionary<string, object?>
                {
                    ["chave_nfe"] = new string('1', 44),
                    ["direcao"] = index % 2 == 0 ? "S" : "E",
                    ["uf"] = index % 3 == 0 ? null : "SP ",
                };
        }
    }

    private static ContraprovaJobRunner Runner(
        FakeServer server, FakeSource source, DatasetDefinition? definition) =>
        new(server.Post, source, (_, _) => definition, "dominio");

    // --- binder -------------------------------------------------------------

    private static IReadOnlyList<JobParameter> Supplied(string json) =>
        JsonDocument.Parse(json).RootElement.EnumerateArray()
            .Select(item => new JobParameter(
                item.GetProperty("name").GetString()!,
                item.GetProperty("value").Clone(),
                item.GetProperty("odbc_type").GetString()!))
            .ToList();

    [Fact]
    public void Binder_produz_valores_tipados_na_ordem_do_manifesto()
    {
        var bound = DatasetParameterBinder.Bind(Real, Supplied(Parameters()));

        Assert.Equal(
            ["codi_emp_sai", "start_sai", "end_sai", "codi_emp_ent", "start_ent", "end_ent"],
            bound.Select(item => item.Name));
        Assert.Equal(123, bound[0].Value);
        Assert.Equal(new DateTime(2026, 8, 1), bound[1].Value);
        Assert.Equal("Int", bound[3].OdbcType);
    }

    [Fact]
    public void Binder_recusa_nome_trocado()
    {
        var erro = Assert.Throws<ParameterBindingException>(() =>
            DatasetParameterBinder.Bind(Real, Supplied(Parameters(first: "codi_emp"))));

        Assert.Contains("codi_emp_sai", erro.Message);
    }

    [Fact]
    public void Binder_recusa_ordem_trocada()
    {
        var itens = Supplied(Parameters()).ToList();
        (itens[1], itens[2]) = (itens[2], itens[1]);

        Assert.Throws<ParameterBindingException>(() => DatasetParameterBinder.Bind(Real, itens));
    }

    [Fact]
    public void Binder_recusa_tipo_odbc_errado_e_quantidade_errada()
    {
        Assert.Throws<ParameterBindingException>(() =>
            DatasetParameterBinder.Bind(Real, Supplied(Parameters(type: "Date"))));
        Assert.Throws<ParameterBindingException>(() =>
            DatasetParameterBinder.Bind(Real, Supplied(Parameters()).Take(5).ToList()));
    }

    [Fact]
    public void Binder_recusa_valor_que_nao_e_do_tipo_sem_vazar_o_valor()
    {
        var itens = Supplied(Parameters()).ToList();
        itens[1] = itens[1] with { Value = JsonDocument.Parse("\"segredo-nao-data\"").RootElement };

        var erro = Assert.Throws<ParameterBindingException>(
            () => DatasetParameterBinder.Bind(Real, itens));

        Assert.DoesNotContain("segredo", erro.Message);
    }

    [Fact]
    public void Binder_aceita_dataset_sem_parametro()
    {
        var semParametro = DatasetCatalog.All.First(item => item.Parameters.Count == 0);

        Assert.Empty(DatasetParameterBinder.Bind(semParametro, []));
    }

    // --- catálogo -----------------------------------------------------------

    [Fact]
    public void Dataset_sob_demanda_existe_no_catalogo_e_nao_entra_no_ciclo()
    {
        Assert.True(Real.IsOnDemand);
        Assert.False(Real.Validated);
        Assert.Equal(6, Real.Parameters.Count);
        Assert.Throws<InvalidOperationException>(
            () => DatasetCatalog.GetForRun("dominio", "fiscal_counterparts", "full"));
        Assert.Null(DatasetCatalog.TryGet("dominio", "inexistente"));
    }

    // --- fila ---------------------------------------------------------------

    [Fact]
    public async Task Sem_job_ou_recurso_desligado_nao_ha_trabalho()
    {
        var source = new FakeSource(1);

        Assert.False(await Runner(new FakeServer(null), source, Validated).RunOnceAsync(default));
        Assert.False(await Runner(
            new FakeServer(null, HttpStatusCode.NotFound), source, Validated).RunOnceAsync(default));
        Assert.Equal(0, source.Reads);
    }

    [Fact]
    public async Task Hash_divergente_falha_com_dataset_mismatch_e_nao_executa()
    {
        var server = new FakeServer(Job(sha: new string('0', 64)));
        var source = new FakeSource(3);

        Assert.True(await Runner(server, source, Validated).RunOnceAsync(default));

        Assert.Equal("dataset_mismatch", server.FailureCode());
        Assert.Equal(0, source.Reads);
        Assert.Empty(server.Under("/batches"));
    }

    [Fact]
    public async Task Dataset_desconhecido_falha_sem_derrubar_o_ciclo()
    {
        var server = new FakeServer(Job(code: "inventado"));
        var source = new FakeSource(3);

        Assert.True(await Runner(server, source, definition: null).RunOnceAsync(default));

        Assert.Equal("dataset_mismatch", server.FailureCode());
        Assert.Equal(0, source.Reads);
    }

    [Fact]
    public async Task Dataset_nao_validado_falha_e_nao_executa()
    {
        var server = new FakeServer(Job());
        var source = new FakeSource(3);

        await Runner(server, source, Real).RunOnceAsync(default);

        Assert.Equal("dataset_not_validated", server.FailureCode());
        Assert.Equal(0, source.Reads);
    }

    [Fact]
    public async Task Parametro_fora_do_contrato_falha_antes_de_ler()
    {
        var server = new FakeServer(Job(parameters: Parameters(first: "codi_emp")));
        var source = new FakeSource(3);

        await Runner(server, source, Validated).RunOnceAsync(default);

        Assert.Equal("dataset_mismatch", server.FailureCode());
        Assert.Equal(0, source.Reads);
    }

    [Fact]
    public async Task Pagina_de_500_numerada_de_zero_e_fecha_com_totais()
    {
        var server = new FakeServer(Job());
        var source = new FakeSource(1203);

        await Runner(server, source, Validated).RunOnceAsync(default);

        var lotes = server.Under("/batches").ToList();
        Assert.Equal([0, 1, 2], lotes.Select(l => l.Body.GetProperty("sequence").GetInt32()));
        Assert.Equal([500, 500, 203],
            lotes.Select(l => l.Body.GetProperty("rows").GetArrayLength()));
        var fim = server.Under("/complete").Single().Body;
        Assert.Equal(1203, fim.GetProperty("row_count").GetInt32());
        Assert.Equal(3, fim.GetProperty("pages").GetInt32());
        Assert.Empty(server.Under("/failure"));
        Assert.Equal(6, source.Bound!.Count);
    }

    [Fact]
    public async Task Page_size_do_job_acima_de_500_e_limitado_a_500()
    {
        var server = new FakeServer(Job(pageSize: 5000));

        await Runner(server, new FakeSource(501), Validated).RunOnceAsync(default);

        Assert.Equal([500, 1],
            server.Under("/batches").Select(l => l.Body.GetProperty("rows").GetArrayLength()));
    }

    [Fact]
    public async Task Linhas_saem_so_com_as_colunas_do_contrato_e_uf_nulo_vira_vazio()
    {
        var server = new FakeServer(Job());

        await Runner(server, new FakeSource(2), Validated).RunOnceAsync(default);

        var rows = server.Under("/batches").Single().Body.GetProperty("rows");
        Assert.Equal("", rows[0].GetProperty("uf").GetString());
        Assert.Equal("SP", rows[1].GetProperty("uf").GetString());
        Assert.Equal("S", rows[0].GetProperty("direcao").GetString());
        Assert.Equal(3, rows[0].EnumerateObject().Count());
    }

    [Fact]
    public async Task Limite_do_job_menor_que_o_do_manifesto_vira_row_limit()
    {
        var server = new FakeServer(Job(maxRows: 10));

        await Runner(server, new FakeSource(11), Validated).RunOnceAsync(default);

        Assert.Equal("row_limit", server.FailureCode());
        Assert.Empty(server.Under("/complete"));
    }

    [Fact]
    public async Task Limite_do_manifesto_vale_mesmo_se_o_job_pedir_mais()
    {
        var pequeno = Validated with { MaxRowsPerRun = 5 };
        var server = new FakeServer(Job(maxRows: 1_000_000));

        await Runner(server, new FakeSource(6), pequeno).RunOnceAsync(default);

        Assert.Equal("row_limit", server.FailureCode());
    }

    [Fact]
    public async Task Erro_de_leitura_vira_odbc_error_com_detalhe_curto()
    {
        var server = new FakeServer(Job());
        var source = new FakeSource(0, new DatasetReadException(new string('x', 500)));

        await Runner(server, source, Validated).RunOnceAsync(default);

        var corpo = server.Under("/failure").Single().Body;
        Assert.Equal("odbc_error", corpo.GetProperty("error_code").GetString());
        Assert.Equal(200, corpo.GetProperty("detail").GetString()!.Length);
    }

    [Fact]
    public async Task Excecao_qualquer_vira_agent_error_sem_a_mensagem()
    {
        var server = new FakeServer(Job());
        var source = new FakeSource(0, new InvalidOperationException("DSN=x;PWD=senha"));

        await Runner(server, source, Validated).RunOnceAsync(default);

        var corpo = server.Under("/failure").Single().Body;
        Assert.Equal("agent_error", corpo.GetProperty("error_code").GetString());
        Assert.DoesNotContain("senha", corpo.GetProperty("detail").GetString());
    }

    [Fact]
    public async Task Lote_recusado_pelo_servidor_aborta_com_failure()
    {
        var server = new FakeServer(Job())
        {
            Reject = path => path.EndsWith("/batches")
                ? new HttpRequestException("x", null, HttpStatusCode.BadRequest)
                : null,
        };

        await Runner(server, new FakeSource(3), Validated).RunOnceAsync(default);

        Assert.Equal("agent_error", server.FailureCode());
        Assert.Empty(server.Under("/complete"));
    }

    [Fact]
    public async Task Autorizacao_recusada_nao_vira_failure_do_job()
    {
        var server = new FakeServer(Job())
        {
            Reject = path => path.EndsWith("/batches") ? new AgentAuthorizationException() : null,
        };

        await Assert.ThrowsAsync<AgentAuthorizationException>(
            () => Runner(server, new FakeSource(3), Validated).RunOnceAsync(default));
        Assert.Empty(server.Under("/failure"));
    }

    [Fact]
    public async Task Job_com_id_que_nao_e_uuid_e_recusado_sem_chamar_nada()
    {
        var job = JsonDocument.Parse(
            """{"job":{"id":"../x","dataset_code":"fiscal_counterparts","schema_version":1}}""");
        var server = new FakeServer(job);

        await Assert.ThrowsAsync<InvalidDataException>(
            () => Runner(server, new FakeSource(1), Validated).RunOnceAsync(default));
        Assert.Single(server.Calls);
    }
}
