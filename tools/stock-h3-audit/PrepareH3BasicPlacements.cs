// Restore unambiguous stock-H3 gameplay placements using official editor fields.
using System;
using System.IO;
using System.Xml;
using System.Collections.Generic;
using Bungie;
using Bungie.Tags;

class PrepareH3BasicPlacements
{
    const string Scenario=@"levels\custom\battle_canyon_fresh\battle_canyon_fresh";
    public static string Value(XmlNode source,string name)
    {
        var field=source.SelectSingleNode("field[@name='"+name+"']");
        if(field==null)throw new InvalidOperationException("Missing source field "+name);
        return field.Attributes["value"].Value;
    }
    public static void Set(TagField field,string value)
    {
        if(field is TagFieldEnum)
        {
            var e=(TagFieldEnum)field;
            foreach(var item in e.Items)if(item.EnumName==value){e.Value=item.EnumIndex;return;}
            throw new InvalidOperationException("Missing H3 enum "+field.FieldPath+": "+value);
        }
        if(field is TagFieldFlags)
        {
            var flags=(TagFieldFlags)field;
            foreach(var item in flags.Items)flags.SetBit(item.FlagName,false);
            if(value!="")
            {
                bool found=false;
                foreach(var item in flags.Items)if(item.FlagName==value){flags.SetBit(item.FlagName,true);found=true;}
                if(!found)throw new InvalidOperationException("Missing H3 flag "+field.FieldPath+": "+value);
            }
            return;
        }
        if(field is TagFieldElementArray)
        {
            if(!((TagFieldElementArray)field).SetStringData(value.Split(',')))throw new InvalidOperationException("Invalid vector "+field.FieldPath);
            return;
        }
        if(field is TagFieldElement)
        {
            if(!((TagFieldElement)field).SetStringData(value))throw new InvalidOperationException("Invalid field "+field.FieldPath);
            return;
        }
        throw new InvalidOperationException("Unsupported field "+field.FieldPath);
    }
    public static void Copy(TagElement destination,XmlNode source,string prefix,string[] names)
    {
        foreach(string name in names)Set(destination.SelectField(prefix+name),Value(source,name));
    }
    static int Main(string[] args)
    {
        if(args.Length!=1 && !(args.Length==2 && args[1]=="--dry-run"))throw new ArgumentException("Expected repository root and optional --dry-run");
        bool apply=args.Length==1;
        string root=Path.GetFullPath(args[0]),kit=Path.Combine(root,@"work\editing-kits\h3ek"),output=Path.Combine(root,@"work\stock-h3-audit");
        string backup=Path.Combine(output,"scenario-before-basic-placements.scenario");
        if(File.Exists(backup))throw new InvalidOperationException("Placement checkpoint exists; inspect before reapplying");
        var original=new XmlDocument();original.Load(Path.Combine(output,"original-lighting-scenario.xml"));
        var inventory=new Dictionary<string,string[]>();
        foreach(var line in File.ReadAllLines(Path.Combine(output,"standoff-forge-no-vehicles.csv")))
        {
            var row=line.Split(',');if(row.Length==7 && (row[3]=="scenery" || row[3]=="weapon" || row[3]=="equipment"))inventory[row[4]]=row;
        }
        Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        using(var tag=new TagFile(TagPath.FromPathAndExtension(Scenario,"scenario")))
        {
            foreach(string category in new[]{"scenery","weapons","equipment"})
            {
                string extension=category=="weapons"?"weapon":category;
                string paletteName=category=="weapons"?"weapon palette":category+" palette";
                var placements=(TagFieldBlock)tag.SelectField(category);
                var palette=(TagFieldBlock)tag.SelectField(paletteName);
                if(placements.Elements.Count!=0 || palette.Elements.Count!=0)throw new InvalidOperationException("Expected fresh empty block "+category);
                var paletteIndices=new Dictionary<string,int>();
                var marker=original.SelectSingleNode("/tag/field[@name='"+category+"']");
                for(var node=marker.NextSibling;node!=null && node.Name=="element";node=node.NextSibling)
                {
                    string sourceType=Value(node,"type"),stockName=sourceType=="energy_sword"?"energy_blade":sourceType;
                    // Initial spawns/objectives require a separate Reach-label to
                    // H3-gametype authoring pass. They are not silently omitted.
                    if(category=="scenery" && sourceType!="respawn_point")continue;
                    string[] stock;
                    if(!inventory.TryGetValue(stockName,out stock) || stock[3]!=extension)
                    {Console.WriteLine("PENDING_STOCK_MAPPING "+category+" "+node.Attributes["index"].Value+" "+sourceType);continue;}
                    if(Value(node,"megalo label")!="" || Value(node,"game engine flags")!="")throw new InvalidOperationException("Unexpected game restriction");
                    if(Value(node,"node orientations")!="0" || (category!="equipment" && (Value(node,"variant name")!="" || Value(node,"active change colors")!="")))throw new InvalidOperationException("Non-default source object customization");
                    foreach(var parent in node.SelectNodes("field[@name='parent object']"))
                        if(((XmlNode)parent).Attributes["value"].Value!="NONE")throw new InvalidOperationException("Parented source placement");
                    if(!paletteIndices.ContainsKey(stockName))
                    {
                        var entry=palette.AddElement();
                        ((TagFieldReference)entry.SelectField("name")).Path=TagPath.FromPathAndExtension(stock[2],extension);
                        paletteIndices[stockName]=entry.ElementIndex;
                    }
                    var target=placements.AddElement();
                    ((TagFieldBlockIndex)target.SelectField("type")).Value=paletteIndices[stockName];
                    Copy(target,node,"Struct:object data/",new[]{"placement flags","position","rotation","scale","transform flags","bsp policy"});
                    Copy(target,node,"Struct:object data/Struct:object id/",new[]{"unique id","source"});
                    Set(target.SelectField("Struct:object data/Struct:object id/type"),extension);
                    ((TagFieldBlockIndex)target.SelectField("Struct:object data/Struct:object id/origin bsp index")).Value=Value(node,"origin bsp index")=="NONE"?-1:0;
                    dynamic attach=target.SelectField("Struct:object data/can attach to bsp flags");
                    if(Value(node,"can attach to bsp flags")!="1" || Value(node,"manual bsp flags")!="0")throw new InvalidOperationException("Unexpected source BSP attachment");
                    foreach(dynamic item in attach.Items)item.IsSet=true;
                    if(category=="weapons")Copy(target,node,"Struct:weapon data/",new[]{"rounds left","rounds loaded","flags"});
                    if(category=="equipment")Copy(target,node,"Struct:equipment data/",new[]{"equipment flags"});
                    if(category=="scenery")Copy(target,node,"Struct:scenery data/",new[]{"Pathfinding policy","Lightmapping policy"});
                    Copy(target,node,"Struct:multiplayer data/",new[]{"game engine symmetric placement","game engine flags","owner team","spawn order","quota minimum","quota maximum","spawn flags","spawn time","abandonment time","remapping policy","boundary shape","teleporter channel","boundary width or radius","boundary box length","boundary positive height","boundary negative height","natural respawn weight"});
                }
                int expected=category=="scenery"?130:category=="weapons"?13:16;
                if(placements.Elements.Count!=expected)throw new InvalidOperationException("Unexpected selected count "+category+": "+placements.Elements.Count);
                Console.WriteLine("H3_BASIC_PLACEMENTS "+category+" "+placements.Elements.Count+" stock palette "+palette.Elements.Count);
            }
            if(apply){File.Copy(Path.Combine(kit,"tags",Scenario+".scenario"),backup);tag.Save();}
            Console.WriteLine(apply?"SAVED":"DRY_RUN_COMPLETE");
        }
        return 0;
    }
}
