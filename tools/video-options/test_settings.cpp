#include <windows.h>
#include <rex/cvar.h>
#include <rex/ui/host_output_schedule.h>
#include "video_options.h"
#include "video_quality.h"
#include <cstring>
#include <iostream>
#include <stdexcept>
REXCVAR_DEFINE_STRING(video_test_string, "", "VideoTest", "Configuration escaping regression fixture");
static void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
int main(int argc,char** argv){try{
 using namespace spartan::video;
 const Throttles original{0,1,1,1,1,1,1,1,6,1,2,1,5,.7f};
 const auto unchanged=Apply(original,{0,0,0,0,0});
 require(std::memcmp(&original,&unchanged,sizeof(original))==0,"Original must retain native bytes");
 const auto low=Apply(original,{2,2,2,2,2});
 require(low.shadows==2 && low.shadow_lod==.35f && low.decorators==.5f && low.object_lod==.5f && low.effects==.5f && low.water==0,"low native quality");
 require(low.flags==original.flags && low.instances==1 && low.object_fade==1 && low.decals==1 && low.cpu_lights==6 && low.gpu_lights==2,"unrelated native fields changed");
 const auto medium=Apply(original,{1,1,1,1,1});
 require(medium.shadows==3 && medium.decorators==.75f && medium.water==.5f,"medium native quality");
 const auto shadows_only=Apply(original,{2,0,0,0,0});
 require(shadows_only.decorators==1 && shadows_only.object_lod==1 && shadows_only.water==1,"independent controls");
 Throttles split=original; split.shadows=0; split.shadow_lod=0; split.water=0; split.decorators=.3f;
 const auto reduced=Apply(split,{2,2,2,2,2});
 require(reduced.shadows==0 && reduced.water==0 && reduced.decorators==.15f,"authored disabled features enabled or split-screen defaults replaced");
 rex::ui::VideoGpuAccumulator gpu;
 require(gpu.Add(1,1,3)<0 && gpu.Add(1,2,4)<0 && gpu.Add(2,3,2)<0,"partial initial frame must be discarded");
 require(gpu.Add(2,4,5)<0 && gpu.Add(3,5,1)==7,"GPU submissions not summed per frame");
 require(gpu.Add(3,7,9)<0 && gpu.Add(4,8,2)<0,"missing submission produced misleading GPU time");
 require(gpu.Add(5,9,3)==2,"GPU accumulator did not recover after gap");
 rex::ui::HostOutputSchedule schedule;
 const void* owner=&schedule;
 const double period=1.0/30.0;
 require(std::abs(schedule.Advance(owner,30,0,0,period)-period)<1e-9,"initial phase deadline");
 // A frame arrives just after its assigned deadline; it must publish now,
 // not wait another complete period and turn 30 FPS into 15 FPS.
 require(schedule.Advance(owner,30,2*period+.001,0,period)<2*period+.001,"late frame unnecessarily delayed");
 require(std::abs(schedule.Advance(owner,30,.075,0,period)-.1)<1e-9,"next phase retained");
 require(schedule.Advance(owner,30,1,0,period)==1,"stall must not wait again");
 require(schedule.Advance(owner,30,1.001,0,period)>1.03,"stall caused catch-up burst");
 rex::ui::HostOutputSchedule drift;
 drift.Advance(owner,30,0,0,period);
 require(std::abs(drift.Advance(owner,30,.04,.002,period)-(2*period+.002))<1e-9,
         "deadline did not follow updated display phase");
 require(argc==2,"repository-local config path required");
 require(LoadLibraryW(L"rexgpu-xenos.dll")!=nullptr,"GPU plugin registration");
 rex::cvar::SetFlagByName("resolution_scale","2");
 for(int i=0;i<3;++i){rex::ui::ApplySurfacePreset(i);
 for(const char* flag:kQualityFlags) require(rex::cvar::GetFlagByName(flag)==std::to_string(2-i),"preset missed native quality");
 require(rex::cvar::GetFlagByName("resolution_scale")=="2","preset changed resolution");}
 rex::ui::ApplySurfacePreset(0);
 require(rex::cvar::GetFlagByName("texture_detail_reduction")=="2","performance detail");
 require(rex::cvar::GetFlagByName("anisotropic_override")=="0","performance filtering");
 const std::string escaped="C:\\Games\\Halo 3\\new path\\\"quoted\"\nline\ttab";
 rex::cvar::SetFlagByName("video_test_string",escaped);
 rex::cvar::SaveConfig(argv[1]);
 rex::cvar::testing::ResetAllForTesting();
 rex::cvar::LoadConfig(argv[1]);
 require(rex::cvar::GetFlagByName("video_test_string")==escaped,"Windows paths/quotes/newlines did not survive TOML");
 require(rex::cvar::GetFlagByName("texture_detail_reduction")=="2","detail persistence");
 require(rex::cvar::GetFlagByName("anisotropic_override")=="0","filter persistence");
 require(rex::cvar::GetFlagByName("resolution_scale")=="2","resolution persistence");
 for(const char* flag:kQualityFlags) require(rex::cvar::GetFlagByName(flag)=="2","native quality persistence");
 for(size_t i=0;i<kQualityFlags.size();++i) rex::cvar::SetFlagByName(kQualityFlags[i], i%2 ? "2" : "1");
 rex::cvar::SaveConfig(argv[1]);
 for(const char* flag:kQualityFlags) rex::cvar::ResetToDefault(flag);
 rex::cvar::LoadConfig(argv[1]);
 for(size_t i=0;i<kQualityFlags.size();++i) require(rex::cvar::GetFlagByName(kQualityFlags[i])==(i%2 ? "2" : "1"),"live custom reload");
 rex::ui::RestoreVideoDefaults();
 for(const char* flag:kQualityFlags) require(rex::cvar::GetFlagByName(flag)=="0","native quality defaults");
 for(const char* name:{"texture_detail_reduction","anisotropic_override","resolution_scale"})
   rex::cvar::ResetToDefault(name);
 rex::cvar::SaveConfig(argv[1]);
 rex::cvar::testing::ResetAllForTesting();
 rex::cvar::LoadConfig(argv[1]);
 require(rex::cvar::GetFlagByName("texture_detail_reduction")=="0","restored defaults persisted");
 require(rex::cvar::GetFlagByName("resolution_scale")=="1","restored resolution persisted");
 ImGui::CreateContext();auto& io=ImGui::GetIO();io.IniFilename=nullptr;io.LogFilename=nullptr;
 io.DisplaySize={1280,720};io.DeltaTime=1.f/60;
 unsigned char* pixels;int w,h;io.Fonts->GetTexDataAsRGBA32(&pixels,&w,&h);
 for(int i=0;i<2;++i){ImGui::NewFrame();ImGui::Begin("Video check");rex::ui::DrawVideoOptions();ImGui::End();ImGui::Render();}
 require(ImGui::GetDrawData()->TotalVtxCount>0,"video panel geometry");
 ImGui::DestroyContext();
 std::cout<<"PASS: native quality math and isolation, authored/split defaults, GPU frame accumulation/gaps, presets, resolution independence, SaveConfig/reload/defaults, panel draw. No OS input.\n";
 return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
