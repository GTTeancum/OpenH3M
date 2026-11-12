#include <windows.h>
#include "pc_video_settings.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <cstring>
static void require(bool v,const char* text){if(!v)throw std::runtime_error(text);}
int main(int argc,char** argv){try{
  using namespace spartan::video;
  require(argc==2,"Pass repository-local evidence directory");
  const std::filesystem::path root=argv[1];std::filesystem::create_directories(root);
  require(LoadLibraryW(L"rexgpu-xenos.dll")!=nullptr,"GPU registration failed");
  rex::cvar::SetFlagByName("host_guest_output_fps","30");
  rex::cvar::SetFlagByName("resolution","1080p");
  rex::cvar::SetFlagByName("resolution_scale","2");
  rex::cvar::SetFlagByName("draw_resolution_scale_x","2");
  rex::cvar::SetFlagByName("draw_resolution_scale_y","2");
  rex::cvar::FinalizeInit();
  PCSettings settings;auto original=settings.values;
  settings.Preset(0);
  require(settings.values[0]=="1080p"&&settings.values[10]=="2","Preset changed resolution");
  require(rex::cvar::GetFlagByName("texture_detail_reduction")=="0","Draft changed live renderer");
  settings.Cancel();require(settings.values==original&&!settings.Dirty(),"Cancel failed");
  settings.Defaults();settings.values[0]="1440p";settings.values[10]="3";settings.values[9]="fxaa";settings.Preset(1);
  std::string error;
  const auto config=root/"settings.toml";
  require(settings.Apply(config,error),error.c_str());
  require(!settings.Dirty()&&settings.RestartRequired(),"Apply/restart state failed");
  require(rex::cvar::GetFlagByName("draw_resolution_scale_x")=="3"&&rex::cvar::GetFlagByName("draw_resolution_scale_y")=="3","Scale axes diverged");
  require(rex::cvar::GetFlagByName("host_guest_output_fps")=="30","Video menu changed timing");
  rex::cvar::testing::ResetAllForTesting();rex::cvar::LoadConfig(config);
  for(size_t i=0;i<PCOptions().size();++i)require(rex::cvar::GetFlagByName(PCOptions()[i].flag)==settings.values[i],"Saved settings failed reload");
  settings.Reload();require(settings.RestartRequired(),"Reopen lost restart warning");
  settings.values[3]="bogus";require(!settings.Apply(config,error),"Invalid choice accepted");settings.Cancel();
  settings.Preset(0);require(!settings.Apply(root/"missing"/"settings.toml",error),"Unwritable config accepted");
  require(rex::cvar::GetFlagByName("texture_detail_reduction")=="1","Failed save changed live state");
  require(!settings.Apply(root,error),"Failed atomic replacement accepted");
  require(rex::cvar::GetFlagByName("texture_detail_reduction")=="1","Atomic replacement failure did not roll back live state");
  settings.Cancel();settings.Defaults();require(settings.Apply(config,error),"Default save failed");
  rex::cvar::SetFlagByName("window_width","1280");
  rex::cvar::SetFlagByName("window_height","720");
  rex::cvar::SetFlagByName("video_mode_width","1920");
  require(settings.Apply(config,error),"Legacy dimensions repair failed");
  require(rex::cvar::GetFlagByName("window_width")=="0" && rex::cvar::GetFlagByName("window_height")=="0" && rex::cvar::GetFlagByName("video_mode_width")=="1280","Legacy dimensions still override resolution");
  rex::cvar::testing::ResetAllForTesting();rex::cvar::LoadConfig(config);
  for(const auto& option:PCOptions())require(rex::cvar::GetFlagByName(option.flag)==option.default_value,"Defaults failed reload");
  std::ofstream matrix(root/"all-values.csv");matrix<<"option,choice,apply,reload,restore\n";
  for(size_t index=0;index<PCOptions().size();++index){
    const auto& option=PCOptions()[index];
    for(const auto& choice:option.choices){
      PCSettings each;each.values[index]=choice.value;
      require(each.Apply(config,error),error.c_str());
      require(rex::cvar::GetFlagByName(option.flag)==choice.value,"Choice did not reach runtime cvar");
      rex::cvar::testing::ResetAllForTesting();rex::cvar::LoadConfig(config);
      require(rex::cvar::GetFlagByName(option.flag)==choice.value,"Choice failed reload");
      each.Reload();each.Defaults();require(each.Apply(config,error),"Restore after choice failed");
      for(const auto& restored:PCOptions())require(rex::cvar::GetFlagByName(restored.flag)==restored.default_value,"Choice leaked into next test");
      matrix<<option.flag<<','<<choice.value<<",pass,pass,pass\n";
    }
  }
  std::cout<<"PASS: draft/cancel, presets, resolution axes, persistence, invalid values, save failure, defaults, timing isolation, every selectable value apply/reload/restore; native menu uses this settings backend.\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
