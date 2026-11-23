// texverify <mcc map> <360 map> [limit]: convert every 2D texture both maps share and compare with the real 360 bytes.
using System;
using System.Collections.Generic;
using System.Linq;
using Blamite.Blam;
using Blamite.Blam.Resources;
using Blamite.Serialization;
using Blamite.Util;
using Inject360;

partial class Program
{
    static int TexVerify(EngineDatabase db, string[] args)
    {
        using (var a = new Cache(db, args[1]))
        using (var b = new Cache(db, args[2]))
        {
            var others = new Dictionary<string, Cache>(StringComparer.OrdinalIgnoreCase);
            var pages = new Dictionary<string, byte[]>();
            var ta = a.File.Resources.LoadResourceTable(a.Reader); var tb = b.File.Resources.LoadResourceTable(b.Reader);
            Func<Cache, string, ResourcePage, byte[]> pageOf = (c, path, pg) =>
            {
                var key = path + "|" + pg.FilePath + "|" + pg.Index;
                if (pages.TryGetValue(key, out var have)) return have;
                if (pages.Count > 300) pages.Clear();
                return pages[key] = Res.PageBytes(c.File, path, c.Stream, pg, pth =>
                {
                    if (!System.IO.File.Exists(pth)) return null;
                    if (!others.TryGetValue(pth, out var o)) others[pth] = o = new Cache(db, pth);
                    return o.File;
                });
            };
            Func<Cache, string, Resource, bool, int, byte[]> seg = (c, path, r, primary, size) =>
            {
                var pg = primary ? r.Location?.PrimaryPage : r.Location?.SecondaryPage; if (pg == null || size <= 0) return null;
                var all = pageOf(c, path, pg); if (all == null) return null;
                int off = Math.Max(0, primary ? r.Location.PrimaryOffset : r.Location.SecondaryOffset);
                return off + size <= all.Length ? all.Skip(off).Take(size).ToArray() : null;
            };
            var stats = new SortedDictionary<string, int[]>(); var shown = new Dictionary<string, int>();
            int bm = CharConstant.FromString("bitm"); int limit = int.MaxValue, done = 0;
            BitmapConverter.CubeFaceMajor = args.Contains("--cube-face-major"); BitmapConverter.CubeSwapFaces = !args.Contains("--cube-no-swap");
            var sa0 = Schema.Load(a.Plugin(bm), 0x10, 0x14, 0xC); var sb0 = Schema.Load(b.Plugin(bm), 0x10, 0x14, 0xC);
            foreach (var kv in a.ByName.Where(k => k.Value.Group.Magic == bm && b.ByName.ContainsKey(k.Key)))
            {
                if (done++ >= limit) break;
                var tra = TagTree.Read(a.File, a.Reader, kv.Value, sa0); var trb = TagTree.Read(b.File, b.Reader, b.ByName[kv.Key], sb0);
                var ha = tra.Block("Hardware Textures"); var hb = trb.Block("Hardware Textures"); var bas = tra.Block("Bitmaps"); var bbs = trb.Block("Bitmaps");
                for (int i = 0; i < Math.Min(ha.Count, hb.Count) && i < bas.Count && i < bbs.Count; i++)
                {
                    var da = new DatumIndex(ha[i].Datum("[zone] Asset Datum")); var dbi = new DatumIndex(hb[i].Datum("[zone] Asset Datum"));
                    if (!da.IsValid || !dbi.IsValid) continue;
                    var ra = ta.Resources[da.Index]; var rb = tb.Resources[dbi.Index]; var ia = ra.Info; var ib = rb.Info;
                    if (ia == null || ib == null || ia.Length < 0x30 || ib.Length < 0x30) continue;
                    int fmt = (int)bas[i].Num("Format"), fmtB = (int)bbs[i].Num("Format");
                    int w = BitConverter.ToUInt16(ia, 0x28), h = BitConverter.ToUInt16(ia, 0x2A), levels = ia[0x2D], type = ia[0x2E], split = ia[0x2F];
                    int wb = ib[0x28] << 8 | ib[0x29], hb2 = ib[0x2A] << 8 | ib[0x2B];
                    string key = "fmt " + fmt + (fmt != fmtB ? "->" + fmtB : "") + " type " + type;
                    if (!stats.TryGetValue(key, out var st)) stats[key] = st = new int[4];   // identical, different, not comparable, no converter
                    if (w != wb || h != hb2 || levels != ib[0x2D] || (split != ib[0x2F] && type != 2) || fmt != fmtB || type != ib[0x2E] || (type != 0 && type != 2)) { st[2]++; if (type == 2) Console.WriteLine("CUBE-NC " + kv.Key + " mcc " + w + "x" + h + " L" + levels + " split " + split + " fmt " + fmt + " / 360 " + wb + "x" + hb2 + " L" + ib[0x2D] + " split " + ib[0x2F] + " fmt " + fmtB); continue; }
                    if (!BitmapConverter.Supported(fmt)) { st[3]++; continue; }
                    int pa = (int)BitConverter.ToUInt32(ia, 0), sa = (int)BitConverter.ToUInt32(ia, 0x14);
                    int pb = ib[0] << 24 | ib[1] << 16 | ib[2] << 8 | ib[3], sb = ib[0x14] << 24 | ib[0x15] << 16 | ib[0x16] << 8 | ib[0x17];
                    byte[] prim = seg(a, args[1], ra, true, pa), sec = seg(a, args[1], ra, false, sa), gp = seg(b, args[2], rb, true, pb), gs = seg(b, args[2], rb, false, sb);
                    if ((pa > 0 && prim == null) || (sa > 0 && sec == null) || (pb > 0 && gp == null) || (sb > 0 && gs == null)) { st[2]++; continue; }
                    byte[] p360, s360, pFF = null, sFF = null;
                    bool tiled = (ib[0x32] & 1) != 0;   // bit 8 of the stock fetch word
                    if (!tiled) key += " untiled";
                    if (!stats.TryGetValue(key, out st)) stats[key] = st = new int[4];
                    try { (p360, s360) = BitmapConverter.Tile360(prim, sec, split != 0 && sec != null, w, h, levels, fmt, tiled, type); Xenos.Fill = 0xFF; (pFF, sFF) = BitmapConverter.Tile360(prim, sec, split != 0 && sec != null, w, h, levels, fmt, tiled, type); Xenos.Fill = 0; }
                    catch (Exception ex)
                    {
                        st[1]++;
                        if (!shown.ContainsKey(key + "x")) { shown[key + "x"] = 1; Console.WriteLine("EXC " + key + " " + kv.Key + " " + w + "x" + h + " L" + levels + ": " + ex.Message); }
                        continue;
                    }
                    // texels only: stock data carries 0xCD filler in padding where ours is zero
                    Func<byte[], byte[], byte[], int> diff = (mine, alt, gold) =>
                    {
                        if (mine == null && gold == null) return 0; if (mine == null || gold == null) return -1;
                        int n = 0; for (int k = 0; k < Math.Min(mine.Length, gold.Length); k++) if (mine[k] != gold[k] && mine[k] == alt[k]) n++;   // a byte that follows the fill value is padding
                        return n + Math.Abs(mine.Length - gold.Length);
                    };
                    if (fmt == 33 && type == 0)
                    {
                        // The MCC copy was re-compressed, so compare the decoded values block by block instead of bytes.
                        Func<byte[], int, int[]> dec = (buf, at0) =>
                        {
                            var v = new int[32];
                            for (int ch = 0; ch < 2; ch++)
                            {
                                int a = at0 + ch * 8; var blk = new byte[8];
                                for (int k = 0; k < 8; k += 2) { blk[k] = buf[a + k + 1]; blk[k + 1] = buf[a + k]; }   // undo 8-in-16
                                int e0 = blk[0], e1 = blk[1]; var pal = new int[8]; pal[0] = e0; pal[1] = e1;
                                if (e0 > e1) for (int q = 1; q < 7; q++) pal[q + 1] = ((7 - q) * e0 + q * e1) / 7;
                                else { for (int q = 1; q < 5; q++) pal[q + 1] = ((5 - q) * e0 + q * e1) / 5; pal[6] = 0; pal[7] = 255; }
                                ulong bits = 0; for (int q = 0; q < 6; q++) bits |= (ulong)blk[2 + q] << (8 * q);
                                for (int q = 0; q < 16; q++) v[ch * 16 + q] = pal[(int)((bits >> (3 * q)) & 7)];
                            }
                            return v;
                        };
                        int worst = 0;
                        foreach (var (mine, gold, ww, hh, lv) in new[] { (p360, gp, split != 0 ? Math.Max(1, w >> 1) : w, split != 0 ? Math.Max(1, h >> 1) : h, split != 0 ? levels - 1 : levels), (s360, gs, w, h, 1) })
                        {
                            if (mine == null || gold == null || lv < 1) continue;
                            foreach (var off in Xenos.BlockOffsets(ww, hh, lv, 4, 16, true, out _))
                            {
                                if (off + 16 > mine.Length || off + 16 > gold.Length) { worst = 999; break; }
                                var x1 = dec(mine, (int)off); var x2 = dec(gold, (int)off);
                                for (int q = 0; q < 32; q++) worst = Math.Max(worst, Math.Abs(x1[q] - x2[q]));
                            }
                        }
                        string k2 = "fmt 33 decoded, worst value difference " + (worst == 0 ? "0" : worst <= 8 ? "1-8" : worst <= 32 ? "9-32" : "over 32");
                        if (!stats.TryGetValue(k2, out var s2)) stats[k2] = s2 = new int[4];
                        s2[0]++;
                        if (worst > 32 && (!shown.TryGetValue(k2, out var sh2) || sh2 < 3)) { shown[k2] = sh2 + 1; Console.WriteLine("DXN " + kv.Key + " worst " + worst); }
                        continue;
                    }
                    int d1 = diff(p360, pFF, gp), d2 = diff(s360, sFF, gs);
                    bool ok = d1 == 0 && d2 == 0; st[ok ? 0 : 1]++;
                    if (!ok && args.Contains("--dump")) { string dn = System.IO.Path.Combine(args[Array.IndexOf(args, "--dump") + 1], System.IO.Path.GetFileName(kv.Key)); if (p360 != null) System.IO.File.WriteAllBytes(dn + ".mine.p", p360); if (gp != null) System.IO.File.WriteAllBytes(dn + ".360.p", gp); if (prim != null) System.IO.File.WriteAllBytes(dn + ".mcc.p", prim); }
                    if (!ok && (!shown.TryGetValue(key, out var sh) || sh < 3))
                    {
                        shown[key] = sh + 1;
                        Console.WriteLine("MISMATCH " + key + " " + kv.Key + "[" + i + "] " + w + "x" + h + " L" + levels + " split " + split + ": primary diff " + d1 + " (mine " + p360?.Length + " / 360 " + gp?.Length + "), secondary diff " + d2 + " (mine " + s360?.Length + " / 360 " + gs?.Length + ")");
                    }
                }
            }
            foreach (var kv in stats) Console.WriteLine(kv.Key + ": identical " + kv.Value[0] + ", different " + kv.Value[1] + ", not comparable " + kv.Value[2] + ", no converter " + kv.Value[3]);
        }
        return 0;
    }
}
