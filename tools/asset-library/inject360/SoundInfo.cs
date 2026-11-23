// sndinfo <map> <name substring> [limit]: how the map describes matching sound tags - the tag's own fields, its rows in the
// shared sound tables (codec, pitch ranges, permutations, chunks) and its resource. Works on 360 and MCC maps.
using System;
using System.Linq;
using System.Xml;
using Blamite.Blam;
using Blamite.Injection;
using Blamite.Plugins;
using Blamite.Serialization;
using Blamite.Util;
using Inject360;

partial class Program
{
    static int SoundInfo(EngineDatabase db, string[] args)
    {
        using (var c = new Cache(db, args[1]))
        {
            int limit = args.Length > 3 ? int.Parse(args[3]) : 5, shown = 0;
            var st = c.File.SoundGestalt.LoadSoundResourceTable(c.Reader);
            var rt = c.File.Resources.LoadResourceTable(c.Reader);
            Console.WriteLine($"codecs {st.Codecs.Count} | pitch ranges {st.PitchRanges.Count} | playbacks {st.Playbacks.Count} | scales {st.Scales.Count} | promotions {st.Promotions.Count} | custom playbacks {st.CustomPlaybacks.Count} | extra infos {st.ExtraInfos.Count}");
            for (int i = 0; i < st.Codecs.Count; i++) Console.WriteLine($"  codec {i}: rate {st.Codecs[i].SampleRate} encoding {st.Codecs[i].Encoding} compression {st.Codecs[i].Compression}");
            int snd = CharConstant.FromString("snd!");
            foreach (var kv in c.ByName.Where(k => k.Value.Group.Magic == snd && k.Key.IndexOf(args[2], StringComparison.OrdinalIgnoreCase) >= 0))
            {
                if (shown++ >= limit) break;
                var b = new DataBlockBuilder(c.Reader, kv.Value, c.File, c.Engine);
                using (var xr = XmlReader.Create(c.Plugin(snd))) AssemblyPluginLoader.LoadPlugin(xr, b);
                var root = b.DataBlocks[0];
                Console.WriteLine(kv.Key + " | tag bytes " + BitConverter.ToString(root.Data).Replace("-", ""));
                foreach (var f in root.SoundFixups)
                {
                    Console.WriteLine($"  codec {f.OriginalCodecIndex} | pitch ranges {f.OriginalPitchRangeIndex}+{f.PitchRangeCount} | language {f.OriginalLanguageDurationIndex} | playback {f.OriginalPlaybackIndex} | scale {f.OriginalScaleIndex} | promotion {f.OriginalPromotionIndex} | custom {f.OriginalCustomPlaybackIndex} | extra {f.OriginalExtraInfoIndex}");
                    for (int p = 0; p < f.PitchRangeCount && f.OriginalPitchRangeIndex >= 0; p++)
                    {
                        var pr = st.PitchRanges[f.OriginalPitchRangeIndex + p];
                        Console.WriteLine($"  pitch range '{c.File.StringIDs.GetString(pr.Name)}' encoded-data {pr.HasEncodedData} required {pr.RequiredPermutationCount} natural pitch {pr.Parameter?.NaturalPitch} bend {pr.Parameter?.BendMin}..{pr.Parameter?.BendMax} permutations {pr.Permutations.Length}");
                        foreach (var pm in pr.Permutations)
                        {
                            Console.WriteLine($"    permutation '{c.File.StringIDs.GetString(pm.Name)}' samples {pm.SampleSize} skip {pm.EncodedSkipFraction} gain {pm.EncodedGain} info {pm.EncodedPermutationInfoIndex} fsb 0x{pm.FSBInfo:X8} languages {pm.Languages?.Length ?? 0} markers {pm.LayerMarkers?.Length ?? 0}");
                            foreach (var ch in pm.Chunks)
                                Console.WriteLine($"      chunk offset {ch.FileOffset} sizeflags 0x{ch.EncodedSizeAndFlags:X8} cache {ch.CacheIndex} xma {ch.XMA2BufferStart}..{ch.XMA2BufferEnd} unk {ch.Unknown},{ch.Unknown1} bank '{c.File.StringIDs.GetString(ch.FModBankSuffix)}'");
                        }
                    }
                    if (f.OriginalExtraInfoIndex >= 0 && f.OriginalExtraInfoIndex < st.ExtraInfos.Count)
                    {
                        var ex = st.ExtraInfos[f.OriginalExtraInfoIndex];
                        Console.WriteLine($"  extra info: sections {ex.PermutationSections?.Length ?? 0} [{string.Join(",", (ex.PermutationSections ?? new Blamite.Blam.Resources.Sounds.SoundExtraInfoPermutationSection[0]).Select(s => (s.EncodedData?.Length ?? 0) + "b/" + (s.DialogueInfos?.Length ?? 0) + "d"))}] datums {string.Join(",", (ex.Datums ?? new DatumIndex[0]).Select(d => d.ToString()))}");
                    }
                }
                foreach (var di in b.ReferencedResources)
                {
                    var r = rt.Resources[di.Index];
                    Console.WriteLine($"  resource {di} type {r.Type} flags 0x{r.Flags:X} info {(r.Info == null ? 0 : r.Info.Length)}b [{(r.Info == null ? "" : BitConverter.ToString(r.Info).Replace("-", ""))}] baseDef 0x{r.BaseDefinitionAddress:X} fixups {string.Join(",", r.ResourceFixups.Select(x => $"@0x{x.Offset:X}->0x{x.Address:X}"))} defFixups {r.DefinitionFixups.Count}");
                    var loc = r.Location;
                    if (loc?.PrimaryPage != null) Console.WriteLine($"    primary page {loc.PrimaryPage.Index} file '{loc.PrimaryPage.FilePath}' offset {loc.PrimaryOffset} usize {loc.PrimaryPage.UncompressedSize} csize {loc.PrimaryPage.CompressedSize} comp {loc.PrimaryPage.CompressionMethod}");
                    if (loc?.SecondaryPage != null) Console.WriteLine($"    secondary page {loc.SecondaryPage.Index} file '{loc.SecondaryPage.FilePath}' offset {loc.SecondaryOffset} usize {loc.SecondaryPage.UncompressedSize}");
                }
            }
        }
        return 0;
    }
}
