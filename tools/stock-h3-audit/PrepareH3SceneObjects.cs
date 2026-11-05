// Standard model, scenery and approved light authoring through official H3 fields.
using System;using System.IO;using System.Xml;using System.Collections.Generic;using System.Web.Script.Serialization;
using Bungie;using Bungie.Tags;
public class PlacedLightFunction {public string data_base64,input,range,output_input;public int output_modifier,master_type,color_graph_type;public bool is_ranged;public float clamp_min,clamp_max;public List<float[]> colors;}
public class PlacedLightSource {public string source,sha256;public Dictionary<string,PlacedLightFunction> functions;}
public class PlacedLightInputs {public List<PlacedLightSource> lights;}
class PrepareH3SceneObjects {
 static string root,kit,output;const string Prefix=@"levels\custom\battle_canyon_fresh\props\";
 static string Value(XmlNode e,string n){return PrepareH3BasicPlacements.Value(e,n);}
 static void Set(TagField f,string v){PrepareH3BasicPlacements.Set(f,v);}
 static void Reference(TagElement e,string field,string path,string ext){((TagFieldReference)e.SelectField(field)).Path=TagPath.FromPathAndExtension(path,ext);}
 static TagFile New(string path,string ext){if(File.Exists(Path.Combine(kit,"tags",path+"."+ext)))throw new InvalidOperationException("Inspect existing tag: "+path+"."+ext);var t=new TagFile();t.New(TagPath.FromPathAndExtension(path,ext));return t;}
 static void Model(string name,bool wheel){string p=Prefix+name+"\\"+name;
  using(var t=New(p,"model")){
   foreach(string[] pair in wheel?new[]{new[]{"render model","render_model"},new[]{"collision model","collision_model"},new[]{"physics_model","physics_model"},new[]{"animation","model_animation_graph"}}:new[]{new[]{"render model","render_model"}}){
    if(!File.Exists(Path.Combine(kit,"tags",p+"."+pair[1])))throw new FileNotFoundException(p+"."+pair[1]);
    ((TagFieldReference)t.SelectField(pair[0])).Path=TagPath.FromPathAndExtension(p,pair[1]);
   }
   if(wheel){var xml=new XmlDocument();xml.Load(Path.Combine(output,"original-prop-frunner_wheel-model.xml"));
    var source=xml.SelectSingleNode("/tag/field[@name='variants']/following-sibling::element[1]");
    var sr=source.SelectSingleNode("field[@name='regions']/following-sibling::element[1]");var sp=sr.SelectSingleNode("field[@name='permutations']/following-sibling::element[1]");
    var v=((TagFieldBlock)t.SelectField("variants")).AddElement();Set(v.SelectField("name"),Value(source,"name"));
    var r=((TagFieldBlock)v.SelectField("regions")).AddElement();Set(r.SelectField("region name"),Value(sr,"region name"));
    var p0=((TagFieldBlock)r.SelectField("permutations")).AddElement();Set(p0.SelectField("permutation name"),Value(sp,"permutation name"));Set(p0.SelectField("probability"),Value(sp,"probability"));
   }t.Save();
  }
 }
 static void Scenery(string name,string model,string light){string p=Prefix+name+"\\"+name;
  using(var t=New(p,"scenery")){
   ((TagFieldReference)t.SelectField("Struct:object/Reference:model")).Path=TagPath.FromPathAndExtension(Prefix+model+"\\"+model,"model");
   Set(t.SelectField("pathfinding policy"),"Pathfinding CUT-OUT");Set(t.SelectField("lightmapping policy"),"Per-Vertex");
   if(light!=null){var a=((TagFieldBlock)t.SelectField("Struct:object/Block:attachments")).AddElement();Reference(a,"type",light,"light");Set(a.SelectField("marker"),"light");}
   t.Save();
  }
 }
 static void Main(string[] args){root=Path.GetFullPath(args[0]);kit=Path.Combine(root,@"work\editing-kits\h3ek");output=Path.Combine(root,@"work\stock-h3-audit");
  if(!File.ReadAllText(Path.Combine(root,@"tools\stock-h3-audit\PLACED-LIGHTS-PROPOSAL.md")).Contains("Approve native H3 placed-light behavior"))throw new InvalidOperationException("Missing approval");
  var inputs=new JavaScriptSerializer().Deserialize<PlacedLightInputs>(File.ReadAllText(Path.Combine(output,"original-placed-light-inputs.json")));
  Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
  foreach(var row in inputs.lights){string name=Path.GetFileNameWithoutExtension(row.source),p=Prefix+name+"\\"+name;
   var source=new XmlDocument();source.Load(Path.Combine(output,"original-placed-"+name+".light.xml"));var s=source.DocumentElement;
   using(var t=New(p,"light")){
    foreach(string f in new[]{"type","frustum near width","frustum height scale","frustum field of view","destroy light after","near priority","far priority"})Set(t.SelectField(f),Value(s,f));
    Set(t.SelectField("maximum distance"),Value(s,"attenuation end distance"));
    // Approved native H3 defaults: no invented conversion of Reach-only falloff.
    Set(t.SelectField("distance diffusion"),"0.5");Set(t.SelectField("angular smoothness"),"1");Set(t.SelectField("percent spherical"),"0");
    var flags=(TagFieldFlags)t.SelectField("flags");flags.SetBit("render in multiplayer override",true);
    if(name!="ca_bcreek_omni_1"){flags.SetBit("allow shadows and gels",true);((TagFieldReference)t.SelectField("gel bitmap")).Path=TagPath.FromPathAndExtension(@"levels\custom\battle_canyon_fresh\bitmaps\ca_bcreek_forerunner_lightgel","bitmap");}
    foreach(var pair in row.functions){var f=pair.Value;string stem="Struct:"+pair.Key+"/";
     Set(t.SelectField(stem+"Input Variable"),f.input);Set(t.SelectField(stem+"Range Variable"),f.range);Set(t.SelectField(stem+"Output Modifier Input"),f.output_input);
     ((TagFieldEnum)t.SelectField(stem+"Output Modifier")).Value=f.output_modifier;
     ((TagFieldData)t.SelectField(stem+"Struct:Mapping/Data:data")).SetData(Convert.FromBase64String(f.data_base64));
    }t.Save();
   }
   using(var t=new TagFile(TagPath.FromPathAndExtension(p,"light")))foreach(var pair in row.functions){string stem="Struct:"+pair.Key+"/";var f=pair.Value;var e=((TagFieldCustomFunctionEditor)t.SelectField(stem+"Custom:Mapping")).Value;
    if(Convert.ToBase64String(((TagFieldData)t.SelectField(stem+"Struct:Mapping/Data:data")).GetData())!=f.data_base64 || (int)e.MasterType!=f.master_type || (int)e.ColorGraphType!=f.color_graph_type || e.IsRanged!=f.is_ranged || e.ClampRangeMin!=f.clamp_min || e.ClampRangeMax!=f.clamp_max || e.ColorCount!=f.colors.Count)throw new InvalidOperationException("Native function readback differs");
    for(int i=0;i<e.ColorCount;i++){var c=e.GetColor(i);if((int)c.ColorMode==1)c=c.ToRgb();var expected=f.colors[i];if(Math.Abs(c.Red-expected[0])>1e-6 || Math.Abs(c.Green-expected[1])>1e-6 || Math.Abs(c.Blue-expected[2])>1e-6 || expected[3]!=1)throw new InvalidOperationException("Native color differs");}
   }
   Console.WriteLine("APPROVED_LIGHT_AUTHORED "+name);
  }
  Model("ca_bcreek_omni_1",false);Model("ca_bcreek_spot_5",false);Model("frunner_wheel",true);
  foreach(string name in new[]{"ca_bcreek_omni_1","ca_bcreek_spot_5","ca_bcreek_spot_7"})Scenery(name,name=="ca_bcreek_spot_7"?"ca_bcreek_spot_5":name,Prefix+name+"\\"+name);
  Scenery("frunner_wheel","frunner_wheel",null);Console.WriteLine("SCENE_OBJECTS_SAVED 3 lights, 3 models, 4 scenery tags");
 }
}
