using System.Data.Odbc;
using System.Diagnostics;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using Cica.Agent.Service;
using Microsoft.Win32;

ApplicationConfiguration.Initialize();
Application.Run(new SetupForm());

internal sealed class SetupForm : Form
{
    private const int DominioWebMode = 0;
    private const int DominioLocalMode = 1;
    private const int SiesconLocalMode = 2;

    private readonly TextBox server = new() { PlaceholderText = "https://cica.seudominio.com.br", Dock = DockStyle.Fill };
    private readonly TextBox code = new() { Dock = DockStyle.Fill };
    private readonly TextBox label = new() { Text = Environment.MachineName, Dock = DockStyle.Fill };
    private readonly ComboBox mode = new() { Dock = DockStyle.Fill, DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly ComboBox dsn = new() { Dock = DockStyle.Fill, DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly ComboBox driver = new() { Dock = DockStyle.Fill, DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly TextBox user = new() { Text = "DBA", Dock = DockStyle.Fill };
    private readonly TextBox password = new() { Text = "sql", UseSystemPasswordChar = true, Dock = DockStyle.Fill };
    private readonly TextBox archiveRoot = new() { Dock = DockStyle.Fill };
    private readonly Label status = new() { AutoSize = true, MaximumSize = new(520, 0), Padding = new(0, 8, 0, 8) };
    private readonly Button test = new() { Text = "Testar conexão", AutoSize = true };
    private readonly Button finish = new() { Text = "Conectar à CICA", AutoSize = true };
    private readonly Button chooseArchiveRoot = new() { Text = "Escolher pasta de arquivos", AutoSize = true };

    internal SetupForm()
    {
        Text = "Configurar agente CICA";
        Width = 640;
        Height = 650;
        MinimumSize = new(560, 560);
        StartPosition = FormStartPosition.CenterScreen;
        Font = new("Segoe UI", 10);
        mode.Items.AddRange([
            "Domínio Web — backups manuais",
            "Domínio Local — DSN de 64 bits",
            "Siescon Local — DSN Pervasive de 32 bits",
        ]);
        mode.SelectedIndex = 0;
        foreach (string value in DiscoverDrivers())
            driver.Items.Add(value);
        if (driver.Items.Count > 0) driver.SelectedIndex = 0;

        var layout = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            Padding = new(28),
            ColumnCount = 1,
            AutoScroll = true
        };
        layout.Controls.Add(new Label { Text = "Agente CICA", Font = new("Segoe UI Semibold", 20), AutoSize = true });
        layout.Controls.Add(new Label { Text = "Conecte este servidor sem abrir portas. A chave privada fica somente neste computador.", AutoSize = true, MaximumSize = new(540, 0) });
        Add(layout, "Endereço HTTPS da CICA", server);
        Add(layout, "Código temporário mostrado na CICA", code);
        Add(layout, "Nome deste servidor", label);
        Add(layout, "Fonte de dados", mode);
        Add(layout, "DSN do ERP local", dsn);
        Add(layout, "Driver SQL Anywhere 64 bits (somente Domínio)", driver);
        Add(layout, "Usuário do banco", user);
        Add(layout, "Senha do banco", password);
        Add(layout, "Pasta raiz para arquivos aprovados (opcional)", archiveRoot);
        layout.Controls.Add(chooseArchiveRoot);
        var buttons = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight };
        buttons.Controls.Add(test); buttons.Controls.Add(finish); layout.Controls.Add(buttons);
        layout.Controls.Add(status);
        Controls.Add(layout);
        mode.SelectedIndexChanged += (_, _) => RefreshMode();
        test.Click += async (_, _) => await TestConnection();
        finish.Click += async (_, _) => await Enroll();
        chooseArchiveRoot.Click += (_, _) => ChooseArchiveRoot();
        RefreshMode();
    }

    private static void Add(TableLayoutPanel layout, string title, Control control)
    {
        layout.Controls.Add(new Label { Text = title, AutoSize = true, Padding = new(0, 10, 0, 3) });
        layout.Controls.Add(control);
    }

    private void RefreshMode()
    {
        bool local = mode.SelectedIndex is DominioLocalMode or SiesconLocalMode;
        SourceSystemProfile profile = SelectedSourceProfile();
        bool siescon = profile.Uses32BitOdbcBridge;

        string anterior = dsn.Text;
        dsn.BeginUpdate();
        dsn.Items.Clear();
        if (local)
            foreach (string value in DiscoverDsns(profile)) dsn.Items.Add(value);
        int indiceAnterior = dsn.FindStringExact(anterior);
        if (indiceAnterior >= 0) dsn.SelectedIndex = indiceAnterior;
        else if (dsn.Items.Count > 0) dsn.SelectedIndex = 0;
        dsn.EndUpdate();

        bool hasCompatibleDsn = dsn.Items.Count > 0;
        dsn.Enabled = local && hasCompatibleDsn;
        test.Enabled = local && hasCompatibleDsn;
        driver.Enabled = !siescon;
        if (siescon)
        {
            if (user.Text == "DBA") user.Text = "";
            if (password.Text == "sql") password.Text = "";
        }
        else
        {
            if (string.IsNullOrWhiteSpace(user.Text)) user.Text = "DBA";
            if (password.Text.Length == 0) password.Text = "sql";
        }
        if (local && !hasCompatibleDsn)
            status.Text = siescon
                ? "Nenhum DSN de sistema Pervasive/PSQL de 32 bits foi encontrado. Configure-o antes de conectar."
                : "Nenhum DSN de sistema SQL Anywhere de 64 bits foi encontrado. Configure-o antes de conectar.";
        else if (status.Text.StartsWith("Nenhum DSN", StringComparison.Ordinal))
            status.Text = "";
    }

    private async Task TestConnection()
    {
        await Busy(async () =>
        {
            if (string.IsNullOrWhiteSpace(dsn.Text))
                throw new InvalidOperationException("Selecione um DSN de sistema compatível com o ERP.");
            if (mode.SelectedIndex == SiesconLocalMode)
            {
                await TestSiesconConnection();
            }
            else await Task.Run(() =>
            {
                using var connection = new OdbcConnection($"DSN={dsn.Text};UID={user.Text};PWD={password.Text}");
                connection.ConnectionTimeout = 10;
                connection.Open();
                using var command = new OdbcCommand("SELECT TOP 1 codi_emp FROM bethadba.geempre", connection);
                command.ExecuteScalar();
            });
            status.Text = mode.SelectedIndex == SiesconLocalMode
                ? "Conexão confirmada. O Siescon está pronto para sincronizar."
                : "Conexão confirmada. O Domínio está pronto para sincronizar.";
        });
    }

    private async Task TestSiesconConnection()
    {
        string bridge = Path.GetFullPath(Path.Combine(
            AppContext.BaseDirectory,
            "..",
            "Service",
            "odbc-bridge",
            "Cica.Agent.OdbcBridge.exe"));
        if (!File.Exists(bridge))
            throw new InvalidOperationException(
                "A ponte ODBC de 32 bits não está instalada. Repare o pacote CICA Agent.");

        using Process process = Process.Start(new ProcessStartInfo(bridge)
        {
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        }) ?? throw new InvalidOperationException("Não foi possível iniciar a ponte ODBC de 32 bits.");

        string request = JsonSerializer.Serialize(new
        {
            Mode = "test",
            Dsn = dsn.Text,
            User = user.Text,
            Password = password.Text,
            Sql = "",
            Parameters = Array.Empty<object>(),
            MaxRows = 0,
        });
        await process.StandardInput.WriteLineAsync(request);
        await process.StandardInput.FlushAsync();
        process.StandardInput.Close();

        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        Task<string> output = process.StandardOutput.ReadToEndAsync(timeout.Token);
        Task<string> error = process.StandardError.ReadToEndAsync(timeout.Token);
        try
        {
            await process.WaitForExitAsync(timeout.Token);
        }
        catch (OperationCanceledException)
        {
            if (!process.HasExited) process.Kill(entireProcessTree: true);
            throw new InvalidOperationException("O teste do Siescon excedeu 30 segundos.");
        }
        string response = await output;
        string failure = await error;
        if (process.ExitCode != 0)
            throw new InvalidOperationException(
                $"A ponte ODBC de 32 bits recusou a conexão: {failure.Trim()}");
        using JsonDocument result = JsonDocument.Parse(response);
        if (!result.RootElement.TryGetProperty("ok", out JsonElement ok) || !ok.GetBoolean())
            throw new InvalidOperationException("A ponte ODBC não confirmou a conexão.");
    }

    private async Task Enroll()
    {
        await Busy(async () =>
        {
            if (!Uri.TryCreate(server.Text.Trim(), UriKind.Absolute, out Uri? uri) || uri.Scheme != "https")
                throw new InvalidOperationException("Informe um endereço HTTPS válido da CICA.");
            SourceSystemProfile profile = SelectedSourceProfile();
            bool siescon = profile.Uses32BitOdbcBridge;
            bool local = mode.SelectedIndex is DominioLocalMode or SiesconLocalMode;
            if (string.IsNullOrWhiteSpace(code.Text))
                throw new InvalidOperationException("Informe o código temporário mostrado na CICA.");
            if (local && string.IsNullOrWhiteSpace(dsn.Text))
                throw new InvalidOperationException("Selecione o DSN do ERP local.");
            if (profile.RequiresSqlAnywhereDriver && string.IsNullOrWhiteSpace(driver.Text))
                throw new InvalidOperationException("Selecione o driver SQL Anywhere.");
            using RSA key = RSA.Create(3072);
            var request = new CertificateRequest(
                $"CN=CICA Agent {Environment.MachineName}", key, HashAlgorithmName.SHA256,
                RSASignaturePadding.Pkcs1);
            string csr = PemEncoding.WriteString("CERTIFICATE REQUEST", request.CreateSigningRequest());
            using var http = new HttpClient
            {
                BaseAddress = new Uri(uri.ToString().TrimEnd('/') + "/"),
                Timeout = TimeSpan.FromSeconds(65)
            };
            using HttpResponseMessage response = await http.PostAsJsonAsync("api/agent/v2/enroll", new
            { code = code.Text.Trim(), label = label.Text.Trim(), fingerprint = MachineFingerprint(), csr });
            string responseText = await response.Content.ReadAsStringAsync();
            if (!response.IsSuccessStatusCode)
            {
                using JsonDocument failed = JsonDocument.Parse(responseText);
                throw new InvalidOperationException(failed.RootElement.GetProperty("error").GetString());
            }
            using JsonDocument result = JsonDocument.Parse(responseText);
            JsonElement root = result.RootElement;
            X509Certificate2 certificate = X509Certificate2.CreateFromPem(root.GetProperty("certificate").GetString()!);
            using X509Certificate2 identity = certificate.CopyWithPrivateKey(key);
            string pfx = Convert.ToBase64String(identity.Export(X509ContentType.Pkcs12));
            Save(new Config(server.Text.Trim(), root.GetProperty("agent_id").GetString()!,
                root.GetProperty("shared_secret").GetString()!, pfx,
                local ? dsn.Text : null,
                profile.RequiresSqlAnywhereDriver ? driver.Text : "",
                user.Text,
                password.Text,
                string.IsNullOrWhiteSpace(archiveRoot.Text) ? null : Path.GetFullPath(archiveRoot.Text),
                profile.SourceSystem));
            status.Text = "Tudo pronto. O serviço CICA Agent pode ser iniciado.";
        });
    }

    private void ChooseArchiveRoot()
    {
        using var dialog = new FolderBrowserDialog
        {
            Description = "Escolha a mesma pasta raiz configurada na Triagem da CICA",
            UseDescriptionForTitle = true,
            ShowNewFolderButton = true,
        };
        if (dialog.ShowDialog(this) == DialogResult.OK) archiveRoot.Text = dialog.SelectedPath;
    }

    private async Task Busy(Func<Task> action)
    {
        test.Enabled = finish.Enabled = false;
        status.Text = "Aguarde…";
        try { await action(); }
        catch (Exception error) { status.Text = error.Message; }
        finally { finish.Enabled = true; RefreshMode(); }
    }

    private static string MachineFingerprint()
    {
        string input = Environment.MachineName + "|" + Environment.OSVersion.VersionString;
        return Convert.ToHexString(SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(input))).ToLowerInvariant();
    }

    private SourceSystemProfile SelectedSourceProfile() => SourceSystemProfiles.Get(
        mode.SelectedIndex == SiesconLocalMode ? "siescon" : "dominio");

    private static IEnumerable<string> DiscoverDsns(SourceSystemProfile profile)
    {
        const string path = @"SOFTWARE\ODBC\ODBC.INI\ODBC Data Sources";
        RegistryView view = profile.Uses32BitOdbcBridge
            ? RegistryView.Registry32
            : RegistryView.Registry64;
        using (RegistryKey baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, view))
        using (RegistryKey? key = baseKey.OpenSubKey(path))
            if (key != null)
                foreach (string name in key.GetValueNames().Order(StringComparer.OrdinalIgnoreCase))
                {
                    string registeredDriver = key.GetValue(name)?.ToString() ?? "";
                    if (profile.DsnDriverMarkers.Any(marker => registeredDriver.Contains(
                        marker, StringComparison.OrdinalIgnoreCase)))
                        yield return name;
                }
    }

    private static IEnumerable<string> DiscoverDrivers()
    {
        const string path = @"SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers";
        var found = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        using (RegistryKey baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64))
        using (RegistryKey? key = baseKey.OpenSubKey(path))
            if (key != null)
                foreach (string name in key.GetValueNames())
                    if (name.Contains("SQL Anywhere", StringComparison.OrdinalIgnoreCase))
                        found.Add(name);
        return found.Order();
    }

    private static void Save(Config config)
    {
        string directory = Path.Combine(Environment.GetFolderPath(
            Environment.SpecialFolder.CommonApplicationData), "CICA", "Agent");
        Directory.CreateDirectory(directory);
        byte[] plain = JsonSerializer.SerializeToUtf8Bytes(config);
        try
        {
            File.WriteAllBytes(Path.Combine(directory, "agent.config"),
                ProtectedData.Protect(plain, null, DataProtectionScope.LocalMachine));
            using Process? acl = Process.Start(new ProcessStartInfo("icacls.exe",
                $"\"{directory}\" /inheritance:r /grant:r *S-1-5-18:(OI)(CI)F *S-1-5-32-544:(OI)(CI)F")
            { UseShellExecute = false, CreateNoWindow = true });
            acl?.WaitForExit();
            if (acl?.ExitCode != 0) throw new InvalidOperationException(
                "Não foi possível restringir a pasta de configuração.");
        }
        finally { CryptographicOperations.ZeroMemory(plain); }
    }

    private sealed record Config(string ServerUrl, string AgentId, string SharedSecret,
        string CertificatePfxBase64, string? Dsn, string SqlAnywhereDriver,
        string DatabaseUser, string DatabasePassword, string? WindowsArchiveRoot,
        string SourceSystem);
}
