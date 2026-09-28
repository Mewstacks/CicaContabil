namespace Cica.Agent.Service;

/// <summary>
/// Parte invariável do contrato local de cada ERP.
///
/// O pacote é único por D-80, mas a arquitetura do driver não é: Domínio usa SQL
/// Anywhere de 64 bits e Siescon usa Pervasive/PSQL de 32 bits pela ponte. Manter
/// os marcadores num contrato compartilhado evita que configurador e serviço
/// aceitem fontes diferentes.
/// </summary>
public sealed record SourceSystemProfile(
    string SourceSystem,
    string DisplayName,
    bool Uses32BitOdbcBridge,
    bool RequiresSqlAnywhereDriver,
    IReadOnlyList<string> DsnDriverMarkers);

public static class SourceSystemProfiles
{
    private static readonly SourceSystemProfile Dominio = new(
        "dominio",
        "Domínio",
        Uses32BitOdbcBridge: false,
        RequiresSqlAnywhereDriver: true,
        DsnDriverMarkers: ["SQL Anywhere"]);

    private static readonly SourceSystemProfile Siescon = new(
        "siescon",
        "Siescon",
        Uses32BitOdbcBridge: true,
        RequiresSqlAnywhereDriver: false,
        DsnDriverMarkers: ["Pervasive", "PSQL"]);

    public static SourceSystemProfile Get(string sourceSystem) => sourceSystem switch
    {
        "dominio" => Dominio,
        "siescon" => Siescon,
        _ => throw new ArgumentOutOfRangeException(
            nameof(sourceSystem), sourceSystem, "Sistema de origem desconhecido."),
    };
}
