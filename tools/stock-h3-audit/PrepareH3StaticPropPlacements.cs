// Original placements and native H3 Territories filtering, through ManagedBlam.
using System;
using System.IO;
using System.Xml;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;
public class StaticPropPlacement
{
    public string SourceType,TargetTag,TargetSha256,Mode,Role;
    public int SourceIndex,UniqueId;
}
public class StaticPropPlan
{
    public string ScenarioSha256,SourceXmlSha256;
    public List<StaticPropPlacement> Placements;
}
class PrepareH3StaticPropPlacements
{
    static string Hash(string path)
    {
        using(var stream=File.OpenRead(path))using(var sha=SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
    }
    static string Value(XmlNode e,string name){return PrepareH3BasicPlacements.Value(e,name);}
    static void Main(string[] args)
    {
        if(args.Length!=1 && !(args.Length==2 && args[1]=="--dry-run"))throw new ArgumentException("Expected root and optional --dry-run");
        bool apply=args.Length==1;
        string root=Path.GetFullPath(args[0]),kit=Path.Combine(root,@"work\editing-kits\h3ek"),output=Path.Combine(root,@"work\stock-h3-audit");
        string relative=@"levels\custom\battle_canyon_fresh\battle_canyon_fresh";
        string path=Path.Combine(kit,"tags",relative+".scenario"),sourcePath=Path.Combine(output,"original-lighting-scenario.xml"),backup=Path.Combine(output,"scenario-before-static-props.scenario");
        if(File.Exists(backup))throw new InvalidOperationException("Existing checkpoint: inspect before rerunning");
        var plan=new JavaScriptSerializer().Deserialize<StaticPropPlan>(File.ReadAllText(Path.Combine(output,"h3-static-prop-placement-plan.json")));
        if(Hash(path)!=plan.ScenarioSha256 || Hash(sourcePath)!=plan.SourceXmlSha256)throw new InvalidOperationException("Stale plan");
        var xml=new XmlDocument();xml.Load(sourcePath);
        var sources=new Dictionary<int,XmlNode>();
        for(var e=xml.SelectSingleNode("/tag/field[@name='crates']").NextSibling;e!=null && e.Name=="element";e=e.NextSibling)sources[int.Parse(e.Attributes["index"].Value)]=e;
        Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        using(var tag=new TagFile(TagPath.FromPathAndExtension(relative,"scenario")))
        {
            var block=(TagFieldBlock)tag.SelectField("crates");var palette=(TagFieldBlock)tag.SelectField("crate palette");
            var ids=new HashSet<long>();
            foreach(var e in block.Elements)ids.Add(((TagFieldElementInteger)e.SelectField("Struct:object data/Struct:object id/unique id")).Data);
            int before=block.Elements.Count;
            foreach(var row in plan.Placements)
            {
                if(!ids.Add(row.UniqueId) || Hash(Path.Combine(kit,"tags",row.TargetTag))!=row.TargetSha256)throw new InvalidOperationException("Duplicate ID or changed dependency");
                var s=sources[row.SourceIndex];
                if(Value(s,"type")!=row.SourceType || Value(s,"node orientations")!="0" || Value(s,"manual bsp flags")!="0" || Value(s,"variant name")!="" || Value(s,"active change colors")!="")throw new InvalidOperationException("Unexpected source customization");
                foreach(XmlNode parent in s.SelectNodes("field[@name='parent object']"))if(parent.Attributes["value"].Value!="NONE")throw new InvalidOperationException("Unexpected parent");
                int index=-1;
                foreach(var e in palette.Elements){var p=((TagFieldReference)e.SelectField("name")).Path;if(p!=null && p.RelativePathWithExtension==row.TargetTag)index=e.ElementIndex;}
                if(index<0){var e=palette.AddElement();((TagFieldReference)e.SelectField("name")).Path=TagPath.FromPathAndExtension(Path.ChangeExtension(row.TargetTag,null),"crate");index=e.ElementIndex;}
                var t=block.AddElement();((TagFieldBlockIndex)t.SelectField("type")).Value=index;
                PrepareH3BasicPlacements.Copy(t,s,"Struct:object data/",new[]{"placement flags","position","rotation","scale","transform flags","bsp policy"});
                PrepareH3BasicPlacements.Copy(t,s,"Struct:object data/Struct:object id/",new[]{"source"});
                PrepareH3BasicPlacements.Set(t.SelectField("Struct:object data/Struct:object id/type"),"crate");
                ((TagFieldElementInteger)t.SelectField("Struct:object data/Struct:object id/unique id")).Data=row.UniqueId;
                ((TagFieldBlockIndex)t.SelectField("Struct:object data/Struct:object id/origin bsp index")).Value=Value(s,"origin bsp index")=="NONE"?-1:0;
                dynamic attach=t.SelectField("Struct:object data/can attach to bsp flags");
                if(Value(s,"can attach to bsp flags")!="1")throw new InvalidOperationException("Unexpected attachment");
                foreach(dynamic item in attach.Items)item.IsSet=true;
                PrepareH3BasicPlacements.Copy(t,s,"Struct:crate data/",new[]{"Pathfinding policy"});
                PrepareH3BasicPlacements.Copy(t,s,"Struct:multiplayer data/",new[]{"game engine symmetric placement","owner team","spawn order","quota minimum","quota maximum","spawn time","abandonment time","remapping policy","boundary shape","teleporter channel","boundary width or radius","boundary box length","boundary positive height","boundary negative height","natural respawn weight"});
                // Source terr_object/required-Megalo becomes the native H3 mode filter.
                // The separate unchanged stock territory object supplies capture rules.
                if(Value(s,"game engine flags")!="" || Value(s,"megalo label")!=(row.Mode=="territories"?"terr_object":"") || Value(s,"spawn flags")!=(row.Mode=="territories"?"hide unless megalo required":""))throw new InvalidOperationException("Unexpected mode restriction");
                PrepareH3BasicPlacements.Set(t.SelectField("Struct:multiplayer data/game engine flags"),row.Mode);
                PrepareH3BasicPlacements.Set(t.SelectField("Struct:multiplayer data/spawn flags"),"");
                Console.WriteLine("PLACED "+row.SourceIndex+" "+row.TargetTag+" "+row.Mode);
            }
            if(block.Elements.Count!=before+9)throw new InvalidOperationException("Unexpected addition count");
            if(apply){if(Hash(path)!=plan.ScenarioSha256)throw new InvalidOperationException("Concurrent scenario change");File.Copy(path,backup);tag.Save();}
            Console.WriteLine(apply?"SAVED":"DRY_RUN_COMPLETE");
        }
    }
}
