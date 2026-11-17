namespace Cica.Agent.Service;

internal static class WorkerFailurePolicy
{
    // HttpClient.Timeout cancels its own token. Only the service's actual stop
    // token may bypass recovery and terminate the worker's execution loop.
    internal static bool Recover(Exception error, CancellationToken stoppingToken)
        => error is not OperationCanceledException || !stoppingToken.IsCancellationRequested;
}
