using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class InboxRulesTests
{
    [Theory]
    [InlineData("~$guia.docx")]
    [InlineData(".hidden.pdf")]
    [InlineData("guia.pdf.crdownload")]
    [InlineData("guia.PART")]
    [InlineData("relatorio.tmp")]
    [InlineData("Thumbs.db")]
    public void TemporaryAndHiddenFilesAreIgnored(string name) =>
        Assert.True(InboxRules.IsIgnored(name));

    [Theory]
    [InlineData("guia.pdf")]
    [InlineData("extrato 01.2026.ofx")]
    public void RealDocumentsAreNotIgnored(string name) => Assert.False(InboxRules.IsIgnored(name));

    [Fact]
    public void ReservedFoldersAreRecognisedCaseInsensitively()
    {
        Assert.True(InboxRules.IsReservedFolder("_PROCESSADOS"));
        Assert.True(InboxRules.IsReservedFolder("_quarentena"));
        Assert.False(InboxRules.IsReservedFolder("clientes"));
    }

    [Fact]
    public void FileIsStableOnlyAfterUnchangedSizeAndTimeForTheWholeWindow()
    {
        var tracker = new StabilityTracker();
        DateTime t0 = new(2026, 11, 26, 12, 0, 0, DateTimeKind.Utc);
        DateTime modified = t0.AddMinutes(-10);
        Assert.False(tracker.IsStable("a.pdf", 100, modified, t0, 30));
        Assert.False(tracker.IsStable("a.pdf", 100, modified, t0.AddSeconds(10), 30));
        Assert.True(tracker.IsStable("a.pdf", 100, modified, t0.AddSeconds(31), 30));
    }

    [Fact]
    public void GrowingFileRestartsTheWindow()
    {
        var tracker = new StabilityTracker();
        DateTime t0 = new(2026, 11, 26, 12, 0, 0, DateTimeKind.Utc);
        Assert.False(tracker.IsStable("a.pdf", 100, t0.AddMinutes(-5), t0, 30));
        Assert.False(tracker.IsStable("a.pdf", 250, t0.AddMinutes(-5), t0.AddSeconds(40), 30));
        Assert.False(tracker.IsStable("a.pdf", 250, t0.AddMinutes(-5), t0.AddSeconds(50), 30));
        Assert.True(tracker.IsStable("a.pdf", 250, t0.AddMinutes(-5), t0.AddSeconds(71), 30));
    }

    [Fact]
    public void FileModifiedJustNowIsNotStableEvenIfObservedTwice()
    {
        var tracker = new StabilityTracker();
        DateTime t0 = new(2026, 11, 26, 12, 0, 0, DateTimeKind.Utc);
        Assert.False(tracker.IsStable("a.pdf", 100, t0, t0, 30));
        Assert.False(tracker.IsStable("a.pdf", 100, t0, t0.AddSeconds(31).AddSeconds(-40), 30));
    }

    [Theory]
    [InlineData(1, 1)]
    [InlineData(2, 2)]
    [InlineData(4, 8)]
    [InlineData(20, 60)]
    public void RetryBackoffDoublesAndCapsAtOneHour(int attempt, int minutes) =>
        Assert.Equal(TimeSpan.FromMinutes(minutes), InboxRules.RetryDelay(attempt));

    [Theory]
    [InlineData(@"D:\Clientes", @"D:\Clientes\Entrada", true)]
    [InlineData(@"D:\Clientes\", @"d:\clientes\ENTRADA\sub", true)]
    [InlineData(@"D:\Clientes", @"D:\Clientes", false)]
    [InlineData(@"D:\Clientes", @"D:\ClientesX\Entrada", false)]
    [InlineData(@"D:\Clientes", @"D:\Clientes\..\Windows", false)]
    [InlineData(@"D:\Clientes", @"C:\Windows\System32", false)]
    [InlineData(@"D:\Clientes", "Entrada", false)]
    [InlineData("", @"D:\Clientes\Entrada", false)]
    public void WatchedPathMustSitStrictlyUnderTheLocalRoot(string root, string path, bool expected) =>
        Assert.Equal(expected, InboxRules.IsStrictlyUnder(root, path));
}
