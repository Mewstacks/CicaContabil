using System.Data.Odbc;
using System.Diagnostics;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using Microsoft.Win32;

ApplicationConfiguration.Initialize();
Application.Run(new SetupForm());

internal sealed class SetupForm : Form
{
    private readonly TextBox server = new() { Text = "https://app.regaro.com.br", Dock = DockStyle.Fill };
    private readonly TextBox code = new() { Dock = DockStyle.Fill };
    private readonly TextBox label = new() { Text = Environment.MachineName, Dock = DockStyle.Fill };
    private readonly ComboBox mode = new() { Dock = DockStyle.Fill, DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly ComboBox dsn = new() { Dock = DockStyle.Fill, DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly ComboBox driver = new() { Dock = DockStyle.Fill };
    private readonly TextBox user = new() { Text = "DBA", Dock = DockStyle.Fill };
    private readonly TextBox password = new() { Text = "sql", UseSystemPasswordChar = true, Dock = DockStyle.Fill };
    private readonly TextBox archiveRoot = new() { Dock = DockStyle.Fill };
    private readonly Label status = new() { AutoSize = true, MaximumSize = new(520, 0), Padding = new(0, 8, 0, 8) };
    private readonly Button test = new() { Text = "Testar conexão", AutoSize = true };
    private readonly Button finish = new() { Text = "Conectar ao Regaro", AutoSize = true };
    private readonly Button chooseArchiveRoot = new() { Text = "Escolher pasta de arquivos", AutoSize = true };

    internal SetupForm()
    {
        Text = "Configurar Regaro Agent";
        Width = 640;
        Height = 650;
        MinimumSize = new(560, 560);
        StartPosition = FormStartPosition.CenterScreen;
        Font = new("Segoe UI", 10);
        mode.Items.AddRange(["Domínio Web — backups manuais", "Domínio Local — DSN"]);
        mode.SelectedIndex = 0;
        foreach (string value in DiscoverDsns()) dsn.Items.Add(value);
        if (dsn.Items.Count > 0) dsn.SelectedIndex = 0;
        foreach (string value in DiscoverDrivers())
            driver.Items.Add(value);
        if (driver.Items.Count > 0) driver.SelectedIndex = 0;

        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new(28),
            ColumnCount = 1, AutoScroll = true };
        layout.Controls.Add(new Label { Text = "Regaro Agent", Font = new("Segoe UI Semibold", 20), AutoSize = true });
        layout.Controls.Add(new Label { Text = "Conecte este servidor sem abrir portas. A chave privada fica somente neste computador.", AutoSize = true, MaximumSize = new(540, 0) });
        Add(layout, "Endereço do Regaro", server);
        Add(layout, "Código temporário mostrado no Regaro", code);
        Add(layout, "Nome deste servidor", label);
        Add(layout, "Fonte de dados", mode);
        Add(layout, "DSN do Domínio Local (opcional)", dsn);
        Add(layout, "Driver SQL Anywhere para backups", driver);
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
        bool local = mode.SelectedIndex == 1;
        dsn.Enabled = local;
        test.Enabled = local;
    }

    private async Task TestConnection()
    {
        await Busy(async () =>
        {
            await Task.Run(() =>
            {
                using var connection = new OdbcConnection($"DSN={dsn.Text};UID={user.Text};PWD={password.Text}");
                connection.ConnectionTimeout = 10;
                connection.Open();
                using var command = new OdbcCommand("SELECT TOP 1 codi_emp FROM bethadba.geempre", connection);
                command.ExecuteScalar();
            });
            status.Text = "Conexão confirmada. O Domínio está pronto para sincronizar.";
        });
    }

    private async Task Enroll()
    {
        await Busy(async () =>
        {
            if (!Uri.TryCreate(server.Text.Trim(), UriKind.Absolute, out Uri? uri) || uri.Scheme != "https")
                throw new InvalidOperationException("Informe um endereço HTTPS válido do Regaro.");
            if (string.IsNullOrWhiteSpace(code.Text) || string.IsNullOrWhiteSpace(driver.Text))
                throw new InvalidOperationException("Informe o código e selecione o driver SQL Anywhere.");
            using RSA key = RSA.Create(3072);
            var request = new CertificateRequest(
                $"CN=Regaro Agent {Environment.MachineName}", key, HashAlgorithmName.SHA256,
                RSASignaturePadding.Pkcs1);
            string csr = PemEncoding.WriteString("CERTIFICATE REQUEST", request.CreateSigningRequest());
            using var http = new HttpClient { BaseAddress = new Uri(uri.ToString().TrimEnd('/') + "/"),
                Timeout = TimeSpan.FromSeconds(65) };
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
                mode.SelectedIndex == 1 ? dsn.Text : null, driver.Text, user.Text, password.Text,
                string.IsNullOrWhiteSpace(archiveRoot.Text) ? null : Path.GetFullPath(archiveRoot.Text)));
            status.Text = "Tudo pronto. O serviço Regaro Agent pode ser iniciado.";
        });
    }

    private void ChooseArchiveRoot()
    {
        using var dialog = new FolderBrowserDialog
        {
            Description = "Escolha a mesma pasta raiz configurada na Triagem do Regaro",
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

    private static IEnumerable<string> DiscoverDsns()
    {
        const string path = @"SOFTWARE\ODBC\ODBC.INI\ODBC Data Sources";
        foreach (RegistryView view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
        using (RegistryKey baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, view))
        using (RegistryKey? key = baseKey.OpenSubKey(path))
            if (key != null)
                foreach (string name in key.GetValueNames()) yield return name;
    }

    private static IEnumerable<string> DiscoverDrivers()
    {
        const string path = @"SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers";
        var found = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (RegistryView view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
        using (RegistryKey baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, view))
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
            Environment.SpecialFolder.CommonApplicationData), "Regaro", "Agent");
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
        string DatabaseUser, string DatabasePassword, string? WindowsArchiveRoot);
}
