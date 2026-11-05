using System.Data.Odbc;

namespace Cica.Agent.Service;

// Shared by the configurator and service: a successful test must use the same
// authentication mode as the background connection. Never retry with a different identity.
internal static class LocalOdbcConnection
{
    internal static string Build(string dsn, string user, string password,
        bool useDsnAuthentication)
    {
        if (string.IsNullOrWhiteSpace(dsn))
            throw new InvalidDataException("Selecione o DSN do Domínio Local.");
        var builder = new OdbcConnectionStringBuilder { Dsn = dsn };
        if (!useDsnAuthentication)
        {
            builder["UID"] = user;
            builder["PWD"] = password;
        }
        // OdbcConnectionStringBuilder omits empty values. Explicit authentication
        // must still override a DSN's stored UID/PWD, even when a field is empty.
        string result = builder.ConnectionString;
        if (!useDsnAuthentication && user.Length == 0) result += ";UID=";
        if (!useDsnAuthentication && password.Length == 0) result += ";PWD=";
        return result;
    }
}
