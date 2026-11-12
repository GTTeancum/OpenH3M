// Read existing native lighting fields; never save.
using System;
using System.IO;
using Bungie;
using Bungie.Tags;
class InspectHavenLightingSchema
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
        using(var tag=new TagFile(TagPath.FromPathAndExtension(@"levels\multi\construct\construct","scenario_structure_lighting_info")))
        {
            Fields(tag.Fields);
            foreach(string name in new[]{"generic light definitions","generic light instances"})
            {
                var block=(TagFieldBlock)tag.SelectField(name);Console.WriteLine("LIGHTING "+name);
                Fields((block.Elements.Count==0?block.AddElement():block.Elements[0]).Fields);
            }
        }
    }
}
