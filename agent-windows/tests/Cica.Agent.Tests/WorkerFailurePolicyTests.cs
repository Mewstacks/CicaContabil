using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class WorkerFailurePolicyTests
{
    [Fact]
    public async Task HttpClientTimeoutReturnsToRecoveryWithoutStoppingTheWorker()
    {
        using var handler = new WaitingHandler();
        using var client = new HttpClient(handler) { Timeout = TimeSpan.FromMilliseconds(30) };
        using var service = new CancellationTokenSource();
        var cycle = new NativeCollectionCycle();
        cycle.Prepare(true, true, false);
        var recovered = false;
        var titlesCalled = false;
        try
        {
            await cycle.RunAsync(async token => {
                using var response = await client.GetAsync("https://synthetic.invalid/never-network", token);
                return NativeCollectionOutcome.Completed(false);
            }, token => {
                titlesCalled = true;
                return Task.FromResult(NativeCollectionOutcome.Idle());
            }, service.Token);
        }
        catch (Exception error) when (WorkerFailurePolicy.Recover(error, service.Token))
        {
            Assert.IsAssignableFrom<OperationCanceledException>(error);
            Assert.IsType<TimeoutException>(error.InnerException);
            recovered = true;
        }
        Assert.True(recovered);
        Assert.False(service.IsCancellationRequested);
        Assert.False(titlesCalled);
        Assert.False(cycle.ContinueImmediately);
        Assert.True(cycle.SynchronizePortfolio);
    }

    [Fact]
    public async Task RealServiceStopPropagatesImmediatelyWithoutRecoveryOrTheOtherFamily()
    {
        using var handler = new WaitingHandler();
        using var client = new HttpClient(handler) { Timeout = Timeout.InfiniteTimeSpan };
        using var service = new CancellationTokenSource();
        var cycle = new NativeCollectionCycle();
        cycle.Prepare(true, true, false);
        var recovered = false;
        var titlesCalled = false;
        var run = cycle.RunAsync(async token => {
            using var response = await client.GetAsync("https://synthetic.invalid/never-network", token);
            return NativeCollectionOutcome.Completed(false);
        }, token => {
            titlesCalled = true;
            return Task.FromResult(NativeCollectionOutcome.Idle());
        }, service.Token);
        await handler.Started.Task;
        service.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(async () => {
            try { await run; }
            catch (Exception error) when (WorkerFailurePolicy.Recover(error, service.Token))
            { recovered = true; }
        });
        Assert.False(recovered);
        Assert.False(titlesCalled);
        Assert.False(cycle.ContinueImmediately);
    }

    private sealed class WaitingHandler : HttpMessageHandler
    {
        internal readonly TaskCompletionSource<bool> Started = new(TaskCreationOptions.RunContinuationsAsynchronously);
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            Started.TrySetResult(true);
            await Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken);
            throw new InvalidOperationException("The synthetic handler must be cancelled.");
        }
    }
}
