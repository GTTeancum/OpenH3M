// addlocale <360 map> <unic tag name> <json file {"string id": "text"}>: add (or replace) localized strings in one string
// list, every language with the same text (Forge display names of converted pieces). The string ids must already be in
// the map's string table (the converter adds them). Run before the build's final step (ReachPort activate), which
// re-finalizes the map's integrity data.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Blamite.Blam;
using Blamite.Blam.Localization;
using Blamite.IO;

namespace Ho2H3
{
    static class AddLocale
    {
        public static int Run(string[] a)
        {
            var add = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(a[3]));
            using (var m = new Map(a[1], true))
            {
                var stream = new EndianStream(m.Stream, m.Engine.Endian);
                int added = 0, missing = 0, langs = 0;
                foreach (var lang in m.File.Languages.AvailableLanguages.ToList())
                {
                    var pack = m.File.Languages.LoadLanguage(lang, stream);
                    var list = pack.StringLists.FirstOrDefault(l => l.SourceTag != null && string.Equals(m.File.FileNames.GetTagName(l.SourceTag), a[2], StringComparison.OrdinalIgnoreCase));
                    if (list == null) continue;
                    langs++;
                    foreach (var kv in add)
                    {
                        var id = m.File.StringIDs.FindStringID(kv.Key);
                        if (id == StringID.Null) { if (lang == GameLanguage.English) missing++; continue; }
                        var have = list.Strings.FirstOrDefault(s => s.Key == id);
                        if (have != null) have.Value = kv.Value; else { list.Strings.Add(new LocalizedString(id, kv.Value)); if (lang == GameLanguage.English) added++; }
                    }
                    m.File.Languages.SaveLanguage(pack, stream);
                }
                m.File.SaveChanges(stream);
                Console.WriteLine($"addlocale: {added} strings added to {a[2]} in {langs} languages, {missing} string ids not in the map");
            }
            return 0;
        }
    }
}
