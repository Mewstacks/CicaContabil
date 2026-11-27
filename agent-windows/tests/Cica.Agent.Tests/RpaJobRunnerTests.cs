using System.Net;
using System.Security.Cryptography;
using System.Text.Json;
using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

/// Fila RPA do agente sem rede nem processo: transporte e executor são falsos, o protocolo é real.
public sealed class RpaJobRunnerTests
{
    private const string JobId = "11111111-2222-3333-4444-555555555555";
    private const string Kind = "folha.calculo";

    private static JsonDocument Job(string kind = Kind, string lease = "tok-123", string id = JobId) =>
        JsonDocument.Parse($$$"""
        {"job":{"id":"{{{id}}}","kind":"{{{kind}}}","payload":{"competencia":"2026-09"},
         "lease_token":"{{{lease}}}","lease_seconds":60,"attempt":1}}
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
                if (nextStatus is { } status) throw new HttpRequestException("x", null, status);
                return Task.FromResult(next ?? JsonDocument.Parse("""{"job":null}"""));
            }
            if (Reject?.Invoke(path) is { } error) throw error;
            return Task.FromResult(JsonDocument.Parse("""{"status":"ok"}"""));
        }

        internal IEnumerable<(string Path, JsonElement Body)> Under(string suffix) =>
            Calls.Where(call => call.Path.EndsWith(suffix));
    }

    private sealed class FakeExecutor(Func<IRpaJobContext, Task<RpaOutcome>> run, string kind = Kind)
        : IRpaExecutor
    {
        internal int Runs { get; private set; }
        public string Kind => kind;

        public Task<RpaOutcome> ExecuteAsync(IRpaJobContext context, CancellationToken token)
        {
            Runs++;
            return run(context);
        }
    }

    private static RpaOutcome Success() =>
        RpaOutcome.Ok(JsonDocument.Parse("""{"ok":true}""").RootElement.Clone());

    [Fact]
    public async Task Sem_executor_nada_e_pedido_a_nuvem()
    {
        FakeServer server = new(Job());
        bool ran = await new RpaJobRunner(server.Post, []).RunOnceAsync(CancellationToken.None);
        Assert.False(ran);
        Assert.Empty(server.Calls);
    }

    [Fact]
    public async Task Pede_so_os_tipos_que_tem_executor_e_fecha_com_sucesso()
    {
        FakeServer server = new(Job());
        FakeExecutor executor = new(_ => Task.FromResult(Success()));
        bool ran = await new RpaJobRunner(server.Post, [executor]).RunOnceAsync(CancellationToken.None);
        Assert.True(ran);
        Assert.Equal(1, executor.Runs);
        JsonElement asked = server.Calls[0].Body.GetProperty("kinds");
        Assert.Equal([Kind], asked.EnumerateArray().Select(k => k.GetString()!).ToArray());
        (string path, JsonElement body) = server.Under("/complete").Single();
        Assert.Equal($"api/agent/v2/rpa/{JobId}/complete", path);
        Assert.Equal("tok-123", body.GetProperty("lease_token").GetString());
        Assert.True(body.GetProperty("result").GetProperty("ok").GetBoolean());
    }

    [Fact]
    public async Task Recurso_desligado_404_e_sem_trabalho()
    {
        FakeServer server = new(null, HttpStatusCode.NotFound);
        bool ran = await new RpaJobRunner(server.Post, [new FakeExecutor(_ => Task.FromResult(Success()))])
            .RunOnceAsync(CancellationToken.None);
        Assert.False(ran);
    }

    [Fact]
    public async Task Tipo_sem_executor_local_e_devolvido_como_nao_suportado()
    {
        FakeServer server = new(Job("fgts.emitir"));
        FakeExecutor executor = new(_ => Task.FromResult(Success()));
        await new RpaJobRunner(server.Post, [executor]).RunOnceAsync(CancellationToken.None);
        Assert.Equal(0, executor.Runs);
        Assert.Equal("nao_suportado", server.Under("/failure").Single().Body.GetProperty("code").GetString());
    }

    [Fact]
    public async Task Id_que_nao_e_uuid_nunca_entra_na_url()
    {
        FakeServer server = new(Job(id: "../../admin"));
        await Assert.ThrowsAsync<InvalidDataException>(() =>
            new RpaJobRunner(server.Post, [new FakeExecutor(_ => Task.FromResult(Success()))])
                .RunOnceAsync(CancellationToken.None));
        Assert.Single(server.Calls);
    }

    [Fact]
    public async Task Falha_do_executor_sobe_com_codigo_e_sem_segredo()
    {
        FakeServer server = new(Job());
        FakeExecutor executor = new(_ => Task.FromResult(
            RpaOutcome.Fail("portal_indisponivel", "falhou senha=Abc123 e " + new string('A', 60))));
        await new RpaJobRunner(server.Post, [executor]).RunOnceAsync(CancellationToken.None);
        JsonElement body = server.Under("/failure").Single().Body;
        Assert.Equal("portal_indisponivel", body.GetProperty("code").GetString());
        string detail = body.GetProperty("detail").GetString()!;
        Assert.DoesNotContain("Abc123", detail);
        Assert.DoesNotContain(new string('A', 40), detail);
        Assert.Empty(server.Under("/complete"));
    }

    [Fact]
    public async Task Excecao_vira_agent_error_so_com_o_tipo()
    {
        FakeServer server = new(Job());
        FakeExecutor executor = new(_ => throw new InvalidOperationException("senha=segredo"));
        await new RpaJobRunner(server.Post, [executor]).RunOnceAsync(CancellationToken.None);
        JsonElement body = server.Under("/failure").Single().Body;
        Assert.Equal("agent_error", body.GetProperty("code").GetString());
        Assert.Equal("InvalidOperationException", body.GetProperty("detail").GetString());
    }

    [Fact]
    public async Task Fase_e_arquivo_vao_com_o_token_e_o_hash_do_conteudo()
    {
        FakeServer server = new(Job());
        byte[] content = "%PDF-1.4 relatorio"u8.ToArray();
        FakeExecutor executor = new(async context =>
        {
            await context.PhaseAsync("emitindo", CancellationToken.None);
            await context.ArtifactAsync(new RpaArtifact("r.pdf", content, "application/pdf"), CancellationToken.None);
            return Success();
        });
        await new RpaJobRunner(server.Post, [executor]).RunOnceAsync(CancellationToken.None);
        JsonElement beat = server.Under("/heartbeat").First().Body;
        Assert.Equal("emitindo", beat.GetProperty("phase").GetString());
        Assert.Equal("tok-123", beat.GetProperty("lease_token").GetString());
        JsonElement art = server.Under("/artifacts").Single().Body;
        Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(content)), art.GetProperty("sha256").GetString());
        Assert.Equal(Convert.ToBase64String(content), art.GetProperty("content_base64").GetString());
    }

    [Fact]
    public async Task Reserva_perdida_409_silencia_o_agente()
    {
        FakeServer server = new(Job())
        {
            Reject = path => path.EndsWith("/complete")
                ? new HttpRequestException("x", null, HttpStatusCode.Conflict)
                : null,
        };
        FakeExecutor executor = new(_ => Task.FromResult(Success()));
        await new RpaJobRunner(server.Post, [executor]).RunOnceAsync(CancellationToken.None);
        Assert.Empty(server.Under("/failure"));
    }

    [Fact]
    public void Arquivo_so_dentro_da_pasta_aprovada()
    {
        string root = Path.Combine(Path.GetTempPath(), "cica-rpa-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        string inside = Path.Combine(root, "a.pdf");
        File.WriteAllText(inside, "x");
        string outside = Path.Combine(Path.GetTempPath(), "cica-fora-" + Guid.NewGuid().ToString("N") + ".pdf");
        File.WriteAllText(outside, "x");
        try
        {
            Assert.Equal(inside, RpaOutputPaths.Resolve(root, inside));
            Assert.Throws<InvalidDataException>(() => RpaOutputPaths.Resolve(root, outside));
            Assert.Throws<InvalidDataException>(() =>
                RpaOutputPaths.Resolve(root, Path.Combine(root, "..", Path.GetFileName(outside))));
            Assert.Throws<InvalidDataException>(() => RpaOutputPaths.Resolve(root, "a.pdf"));
            Assert.Throws<InvalidDataException>(() => RpaOutputPaths.Resolve("", inside));
        }
        finally
        {
            Directory.Delete(root, recursive: true);
            File.Delete(outside);
        }
    }
}
