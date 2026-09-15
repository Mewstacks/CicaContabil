# Regaro Agent for Windows

Native .NET 8 Windows service and guided configurator. The MSI supports:

- Domínio Web backup jobs uploaded manually in Regaro.

The configurator discovers 32- and 64-bit system DSNs and can validate a Domínio Local connection.
Local synchronization remains on the compatible Python agent until the native x86/x64 workers are
finished; the native service in this version processes Domínio Web backup jobs.

The service only opens outbound HTTPS connections. Enrollment creates the private key and CSR
on the office computer; the API returns only the signed client certificate and its chain. Runtime
configuration is protected with Windows DPAPI (`LocalMachine`) and the MSI restricts its folder to
Administrators and `LocalSystem`.

Domínio Web `.dom` files are password-protected ZIP-compatible containers. The agent extracts the
`contabil.db` file with the per-file Onvio key, then opens the database with an installed SQL
Anywhere 16/17 ODBC driver. SAP/Thomson Reuters runtime files are proprietary and are deliberately
not redistributed by Regaro.

Build the MSI on Windows:

```powershell
.\build.ps1
```

The deterministic outputs are written to `artifacts/`, including a SHA-256 checksum and dependency
inventory. Publish the checksum alongside the stable MSI download URL. Existing Python agents keep
using `/api/v1/intelligence/agent/*` during migration.
