// Retain stock mode tags, all FFA starts and four starts per team for first 360 review.
using System;
using System.IO;
using System.Collections.Generic;
using Bungie;
using Bungie.Tags;
class Trim360InitialStarts {
 static void Main(string[] args) {
  string root=Path.GetFullPath(args[0]),kit=Path.Combine(root,@"work\editing-kits\h3ek");
  string path=@"levels\custom\battle_canyon_fresh\battle_canyon_fresh";
  string original=Path.Combine(kit,"tags",path+".scenario"), backup=Path.Combine(root,@"work\stock-h3-audit\scenario-before-360-start-budget.scenario");
  if(File.Exists(backup))throw new Exception("Checkpoint exists");
  Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
  using(var tag=new TagFile(TagPath.FromPathAndExtension(path,"scenario"))) {
   var block=(TagFieldBlock)tag.SelectField("scenery");
   var palette=(TagFieldBlock)tag.SelectField("scenery palette");
   var counts=new Dictionary<string,int>();var remove=new List<int>();
   foreach(var e in block.Elements) {
    int p=((TagFieldBlockIndex)e.SelectField("type")).Value;
    if(p<0)continue;
    string name=((TagFieldReference)palette.Elements[p].SelectField("name")).Path.RelativePath;
    if(!name.EndsWith("_initial_spawn_point") || name.Contains("infection"))continue;
    var team=(TagFieldEnum)e.SelectField("Struct:multiplayer data/owner team");
    string key=name+":"+team.Value;
    if(!counts.ContainsKey(key))counts[key]=0;
    counts[key]++;
    // Native team index 8 is neutral; preserve all sixteen FFA starts.
    if(team.Value!=8 && counts[key]>4)remove.Add(e.ElementIndex);
   }
   if(remove.Count!=140)throw new Exception("Unexpected reduction "+remove.Count);
   remove.Reverse();foreach(int i in remove)block.RemoveElement(i);
   File.Copy(original,backup);tag.Save();Console.WriteLine("360_INITIAL_STARTS_REMOVED "+remove.Count+" scenery "+block.Elements.Count);
  }
 }
}
