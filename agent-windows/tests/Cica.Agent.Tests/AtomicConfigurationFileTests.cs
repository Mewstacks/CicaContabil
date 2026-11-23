using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class AtomicConfigurationFileTests : IDisposable
{
    private readonly string directory = Path.Combine(Path.GetTempPath(), "cica-atomic-" + Guid.NewGuid().ToString("N"));
    public AtomicConfigurationFileTests() => Directory.CreateDirectory(directory);
    public void Dispose() => Directory.Delete(directory, recursive: true);

    [Fact]
    public void InitialWriteAndReplacementLeaveOnlyTheCompleteConfiguration()
    {
        string path = Path.Combine(directory, "agent.config");
        AtomicConfigurationFile.Write(path, [1, 2, 3]);
        Assert.Equal(new byte[] { 1, 2, 3 }, File.ReadAllBytes(path));
        byte[] replacement = Enumerable.Repeat((byte)42, 128 * 1024).ToArray();
        AtomicConfigurationFile.Write(path, replacement);
        Assert.Equal(replacement, File.ReadAllBytes(path));
        Assert.Single(Directory.GetFiles(directory));
    }

    [Fact]
    public void FailedReplacementCleansItsEncryptedTemporaryFile()
    {
        string path = Path.Combine(directory, "agent.config");
        Directory.CreateDirectory(path);
        Assert.ThrowsAny<IOException>(() => AtomicConfigurationFile.Write(path, [4, 5, 6]));
        Assert.True(Directory.Exists(path));
        Assert.Empty(Directory.GetFiles(directory));
    }

    [WindowsFact]
    public void LockedWindowsConfigurationKeepsItsLastValidBytesOnFailure()
    {
        string path = Path.Combine(directory, "agent.config");
        byte[] previous = [1, 2, 3];
        AtomicConfigurationFile.Write(path, previous);
        using (var locked = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
            Assert.ThrowsAny<IOException>(() => AtomicConfigurationFile.Write(path, [4, 5, 6]));
        Assert.Equal(previous, File.ReadAllBytes(path));
        Assert.Single(Directory.GetFiles(directory));
    }

    private sealed class WindowsFactAttribute : FactAttribute
    {
        public WindowsFactAttribute()
        {
            if (!OperatingSystem.IsWindows()) Skip = "Requires Windows file sharing/replace semantics.";
        }
    }
}
