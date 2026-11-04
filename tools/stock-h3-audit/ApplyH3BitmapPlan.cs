// Apply import settings through official H3 ManagedBlam; Tool imports pixels.
using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

public class BitmapPlan { public string Kit; public List<BitmapInput> Bitmaps; }
public class BitmapInput
{
    public string Path;
    public string Usage;
    public string Format;
    public bool LinearSource;
}
class ApplyH3BitmapPlan
{
    static void SetEnum(TagField field,string value)
    {
        var enumeration=(TagFieldEnum)field;
        for(int i=0;i<enumeration.Items.Length;i++)
            if(enumeration.Items[i].EnumName==value){enumeration.Value=i;return;}
        throw new InvalidOperationException("Unknown option: "+value);
    }
    static int Main(string[] args)
    {
        if(args.Length!=1)throw new ArgumentException("Expected bitmap import plan JSON");
        var plan=new JavaScriptSerializer().Deserialize<BitmapPlan>(File.ReadAllText(args[0]));
        Directory.SetCurrentDirectory(plan.Kit);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,plan.Kit);
        var tags=Path.GetFullPath(Path.Combine(plan.Kit,@"tags\levels\custom\battle_canyon_fresh\bitmaps"))+Path.DirectorySeparatorChar;
        foreach(var input in plan.Bitmaps)
        {
            var absolute=Path.GetFullPath(Path.Combine(plan.Kit,"tags",input.Path));
            if(!absolute.StartsWith(tags,StringComparison.OrdinalIgnoreCase)||!absolute.EndsWith(".bitmap")||!File.Exists(absolute))
                throw new InvalidOperationException("Expected existing fresh bitmap: "+input.Path);
            using(var tag=new TagFile(TagPath.FromPathAndType(Path.ChangeExtension(input.Path,null),"bitm*")))
            {
                SetEnum(tag.SelectField("Usage"),input.Usage);
                SetEnum(tag.SelectField("force bitmap format"),input.Format);
                if(input.LinearSource)
                {
                    if(input.Usage!="Diffuse Map" && input.Usage!="Detail Map")
                        throw new InvalidOperationException("Linear override supports only these 2D inputs");
                    var block=(TagFieldBlock)tag.SelectField("usage override");
                    if(block.Elements.Count>1)throw new InvalidOperationException("Unexpected override count");
                    var element=block.Elements.Count==0?block.AddElement():block.Elements[0];
                    ((TagFieldElementSingle)element.SelectField("source gamma")).Data=1;
                    SetEnum(element.SelectField("bitmap curve"),"linear");
                    ((TagFieldFlags)element.SelectField("flags")).SetBit("Ignore Curve Override",true);
                    SetEnum(element.SelectField("type"),"2D texture");
                    SetEnum(element.SelectField("downsample filter"),"Box Filter");
                    SetEnum(element.SelectField("bitmap format"),input.Format);
                }
                tag.Save();
            }
            Console.WriteLine("H3_BITMAP_IMPORT_SETTINGS_SAVED "+input.Path);
        }
        return 0;
    }
}
