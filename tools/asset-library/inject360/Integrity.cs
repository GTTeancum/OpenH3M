// Original 360 Halo 3 cache integrity values: resource page CRC/SHA-1s and the header body checksum + salted digests.
// Algorithms per the project's cache notes (cache_integrity.py / cache_registry.py); the salt is the 34-byte block in
// default.xex. New implementation; `verify` recomputes a stock map's stored values to prove it.
using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;

namespace Inject360
{
    public static class Integrity
    {
        static uint Be32(byte[] b, long at) => (uint)(b[at] << 24 | b[at + 1] << 16 | b[at + 2] << 8 | b[at + 3]);
        static void Put(byte[] b, long at, uint v) { b[at] = (byte)(v >> 24); b[at + 1] = (byte)(v >> 16); b[at + 2] = (byte)(v >> 8); b[at + 3] = (byte)v; }

        static byte[] Sha(byte[] salt, byte[] data, int offset, int count)
        {
            using (var s = SHA1.Create()) { s.TransformBlock(salt, 0, salt.Length, null, 0); s.TransformFinalBlock(data, offset, count); return s.Hash; }
        }

        // Page hashes: SHA-1(salt + data), SHA-1(salt + first KiB), SHA-1(salt + last KiB).
        public static (byte[], byte[], byte[]) PageHashes(byte[] salt, byte[] raw)
        {
            int n = Math.Min(1024, raw.Length);
            return (Sha(salt, raw, 0, raw.Length), Sha(salt, raw, 0, n), Sha(salt, raw, raw.Length - n, n));
        }

        static byte[] NormalizedHeader(byte[] d)
        {
            var h = new byte[0x3000]; Buffer.BlockCopy(d, 0, h, 0, 0x3000);
            foreach (var (at, size) in new[] { (0x320, 4), (0x328, 8), (0x330, 0x13C), (0x1C, 0x100), (0x144, 8), (0x16C, 0x20), (0x49C, 0x10) })
                Array.Clear(h, at, size);
            return h;
        }

        // Returns (body checksum, three header digests) for a complete version-11 360 cache image.
        public static (uint checksum, byte[] digests) Compute(byte[] d, byte[] salt)
        {
            if (d.Length < 0x3000 || d[0] != 'h' || d[1] != 'e' || d[2] != 'a' || d[3] != 'd' || Be32(d, 4) != 11 || Be32(d, 8) != d.Length)
                throw new Exception("not a complete version-11 360 cache (header length must equal file length)");
            uint x = 0; for (long at = 0x3000; at + 4 <= d.Length; at += 4) x ^= Be32(d, at);
            Put(d, 0x2C4, x);   // the header digest covers the body checksum
            long start = (Be32(d, 0x48C) + Be32(d, 0x474)) & 0xFFFFFFFF;
            long[] sizes = { (long)Be32(d, 0x2F4) + Be32(d, 0x2FC) + Be32(d, 0x304), (long)Be32(d, 0x30C) + Be32(d, 0x314) + Be32(d, 0x31C) };
            if (sizes.Sum() != Be32(d, 0x18) || sizes.Sum() != Be32(d, 0x490)) throw new Exception("metadata partition sizes disagree");
            var digests = new byte[60];
            Buffer.BlockCopy(Sha(salt, NormalizedHeader(d), 0, 0x3000), 0, digests, 0, 20);
            bool resourcesOnly = (short)(d[0x13C] << 8 | d[0x13D]) == 3 && sizes.All(s => s == 0);
            for (int i = 0; i < 2; i++)
            {
                if (!resourcesOnly) Buffer.BlockCopy(Sha(salt, d, (int)start, (int)sizes[i]), 0, digests, 20 + i * 20, 20);
                start += sizes[i];
            }
            return (x, digests);
        }

        public static string Verify(string path, byte[] salt)
        {
            var d = File.ReadAllBytes(path);
            uint storedX = Be32(d, 0x2C4); var storedD = d.Skip(0x330).Take(60).ToArray();
            var (x, dig) = Compute(d, salt);
            bool okX = x == storedX, okD = dig.SequenceEqual(storedD);
            return $"body checksum {(okX ? "matches" : "DIFFERS")}, header digests {(okD ? "match" : "DIFFER")}";
        }

        public static void Finalize(string path, byte[] salt)
        {
            var d = File.ReadAllBytes(path);
            var (x, dig) = Compute(d, salt);
            using (var f = File.Open(path, FileMode.Open, FileAccess.ReadWrite))
            {
                var b = new byte[4]; Put(b, 0, x); f.Seek(0x2C4, SeekOrigin.Begin); f.Write(b, 0, 4);
                // the body checksum sits in the header, which is excluded from both itself and (normalized) the digests
                f.Seek(0x330, SeekOrigin.Begin); f.Write(dig, 0, 60);
            }
        }
    }
}
