// locale <360 map> [regex]: English localized strings per string list (unic tag) whose key or text matches
using System;
using System.Linq;
using System.Text.RegularExpressions;
using Blamite.Blam;
using Blamite.Blam.Localization;

namespace Ho2H3
{
    static class LocaleProbe
    {
        public static int Run(string[] a)
        {
            using (var m = new Map(a[1]))
            {
                var re = new Regex(a.Length > 2 ? a[2] : ".", RegexOptions.IgnoreCase);
                var pack = m.File.Languages.LoadLanguage(GameLanguage.English, m.Reader);
                foreach (var list in pack.StringLists)
                {
                    var name = list.SourceTag != null ? m.File.FileNames.GetTagName(list.SourceTag) : "?";
                    var hits = list.Strings.Where(s => re.IsMatch(m.File.StringIDs.GetString(s.Key) ?? "") || re.IsMatch(s.Value ?? "")).ToList();
                    if (hits.Count == 0) continue;
                    Console.WriteLine($"== {name} ({list.Strings.Count} strings)");
                    foreach (var s in hits.Take(40)) Console.WriteLine($"  {m.File.StringIDs.GetString(s.Key)} = {s.Value}");
                }
            }
            return 0;
        }
    }
}
