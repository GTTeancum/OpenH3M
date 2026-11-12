#include "pc_video_settings.h"
#include <algorithm>
#include <fstream>
#include <windows.h>

namespace spartan::video {
const std::vector<Option>& PCOptions() {
  static const std::vector<Choice> quality={{"Original","0"},{"Medium","1"},{"Low","2"}};
  static const std::vector<Option> options={
    {"Resolution","resolution","720p",true,{{"Game default",""},{"1280 x 720","720p"},{"1920 x 1080","1080p"},{"2560 x 1440","1440p"},{"3840 x 2160","4k"}}},
    {"Display mode","fullscreen","false",false,{{"Windowed","false"},{"Fullscreen","true"}}},
    {"Texture quality","texture_detail_reduction","0",false,quality},
    {"Texture filtering","anisotropic_override","3",false,{{"Game default","-1"},{"Off","0"},{"2x","2"},{"4x","3"},{"8x","4"},{"16x","5"}}},
    {"Dynamic shadows","halo3mp_shadow_quality","0",false,quality},
    {"Object detail","halo3mp_object_quality","0",false,quality},
    {"Decoration distance","halo3mp_decorator_quality","0",false,{{"Original","0"},{"Medium","1"},{"Near","2"}}},
    {"Cosmetic effect distance","halo3mp_effect_quality","0",false,{{"Original","0"},{"Medium","1"},{"Near","2"}}},
    {"Water quality","halo3mp_water_quality","0",false,{{"Original","0"},{"Reduced","1"},{"Basic","2"}}},
    {"Extra anti-aliasing","swap_post_effect","none",true,{{"Off","none"},{"FXAA","fxaa"},{"Strong FXAA","fxaa_extreme"}}},
    {"Internal render scale","resolution_scale","1",true,{{"1x","1"},{"2x (4x pixels)","2"},{"3x (9x pixels)","3"}}},
  };
  return options;
}
PCSettings::PCSettings() {
  for(const auto& option:PCOptions()) values.push_back(rex::cvar::GetFlagByName(option.flag));
  saved_=values;
  startup_={values[0],values[9],values[10]};
}
void PCSettings::Defaults() {
  for(size_t i=0;i<values.size();++i) values[i]=PCOptions()[i].default_value;
}
void PCSettings::Preset(int index) {
  if(index<0||index>2)return;
  const auto level=std::to_string(2-index);
  values[2]=level;values[3]=index==0?"0":index==1?"2":"-1";
  for(size_t i=4;i<=8;++i)values[i]=level;
}
int PCSettings::PresetIndex() const {
  for(int p=0;p<3;++p){
    const auto level=std::to_string(2-p);
    if(values[2]!=level||values[3]!=(p==0?"0":p==1?"2":"-1"))continue;
    bool match=true;for(size_t i=4;i<=8;++i)match&=values[i]==level;
    if(match)return p;
  }
  return 3;
}
bool PCSettings::Dirty() const{return values!=saved_;}
bool PCSettings::RestartRequired() const{return values[0]!=startup_[0]||values[9]!=startup_[1]||values[10]!=startup_[2];}
void PCSettings::Cancel(){values=saved_;}
void PCSettings::Reload(){
  for(size_t i=0;i<values.size();++i)values[i]=rex::cvar::GetFlagByName(PCOptions()[i].flag);
  saved_=values;
}
bool PCSettings::Apply(const std::filesystem::path& path,std::string& error) {
  error.clear();
  std::vector<std::pair<std::string,std::string>> changes,previous;
  const auto& options=PCOptions();
  for(size_t i=0;i<options.size();++i){
    if(i==0 && !values[i].empty() && std::any_of(options[i].choices.begin(),options[i].choices.end(),[&](auto c){return values[i]==c.value;})){
      // Repair legacy dimensions even when the selected resolution is unchanged.
      changes.emplace_back("window_width","0");changes.emplace_back("window_height","0");
      changes.emplace_back("video_mode_width","1280");changes.emplace_back("video_mode_height","720");
    }
    if(values[i]==saved_[i])continue; // Preserve custom CLI values not offered by the menu.
    if(std::none_of(options[i].choices.begin(),options[i].choices.end(),[&](auto c){return values[i]==c.value;})){
      error="Invalid value for "+std::string(options[i].label);return false;
    }
    changes.emplace_back(options[i].flag,values[i]);
    if(i==0 && values[i].empty()){
      // A menu resolution selection supersedes legacy explicit window/video
      // dimensions; otherwise previously saved 1280x720 pins every choice.
      changes.emplace_back("window_width","0");changes.emplace_back("window_height","0");
      changes.emplace_back("video_mode_width","1280");changes.emplace_back("video_mode_height","720");
    }
    if(i==10){changes.emplace_back("draw_resolution_scale_x",values[i]);changes.emplace_back("draw_resolution_scale_y",values[i]);}
  }
  // Check the destination before any live setting changes. Publish by rename,
  // retaining the previous configuration if writing or replacement fails.
  auto temporary=path;temporary+=".video-pending";
  std::ofstream file(temporary,std::ios::binary|std::ios::trunc);
  if(!file){error="Unable to save video settings.";return false;}
  bool success=true;
  for(const auto& [flag,value]:changes){
    previous.emplace_back(flag,rex::cvar::GetFlagByName(flag));
    if(!rex::cvar::SetFlagByName(flag,value)){error="Unable to apply "+flag;success=false;break;}
  }
  if(success){
    file<<"# Spartan settings\n"<<rex::cvar::SerializeToTOML();
    file.flush();success=bool(file);file.close();success=success&&!file.fail();
    if(success)success=MoveFileExW(temporary.c_str(),path.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
    if(!success)error="Unable to save video settings; previous settings restored.";
  }
  if(!success){
    file.close();for(auto it=previous.rbegin();it!=previous.rend();++it)rex::cvar::SetFlagByName(it->first,it->second);
    std::error_code ec;std::filesystem::remove(temporary,ec);return false;
  }
  saved_=values;return true;
}
}
