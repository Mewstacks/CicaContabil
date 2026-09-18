using System.Text.Json;

namespace Cica.Agent.Service;

internal sealed class AgentRuntimeStatus
{
    private static readonly string FilePath = Path.Combine(AgentConfig.DirectoryPath, "agent-status.json");

    internal static void Write(string state, string detail)
    {
        try
        {
            Directory.CreateDirectory(AgentConfig.DirectoryPath);
            string temporary = FilePath + ".partial";
            byte[] content = JsonSerializer.SerializeToUtf8Bytes(new
            {
                state,
                detail,
                observed_at_utc = DateTimeOffset.UtcNow.ToString("O"),
                version = "1.0.0",
            });
            try
            {
                File.WriteAllBytes(temporary, content);
                File.Move(temporary, FilePath, true);
            }
            finally
            {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }
        catch (Exception)
        {
            // O diagnóstico jamais pode derrubar o serviço. O erro ainda é enviado ao Event Log pelo Worker.
        }
    }
}
