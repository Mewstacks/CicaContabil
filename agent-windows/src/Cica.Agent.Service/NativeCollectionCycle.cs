namespace Cica.Agent.Service;

internal readonly record struct NativeCollectionOutcome(
    bool ProcessedJob, bool RequiresReview, bool Failed = false)
{
    internal static NativeCollectionOutcome Idle(bool review = false) => new(false, review);
    internal static NativeCollectionOutcome Completed(bool review) => new(true, review);
    internal static NativeCollectionOutcome Rejected() => new(true, true, true);
}

// Each pair returns through the Worker's authenticated control cycle. Only the
// idle delay and repeated portfolio scan are omitted while a bounded batch is active.
internal sealed class NativeCollectionCycle(TimeProvider? clock = null)
{
    internal const int MaximumPairs = 4;
    internal static readonly TimeSpan MaximumBatchDuration = TimeSpan.FromSeconds(30);
    internal static readonly TimeSpan IdleDelay = TimeSpan.FromMinutes(1);
    private readonly TimeProvider _clock = clock ?? TimeProvider.System;
    private bool _allowed;
    private int _pairs;
    private long _started;
    internal bool SynchronizePortfolio { get; private set; } = true;
    internal bool ContinueImmediately { get; private set; }

    internal void Prepare(bool collectionEnabled, bool activeScope, bool configurationChanged)
    {
        if (!collectionEnabled || !activeScope || configurationChanged) Reset();
        _allowed = collectionEnabled && activeScope;
    }

    internal void Reset()
    {
        _allowed = false;
        _pairs = 0;
        SynchronizePortfolio = true;
        ContinueImmediately = false;
    }

    internal async Task<NativeCollectionOutcome> RunAsync(
        Func<CancellationToken, Task<NativeCollectionOutcome>> ledger,
        Func<CancellationToken, Task<NativeCollectionOutcome>> titles,
        CancellationToken token)
    {
        try
        {
            token.ThrowIfCancellationRequested();
            if (!_allowed) return NativeCollectionOutcome.Idle();
            if (_pairs == 0) _started = _clock.GetTimestamp();
            var ledgerResult = await ledger(token);
            token.ThrowIfCancellationRequested();
            // A reported source failure must not starve the other family. Transport
            // or authorization exceptions still abort immediately via the catch below.
            var titleResult = await titles(token);
            token.ThrowIfCancellationRequested();
            var result = new NativeCollectionOutcome(
                ledgerResult.ProcessedJob || titleResult.ProcessedJob,
                ledgerResult.RequiresReview || titleResult.RequiresReview,
                ledgerResult.Failed || titleResult.Failed);
            if (!result.ProcessedJob || result.Failed)
            {
                Reset();
                return result;
            }
            ContinueImmediately = true;
            _pairs++;
            SynchronizePortfolio = _pairs >= MaximumPairs
                || _clock.GetElapsedTime(_started) >= MaximumBatchDuration;
            if (SynchronizePortfolio) _pairs = 0;
            return result;
        }
        catch
        {
            Reset();
            throw;
        }
    }
}
