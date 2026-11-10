using System.Text.Json;

namespace Cica.Agent.Service;

internal static class AgentCollectionGate
{
    internal static bool IsEnabled(JsonElement configuration)
    {
        // Existing active installations remain compatible with an older backend.
        if (!configuration.TryGetProperty("collection_enabled", out JsonElement value)) return true;
        return value.ValueKind switch
        {
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            _ => throw new InvalidDataException("O servidor não confirmou a autorização de coleta."),
        };
    }
}
