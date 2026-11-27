using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace Cica.Agent.Service;

/// Fila RPA do agente: monta um executor por tipo aprovado na configuração local e entrega ao
/// `RpaJobRunner`. A nuvem nunca escolhe o programa: o caminho vem do `agent.config`
/// (protegido por DPAPI), validado como caminho absoluto de disco local. Sem executor
/// aprovado, nada é pedido à nuvem.
internal sealed class RpaProcessor(AgentConfig config, AgentClient client)
{
    internal async Task RunOnce(CancellationToken token)
    {
        if (config.RpaExecutors is not { Count: > 0 }) return;
        IEnumerable<IRpaExecutor> executors = config.RpaExecutors.Select(
            entry => (IRpaExecutor)new ProcessRpaExecutor(
                entry.Key, entry.Value, config.RpaOutputRoot ?? ""));
        await new RpaJobRunner(client.PostAsync, executors).RunOnceAsync(token);
    }
}

/// Executa o trabalho num processo filho (por exemplo o worker Python x86 que controla o
/// Domínio desktop). Protocolo por entrada e saída padrão, sem rede nem arquivo temporário:
///
/// * entrada: uma linha JSON `{"job_id","kind","payload"}`;
/// * saída, uma linha JSON por evento: `{"event":"phase","phase":"..."}`,
///   `{"event":"artifact","path":"...","name":"...","content_type":"..."}`,
///   `{"event":"result","result":{...}}` ou `{"event":"failure","code":"...","detail":"..."}`.
///
/// Credencial nenhuma passa por aqui: o executor lê do Cofre do Windows da própria conta. Arquivo
/// só é aceito dentro de `RpaOutputRoot`, sem caminho que escape nem ponto de reanálise.
internal sealed class ProcessRpaExecutor(string kind, string executable, string outputRoot) : IRpaExecutor
{
    private static readonly TimeSpan HardLimit = TimeSpan.FromHours(2);

    public string Kind => kind;

    public async Task<RpaOutcome> ExecuteAsync(IRpaJobContext context, CancellationToken token)
    {
        if (!Path.IsPathFullyQualified(executable) || !File.Exists(executable))
            return RpaOutcome.Fail("nao_suportado", "Executor local não encontrado.");

        ProcessStartInfo start = new(executable)
        {
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = false,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            WorkingDirectory = Path.GetDirectoryName(executable)!,
        };
        using Process process = Process.Start(start)
            ?? throw new InvalidOperationException("Executor não iniciou.");
        using CancellationTokenSource limit = CancellationTokenSource.CreateLinkedTokenSource(token);
        limit.CancelAfter(HardLimit);
        try
        {
            string request = JsonSerializer.Serialize(new
            {
                job_id = context.JobId,
                kind = context.Kind,
                payload = context.Payload,
            });
            await process.StandardInput.WriteLineAsync(request.AsMemory(), limit.Token);
            process.StandardInput.Close();

            RpaOutcome? outcome = null;
            while (await process.StandardOutput.ReadLineAsync(limit.Token) is { } line)
            {
                outcome = await Handle(line, context, limit.Token) ?? outcome;
            }
            await process.WaitForExitAsync(limit.Token);
            return outcome ?? RpaOutcome.Fail("agent_error", "Executor terminou sem resultado.");
        }
        catch (OperationCanceledException) when (!token.IsCancellationRequested)
        {
            return RpaOutcome.Fail("timeout", "Executor passou do tempo limite.");
        }
        finally
        {
            if (!process.HasExited) process.Kill(entireProcessTree: true);
        }
    }

    private async Task<RpaOutcome?> Handle(string line, IRpaJobContext context, CancellationToken token)
    {
        JsonDocument message;
        try { message = JsonDocument.Parse(line); }
        catch (JsonException) { return null; } // linha de diagnóstico, ignorada
        using (message)
        {
            JsonElement root = message.RootElement;
            if (root.ValueKind != JsonValueKind.Object) return null;
            switch (Text(root, "event"))
            {
                case "phase":
                    await context.PhaseAsync(Text(root, "phase"), token);
                    return null;
                case "artifact":
                    await context.ArtifactAsync(ReadArtifact(root), token);
                    return null;
                case "result" when root.TryGetProperty("result", out JsonElement result)
                    && result.ValueKind == JsonValueKind.Object:
                    return RpaOutcome.Ok(result.Clone());
                case "failure":
                    return RpaOutcome.Fail(Text(root, "code"), Text(root, "detail"));
                default:
                    return null;
            }
        }
    }

    private RpaArtifact ReadArtifact(JsonElement root)
    {
        string path = RpaOutputPaths.Resolve(outputRoot, Text(root, "path"));
        FileInfo info = new(path);
        if (info.Length > RpaJobRunner.MaxArtifactBytes)
            throw new InvalidDataException("Arquivo acima do limite.");
        string name = Text(root, "name");
        return new RpaArtifact(
            name.Length > 0 ? name : info.Name,
            File.ReadAllBytes(path),
            Text(root, "content_type"));
    }

    private static string Text(JsonElement root, string name) =>
        root.TryGetProperty(name, out JsonElement value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? ""
            : "";
}
