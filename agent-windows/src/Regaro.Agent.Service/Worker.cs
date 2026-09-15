using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Regaro.Agent.Service;

internal sealed class Worker(ILogger<Worker> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                AgentConfig config = AgentConfig.Load();
                using var client = new AgentClient(config);
                await client.PostAsync("api/agent/v2/heartbeat", new { version = "1.0.0" }, stoppingToken);
                await new BackupProcessor(config, client).RunOnce(stoppingToken);
            }
            catch (Exception error) when (error is not OperationCanceledException)
            {
                logger.LogWarning("Regaro agent cycle failed with code {Code}", error.GetType().Name);
            }
            await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
        }
    }
}
