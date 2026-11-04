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
    public string Curve;
    public float SourceGamma;
    public bool ClearOverride;
    public int? MaxMipmapLevel;
}
class ApplyH3BitmapPlan
{
    static void SetEnum(TagField field,string value)
    {
        var enumeration=(TagFieldEnum)field;
        for(int i=0;i<enumeration.Items.Length;i++)
            if(enumeration.Items[i].EnumName==value){enumeration.Value=enumeration.Items[i].EnumIndex;return;}
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
                if(input.MaxMipmapLevel.HasValue)
                    ((TagFieldElementInteger)tag.SelectField("max mipmap level")).Data=input.MaxMipmapLevel.Value;
                if(input.ClearOverride)((TagFieldBlock)tag.SelectField("usage override")).RemoveAllElements();
                if(input.LinearSource || input.Curve!=null)
                {
                    bool cube=input.Usage=="Cube Map (Reflection Map)";
                    if(input.Usage!="Diffuse Map" && input.Usage!="Detail Map" && input.Usage!="Self-Illum Map" && input.Usage!="ZBrush Bump Map (from Bump Map)" && input.Usage!="Height Map (for Parallax)" && !cube)
                        throw new InvalidOperationException("Unsupported bitmap usage override");
                    var block=(TagFieldBlock)tag.SelectField("usage override");
                    if(block.Elements.Count>1)throw new InvalidOperationException("Unexpected override count");
                    var element=block.Elements.Count==0?block.AddElement():block.Elements[0];
                    ((TagFieldElementSingle)element.SelectField("source gamma")).Data=input.LinearSource?1:input.SourceGamma;
                    SetEnum(element.SelectField("bitmap curve"),input.LinearSource?"linear":input.Curve);
                    ((TagFieldFlags)element.SelectField("flags")).SetBit("Ignore Curve Override",true);
                    SetEnum(element.SelectField("type"),cube?"cube map":"2D texture");
                    if(cube)
                    {
                        SetEnum(element.SelectField("slicer"),"Cube Map Slicer");
                        ((TagFieldFlags)element.SelectField("dicer flags")).SetBit("Rotate Cube Map to Match DirectX Format",true);
                    }
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
