# Agente CICA para Windows

Native .NET 8 Windows service and guided configurator. The MSI supports:

- Trabalhos de backup Domínio Web enviados manualmente na CICA.
- approved Triagem attachments copied to the office's Windows folder.

Leia o fluxo de instalação e diagnóstico em [INSTALACAO.md](INSTALACAO.md).
Os contratos técnicos Domínio confirmados por metadados estão em [CONTRATOS-DOMINIO.md](CONTRATOS-DOMINIO.md).

The configurator lists only 64-bit system DSNs and SQL Anywhere drivers, because the installed
native service is x64. It can validate a Domínio Local connection without exposing credentials
in logs.
The native CICA service is the installed and supported component for read-only Domínio Local
synchronization, Domínio Web backups, and Triagem archiving. The Python agent is restricted to
temporary diagnostics and migration. For Triagem, the configurator stores the approved root with DPAPI and the server
sends only a relative company/document path. The service refuses path escape and reparse-point
redirects, proves the configured root, writes a temporary file, validates SHA-256 and size, and
renames atomically. CICA keeps the item in `Arquivando` until that proof returns.

The service only opens outbound HTTPS connections. Enrollment creates the private key and CSR
on the office computer; the API returns only the signed client certificate and its chain. Runtime
configuration is protected with Windows DPAPI (`LocalMachine`) and the MSI restricts its folder to
Administrators and `LocalSystem`.

Domínio Web `.dom` files are password-protected ZIP-compatible containers. The agent extracts the
`contabil.db` file with the per-file Onvio key, then opens the database with an installed SQL
Anywhere 16/17 ODBC driver. SAP/Thomson Reuters runtime files are proprietary and are deliberately
não redistribuídos pela CICA.

Build the MSI on Windows:

```powershell
.\build.ps1
```

The deterministic outputs are written to `artifacts/`, including a SHA-256 checksum and dependency
inventory. Publish the checksum alongside the stable MSI download URL. Existing Python agents keep
using `/api/v1/intelligence/agent/*` during migration.
