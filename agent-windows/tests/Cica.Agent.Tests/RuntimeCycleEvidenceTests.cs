using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class RuntimeCycleEvidenceTests
{
    [Theory]
    [InlineData("ready")]
    [InlineData("update_available")]
    [InlineData("source_review_required")]
    public void ActiveCyclePreservesTheLastCompletedCycleAndReview(string state)
    {
        var evidence = new RuntimeCycleEvidence();
        var completed = DateTimeOffset.Parse("2026-11-17T12:00:00Z");
        evidence.Observe(state, completed);
        evidence.Observe("synchronizing", completed.AddSeconds(1));
        Assert.Equal(completed, evidence.CompletedAt);
        Assert.Equal(state, evidence.CompletedState);
    }

    [Theory]
    [InlineData("temporary_error")]
    [InlineData("authorization_error")]
    [InlineData("configuration_error")]
    [InlineData("awaiting_activation")]
    [InlineData("awaiting_configuration")]
    [InlineData("catalog_error")]
    public void FailureOrDisabledConfigurationInvalidatesEarlierCompletion(string state)
    {
        var evidence = new RuntimeCycleEvidence();
        var completed = DateTimeOffset.Parse("2026-11-17T12:00:00Z");
        evidence.Observe("ready", completed);
        evidence.Observe(state, completed.AddSeconds(1));
        evidence.Observe("synchronizing", completed.AddSeconds(2));
        Assert.Null(evidence.CompletedAt);
        Assert.Null(evidence.CompletedState);
    }

    [Fact]
    public void NewProcessCannotClaimCompletionFromAnEarlierProcess()
    {
        var oldProcess = new RuntimeCycleEvidence();
        oldProcess.Observe("ready", DateTimeOffset.UtcNow);
        var restarted = new RuntimeCycleEvidence();
        restarted.Observe("synchronizing", DateTimeOffset.UtcNow);
        Assert.Null(restarted.CompletedAt);
        Assert.Null(restarted.CompletedState);
    }
}
