// Apply reviewed stock object mappings with official ManagedBlam editor fields.
using System;
using System.IO;
using System.Xml;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;
public class GameplayPlacement
{
    public string SourceBlock,SourceType,SourceLabel,TargetBlock,TargetTag,TargetSha256;
    public int SourceIndex,UniqueId;
    public bool TranslateScriptedFlag;
}
public class GameplayPlan
{
    public string ScenarioSha256,SourceXmlSha256;
    public List<GameplayPlacement> Placements;
}
class PrepareH3Gameplay
{
    const string Scenario=@"levels\custom\battle_canyon_fresh\battle_canyon_fresh";
    static string Hash(string path)
    {
        using(var stream=File.OpenRead(path))using(var sha=SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
    }
    static void Main(string[] args)
    {
        if(args.Length<1 || args.Length>3)throw new ArgumentException("Expected repository root, optional --dry-run and optional --scene-objects");
        bool apply=true,sceneObjects=false;
        for(int i=1;i<args.Length;i++){if(args[i]=="--dry-run")apply=false;else if(args[i]=="--scene-objects")sceneObjects=true;else throw new ArgumentException("Unknown argument "+args[i]);}
        string root=Path.GetFullPath(args[0]),kit=Path.Combine(root,@"work\editing-kits\h3ek"),output=Path.Combine(root,@"work\stock-h3-audit");
        string scenarioPath=Path.Combine(kit,"tags",Scenario+".scenario"),sourcePath=Path.Combine(output,"original-lighting-scenario.xml");
        string backup=Path.Combine(output,sceneObjects?"scenario-before-scene-objects.scenario":"scenario-before-gameplay-setup.scenario");
        if(File.Exists(backup))throw new InvalidOperationException("Gameplay checkpoint exists; inspect before rerunning");
        var json=new JavaScriptSerializer();json.MaxJsonLength=16*1024*1024;
        var plan=json.Deserialize<GameplayPlan>(File.ReadAllText(Path.Combine(output,sceneObjects?"h3-scene-object-plan.json":"h3-gameplay-plan.json")));
        if(Hash(scenarioPath)!=plan.ScenarioSha256 || Hash(sourcePath)!=plan.SourceXmlSha256)throw new InvalidOperationException("Stale gameplay plan");
        var source=new XmlDocument();source.Load(sourcePath);
        var sourceRows=new Dictionary<string,XmlNode>();
        foreach(string category in new[]{"scenery","crates","equipment","weapons"})
            for(var node=source.SelectSingleNode("/tag/field[@name='"+category+"']").NextSibling;node!=null && node.Name=="element";node=node.NextSibling)
                sourceRows[category+":"+node.Attributes["index"].Value]=node;
        Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        using(var scenario=new TagFile(TagPath.FromPathAndExtension(Scenario,"scenario")))
        {
            var counts=new Dictionary<string,int>();
            foreach(var row in plan.Placements)
            {
                if(Hash(Path.Combine(kit,"tags",row.TargetTag))!=row.TargetSha256)throw new InvalidOperationException("Changed stock tag "+row.TargetTag);
                var sourceNode=sourceRows[row.SourceBlock+":"+row.SourceIndex];
                if(PrepareH3BasicPlacements.Value(sourceNode,"type")!=row.SourceType || PrepareH3BasicPlacements.Value(sourceNode,"megalo label")!=row.SourceLabel)throw new InvalidOperationException("Source identity differs");
                string extension=Path.GetExtension(row.TargetTag).Substring(1),path=Path.ChangeExtension(row.TargetTag,null);
                string paletteName=(row.TargetBlock=="weapons"?"weapon":row.TargetBlock=="crates"?"crate":row.TargetBlock)+" palette";
                var palette=(TagFieldBlock)scenario.SelectField(paletteName);int index=-1;
                foreach(var entry in palette.Elements)
                {
                    var reference=((TagFieldReference)entry.SelectField("name")).Path;
                    if(reference!=null && reference.RelativePathWithExtension==row.TargetTag)index=entry.ElementIndex;
                }
                if(index<0)
                {
                    var entry=palette.AddElement();((TagFieldReference)entry.SelectField("name")).Path=TagPath.FromPathAndExtension(path,extension);index=entry.ElementIndex;
                }
                var target=((TagFieldBlock)scenario.SelectField(row.TargetBlock)).AddElement();
                ((TagFieldBlockIndex)target.SelectField("type")).Value=index;
                PrepareH3BasicPlacements.Copy(target,sourceNode,"Struct:object data/",new[]{"placement flags","position","rotation","scale","transform flags","bsp policy"});
                PrepareH3BasicPlacements.Set(target.SelectField("Struct:object data/Struct:object id/type"),extension);
                PrepareH3BasicPlacements.Copy(target,sourceNode,"Struct:object data/Struct:object id/",new[]{"source"});
                ((TagFieldElementInteger)target.SelectField("Struct:object data/Struct:object id/unique id")).Data=row.UniqueId;
                ((TagFieldBlockIndex)target.SelectField("Struct:object data/Struct:object id/origin bsp index")).Value=PrepareH3BasicPlacements.Value(sourceNode,"origin bsp index")=="NONE"?-1:0;
                if(PrepareH3BasicPlacements.Value(sourceNode,"node orientations")!="0" || PrepareH3BasicPlacements.Value(sourceNode,"manual bsp flags")!="0")throw new InvalidOperationException("Unexpected source transform/BSP setup");
                foreach(XmlNode parent in sourceNode.SelectNodes("field[@name='parent object']"))if(parent.Attributes["value"].Value!="NONE")throw new InvalidOperationException("Parent requires explicit mapping");
                dynamic attach=target.SelectField("Struct:object data/can attach to bsp flags");
                if(PrepareH3BasicPlacements.Value(sourceNode,"can attach to bsp flags")!="1")throw new InvalidOperationException("Unexpected BSP attachment");
                foreach(dynamic item in attach.Items)item.IsSet=true;
                if(row.TargetBlock!="equipment")
                {
                    if(PrepareH3BasicPlacements.Value(sourceNode,"variant name")!="" || PrepareH3BasicPlacements.Value(sourceNode,"active change colors")!="")throw new InvalidOperationException("Source variant/color requires mapping");
                }
                if(row.TargetBlock=="weapons")PrepareH3BasicPlacements.Copy(target,sourceNode,"Struct:weapon data/",new[]{"rounds left","rounds loaded","flags"});
                if(row.SourceBlock=="scenery")PrepareH3BasicPlacements.Copy(target,sourceNode,"Struct:scenery data/",new[]{"Pathfinding policy","Lightmapping policy"});
                PrepareH3BasicPlacements.Copy(target,sourceNode,"Struct:multiplayer data/",new[]{"game engine symmetric placement","game engine flags","spawn order","quota minimum","quota maximum","spawn time","abandonment time","remapping policy","boundary shape","teleporter channel","boundary width or radius","boundary box length","boundary positive height","boundary negative height","natural respawn weight"});
                string team=PrepareH3BasicPlacements.Value(sourceNode,"owner team");
                PrepareH3BasicPlacements.Set(target.SelectField("Struct:multiplayer data/owner team"),team=="eighth party"?"eigth party":team);
                string flags=PrepareH3BasicPlacements.Value(sourceNode,"spawn flags");
                if(row.TranslateScriptedFlag)
                {
                    if(flags!="hide unless megalo required" || row.SourceLabel=="")throw new InvalidOperationException("Unexpected scripted flag");
                    // Dedicated stock H3 object tags provide native mode inclusion.
                    flags="";
                }
                PrepareH3BasicPlacements.Set(target.SelectField("Struct:multiplayer data/spawn flags"),flags);
                if(!counts.ContainsKey(row.TargetBlock))counts[row.TargetBlock]=0;counts[row.TargetBlock]++;
            }
            foreach(var count in counts)Console.WriteLine("H3_GAMEPLAY_ADDED "+count.Key+" "+count.Value);
            if(apply){File.Copy(scenarioPath,backup);scenario.Save();}
            Console.WriteLine(apply?"SAVED":"DRY_RUN_COMPLETE");
        }
    }
}
