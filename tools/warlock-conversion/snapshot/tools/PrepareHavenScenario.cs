// Reuses existing official H3 scenario/profile/placement authoring operations.
// No binary serializer, translated H4 gameplay or installed-map writes.
using System;
using System.IO;
using System.Collections.Generic;
using System.Globalization;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

public class HavenForge { public string Category,Path,Name; public int Maximum; public float Cost; }
public class HavenSpawn
{
    public string SourceScenario,SourceTag,SourceLabel,Target,TargetSha256;
    public int SourceIndex,UniqueId;
    public Dictionary<string,string> Fields;
}
public class HavenScenarioPlan
{
    public string Kit,Target,Donor,Bsp,LightingInfo,Design,Output;
    public float[] StartPosition;
    public float StartFacing;
    public List<HavenForge> Forge;
    public List<HavenSpawn> Placements;
}
class PrepareHavenScenario
{
    static string Hash(string path)
    { using(var s=File.OpenRead(path))using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant(); }
    static void Require(bool condition,string message) { if(!condition)throw new InvalidOperationException(message); }
    static TagPath PathFor(string path,string extension) { return TagPath.FromPathAndExtension(path,extension); }
    static void CopySimple(TagElement source,TagElement target)
    {
        foreach(var field in source.Fields)
        {
            var dest=target.SelectField(field.DisplayName);
            if(field is TagFieldReference)((TagFieldReference)dest).Path=((TagFieldReference)field).Path;
            else if(field is TagFieldEnum)((TagFieldEnum)dest).Value=((TagFieldEnum)field).Value;
            else
            {
                var data=field.GetType().GetProperty("Data");
                if(data!=null && data.CanRead && data.CanWrite)data.SetValue(dest,data.GetValue(field,null),null);
            }
        }
    }
    static void VerifyField(TagField field,string expected)
    {
        if(field is TagFieldEnum)
        {
            var e=(TagFieldEnum)field;Require(e.Items[e.Value].EnumName==expected,"Saved enum differs: "+field.FieldPath);return;
        }
        if(field is TagFieldFlags)
        {
            var f=(TagFieldFlags)field;
            foreach(var item in f.Items)Require(f.TestBit(item.FlagName)==(expected==item.FlagName),"Saved flags differ");return;
        }
        var property=field.GetType().GetProperty("Data");
        Require(property!=null,"No native readback property: "+field.FieldPath);
        var actual=property.GetValue(field,null);
        var values=actual as Array;
        if(values!=null)
        {
            var tokens=expected.Split(',');Require(tokens.Length==values.Length,"Saved array size differs");
            for(int i=0;i<tokens.Length;i++)Require(Math.Abs(Convert.ToDouble(values.GetValue(i))-double.Parse(tokens[i],CultureInfo.InvariantCulture))<0.00001,"Saved vector differs: "+field.FieldPath);
        }
        else
        {
            double wanted;
            if(double.TryParse(expected,NumberStyles.Float,CultureInfo.InvariantCulture,out wanted))
                Require(Math.Abs(Convert.ToDouble(actual)-wanted)<0.00001,"Saved number differs: "+field.FieldPath);
            else Require(Convert.ToString(actual)==expected,"Saved value differs: "+field.FieldPath);
        }
    }
    static int Main(string[] args)
    {
        Require(args.Length==1,"Expected Haven scenario plan");
        var json=new JavaScriptSerializer{MaxJsonLength=32*1024*1024};
        var plan=json.Deserialize<HavenScenarioPlan>(File.ReadAllText(args[0]));
        Require(plan.Target==@"levels\custom\haven_h4\haven_draft","Only private Haven draft may be created");
        var destination=Path.Combine(plan.Kit,"tags",plan.Target+".scenario");
        Require(!File.Exists(destination),"Preserve existing scenario before another authoring pass");
        var donorFile=Path.Combine(plan.Kit,"tags",plan.Donor+".scenario");var donorHash=Hash(donorFile);
        foreach(var row in plan.Placements)Require(Hash(Path.Combine(plan.Kit,"tags",row.Target))==row.TargetSha256,"Stock placement tag changed");
        foreach(var pair in new[]{new[]{plan.Bsp,"scenario_structure_bsp"},new[]{plan.LightingInfo,"scenario_structure_lighting_info"},new[]{plan.Design,"structure_design"}})
            Require(File.Exists(Path.Combine(plan.Kit,"tags",pair[0]+"."+pair[1])),"Missing native geometry dependency");
        Directory.SetCurrentDirectory(plan.Kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,plan.Kit);
        var categories=new Dictionary<string,string>{{"Vehicles","mv vehicle palette"},{"Weapons","mv weapon palette"},{"Equipment","mv equipment palette"},
            {"Scenery","mv scenery palette"},{"Teleporters","mv teleporters palette"},{"Goals","mv goals palette"},{"Spawning","mv spawners palette"}};
        int mapId;float budget,weight=-1;
        using(var donor=new TagFile(PathFor(plan.Donor,"scenario")))
        using(var scenario=new TagFile())
        {
            scenario.New(PathFor(plan.Target,"scenario"));
            PrepareH3BasicPlacements.Set(scenario.SelectField("type"),"multiplayer");
            mapId=(int)((TagFieldElementInteger)donor.SelectField("map id")).Data;
            budget=((TagFieldElementSingle)donor.SelectField("sandbox budget")).Data;
            ((TagFieldElementInteger)scenario.SelectField("map id")).Data=mapId;
            ((TagFieldElementSingle)scenario.SelectField("sandbox budget")).Data=budget;
            var bsp=((TagFieldBlock)scenario.SelectField("structure bsps")).AddElement();
            ((TagFieldReference)bsp.SelectField("structure bsp")).Path=PathFor(plan.Bsp,"scenario_structure_bsp");
            ((TagFieldReference)bsp.SelectField("structure lighting_info")).Path=PathFor(plan.LightingInfo,"scenario_structure_lighting_info");
            ((TagFieldReference)bsp.SelectField("structure design")).Path=PathFor(plan.Design,"structure_design");
            var zone=((TagFieldBlock)scenario.SelectField("zone sets")).AddElement();
            ((TagFieldElementStringID)zone.SelectField("name")).SetStringData("default");
            dynamic zoneFlags=zone.SelectField("bsp zone flags");foreach(dynamic flag in zoneFlags.Items)flag.IsSet=true;
            var donorProfiles=(TagFieldBlock)donor.SelectField("player starting profile");Require(donorProfiles.Elements.Count>0,"Stock profile missing");
            CopySimple(donorProfiles.Elements[0],((TagFieldBlock)scenario.SelectField("player starting profile")).AddElement());
            var start=((TagFieldBlock)scenario.SelectField("player starting locations")).AddElement();
            ((dynamic)start.SelectField("position")).Data=plan.StartPosition;
            ((dynamic)start.SelectField("facing")).Data=plan.StartFacing;
            foreach(var row in plan.Forge)
            {
                TagElement found=null;
                foreach(var entry in ((TagFieldBlock)donor.SelectField(categories[row.Category])).Elements)
                {
                    var reference=((TagFieldReference)entry.SelectField("name")).Path;
                    if(reference!=null && reference.RelativePathWithExtension==row.Path)found=entry;
                }
                Require(found!=null,"Editing kit lacks original Forge entry: "+row.Path);
                Require(((TagFieldElementStringID)found.SelectField("display_name")).GetStringData()==row.Name &&
                    ((TagFieldElementInteger)found.SelectField("maximum allowed")).Data==row.Maximum &&
                    ((TagFieldElementSingle)found.SelectField("price per instance")).Data==row.Cost,"Forge entry differs from original H3: "+row.Path);
                CopySimple(found,((TagFieldBlock)scenario.SelectField(categories[row.Category])).AddElement());
            }
            var stockPalette=(TagFieldBlock)donor.SelectField("scenery palette");
            foreach(var item in ((TagFieldBlock)donor.SelectField("scenery")).Elements)
            {
                int i=((TagFieldBlockIndex)item.SelectField("type")).Value;if(i<0)continue;
                var path=((TagFieldReference)stockPalette.Elements[i].SelectField("name")).Path;
                if(path!=null && path.RelativePathWithExtension==@"objects\multi\spawning\respawn_point.scenery")
                {weight=((TagFieldElementSingle)item.SelectField("Struct:multiplayer data/natural respawn weight")).Data;break;}
            }
            Require(weight>=0,"No stock respawn weight witness");
            var indices=new Dictionary<string,int>();var palette=(TagFieldBlock)scenario.SelectField("scenery palette");
            var placements=(TagFieldBlock)scenario.SelectField("scenery");
            foreach(var row in plan.Placements)
            {
                if(!indices.ContainsKey(row.Target))
                {
                    var entry=palette.AddElement();((TagFieldReference)entry.SelectField("name")).Path=PathFor(Path.ChangeExtension(row.Target,null),"scenery");indices[row.Target]=entry.ElementIndex;
                }
                var item=placements.AddElement();((TagFieldBlockIndex)item.SelectField("type")).Value=indices[row.Target];
                foreach(var field in row.Fields)PrepareH3BasicPlacements.Set(item.SelectField(field.Key),field.Value);
                ((TagFieldElementInteger)item.SelectField("Struct:object data/Struct:object id/unique id")).Data=row.UniqueId;
                ((TagFieldBlockIndex)item.SelectField("Struct:object data/Struct:object id/origin bsp index")).Value=0;
                ((TagFieldElementSingle)item.SelectField("Struct:multiplayer data/natural respawn weight")).Data=weight;
                dynamic attach=item.SelectField("Struct:object data/can attach to bsp flags");foreach(dynamic flag in attach.Items)flag.IsSet=true;
            }
            Directory.CreateDirectory(Path.GetDirectoryName(destination));scenario.Save();
        }
        using(var scenario=new TagFile(PathFor(plan.Target,"scenario")))
        {
            var placements=(TagFieldBlock)scenario.SelectField("scenery");var palette=(TagFieldBlock)scenario.SelectField("scenery palette");
            Require(placements.Elements.Count==plan.Placements.Count,"Saved spawn count differs");
            for(int i=0;i<plan.Placements.Count;i++)
            {
                var item=placements.Elements[i];var row=plan.Placements[i];
                int index=((TagFieldBlockIndex)item.SelectField("type")).Value;
                Require(((TagFieldReference)palette.Elements[index].SelectField("name")).Path.RelativePathWithExtension==row.Target,"Saved spawn object differs");
                foreach(var field in row.Fields)VerifyField(item.SelectField(field.Key),field.Value);
                Require(((TagFieldElementInteger)item.SelectField("Struct:object data/Struct:object id/unique id")).Data==row.UniqueId,"Saved object ID differs");
            }
            VerifyField(((TagFieldBlock)scenario.SelectField("player starting locations")).Elements[0].SelectField("position"),string.Join(",",Array.ConvertAll(plan.StartPosition,x=>x.ToString("R",CultureInfo.InvariantCulture))));
            Require(((TagFieldBlock)scenario.SelectField("structure bsps")).Elements.Count==1,"Saved BSP count differs");
        }
        Require(Hash(donorFile)==donorHash,"Stock scenario changed");
        File.WriteAllText(plan.Output,json.Serialize(new{status="native_scenario_authoring_readback_pass",scenario=plan.Target,sha256=Hash(destination),
            bsp=plan.Bsp,design=plan.Design,spawn_objects=plan.Placements.Count,forge_entries=plan.Forge.Count,stock_respawn_weight=weight,
            source_start=plan.StartPosition,donor=plan.Donor,donor_unchanged=true,editor_draft_map_id=mapId,budget=budget,
            release_identity_pending=true,actual_gameplay_verified=false,complete_map_built=false}));
        Console.WriteLine("H4_H3_SCENARIO_SAVED "+plan.Placements.Count+" stock spawn objects; "+plan.Forge.Count+" Forge entries");
        return 0;
    }
}
