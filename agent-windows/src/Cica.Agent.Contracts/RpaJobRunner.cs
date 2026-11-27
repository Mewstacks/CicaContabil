using System.Net;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Cica.Agent.Service;

/// O que um executor RPA devolve. Sucesso leva só o resultado (objeto JSON sem segredo);
/// falha leva um código do protocolo e um texto curto, nunca dado de linha.
internal sealed record RpaOutcome(bool Success, JsonElement? Result, string Code, string Detail)
{
    internal static RpaOutcome Ok(JsonElement result) => new(true, result, "", "");
    internal static RpaOutcome Fail(string code, string detail) => new(false, null, code, detail);
}

/// Um arquivo que o executor produziu. O conteúdo já vem lido e limitado por quem o entrega.
internal sealed record RpaArtifact(string Name, byte[] Content, string ContentType);

/// O que o executor pode fazer enquanto roda: avisar a fase (renova a reserva) e entregar arquivos.
internal interface IRpaJobContext
{
    string JobId { get; }
    string Kind { get; }
    JsonElement Payload { get; }
    Task PhaseAsync(string phase, CancellationToken token);
    Task ArtifactAsync(RpaArtifact artifact, CancellationToken token);
}

/// Quem sabe executar um tipo de trabalho nesta máquina (Domínio desktop, portal...).
internal interface IRpaExecutor
{
    string Kind { get; }
    Task<RpaOutcome> ExecuteAsync(IRpaJobContext context, CancellationToken token);
}

/// A fila RPA do agente, sem rede nem processo concretos: pede um trabalho dos tipos que ele
/// executa, mantém a reserva viva, entrega arquivos com hash e fecha. Fica na biblioteca de
/// contratos para ser testável sem Windows.
///
/// O servidor decide o que existe; o agente só executa os tipos que ele mesmo registrou e que a
/// configuração local aprovou. Texto de exceção nunca sobe: só o tipo.
internal sealed partial class RpaJobRunner(PostJson post, IEnumerable<IRpaExecutor> executors)
{
    private const string Base = "api/agent/v2/rpa";
    private const int MaxDetail = 200;
    internal const int MaxArtifactBytes = 25_000_000;

    private PostJson Post => post;

    private readonly Dictionary<string, IRpaExecutor> byKind =
        executors.ToDictionary(executor => executor.Kind, StringComparer.Ordinal);

    /// Devolve true quando havia um trabalho (concluído ou fechado com falha).
    internal async Task<bool> RunOnceAsync(CancellationToken token)
    {
        if (byKind.Count == 0) return false;
        JsonDocument next;
        try
        {
            next = await post($"{Base}/next", new { kinds = byKind.Keys.ToArray() }, token);
        }
        catch (HttpRequestException error) when (error.StatusCode == HttpStatusCode.NotFound)
        {
            return false; // recurso desligado no servidor
        }

        using (next)
        {
            if (!next.RootElement.TryGetProperty("job", out JsonElement job)
                || job.ValueKind != JsonValueKind.Object)
                return false;
            await Handle(job.Clone(), token);
            return true;
        }
    }

    private async Task Handle(JsonElement job, CancellationToken token)
    {
        string id = ParseId(job);
        string kind = StringOf(job, "kind");
        string lease = StringOf(job, "lease_token");
        if (lease.Length == 0 || !byKind.TryGetValue(kind, out IRpaExecutor? executor))
        {
            if (lease.Length > 0)
                await Fail(id, lease, "nao_suportado", "Tipo de trabalho sem executor local.", token);
            return;
        }

        int leaseSeconds = job.TryGetProperty("lease_seconds", out JsonElement s) && s.TryGetInt32(out int v)
            ? Math.Clamp(v, 10, 3600) : 120;
        JsonElement payload = job.TryGetProperty("payload", out JsonElement p) ? p : default;
        Context context = new(this, id, lease, kind, payload);

        using CancellationTokenSource stop = CancellationTokenSource.CreateLinkedTokenSource(token);
        Task beat = KeepAlive(context, TimeSpan.FromSeconds(Math.Max(5, leaseSeconds / 3)), stop.Token);
        try
        {
            RpaOutcome outcome = await executor.ExecuteAsync(context, token);
            await stop.CancelAsync();
            if (outcome.Success && outcome.Result is JsonElement result)
            {
                using JsonDocument _ = await post(
                    $"{Base}/{id}/complete", new { lease_token = lease, result }, token);
            }
            else
            {
                await Fail(id, lease, outcome.Code.Length > 0 ? outcome.Code : "agent_error",
                    outcome.Detail, token);
            }
        }
        catch (HttpRequestException error)
        {
            await stop.CancelAsync();
            // 409 = a reserva já não é nossa: calar. Outro agente decide daqui.
            if (error.StatusCode != HttpStatusCode.Conflict)
                await TryFail(id, lease, "agent_error",
                    $"Servidor recusou a chamada (HTTP {(int?)error.StatusCode}).", token);
        }
        catch (Exception error) when (
            error is not OperationCanceledException and not AgentAuthorizationException)
        {
            await stop.CancelAsync();
            await TryFail(id, lease, "agent_error", error.GetType().Name, token);
        }
        finally
        {
            await stop.CancelAsync();
            try { await beat; } catch (OperationCanceledException) { }
        }
    }

    private async Task KeepAlive(Context context, TimeSpan every, CancellationToken token)
    {
        using PeriodicTimer timer = new(every);
        while (await timer.WaitForNextTickAsync(token))
        {
            try { await context.PhaseAsync("", token); }
            catch (HttpRequestException) { /* reserva perdida: o fechamento falha sozinho */ }
        }
    }

    private async Task TryFail(string id, string lease, string code, string detail, CancellationToken token)
    {
        try { await Fail(id, lease, code, detail, token); }
        catch (HttpRequestException) { /* sem rede: a reserva vence e volta à fila */ }
    }

    private async Task Fail(string id, string lease, string code, string detail, CancellationToken token)
    {
        using JsonDocument _ = await post(
            $"{Base}/{id}/failure", new { lease_token = lease, code, detail = Clean(detail) }, token);
    }

    /// Detalhe curto, em uma linha, sem nada que pareça credencial.
    internal static string Clean(string detail)
    {
        string line = detail.ReplaceLineEndings(" ");
        line = SecretAssignment().Replace(line, "$1=[oculto]");
        line = LongBlob().Replace(line, "[oculto]");
        return line.Length > MaxDetail ? line[..MaxDetail] : line;
    }

    [GeneratedRegex(@"(?i)\b(senha|password|passwd|pwd|token|secret|segredo|api[_-]?key)\b\s*[:=]\s*\S+")]
    private static partial Regex SecretAssignment();

    [GeneratedRegex(@"[A-Za-z0-9+/=_-]{40,}")]
    private static partial Regex LongBlob();

    private static string ParseId(JsonElement job)
    {
        // O id entra na URL: só aceita UUID, nada de segmento de caminho vindo do JSON.
        if (!job.TryGetProperty("id", out JsonElement idElement)
            || idElement.ValueKind != JsonValueKind.String
            || !Guid.TryParse(idElement.GetString(), out Guid parsed))
            throw new InvalidDataException("Trabalho RPA sem id válido.");
        return parsed.ToString();
    }

    private static string StringOf(JsonElement job, string name) =>
        job.TryGetProperty(name, out JsonElement value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? ""
            : "";

    private sealed class Context(
        RpaJobRunner runner, string id, string lease, string kind, JsonElement payload)
        : IRpaJobContext
    {
        public string JobId => id;
        public string Kind => kind;
        public JsonElement Payload => payload;

        public async Task PhaseAsync(string phase, CancellationToken token)
        {
            using JsonDocument _ = await runner.Post(
                $"{Base}/{id}/heartbeat", new { lease_token = lease, phase }, token);
        }

        public async Task ArtifactAsync(RpaArtifact artifact, CancellationToken token)
        {
            if (artifact.Content.Length > MaxArtifactBytes)
                throw new InvalidDataException("Arquivo acima do limite.");
            string sha = Convert.ToHexStringLower(SHA256.HashData(artifact.Content));
            using JsonDocument _ = await runner.Post(
                $"{Base}/{id}/artifacts",
                new
                {
                    lease_token = lease,
                    name = artifact.Name,
                    sha256 = sha,
                    content_type = artifact.ContentType,
                    content_base64 = Convert.ToBase64String(artifact.Content),
                },
                token);
        }
    }
}
