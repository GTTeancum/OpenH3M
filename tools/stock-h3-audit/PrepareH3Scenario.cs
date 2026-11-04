// Basic preview scenario setup through official ManagedBlam editor fields.
// No tag serializer or fabricated gameplay: stock H3 profile, Reach start point.
using System;
using System.IO;
using System.Xml;
using System.Collections.Generic;
using System.Globalization;
using Bungie;
using Bungie.Tags;

class PrepareH3Scenario
{
    const string Scenario=@"levels\custom\battle_canyon_fresh\battle_canyon_fresh";
    static void ForgePalette(TagFile donor,TagFile target,string csv)
    {
        var names=new Dictionary<string,string>{{"Weapons","mv weapon palette"},{"Equipment","mv equipment palette"},
            {"Scenery","mv scenery palette"},{"Teleporters","mv teleporters palette"},{"Goals","mv goals palette"},{"Spawning","mv spawners palette"}};
        foreach(var name in names.Values)
            if(((TagFieldBlock)target.SelectField(name)).Elements.Count!=0)throw new InvalidOperationException("Palette is not empty");
        if(((TagFieldBlock)target.SelectField("mv vehicle palette")).Elements.Count!=0)throw new InvalidOperationException("Vehicle palette is not empty");
        var rows=File.ReadAllLines(csv);
        if(rows.Length!=100)throw new InvalidOperationException("Expected exactly 99 approved stock choices");
        for(int i=1;i<rows.Length;i++)
        {
            var row=rows[i].Split(',');if(row.Length!=7)throw new InvalidOperationException("Unexpected inventory CSV row");
            string blockName=names[row[0]];TagElement source=null;
            foreach(var item in ((TagFieldBlock)donor.SelectField(blockName)).Elements)
            {
                var reference=(TagFieldReference)item.SelectField("name");
                if(reference.Path!=null && Path.ChangeExtension(reference.Path.RelativePathWithExtension,null)==row[2]){source=item;break;}
            }
            if(source==null)throw new InvalidOperationException("Stock MCC donor lacks "+row[2]);
            var path=((TagFieldReference)source.SelectField("name")).Path;
            string display=((TagFieldElementStringID)source.SelectField("display_name")).GetStringData();
            long maximum=((TagFieldElementInteger)source.SelectField("maximum allowed")).Data;
            float price=((TagFieldElementSingle)source.SelectField("price per instance")).Data;
            if(Path.GetExtension(path.RelativePathWithExtension)!="."+row[3] || display!=row[4] ||
                maximum!=int.Parse(row[5]) || price!=float.Parse(row[6],CultureInfo.InvariantCulture))
                throw new InvalidOperationException("MCC entry differs from approved original-360 inventory: "+row[2]);
            var dest=((TagFieldBlock)target.SelectField(blockName)).AddElement();
            ((TagFieldReference)dest.SelectField("name")).Path=path;
            ((TagFieldElementStringID)dest.SelectField("display_name")).SetStringData(display);
            ((TagFieldElementInteger)dest.SelectField("maximum allowed")).Data=maximum;
            ((TagFieldElementSingle)dest.SelectField("price per instance")).Data=price;
        }
    }
    static void CopyProfile(TagElement source,TagElement target)
    {
        foreach(var field in source.Fields)
        {
            var dest=target.SelectField(field.DisplayName);
            if(field is TagFieldReference)
                ((TagFieldReference)dest).Path=((TagFieldReference)field).Path;
            else if(field is TagFieldEnum)
                ((TagFieldEnum)dest).Value=((TagFieldEnum)field).Value;
            else
            {
                var data=field.GetType().GetProperty("Data");
                if(data!=null && data.CanRead && data.CanWrite)
                {
                    if(dest==null)throw new InvalidOperationException("Missing profile field "+field.DisplayName);
                    data.SetValue(dest,data.GetValue(field,null),null);
                }
            }
        }
        ((dynamic)target.SelectField("name")).SetStringData("default");
    }
    static int Main(string[] args)
    {
        if(args.Length!=1 && !(args.Length==2 && args[1]=="--dry-run"))throw new ArgumentException("Expected repository root and optional --dry-run");
        bool apply=args.Length==1;
        string root=Path.GetFullPath(args[0]),kit=Path.Combine(root,@"work\editing-kits\h3ek");
        string output=Path.Combine(root,@"work\stock-h3-audit");
        string path=Path.Combine(kit,"tags",Scenario+".scenario");
        string backup=Path.Combine(output,"scenario-before-basic-setup.scenario");
        if(File.Exists(backup))throw new InvalidOperationException("Scenario setup backup exists; inspect before rerunning");
        string design=@"levels\custom\battle_canyon_rebuild\battle_canyon";
        if(!File.Exists(Path.Combine(kit,"tags",design+".structure_design")))throw new FileNotFoundException(design);
        var reach=new XmlDocument();reach.Load(Path.Combine(output,"original-lighting-scenario.xml"));
        var start=reach.SelectSingleNode("/tag/field[@name='player starting locations']/following-sibling::element[1]");
        if(start==null)throw new InvalidOperationException("Missing original Reach start");
        string position=start.SelectSingleNode("field[@name='position']").Attributes["value"].Value;
        string facing=start.SelectSingleNode("field[@name='facing']").Attributes["value"].Value;
        Directory.SetCurrentDirectory(kit);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        using(var tag=new TagFile(TagPath.FromPathAndType(Scenario,"scnr")))
        using(var donor=new TagFile(TagPath.FromPathAndType(@"levels\dlc\bunkerworld\bunkerworld","scnr")))
        {
            var type=(TagFieldEnum)tag.SelectField("type");
            bool found=false;
            foreach(var option in type.Items)if(option.EnumName=="multiplayer"){type.Value=option.EnumIndex;found=true;}
            if(!found)throw new InvalidOperationException("No multiplayer enum");
            ((TagFieldElementSingle)tag.SelectField("sandbox budget")).Data=800;
            ((TagFieldElementInteger)tag.SelectField("map id")).Data=int.Parse(reach.SelectSingleNode("/tag/field[@name='map id']").Attributes["value"].Value);
            ForgePalette(donor,tag,Path.Combine(output,"standoff-forge-no-vehicles.csv"));
            var bsps=(TagFieldBlock)tag.SelectField("structure bsps");
            if(bsps.Elements.Count!=1)throw new InvalidOperationException("Expected one map BSP");
            ((TagFieldReference)bsps.Elements[0].SelectField("structure design")).Path=TagPath.FromPathAndExtension(design,"structure_design");
            var zones=(TagFieldBlock)tag.SelectField("zone sets");
            var starts=(TagFieldBlock)tag.SelectField("player starting locations");
            var profiles=(TagFieldBlock)tag.SelectField("player starting profile");
            if(zones.Elements.Count!=0||starts.Elements.Count!=0||profiles.Elements.Count!=0)
                throw new InvalidOperationException("Expected fresh empty scenario blocks");
            var zone=zones.AddElement();((dynamic)zone.SelectField("name")).SetStringData("default");
            dynamic flags=zone.SelectField("bsp zone flags");
            foreach(dynamic item in flags.Items)item.IsSet=true;
            var sourceProfiles=(TagFieldBlock)donor.SelectField("player starting profile");
            if(sourceProfiles.Elements.Count<1)throw new InvalidOperationException("Stock H3 profile missing");
            CopyProfile(sourceProfiles.Elements[0],profiles.AddElement());
            var location=starts.AddElement();
            ((dynamic)location.SelectField("position")).Data=Array.ConvertAll(position.Split(','),s=>float.Parse(s,System.Globalization.CultureInfo.InvariantCulture));
            ((dynamic)location.SelectField("facing")).Data=float.Parse(facing,System.Globalization.CultureInfo.InvariantCulture);
            if(apply){File.Copy(path,backup,false);tag.Save();}
            Console.WriteLine("H3_SCENARIO_BASIC_SETUP "+(apply?"SAVED":"DRY RUN")+" multiplayer; budget 800; 99 verified stock Forge choices; original Reach start "+position+"; Standoff profile; original structure design; one BSP zone");
        }
        return 0;
    }
}
