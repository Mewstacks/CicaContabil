namespace Cica.Agent.Service;

// In-memory only: restarting the process never inherits an earlier healthy cycle.
internal sealed class RuntimeCycleEvidence
{
    internal DateTimeOffset? CompletedAt { get; private set; }
    internal string? CompletedState { get; private set; }

    internal void Observe(string state, DateTimeOffset observedAt)
    {
        if (state is "ready" or "update_available" or "source_review_required")
        {
            CompletedAt = observedAt;
            CompletedState = state;
        }
        else if (state != "synchronizing")
        {
            CompletedAt = null;
            CompletedState = null;
        }
    }
}
