// Read native gameplay controls and stock spawn definitions; never save.
using System;
using System.IO;
using Bungie;
using Bungie.Tags;
class InspectH3GameplaySchema
{
    static void Fields(TagField[] fields)
    {
        foreach(var field in fields)
        {
            Console.WriteLine(field.FieldPath+" | "+field.GetType().Name);
            if(field is TagFieldEnum)foreach(var item in ((TagFieldEnum)field).Items)Console.WriteLine(" ENUM "+item.EnumIndex+" "+item.EnumName);
            if(field is TagFieldFlags)foreach(var item in ((TagFieldFlags)field).Items)Console.WriteLine(" FLAG "+item.FlagName+" = "+((TagFieldFlags)field).TestBit(item.FlagName));
            if(field is TagFieldElement)Console.WriteLine(" VALUE "+((TagFieldElement)field).GetStringData());
            if(field is TagFieldBlock)Console.WriteLine(" COUNT "+((TagFieldBlock)field).Elements.Count);
            if(field is TagFieldStruct)foreach(var element in ((TagFieldStruct)field).Elements)Fields(element.Fields);
        }
    }
    static void Main(string[] args)
    {
        string kit=Path.Combine(Path.GetFullPath(args[0]),@"work\editing-kits\h3ek");
        Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        using(var scenario=new TagFile(TagPath.FromPathAndExtension(@"levels\dlc\bunkerworld\bunkerworld","scenario")))
        {
            foreach(string name in new[]{"scenery","crates","player starting locations"})
            {
                var block=(TagFieldBlock)scenario.SelectField(name);Console.WriteLine("SCENARIO "+name);
                Fields((block.Elements.Count==0?block.AddElement():block.Elements[0]).Fields);
            }
        }
        foreach(string path in new[]{@"objects\multi\slayer\slayer_initial_spawn_point",@"objects\multi\infection\infection_initial_spawn_point",@"objects\multi\spawning\respawn_point_invisible"})
        using(var tag=new TagFile(TagPath.FromPathAndExtension(path,"scenery")))
        {
            Console.WriteLine("STOCK "+path);
            foreach(var element in ((TagFieldBlock)tag.SelectField("Struct:object/Block:multiplayer object")).Elements)Fields(element.Fields);
        }
    }
}
