namespace Cica.Agent.Service;

internal static class AtomicConfigurationFile
{
    // The caller creates the protected configuration directory. Only encrypted
    // bytes enter this same-directory temporary file; failed replacement keeps
    // the previous DPAPI configuration and never truncates it in place.
    internal static void Write(string path, ReadOnlySpan<byte> encrypted)
    {
        string temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew,
                FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough))
            {
                stream.Write(encrypted);
                stream.Flush(flushToDisk: true);
            }
            if (File.Exists(path)) File.Replace(temporary, path, null);
            else File.Move(temporary, path);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }
}
