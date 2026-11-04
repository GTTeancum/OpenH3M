// Read-only probe of the official H3 ManagedBlam API. No tag writes.
using System;
using System.IO;
using Bungie;
using Bungie.Tags;

class ProbeH3Api
{
    static int Main(string[] args)
    {
        if (args.Length < 1 || args.Length > 2) throw new ArgumentException("Expected repository-local H3EK path and optional bitmap path");
        var kit = Path.GetFullPath(args[0]);
        Directory.SetCurrentDirectory(kit);
        Console.WriteLine("H3_INITIALIZING");
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly, kit);
        Console.WriteLine("H3_INITIALIZED");
        if(args.Length==2)
        {
            using(var bitmap=new TagFile(TagPath.FromPathAndType(args[1],"bitm*")))
            {
                foreach(var field in bitmap.Fields)
                {
                    Console.WriteLine(field.DisplayName+" | "+field.FieldPath+" | "+field.GetType().Name);
                    var enumeration=field as TagFieldEnum;
                    if(enumeration!=null)
                        foreach(var item in enumeration.Items)Console.WriteLine("  "+item.EnumName);
                }
                // Inspect one in-memory override's schema; never Save this tag.
                var block=(TagFieldBlock)bitmap.SelectField("usage override");
                var element=block.Elements.Count>0?block.Elements[0]:block.AddElement();
                foreach(var field in element.Fields)
                {
                    Console.WriteLine("OVERRIDE "+field.DisplayName+" | "+field.FieldPath+" | "+field.GetType().Name);
                    if(field is TagFieldElementSingle)Console.WriteLine("  DEFAULT "+((TagFieldElementSingle)field).Data);
                    if(field is TagFieldElementInteger)Console.WriteLine("  DEFAULT "+((TagFieldElementInteger)field).Data);
                    if(field is TagFieldFlags)
                        foreach(var item in ((TagFieldFlags)field).Items)Console.WriteLine("  FLAG "+item.FlagName);
                    var enumeration=field as TagFieldEnum;
                    if(enumeration!=null)
                        foreach(var item in enumeration.Items)Console.WriteLine("  "+item.EnumName);
                }
            }
            return 0;
        }
        var path = TagPath.FromPathAndType(@"levels\dlc\bunkerworld\shaders\bunker_plate_wall", "rmsh*");
        Console.WriteLine("H3_PATH_CREATED " + path.RelativePathWithExtension);
        using (var tag = new TagFile(path))
        {
            Console.WriteLine("H3_TAG_OPENED");
            foreach (var field in tag.Fields)
                Console.WriteLine(field.DisplayName + " | " + field.FieldPath);
            var parameters = (TagFieldBlock)tag.SelectField("Struct:render_method/Block:parameters");
            Console.WriteLine("PARAMETERS " + parameters.Elements.Count);
            var animations=(TagFieldBlock)parameters.Elements[0].SelectField("animated parameters");
            if(animations.Elements.Count>0)
            {
                foreach(var item in ((TagFieldEnum)animations.Elements[0].SelectField("type")).Items)
                    Console.WriteLine("ANIMATION_TYPE "+item.EnumName);
                foreach(var field in animations.Elements[0].Fields)
                {
                    Console.WriteLine("ANIMATION_FIELD "+field.DisplayName+" "+field.GetType().Name);
                    if(field is TagFieldCustomFunctionEditor)
                    {
                        var editor=((TagFieldCustomFunctionEditor)field).Value;
                        foreach(var property in editor.GetType().GetProperties())
                            Console.WriteLine("EDITOR_PROPERTY "+property.Name+" "+property.PropertyType+" writable="+property.CanWrite);
                    }
                }
            }
            foreach (var method in typeof(TagFieldBlock).GetMethods())
                if (method.Name.Contains("Element")) Console.WriteLine(method);
            foreach (var method in typeof(TagFieldData).GetMethods())
                if (method.Name.Contains("Data")) Console.WriteLine(method);
            foreach (var field in parameters.Elements[0].Fields)
                Console.WriteLine(field.DisplayName + " " + field.GetType().Name);
        }
        Console.WriteLine("H3_READ_ONLY_PROBE_COMPLETE");
        return 0;
    }
}
