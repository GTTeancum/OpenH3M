// Sound conversion, H3 MCC -> original Xbox 360.
// MCC keeps a sound's samples in FMOD banks (sfx[.suffix].fsb beside the map, indexed by a hash stored on each
// permutation); the 360 keeps them in a sound resource addressed by chunk rows in the shared sound tables (ugh!).
// Two sources for the samples:
//   native  - the same sound from an Xbox 360 map (Halo 3 or Reach): its XMA chunks are copied byte for byte, so the
//             2007 engine plays exactly what a 360 game shipped. Used whenever a donor map has the sound.
//   decoded - each permutation decoded from the MCC bank with vgmstream, resampled to 44.1 kHz and encoded to XMA2 with
//             the Xbox 360 SDK encoder (xma2encode.exe), i.e. the same format stock sounds are in. Without the encoder it
//             falls back to big-endian 16-bit PCM (codec "none"), which was SILENT in the user's tests (2026-11-20).
// The table rows (codec, pitch ranges, permutations, chunks, playback, scale, promotion, extra info) are added
// through Blamite's own sound injection. A 360 sound resource has no control bytes: the engine learns how much
// data it has from the resource's size record, so that record must be written (stock: size n, one part 0+n).
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Blamite.Blam;
using Blamite.Blam.Resources;
using Blamite.Blam.Resources.Sounds;
using Blamite.Injection;

namespace Inject360
{
    // One sound as a 360 donor map holds it.
    public class NativeSound
    {
        public DataBlockSoundFixup Fixup; public SoundResourceTable Table; public Func<StringID, string> Str; public byte[] Data; public string Source;
    }

    public class SoundConverter
    {
        readonly SoundResourceTable _table; readonly Func<StringID, string> _str; readonly string[] _bankDirs; readonly string _decoder, _work;
        readonly TagContainer _container; readonly ResourceSink _sink;
        readonly Dictionary<string, Dictionary<uint, int>> _index = new Dictionary<string, Dictionary<uint, int>>(StringComparer.OrdinalIgnoreCase);
        readonly HashSet<int> _codecs = new HashSet<int>(), _playbacks = new HashSet<int>(), _scales = new HashSet<int>(), _promotions = new HashSet<int>(), _extras = new HashSet<int>();
        static readonly int[] Rates = { 22050, 44100, 32000, 48000 }, Channels = { 1, 2, 4, 6 };
        public long Bytes; public int Native, Decoded;

        public SoundConverter(SoundResourceTable table, Func<StringID, string> str, string[] bankDirs, string decoder, string work, TagContainer container, ResourceSink sink)
        {
            _table = table; _str = str; _bankDirs = bankDirs; _decoder = decoder; _work = work; _container = container; _sink = sink;
        }

        string Bank(string suffix)
        {
            string file = string.IsNullOrEmpty(suffix) ? "sfx.fsb" : "sfx." + suffix + ".fsb";
            foreach (var d in _bankDirs) { var p = Path.Combine(d, file); if (File.Exists(p) && File.Exists(p + ".info")) return p; }
            throw new Exception("sound bank " + file + " not found in " + string.Join(" ; ", _bankDirs));
        }

        // .info: 280-byte rows, the first word is the permutation hash; the row number is the bank's stream number.
        Dictionary<uint, int> Index(string bank)
        {
            if (_index.TryGetValue(bank, out var ix)) return ix;
            ix = new Dictionary<uint, int>(); var b = File.ReadAllBytes(bank + ".info");
            for (int i = 0; i + 280 <= b.Length; i += 280) { uint k = BitConverter.ToUInt32(b, i); if (!ix.ContainsKey(k)) ix[k] = i / 280; }
            return _index[bank] = ix;
        }

        // -> 16-bit little-endian interleaved PCM as decoded
        (byte[] pcm, int rate, int channels, int frames) Decode(string bank, uint hash)
        {
            if (!File.Exists(_decoder)) throw new Exception("sound decoder not found: " + _decoder);
            Directory.CreateDirectory(_work);
            if (!Index(bank).TryGetValue(hash, out int row)) throw new Exception($"sound 0x{hash:X8} is not in {Path.GetFileName(bank)}");
            string wav = Path.Combine(_work, $"{hash:X8}.wav");
            var psi = new ProcessStartInfo(_decoder, $"-i -s {row + 1} -o \"{wav}\" \"{bank}\"") { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true, WorkingDirectory = _work };
            using (var p = Process.Start(psi))
            {
                string o = p.StandardOutput.ReadToEnd() + p.StandardError.ReadToEnd(); p.WaitForExit();
                if (p.ExitCode != 0 || !File.Exists(wav)) throw new Exception("decoder failed for 0x" + hash.ToString("X8") + ": " + o.Trim());
            }
            var w = File.ReadAllBytes(wav); File.Delete(wav);
            if (w.Length < 44 || w[0] != 'R' || w[8] != 'W') throw new Exception("decoder output is not a WAV file");
            int at = 12, rate = 0, ch = 0, bits = 0; byte[] data = null;
            while (at + 8 <= w.Length)
            {
                string id = System.Text.Encoding.ASCII.GetString(w, at, 4); int n = BitConverter.ToInt32(w, at + 4);
                if (id == "fmt ") { ch = BitConverter.ToUInt16(w, at + 10); rate = BitConverter.ToInt32(w, at + 12); bits = BitConverter.ToUInt16(w, at + 22); }
                else if (id == "data") { n = Math.Min(n, w.Length - at - 8); data = new byte[n]; Buffer.BlockCopy(w, at + 8, data, 0, n); }
                at += 8 + n + (n & 1);
            }
            if (data == null || bits != 16) throw new Exception($"unexpected decoded audio ({bits} bits)");
            return (data, rate, ch, data.Length / (2 * ch));
        }

        public string XmaEncoder = @"C:\X360\Tools\xma2encode.exe", Ffmpeg = "ffmpeg";

        string Run(string exe, string args)
        {
            var psi = new ProcessStartInfo(exe, args) { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true, WorkingDirectory = _work };
            using (var p = Process.Start(psi))
            {
                string o = p.StandardOutput.ReadToEnd() + p.StandardError.ReadToEnd(); p.WaitForExit();
                if (p.ExitCode != 0) throw new Exception(Path.GetFileName(exe) + " failed: " + o.Trim());
                return o;
            }
        }

        // 16-bit PCM -> XMA2 with the Xbox 360 SDK encoder, at 44.1 kHz (the only rate stock Halo 3 sounds use) and
        // 16 KiB blocks (as stock and Reach chunks have). Returns the packet data and the header's sample counts.
        // Checked against a Reach 360 chunk of the same sound: same packet layout, same block boundaries, same sample count.
        (byte[] data, int samplesEncoded, int playLength) EncodeXma(byte[] pcm, int rate, int channels, string tag)
        {
            Directory.CreateDirectory(_work);
            string wav = Path.Combine(_work, tag + ".wav"), wav44 = Path.Combine(_work, tag + ".44.wav"), xma = Path.Combine(_work, tag + ".xma");
            using (var w = new BinaryWriter(File.Create(wav)))
            {
                w.Write(System.Text.Encoding.ASCII.GetBytes("RIFF")); w.Write(36 + pcm.Length); w.Write(System.Text.Encoding.ASCII.GetBytes("WAVEfmt "));
                w.Write(16); w.Write((short)1); w.Write((short)channels); w.Write(rate); w.Write(rate * channels * 2); w.Write((short)(channels * 2)); w.Write((short)16);
                w.Write(System.Text.Encoding.ASCII.GetBytes("data")); w.Write(pcm.Length); w.Write(pcm);
            }
            string input = wav;
            if (rate != 44100) { Run(Ffmpeg, $"-hide_banner -loglevel error -y -i \"{wav}\" -ar 44100 -c:a pcm_s16le \"{wav44}\""); input = wav44; }
            Run(XmaEncoder, $"\"{input}\" /TargetFile \"{xma}\" /BlockSize 16");
            var d = File.ReadAllBytes(xma); File.Delete(wav); if (File.Exists(wav44)) File.Delete(wav44); File.Delete(xma);
            byte[] data = null; int enc = 0, play = 0;
            for (int at = 12; at + 8 <= d.Length;)
            {
                string id = System.Text.Encoding.ASCII.GetString(d, at, 4); int n = BitConverter.ToInt32(d, at + 4);
                if (id == "fmt ") { enc = BitConverter.ToInt32(d, at + 8 + 24); play = BitConverter.ToInt32(d, at + 8 + 36); }
                else if (id == "data") { data = new byte[n]; Buffer.BlockCopy(d, at + 8, data, 0, n); }
                at += 8 + n + (n & 1);
            }
            if (data == null || data.Length % 2048 != 0 || play <= 0) throw new Exception("unexpected XMA encoder output");
            return (data, enc, play);
        }

        static List<ExtractedSoundPermutation> NativePermutations(NativeSound n, SoundPitchRange pr)
        {
            var list = new List<ExtractedSoundPermutation>();
            foreach (var pm in pr.Permutations)
            {
                if (pm.Languages != null && pm.Languages.Length > 0) throw new Exception("localized permutation in the donor");
                list.Add(new ExtractedSoundPermutation
                {
                    Name = n.Str(pm.Name), EncodedSkipFraction = pm.EncodedSkipFraction, SampleSize = pm.SampleSize, EncodedGain = pm.EncodedGain,
                    EncodedPermutationInfoIndex = pm.EncodedPermutationInfoIndex, FSBInfo = 0,
                    Chunks = pm.Chunks.Select(c => new ExtractedSoundChunk(new SoundChunk
                    {
                        FileOffset = c.FileOffset, EncodedSizeAndFlags = c.EncodedSizeAndFlags, CacheIndex = c.CacheIndex,
                        XMA2BufferStart = c.XMA2BufferStart, XMA2BufferEnd = c.XMA2BufferEnd, Unknown = c.Unknown, Unknown1 = c.Unknown1, FModBankSuffix = StringID.Null,
                    }, "")).ToList(),
                    LayerMarkers = pm.LayerMarkers != null ? pm.LayerMarkers.ToList() : null,
                });
            }
            return list;
        }

        // The MCC sound tag's rows -> container entries; returns the new 360 resource and the fixup the 360 tag carries.
        // native != null: samples, permutations and codec come from that 360 sound; playback, scale and pitch parameters stay the MCC tag's.
        public (ExtractedResourceInfo resource, DataBlockSoundFixup fixup, string note) Convert(DataBlockSoundFixup f, string bankSuffix, Resource src, DatumIndex parentTag, NativeSound native = null)
        {
            if (f.OriginalPitchRangeIndex < 0 || f.PitchRangeCount <= 0) throw new Exception("sound has no pitch ranges");
            if (f.OriginalLanguageDurationIndex != -1) throw new Exception("localized (dialogue) sounds are not converted yet");
            if (f.OriginalCustomPlaybackIndex != -1) throw new Exception("sounds with a custom playback are not converted yet");
            byte[] data; int codecKey, perms = 0; string how;
            if (native != null)
            {
                var nf = native.Fixup;
                if (nf.PitchRangeCount != f.PitchRangeCount) throw new Exception($"donor has {nf.PitchRangeCount} pitch range(s), the MCC tag {f.PitchRangeCount}");
                var nc = native.Table.Codecs[nf.OriginalCodecIndex];
                for (int p = 0; p < f.PitchRangeCount; p++)
                {
                    int index = f.OriginalPitchRangeIndex + p; var mpr = _table.PitchRanges[index]; var npr = native.Table.PitchRanges[nf.OriginalPitchRangeIndex + p];
                    var list = NativePermutations(native, npr); perms += list.Count;
                    foreach (var pm in list) foreach (var c in pm.Chunks)
                        if (c.Source.FileOffset < 0 || c.Source.FileOffset + c.Source.DecodedSize > native.Data.Length) throw new Exception("donor chunk outside its data");
                    _container.AddSoundPitchRange(new ExtractedSoundPitchRange(index, _str(mpr.Name), mpr.Parameter, npr.HasEncodedData, npr.RequiredPermutationCount, list));
                }
                codecKey = 2000 + nc.SampleRate * 64 + nc.Encoding * 8 + nc.Compression;
                if (_codecs.Add(codecKey)) _container.AddSoundCodec(new ExtractedSoundCodec(codecKey, new SoundCodec { SampleRate = nc.SampleRate, Encoding = nc.Encoding, Compression = nc.Compression }));
                data = native.Data; Native++;
                how = $"{perms} permutation(s), {data.Length} bytes copied unchanged from {native.Source} (codec rate {nc.SampleRate} encoding {nc.Encoding} compression {nc.Compression})";
            }
            else
            {
                var mccCodec = _table.Codecs[f.OriginalCodecIndex];
                string bank = Bank(bankSuffix);
                var raw = new List<byte>(); int rate = 0, channels = 0; bool xmaOk = File.Exists(XmaEncoder);
                for (int p = 0; p < f.PitchRangeCount; p++)
                {
                    int index = f.OriginalPitchRangeIndex + p; var pr = _table.PitchRanges[index];
                    var list = new List<ExtractedSoundPermutation>();
                    foreach (var pm in pr.Permutations)
                    {
                        if (pm.Languages != null && pm.Languages.Length > 0) throw new Exception("localized permutation");
                        var (pcm, r, ch, frames) = Decode(bank, (uint)pm.FSBInfo);
                        if (rate == 0) { rate = r; channels = ch; }
                        else if (r != rate || ch != channels) throw new Exception("permutations of one sound differ in rate or channel count");
                        int offset = raw.Count; SoundChunk chunk;
                        if (xmaOk)
                        {
                            // XMA: as stock chunks record it - flags 0xE8, play window = encoder lead-in .. samples encoded
                            var (xd, enc, play) = EncodeXma(pcm, r, ch, ((uint)pm.FSBInfo).ToString("X8"));
                            if (xd.Length > 0xFFFFFF) throw new Exception("permutation larger than one chunk can describe");
                            raw.AddRange(xd); frames = play;
                            chunk = new SoundChunk { FileOffset = offset, EncodedSizeAndFlags = unchecked((int)0xE8000000) | xd.Length, CacheIndex = -1, XMA2BufferStart = enc - play, XMA2BufferEnd = enc, FModBankSuffix = StringID.Null };
                        }
                        else
                        {
                            while (raw.Count % 16 != 0) raw.Add(0);
                            offset = raw.Count;
                            for (int i = 0; i + 1 < pcm.Length; i += 2) { raw.Add(pcm[i + 1]); raw.Add(pcm[i]); }   // big-endian samples
                            if (pcm.Length > 0xFFFFFF) throw new Exception("permutation larger than one chunk can describe");
                            chunk = new SoundChunk { FileOffset = offset, EncodedSizeAndFlags = 0x70000000 | pcm.Length, CacheIndex = -1, XMA2BufferStart = 0, XMA2BufferEnd = frames, FModBankSuffix = StringID.Null };
                        }
                        list.Add(new ExtractedSoundPermutation
                        {
                            Name = _str(pm.Name), EncodedSkipFraction = pm.EncodedSkipFraction, SampleSize = frames, EncodedGain = pm.EncodedGain,
                            EncodedPermutationInfoIndex = pm.EncodedPermutationInfoIndex, FSBInfo = 0,
                            Chunks = new List<ExtractedSoundChunk> { new ExtractedSoundChunk(chunk, "") },
                            LayerMarkers = pm.LayerMarkers != null ? pm.LayerMarkers.ToList() : null,
                        });
                        perms++;
                    }
                    _container.AddSoundPitchRange(new ExtractedSoundPitchRange(index, _str(pr.Name), pr.Parameter, pr.HasEncodedData, pr.RequiredPermutationCount, list));   // the flag marks a single fixed permutation; carried as the source has it
                }
                if (xmaOk) rate = 44100;
                int ri = Array.IndexOf(Rates, rate), ci = Array.IndexOf(Channels, channels);
                if (ri < 0 || ci < 0) throw new Exception($"decoded audio is {rate} Hz, {channels} channels: no 360 codec row for that");
                if (ci != mccCodec.Encoding) throw new Exception($"decoded audio has {channels} channels, the tag's codec row says encoding {mccCodec.Encoding}");
                codecKey = (xmaOk ? 3000 : 1000) + f.OriginalCodecIndex * 8 + ri;
                if (_codecs.Add(codecKey)) _container.AddSoundCodec(new ExtractedSoundCodec(codecKey, new SoundCodec { SampleRate = ri, Encoding = ci, Compression = xmaOk ? 7 : 0 }));
                data = raw.ToArray(); Decoded++;
                how = $"{perms} permutation(s), {rate} Hz, {channels} ch, {data.Length} bytes {(xmaOk ? "XMA encoded" : "PCM")} from {Path.GetFileName(bank)}";
            }
            if (f.OriginalPlaybackIndex >= 0 && _playbacks.Add(f.OriginalPlaybackIndex)) _container.AddSoundPlayback(new ExtractedSoundPlayback(f.OriginalPlaybackIndex, _table.Playbacks[f.OriginalPlaybackIndex]));
            if (f.OriginalScaleIndex >= 0 && _scales.Add(f.OriginalScaleIndex)) _container.AddSoundScale(new ExtractedSoundScale(f.OriginalScaleIndex, _table.Scales[f.OriginalScaleIndex]));
            if (f.OriginalPromotionIndex >= 0 && _promotions.Add(f.OriginalPromotionIndex)) _container.AddSoundPromotion(new ExtractedSoundPromotion(f.OriginalPromotionIndex, _table.Promotions[f.OriginalPromotionIndex]));
            int extra = f.OriginalExtraInfoIndex;
            if (extra >= 0)
            {
                var ex = _table.ExtraInfos[extra];
                if ((ex.PermutationSections != null && ex.PermutationSections.Length > 0) || (ex.Datums != null && ex.Datums.Any(d => d != DatumIndex.Null)))
                    throw new Exception("sound with lipsync / encoded extra info is not converted yet");
                if (_extras.Add(extra)) _container.AddSoundExtraInfo(new ExtractedSoundExtraInfo(extra, ex));
            }

            Bytes += data.Length;
            var res = new ExtractedResourceInfo(src.Index)
            {
                Flags = src.Flags, Type = src.Type, Info = new byte[0], ResourceBits = 1, BaseDefinitionAddress = 0x20000000,
                OriginalParentTagIndex = parentTag, Location = new ExtractedResourcePointer(),
            };
            res.Location.OriginalPrimaryPageIndex = _sink.Page(data, false); res.Location.PrimaryOffset = 0;   // stock sound pages are stored uncompressed
            res.Location.PrimarySize = new ResourceSize { Size = data.Length, Parts = new List<ResourceSizePart> { new ResourceSizePart { Offset = 0, Size = data.Length } } };
            res.ResourceFixups.Add(new ResourceFixup { Offset = 0x0C, Address = 0x40000000 });   // as every stock 360 sound resource has it
            _sink.Add(res);
            var fix = new DataBlockSoundFixup(codecKey, f.PitchRangeCount, f.OriginalPitchRangeIndex, -1, f.OriginalPlaybackIndex, f.OriginalScaleIndex, f.OriginalPromotionIndex, -1, extra);
            return (res, fix, how);
        }
    }
}
