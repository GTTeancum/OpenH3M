#include "pc_video_menu.h"
#include "pc_video_settings.h"
#include <rex/hook.h>
#include <rex/system/function_dispatcher.h>
#include <bit>
#include <cstring>
#include <cctype>
#include <optional>
#include <array>
#include <memory>
#include <unordered_map>

namespace spartan::video {
namespace {
constexpr uint32_t kLabel=0x00fd1000,kHelp=0x00fd1200,kValue=0x00fd2000,kTitle=0x00fd1300;
constexpr uint32_t kBrightness=0x101fb,kSidebarWidget=0x1010a;
uint32_t Word(uint8_t* b,uint32_t a){uint32_t v;std::memcpy(&v,b+a,4);return std::byteswap(v);}
void Store(uint8_t* b,uint32_t a,uint32_t v){v=std::byteswap(v);std::memcpy(b+a,&v,4);}
bool Ptr(uint32_t p){return p>=0x10000&&p<0xbffff000;}
uint32_t Call(PPCContext& original,uint8_t* base,uint32_t address,uint32_t a,
              uint32_t b=0,uint32_t c=0,uint32_t d=0){
 auto ctx=original;ctx.r3.u64=a;ctx.r4.u64=b;ctx.r5.u64=c;ctx.r6.u64=d;
 auto* fn=REX_KERNEL_STATE()->function_dispatcher()->GetFunction(address);
 if(!fn)return 0;fn(ctx,base);return ctx.r3.u32;
}
struct Page{uint32_t screen=0,sidebar=0,choices=0,wrapper=0,row=0;std::array<uint32_t,15> custom_sources{};};
std::unordered_map<uint32_t,Page> pages;
std::unique_ptr<PCSettings> settings;
std::filesystem::path config_path;
std::string status;
uint32_t focused_screen=0;
unsigned ExtraRows(){return unsigned(PCOptions().size())+4;}
Page* Screen(uint8_t* b,uint32_t s){
 auto it=pages.find(s);return it!=pages.end()&&Ptr(s)&&Word(b,s)==0x82053618?&it->second:nullptr;
}
std::optional<Page> Source(uint8_t* b,uint32_t source){
 for(auto& [key,p]:pages)if(Screen(b,key)){
  if(p.sidebar==source||p.wrapper==source)return p;
  for(unsigned i=0;i<p.custom_sources.size();++i)if(p.custom_sources[i]==source){auto copy=p;copy.row=i+1;copy.choices=source;return copy;}
 }
 return std::nullopt;
}
unsigned OptionRow(const Page& p){return p.row-2;}
bool Custom(const Page& p){return p.row>=1&&p.row<1+ExtraRows();}
unsigned ChoiceCount(const Page& p){
 if(p.row==1)return 3;
 if(p.row>=2&&OptionRow(p)<PCOptions().size())return unsigned(PCOptions()[OptionRow(p)].choices.size());
 return 1;
}
unsigned Selected(const Page& p){
 if(p.row==1)return std::min(settings->PresetIndex(),2);
 if(p.row>=2&&OptionRow(p)<PCOptions().size()){
  const auto i=OptionRow(p);const auto& choices=PCOptions()[i].choices;
  for(unsigned j=0;j<choices.size();++j)if(settings->values[i]==choices[j].value)return j;
 }
 return 0;
}
const char* Label(unsigned row){
 if(row==0)return "QUALITY PRESET";
 if(row<=PCOptions().size())return PCOptions()[row-1].label;
 switch(row-unsigned(PCOptions().size())){case 1:return "APPLY CHANGES";case 2:return "CANCEL CHANGES";default:return "RESTORE DEFAULTS";}
}
void Refresh(PPCContext& ctx,uint8_t* b,Page& p){
 auto list=Call(ctx,b,0x824a3180,p.screen,7,kSidebarWidget);
 if(Ptr(list)){auto row=Call(ctx,b,0x824fc850,list);if(row<1+ExtraRows()&&p.row!=row){p.row=row;REXLOG_INFO("PC video row {}",row);}}
 focused_screen=p.screen;
}
void CommitChoice(Page& p,unsigned choice){
 if(choice>=ChoiceCount(p))return;
 if(p.row<2+PCOptions().size())status.clear();
 if(p.row==1)settings->Preset(int(choice));
 else if(OptionRow(p)<PCOptions().size())settings->values[OptionRow(p)]=PCOptions()[OptionRow(p)].choices[choice].value;
 else{
  switch(OptionRow(p)-PCOptions().size()){
   case 0:if(settings->Apply(config_path,status))status=settings->RestartRequired()?"SAVED. RESTART REQUIRED FOR DISPLAY CHANGES.":"VIDEO SETTINGS SAVED.";break;
   case 1:settings->Cancel();status="UNAPPLIED CHANGES DISCARDED.";break;
   case 2:settings->Defaults();status="DEFAULTS SELECTED. CHOOSE APPLY TO SAVE.";break;
  }
 }
}
// Extend the loaded screen definition in guest memory only. Disc caches stay unchanged.
// Reuse stock list rows, value spinners, animations and fonts.
void PrepareLayout(PPCContext& ctx,uint8_t* b,uint32_t screen){
 const auto datum=Call(ctx,b,0x82496888,Word(b,screen+0x110));
 const auto table=Word(b,0x827f0f8c);if(datum==0xffffffff||!Ptr(table))return;
 const auto tag=Word(b,table+(datum&0xffff)*8+4);if(!Ptr(tag))return;
 auto groups=Word(b,tag+0x60);auto count=Word(b,tag+0x5c);if(!Ptr(groups)||count>16)return;
 auto rect=[&](uint32_t a,int top,int left,int bottom,int right){int vals[]={top,left,bottom,right};for(int i=0;i<4;++i){auto v=std::byteswap(uint16_t(vals[i]));std::memcpy(b+a+i*2,&v,2);}};
 for(unsigned i=0;i<count;++i){auto g=groups+i*108;
  const auto name=Word(b,g+20);
  if(name==kBrightness){Store(b,g+84,0);auto t=Word(b,g+76);if(Word(b,g+72)&&Ptr(t)){rect(t+28,388,54,438,780);rect(t+36,388,54,438,600);}}
  if(name==0x105b1){
   auto lists=Word(b,g+64);auto list_count=Word(b,g+60);
   if(list_count==3){
    auto extended=Call(ctx,b,0x8249c140,(list_count+ExtraRows())*128,0,0);
    if(Ptr(extended)){
     std::memcpy(b+extended,b+lists,list_count*128);
     // Extend this screen's sidebar using the stock row skin and animation.
     auto parent_datum=Word(b,lists+12);auto parent=Word(b,table+(parent_datum&0xffff)*8+4);
     if(Ptr(parent)){
      auto originals=Word(b,parent+0x48);auto rows=Call(ctx,b,0x8249c140,10*48,0,0);
      if(Ptr(rows)&&Ptr(originals)){
       for(unsigned j=0;j<10;++j){auto r=rows+j*48;std::memcpy(b+r,b+originals+std::min(j,6u)*48,48);if(j>=7)Store(b,r+4,0x00fd3000+j);rect(r+12,j*25,0,0,0);rect(r+20,j*25,0,0,0);}
       Store(b,extended+0x54,10);Store(b,extended+0x58,rows);
      }
     }

     for(unsigned j=0;j<ExtraRows();++j){auto l=extended+(list_count+j)*128;std::memcpy(b+l,b+lists+2*128,128);Store(b,l+20,kLabel+j);Store(b,l+60,kLabel+j);}
     Store(b,g+60,list_count+ExtraRows());Store(b,g+64,extended);
    }
   }
   auto texts=Word(b,g+76);for(unsigned j=0;j<Word(b,g+72);++j){auto t=texts+j*76;if(Word(b,t+20)==0x29d)Store(b,t+64,kTitle);}
  }
 }
}
void Attach(PPCContext& ctx,uint8_t* b,uint32_t screen){
 Page p;p.screen=screen;
 const auto count=Word(b,screen+0x214);if(count+ExtraRows()>32||!settings)return;
 for(unsigned i=0;i<count;++i){auto ds=Word(b,screen+0x194+i*4);if(!Ptr(ds))continue;
  if(Word(b,ds)==0x820536e8){p.wrapper=ds;p.sidebar=Word(b,ds+8);}
  else if(Word(b,ds+4)==kBrightness)p.choices=ds;
 }
 if(p.sidebar&&p.choices&&p.wrapper){
  for(unsigned i=0;i<ExtraRows();++i){
   auto ds=Call(ctx,b,0x8249c140,0x110,0,0);if(!Ptr(ds))return;
   std::memcpy(b+ds,b+p.choices,0x110);Store(b,ds+4,kLabel+i);Store(b,ds+0x108,0);
   p.custom_sources[i]=ds;auto n=Word(b,screen+0x214);Store(b,screen+0x194+n*4,ds);Store(b,screen+0x214,n+1);
  }
  pages[screen]=p;focused_screen=screen;settings->Reload();status.clear();
  REXLOG_INFO("Native PC video screen {:08X}: sidebar {:08X}, values {:08X}",screen,p.sidebar,p.choices);
 }
}
}
void InitializePCVideoMenu(const std::filesystem::path& path){config_path=path;settings=std::make_unique<PCSettings>();}
void ForgetPCVideoSource(uint32_t source){
 for(auto it=pages.begin();it!=pages.end();)if(it->second.sidebar==source||it->second.wrapper==source||it->second.choices==source)it=pages.erase(it);else ++it;
}
bool PCVideoText(uint8_t* base,uint32_t sid,uint32_t output){
 if(!Ptr(output))return false;
 std::string text;
 if(sid==0x23b5)text="Video";
 else if(sid==kTitle)text="VIDEO SETTINGS";
 else if(sid>=kValue&&sid<kValue+32*16){
  auto* active=Screen(base,focused_screen);if(!active)return false;auto row=*active;row.row=(sid-kValue)/16;auto choice=(sid-kValue)%16;
  if(row.row==1){constexpr const char* names[]={"PERFORMANCE","BALANCED","ORIGINAL","CUSTOM"};text=names[std::min(choice,3u)];}
  else if(OptionRow(row)<PCOptions().size()){const auto& o=PCOptions()[OptionRow(row)];if(choice>=o.choices.size())return false;text=o.choices[choice].label;}
  else text="";
 }
 else if(sid>=kLabel&&sid<kLabel+ExtraRows())text=Label(sid-kLabel);
 else if(sid==kHelp||sid==0x24ef||sid==0x24e3){
  auto* p=Screen(base,focused_screen);if(!p||!Custom(*p))return false;
  if(!status.empty())text=status;
  else if(p->row==2)
   text="Requires restart. Windows fit your desktop; fullscreen uses desktop size. Internal render scale controls scene detail.";
  else if(p->row>=2&&OptionRow(*p)<PCOptions().size()&&PCOptions()[OptionRow(*p)].restart)
   text="Requires a game restart. Choose APPLY CHANGES to save.";
  else text="Choose a value, then APPLY CHANGES to save. CANCEL CHANGES discards edits.";
 }else return false;
 if(sid!=kHelp&&sid!=0x24ef&&sid!=0x24e3)for(auto& c:text)c=char(std::toupper(static_cast<unsigned char>(c)));
 const auto size=std::min(text.size(),size_t(500));
 for(size_t i=0;i<=size;++i){uint16_t v=std::byteswap(uint16_t(i<size?static_cast<unsigned char>(text[i]):0));std::memcpy(base+output+i*2,&v,2);}return true;
}
}
#define PC_IMPORT(name) extern "C" void __imp__##name(PPCContext&,uint8_t*)
PC_IMPORT(sub_824D68F8);
PC_IMPORT(sub_824D6980);PC_IMPORT(sub_824B86F0);PC_IMPORT(sub_824B8C40);
PC_IMPORT(sub_824B8CD8);PC_IMPORT(sub_824B8D70);PC_IMPORT(sub_824B8E10);
PC_IMPORT(sub_824B8978);PC_IMPORT(sub_824B8B30);PC_IMPORT(sub_824B8A08);
PC_IMPORT(sub_824D6710);PC_IMPORT(sub_824D6B30);PC_IMPORT(sub_824D6E00);PC_IMPORT(sub_824D6C10);
using namespace spartan::video;
REX_HOOK_RAW(sub_824D68F8){PrepareLayout(ctx,base,ctx.r3.u32);__imp__sub_824D68F8(ctx,base);}
REX_HOOK_RAW(sub_824D6980){auto screen=ctx.r3.u32;__imp__sub_824D6980(ctx,base);Attach(ctx,base,screen);}
// Static native datasources supply the original list skins and navigation.
// Scope hooks to this screen's sidebar and one native spinner datasource per option.
// Brightness keeps its original datasource and behavior.
REX_HOOK_RAW(sub_824B86F0){auto source=Source(base,ctx.r3.u32);auto* p=source?&*source:nullptr;if(p&&ctx.r3.u32==p->sidebar){ctx.r3.u64=1+ExtraRows();return;}if(p&&ctx.r3.u32==p->choices&&Custom(*p)){ctx.r3.u64=ChoiceCount(*p);return;}__imp__sub_824B86F0(ctx,base);}
REX_HOOK_RAW(sub_824B8C40){auto source=Source(base,ctx.r3.u32);auto* p=source?&*source:nullptr;if(p&&(ctx.r3.u32==p->sidebar||Custom(*p))){ctx.r3.u64=ctx.r3.u32==p->sidebar?1+ExtraRows():ChoiceCount(*p);return;}__imp__sub_824B8C40(ctx,base);}
REX_HOOK_RAW(sub_824B8CD8){auto source=Source(base,ctx.r3.u32);auto* p=source?&*source:nullptr;if(p&&(ctx.r3.u32==p->sidebar||Custom(*p))){ctx.r3.u64=0;return;}__imp__sub_824B8CD8(ctx,base);}
REX_HOOK_RAW(sub_824B8D70){auto source=Source(base,ctx.r3.u32);auto* p=source?&*source:nullptr;if(p&&(ctx.r3.u32==p->sidebar||Custom(*p))){auto count=ctx.r3.u32==p->sidebar?1+ExtraRows():ChoiceCount(*p);ctx.r3.u64=ctx.r4.u32+1<count?ctx.r4.u32+1:0xffffffff;return;}__imp__sub_824B8D70(ctx,base);}
REX_HOOK_RAW(sub_824B8E10){auto source=Source(base,ctx.r3.u32);auto* p=source?&*source:nullptr;if(p&&(ctx.r3.u32==p->sidebar||Custom(*p))){ctx.r3.u64=ctx.r4.u32?ctx.r4.u32-1:0xffffffff;return;}__imp__sub_824B8E10(ctx,base);}
REX_HOOK_RAW(sub_824B8978){auto source=Source(base,ctx.r3.u32);auto* p=source?&*source:nullptr;if(p){if(ctx.r3.u32==p->sidebar&&ctx.r4.u32>=1)ctx.r4.u64=0;else if(ctx.r3.u32==p->choices&&Custom(*p))ctx.r4.u64=0;}__imp__sub_824B8978(ctx,base);}
REX_HOOK_RAW(sub_824B8B30){auto source=Source(base,ctx.r3.u32);auto* p=source?&*source:nullptr;if(p){
 if(ctx.r3.u32==p->sidebar&&ctx.r4.u32>=1&&ctx.r4.u32<1+ExtraRows()){
  if(ctx.r5.u32==0x29c||ctx.r5.u32==0x10006){Store(base,ctx.r6.u32,kLabel+ctx.r4.u32-1);ctx.r3.u64=1;return;}ctx.r4.u64=0;
 }else if(ctx.r3.u32==p->choices&&Custom(*p)&&ctx.r4.u32<ChoiceCount(*p)){
  if(ctx.r5.u32==0x29c||ctx.r5.u32==0x29e){Store(base,ctx.r6.u32,ctx.r5.u32==0x29c?kValue+p->row*16+ctx.r4.u32:kHelp);ctx.r3.u64=1;return;}
  ctx.r4.u64=0;
 }}__imp__sub_824B8B30(ctx,base);}
REX_HOOK_RAW(sub_824B8A08){auto source=Source(base,ctx.r3.u32);auto* p=source?&*source:nullptr;if(p&&ctx.r3.u32==p->choices&&Custom(*p)&&ctx.r4.u32<ChoiceCount(*p)&&ctx.r5.u32==0x10a){Store(base,ctx.r6.u32,ctx.r4.u32);ctx.r3.u64=1;return;}__imp__sub_824B8A08(ctx,base);}
REX_HOOK_RAW(sub_824D6710){auto source=Source(base,ctx.r3.u32);auto* p=source?&*source:nullptr;if(p&&ctx.r4.u32>=1&&ctx.r4.u32<1+ExtraRows()&&(ctx.r5.u32==0x10a||ctx.r5.u32==0x29e)){auto row=*p;row.row=ctx.r4.u32;Store(base,ctx.r6.u32,ctx.r5.u32==0x29e?kHelp:kValue+row.row*16+(row.row==1?unsigned(settings->PresetIndex()):Selected(row)));ctx.r3.u64=1;return;}__imp__sub_824D6710(ctx,base);}
REX_HOOK_RAW(sub_824D6B30){auto* p=Screen(base,ctx.r3.u32);if(p){Refresh(ctx,base,*p);if(Custom(*p)){ctx.r3.u64=Call(ctx,base,0x825024a8,p->screen,ctx.r4.u32);return;}}__imp__sub_824D6B30(ctx,base);}
REX_HOOK_RAW(sub_824D6E00){auto* p=Screen(base,ctx.r3.u32);if(p){Refresh(ctx,base,*p);if(Custom(*p)&&Word(base,ctx.r4.u32+0x40)==kLabel+p->row-1){Call(ctx,base,0x824fc9c0,ctx.r4.u32,0x10a,Selected(*p),0);return;}}__imp__sub_824D6E00(ctx,base);}
REX_HOOK_RAW(sub_824D6C10){auto* p=Screen(base,ctx.r3.u32);if(p){Refresh(ctx,base,*p);if(Custom(*p)){
 const auto event=ctx.r4.u32;
 if(Word(base,event+0x18)==13&&Word(base,event+0x1c)==0){
  auto sidebar_focus=Word(base,p->screen+0xd8);auto sidebar_list=Ptr(sidebar_focus)?Call(ctx,base,0x824a2918,sidebar_focus):0;
  if(Ptr(sidebar_list)&&Word(base,sidebar_list+0x40)==kSidebarWidget&&p->row>=2+PCOptions().size()){
   CommitChoice(*p,0);ctx.r3.u64=1;return;
  }

  auto focus=Word(base,p->screen+0xd8);auto list=Ptr(focus)?Call(ctx,base,0x824a2918,focus):0;
  if(Ptr(list)&&Word(base,list+0x40)==kLabel+p->row-1){auto choice=Call(ctx,base,0x824fc850,list);CommitChoice(*p,choice);if(Ptr(focus))Call(ctx,base,Word(base,Word(base,focus)+0x6c),focus);ctx.r3.u64=1;return;}
 }
 ctx.r3.u64=Call(ctx,base,0x82502ac0,p->screen,event);return;
 }}__imp__sub_824D6C10(ctx,base);}
#ifndef OPENH3M_ADVANCED_FORGE
PC_IMPORT(sub_821CF8C8);PC_IMPORT(sub_825040A8);
REX_HOOK_RAW(sub_821CF8C8){if(PCVideoText(base,ctx.r4.u32,ctx.r5.u32)){ctx.r3.u64=1;return;}__imp__sub_821CF8C8(ctx,base);}
REX_HOOK_RAW(sub_825040A8){ForgetPCVideoSource(ctx.r3.u32);__imp__sub_825040A8(ctx,base);}
#endif

