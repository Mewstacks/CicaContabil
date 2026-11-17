using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class NativeCollectionCycleTests
{
    private static Task<NativeCollectionOutcome> Pending(CancellationToken token)
        => Task.FromResult(NativeCollectionOutcome.Completed(review: true));
    private static Task<NativeCollectionOutcome> Empty(CancellationToken token)
        => Task.FromResult(NativeCollectionOutcome.Idle());

    [Fact]
    public async Task ActiveQueueAlternatesFamiliesAndRefreshesPortfolioInBoundedBatches()
    {
        var clock = new ManualClock();
        var cycle = new NativeCollectionCycle(clock);
        var events = new List<string>();
        var portfolioAt = new List<int>();
        for (var pair = 0; pair < 10; pair++)
        {
            // The real worker refreshes authorization/configuration on every pair.
            events.Add("control");
            cycle.Prepare(collectionEnabled: true, activeScope: true, configurationChanged: false);
            if (cycle.SynchronizePortfolio) portfolioAt.Add(pair);
            await cycle.RunAsync(
                token => { events.Add("ledger"); return Pending(token); },
                token => { events.Add("titles"); return Pending(token); }, CancellationToken.None);
            Assert.True(cycle.ContinueImmediately);
        }
        Assert.Equal(new[] { 0, 4, 8 }, portfolioAt);
        Assert.Equal(Enumerable.Range(0, 10).SelectMany(_ => new[] { "control", "ledger", "titles" }), events);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task EmptyQueueOrPendingReviewKeepsTheOneMinuteIdleCadence(bool review)
    {
        var cycle = new NativeCollectionCycle();
        cycle.Prepare(true, true, false);
        var calls = 0;
        Task<NativeCollectionOutcome> Poll(CancellationToken token)
        { calls++; return Task.FromResult(NativeCollectionOutcome.Idle(review)); }
        var result = await cycle.RunAsync(Poll, Poll, CancellationToken.None);
        Assert.Equal(2, calls);
        Assert.Equal(review, result.RequiresReview);
        Assert.False(result.ProcessedJob);
        Assert.False(cycle.ContinueImmediately);
        Assert.True(cycle.SynchronizePortfolio);
        Assert.Equal(TimeSpan.FromMinutes(1), NativeCollectionCycle.IdleDelay);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task EitherFamilyCanKeepAnActiveBatchMoving(bool ledgerHasWork)
    {
        var cycle = new NativeCollectionCycle();
        cycle.Prepare(true, true, false);
        var result = await cycle.RunAsync(ledgerHasWork ? Pending : Empty,
            ledgerHasWork ? Empty : Pending, CancellationToken.None);
        Assert.True(result.ProcessedJob);
        Assert.True(cycle.ContinueImmediately);
        Assert.False(cycle.SynchronizePortfolio);
    }

    [Fact]
    public async Task TimeBudgetReturnsToPortfolioSyncWithoutCancellingAnInFlightJob()
    {
        var clock = new ManualClock();
        var cycle = new NativeCollectionCycle(clock);
        cycle.Prepare(true, true, false);
        var result = await cycle.RunAsync(token => {
            clock.Advance(TimeSpan.FromSeconds(31));
            Assert.False(token.IsCancellationRequested);
            return Pending(token);
        }, Pending, CancellationToken.None);
        Assert.True(result.ProcessedJob);
        Assert.True(cycle.SynchronizePortfolio);
        Assert.True(cycle.ContinueImmediately);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task SourceFailureEndsTheActiveBatchAndDoesNotBusyRetry(bool ledgerFails)
    {
        var cycle = new NativeCollectionCycle();
        cycle.Prepare(true, true, false);
        await cycle.RunAsync(Pending, Pending, CancellationToken.None);
        cycle.Prepare(true, true, false);
        var titleCalled = false;
        Task<NativeCollectionOutcome> Failed(CancellationToken token)
            => Task.FromResult(NativeCollectionOutcome.Rejected());
        var result = await cycle.RunAsync(ledgerFails ? Failed : Pending, token => {
            titleCalled = true; return Failed(token);
        }, CancellationToken.None);
        Assert.True(titleCalled);
        Assert.True(result.Failed);
        Assert.True(result.RequiresReview);
        Assert.False(cycle.ContinueImmediately);
        Assert.True(cycle.SynchronizePortfolio);
    }

    [Fact]
    public async Task RepeatedRejectedLedgerDoesNotStarveValidTitleJobsOrBusyRetry()
    {
        var cycle = new NativeCollectionCycle();
        var titleJobs = new Queue<int>(new[] { 1, 2, 3 });
        var completed = new List<int>();
        for (var attempt = 0; attempt < 3; attempt++)
        {
            cycle.Prepare(true, true, false);
            var result = await cycle.RunAsync(
                _ => Task.FromResult(NativeCollectionOutcome.Rejected()),
                token => { completed.Add(titleJobs.Dequeue()); return Pending(token); },
                CancellationToken.None);
            Assert.True(result.Failed);
            Assert.False(cycle.ContinueImmediately);
            Assert.True(cycle.SynchronizePortfolio);
        }
        Assert.Equal(new[] { 1, 2, 3 }, completed);
        Assert.Empty(titleJobs);
    }

    [Fact]
    public async Task TransportFailurePropagatesToExistingWorkerBackoffAndStopsThePair()
    {
        var cycle = new NativeCollectionCycle();
        cycle.Prepare(true, true, false);
        await cycle.RunAsync(Pending, Pending, CancellationToken.None);
        var titleCalled = false;
        await Assert.ThrowsAsync<HttpRequestException>(() => cycle.RunAsync(
            _ => throw new HttpRequestException("synthetic failure"),
            token => { titleCalled = true; return Pending(token); }, CancellationToken.None));
        Assert.False(titleCalled);
        Assert.False(cycle.ContinueImmediately);
        Assert.True(cycle.SynchronizePortfolio);
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public async Task RevokedCollectionOrChangedScopeStopsBeforeAnyFurtherRead(bool enabled, bool activeScope)
    {
        var cycle = new NativeCollectionCycle();
        cycle.Prepare(true, true, false);
        await cycle.RunAsync(Pending, Pending, CancellationToken.None);
        cycle.Prepare(enabled, activeScope, false);
        var calls = 0;
        Task<NativeCollectionOutcome> Read(CancellationToken token) { calls++; return Pending(token); }
        var result = await cycle.RunAsync(Read, Read, CancellationToken.None);
        Assert.Equal(0, calls);
        Assert.False(result.ProcessedJob);
        Assert.False(cycle.ContinueImmediately);
        Assert.True(cycle.SynchronizePortfolio);
    }

    [Fact]
    public async Task ChangedConfigurationRequiresAFullPortfolioCycleBeforeContinuing()
    {
        var cycle = new NativeCollectionCycle();
        cycle.Prepare(true, true, false);
        await cycle.RunAsync(Pending, Pending, CancellationToken.None);
        Assert.False(cycle.SynchronizePortfolio);
        cycle.Prepare(true, true, true);
        Assert.True(cycle.SynchronizePortfolio);
        Assert.False(cycle.ContinueImmediately);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task CancellationBeforeOrBetweenJobsPreventsTheNextRead(bool before)
    {
        var cycle = new NativeCollectionCycle();
        using var cancellation = new CancellationTokenSource();
        cycle.Prepare(true, true, false);
        await cycle.RunAsync(Pending, Pending, CancellationToken.None);
        var ledgerCalled = false;
        var titleCalled = false;
        if (before) cancellation.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => cycle.RunAsync(token => {
            ledgerCalled = true;
            cancellation.Cancel();
            return Pending(token);
        }, token => { titleCalled = true; return Pending(token); }, cancellation.Token));
        Assert.Equal(!before, ledgerCalled);
        Assert.False(titleCalled);
        Assert.False(cycle.ContinueImmediately);
        Assert.True(cycle.SynchronizePortfolio);
    }

    private sealed class ManualClock : TimeProvider
    {
        private long _ticks;
        public override long TimestampFrequency => TimeSpan.TicksPerSecond;
        public override long GetTimestamp() => _ticks;
        internal void Advance(TimeSpan duration) => _ticks += duration.Ticks;
    }
}
