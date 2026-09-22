using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.Win32;

namespace Cica.Agent.Service;

internal sealed record AgentConfig(
    string ServerUrl,
    string AgentId,
    string SharedSecret,
    string CertificatePfxBase64,
    string? Dsn,
    string SqlAnywhereDriver,
    string DatabaseUser,
    string DatabasePassword,
    string? WindowsArchiveRoot,
    // Qual ERP este conector lê. Por D-80 o pacote é único, então o sistema vem da
    // configuração e não compilado no binário como fazia o conector de origem.
    // Instalação antiga não tem o campo, e é do Domínio: era o único perfil que
    // existia, e ninguém recompila o que já está em campo para ganhar uma marca.
    string? SourceSystem = null)
{
    internal string EffectiveSourceSystem =>
        string.IsNullOrWhiteSpace(SourceSystem) ? "dominio" : SourceSystem;

    internal static readonly string DirectoryPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "CICA", "Agent");
    internal static readonly string FilePath = Path.Combine(DirectoryPath, "agent.config");

    internal static AgentConfig Load()
    {
        byte[] encrypted = File.ReadAllBytes(FilePath);
        byte[] plain = ProtectedData.Unprotect(encrypted, null, DataProtectionScope.LocalMachine);
        try { return JsonSerializer.Deserialize<AgentConfig>(plain) ?? throw new InvalidDataException(); }
        finally { CryptographicOperations.ZeroMemory(plain); }
    }

    internal void Validate()
    {
        if (!Uri.TryCreate(ServerUrl, UriKind.Absolute, out Uri? server)
            || !string.Equals(server.Scheme, Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("O endereço do servidor CICA precisa usar HTTPS.");
        if (string.IsNullOrWhiteSpace(AgentId) || string.IsNullOrWhiteSpace(SharedSecret)
            || string.IsNullOrWhiteSpace(CertificatePfxBase64))
            throw new InvalidDataException("O pareamento do agente está incompleto. Execute o configurador novamente.");
        if (EffectiveSourceSystem is not ("dominio" or "siescon"))
            throw new InvalidDataException("Sistema de origem desconhecido na configuração.");
        // O Siescon lê pelo Pervasive, que só publica driver ODBC de 32 bits, e por
        // isso passa pela ponte isolada em vez do processo do serviço. As duas
        // verificações abaixo perguntam pelo registro de 64 bits, então valem só
        // para o Domínio: aplicá-las ao Siescon recusaria justamente a instalação
        // que a ponte existe para atender.
        if (EffectiveSourceSystem == "dominio")
        {
            if (!string.IsNullOrWhiteSpace(Dsn) && !IsRegistered64BitDsn(Dsn))
                throw new InvalidDataException(
                    "O DSN configurado não está disponível para o serviço CICA Agent 64 bits.");
            if (!IsRegistered64BitSqlAnywhereDriver(SqlAnywhereDriver))
                throw new InvalidDataException(
                    "O driver SQL Anywhere configurado não está disponível em 64 bits.");
        }
        if (!string.IsNullOrWhiteSpace(WindowsArchiveRoot) && (!Path.IsPathFullyQualified(WindowsArchiveRoot)
            || WindowsArchiveRoot.StartsWith("\\\\", StringComparison.Ordinal)))
            throw new InvalidDataException("A pasta de arquivos aprovada precisa ser um caminho absoluto do Windows.");
    }

    private static bool IsRegistered64BitDsn(string dsn)
    {
        const string path = @"SOFTWARE\ODBC\ODBC.INI\ODBC Data Sources";
        using RegistryKey baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64);
        using RegistryKey? key = baseKey.OpenSubKey(path);
        return key?.GetValueNames().Contains(dsn, StringComparer.OrdinalIgnoreCase) is true;
    }

    private static bool IsRegistered64BitSqlAnywhereDriver(string driver)
    {
        const string path = @"SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers";
        using RegistryKey baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64);
        using RegistryKey? key = baseKey.OpenSubKey(path);
        return key?.GetValueNames().Contains(driver, StringComparer.OrdinalIgnoreCase) is true
            && driver.Contains("SQL Anywhere", StringComparison.OrdinalIgnoreCase);
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
