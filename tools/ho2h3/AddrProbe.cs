// addr <map> <hex guest address>: which tag's data a guest address falls in (nearest tag starts around it), for crash triage
using System;
using System.Linq;
using Blamite.Blam;
using Blamite.Util;

namespace Ho2H3
{
    static class AddrProbe
    {
        public static int Run(string[] a)
        {
            using (var m = new Map(a[1]))
            {
                uint t = Convert.ToUInt32(a[2].Replace("0x", ""), 16);
                var tags = m.File.Tags.Where(x => x != null && x.MetaLocation != null).Select(x => (x, p: x.MetaLocation.AsPointer())).OrderBy(z => z.p).ToList();
                Console.WriteLine($"tags 0x{tags.First().p:X8} .. 0x{tags.Last().p:X8} meta area 0x{m.File.MetaArea.BasePointer:X8} size 0x{m.File.MetaArea.Size:X} ({m.File.MetaArea.Size / 1048576.0:F2} MB)");
                if (t == 1)
                {
                    // size by group: distance to the next tag start (blocks follow their tag), the top 15 groups and tags
                    var sz = tags.Select((z, i) => (z.x, n: (i + 1 < tags.Count ? tags[i + 1].p : z.p) - z.p)).ToList();
                    foreach (var g in sz.GroupBy(z => CharConstant.ToString(z.x.Group.Magic)).Select(g => (g.Key, n: g.Sum(z => (long)z.n), c: g.Count())).OrderByDescending(g => g.n).Take(15))
                        Console.WriteLine($"{g.Key} {g.c} tags {g.n / 1048576.0:F2} MB");
                    foreach (var z in sz.OrderByDescending(z => z.n).Take(15)) Console.WriteLine($"  {z.n / 1048576.0:F2} MB {CharConstant.ToString(z.x.Group.Magic)} {m.File.FileNames.GetTagName(z.x)}");
                    return 0;
                }
                var below = tags.Where(z => z.p <= t).ToList();
                foreach (var z in below.Skip(Math.Max(0, below.Count - 3)).Concat(tags.Where(z => z.p > t).Take(2)))
                    Console.WriteLine($"0x{z.p:X8} {CharConstant.ToString(z.x.Group.Magic)} {m.File.FileNames.GetTagName(z.x)} {(z.p <= t ? "+0x" + (t - z.p).ToString("X") : "")}");
            }
            return 0;
        }
    }
}
