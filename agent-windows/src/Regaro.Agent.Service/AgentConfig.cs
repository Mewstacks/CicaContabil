using System.Security.Cryptography;
using System.Text.Json;

namespace Regaro.Agent.Service;

internal sealed record AgentConfig(
    string ServerUrl,
    string AgentId,
    string SharedSecret,
    string CertificatePfxBase64,
    string? Dsn,
    string SqlAnywhereDriver,
    string DatabaseUser,
    string DatabasePassword)
{
    internal static readonly string DirectoryPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "Regaro", "Agent");
    internal static readonly string FilePath = Path.Combine(DirectoryPath, "agent.config");

    internal static AgentConfig Load()
    {
        byte[] encrypted = File.ReadAllBytes(FilePath);
        byte[] plain = ProtectedData.Unprotect(encrypted, null, DataProtectionScope.LocalMachine);
        try { return JsonSerializer.Deserialize<AgentConfig>(plain) ?? throw new InvalidDataException(); }
        finally { CryptographicOperations.ZeroMemory(plain); }
    }

    internal void Save()
    {
        Directory.CreateDirectory(DirectoryPath);
        byte[] plain = JsonSerializer.SerializeToUtf8Bytes(this);
        try
        {
            byte[] encrypted = ProtectedData.Protect(plain, null, DataProtectionScope.LocalMachine);
            File.WriteAllBytes(FilePath, encrypted);
        }
        finally { CryptographicOperations.ZeroMemory(plain); }
    }
}
