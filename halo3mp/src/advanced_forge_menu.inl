// Runtime-only adapter for the original H3 object-properties screen. No tag
// file, variant property, or original property row is replaced.
#include <rex/system/function_dispatcher.h>
namespace advanced_forge { namespace {
constexpr uint32_t kPhysicsProperty=0x00fe0001,kPhysicsHelp=0x00fe0005;
constexpr uint32_t kCoordinateProperty=0x00fe0100,kEditorRows=7;
struct NativePhysicsMenu {uint32_t screen,datum,row;std::array<CoordinateRange,2> ranges;};
std::unordered_map<uint32_t,NativePhysicsMenu> physicsMenus;
struct NumericPreview {
 uint32_t screen,datum;unsigned row;CoordinateSession::View original;
 // Cancel only the transform edited by event13, not intervening contact,
 // input, ownership or magnet state from the running editor.
 std::optional<std::array<uint8_t,52>> originalHeldTransform;
};
std::unordered_map<uint32_t,NumericPreview> numericPreviews;
void StoreUI(uint8_t* base,uint32_t address,uint32_t value){value=std::byteswap(value);std::memcpy(base+address,&value,4);}
uint32_t UICall(PPCContext& source,uint8_t* base,uint32_t address,std::initializer_list<uint32_t> args){
 auto call=source;
 PPCRegister* registers[]={&call.r3,&call.r4,&call.r5,&call.r6,&call.r7,&call.r8};
 unsigned i=0;for(auto value:args)registers[i++]->u64=value;
 auto* function=REX_KERNEL_STATE()->function_dispatcher()->GetFunction(address);
 if(!function)throw std::runtime_error("Missing native Forge UI function");
 function(call,base);return call.r3.u32;
}
uint32_t UIVirtual(PPCContext& ctx,uint8_t* base,uint32_t object,uint32_t offset,
                   std::initializer_list<uint32_t> args={}){
 auto call=ctx;call.r3.u64=object;
 PPCRegister* registers[]={&call.r4,&call.r5,&call.r6,&call.r7};
 unsigned i=0;for(auto value:args)registers[i++]->u64=value;
 auto* function=REX_KERNEL_STATE()->function_dispatcher()->GetFunction(U(base,U(base,object)+offset));
 if(!function)throw std::runtime_error("Missing native Forge datasource function");
 function(call,base);return call.r3.u32;
}
void UIText(uint8_t* base,uint32_t output,const char* text){
 // Native string callers provide a 1024-code-unit buffer. These labels/help
 // are bounded well below that capacity; encode the game's big-endian UTF-16.
 for(unsigned i=0;i<128;++i){uint16_t value=std::byteswap(uint16_t(static_cast<unsigned char>(text[i])));
  std::memcpy(base+output+i*2,&value,2);if(!text[i])return;}
}
const char* ModeText(PhysicsMode mode){
 return mode==PhysicsMode::Phased?"Phased":mode==PhysicsMode::Fixed?"Fixed":"Normal";
}
int PropertyRow(uint32_t sid){
 if(sid==kPhysicsProperty)return 0;
 return sid>=kCoordinateProperty&&sid<kCoordinateProperty+6?int(sid-kCoordinateProperty)+1:-1;
}
uint32_t PropertyID(unsigned row){return row?kCoordinateProperty+row-1:kPhysicsProperty;}
bool ExtraRow(const NativePhysicsMenu* menu,uint32_t row){return menu&&row>=menu->row&&row-menu->row<kEditorRows;}
bool MenuObject(PPCContext& ctx,uint8_t* base,uint32_t screen,uint32_t& datum){
 if(!enabled.load()||failed||!PhysicsWorld(ctx,base))return false;
 const auto slot=U(base,screen+0x1a8c);if(slot>=640)return false;
 datum=U(base,physicsEngine+0x1ac+slot*0x54);
 const auto pointer=ObjectPointer(base,physicsHeaders,datum);if(!pointer)return false;
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 const auto definition=TagDefinition(base,U(base,pointer));
 if((type!=6&&type!=10)||!definition||(H(base,definition+2)&(1u<<11))||U(base,pointer+0x10)!=0xffffffff)return false;
 auto it=physicsObjects.find(datum);
 if(it==physicsObjects.end()||!PhysicsValid(base,datum,it->second)){
  if(!(U(base,pointer+0xac)&kConnected))return false;
  physicsObjects[datum]={pointer,U(base,pointer),U(base,pointer+0xac),AuthoredPhysics(base,pointer),std::nullopt,false};
 }
 return true;
}
NativePhysicsMenu* MenuFor(uint8_t* base,uint32_t wrapper){
 auto it=physicsMenus.find(wrapper);
 if(it==physicsMenus.end()||U(base,wrapper)!=0x82056988||U(base,wrapper+12)!=it->second.screen)return nullptr;
 return &it->second;
}
PhysicsMode MenuMode(uint8_t* base,const NativePhysicsMenu& menu){
 auto it=physicsObjects.find(menu.datum);
 return it!=physicsObjects.end()&&PhysicsValid(base,menu.datum,it->second)?
     it->second.mode.value_or(it->second.authoredMode):PhysicsMode::Normal;
}
NativePhysicsMenu* ScreenMenu(uint8_t* base,uint32_t screen){
 for(auto& [wrapper,menu]:physicsMenus)if(menu.screen==screen&&MenuFor(base,wrapper))return &menu;
 return nullptr;
}
CoordinateSession::View MenuCoordinates(uint8_t* base,const NativePhysicsMenu& menu){
 const auto it=physicsObjects.find(menu.datum);
 if(it==physicsObjects.end()||!PhysicsValid(base,menu.datum,it->second))return {};
 const auto pointer=it->second.pointer;
 CoordinatePose current{Vec(base,pointer+0x54),Basis(Vec(base,pointer+0x60),Vec(base,pointer+0x6c))};
 coordinates.Update(physicsMap,menu.datum,current,*bridge);
 return coordinates.Read();
}
std::string MenuValue(uint8_t* base,const NativePhysicsMenu& menu,unsigned row){
 if(!row)return ModeText(MenuMode(base,menu));
 const auto view=MenuCoordinates(base,menu);

 const float value=row<=3?view.pose.position[row-1]:view.angles[row-4];
 return row<=3?fmt::format("{:.1f}",value):fmt::format("{:.0f}",value);
}
uint32_t MenuChoiceCount(const NativePhysicsMenu& menu,unsigned row){
 const auto& range=menu.ranges[row<=3?0:1];
 return uint32_t(std::lround((range.maximum-range.minimum)/range.step))+1;
}
uint32_t MenuChoice(uint8_t* base,const NativePhysicsMenu& menu,unsigned row){
 if(!row){const auto mode=MenuMode(base,menu);return mode==PhysicsMode::Normal?0:mode==PhysicsMode::Fixed?1:2;}
 const auto view=MenuCoordinates(base,menu);

 const auto& range=menu.ranges[row<=3?0:1];
 const float value=row<=3?view.pose.position[row-1]:view.angles[row-4];
 return uint32_t(std::clamp(std::lround((value-range.minimum)/range.step),0l,long(MenuChoiceCount(menu,row)-1)));
}
float NumericChoice(const NativePhysicsMenu& menu,unsigned row,uint32_t choice){
 const auto& range=menu.ranges[row<=3?0:1];
 return std::clamp(range.minimum+float(choice)*range.step,range.minimum,range.maximum);
}
NativePhysicsMenu* NumericMenu(uint8_t* base,uint32_t source,unsigned& row){
 if(!Ptr(source)||U(base,source)!=0x82056918)return nullptr;
 const auto property=PropertyRow(U(base,source+4));
 if(property<1||property>6)return nullptr;
 row=unsigned(property);
 // Only the custom native numeric sources use this otherwise unused word.
 return ScreenMenu(base,U(base,source+520));
}
void ShowNumericPose(PPCContext& ctx,uint8_t* base,uint32_t datum,const CoordinatePose& requested,
                     bool updateHeld=true){
 auto pose=requested;
 if(updateHeld){
  if(auto* editor=OwnedOriginalSceneryEditor(datum)){
   const auto selected=coordinates.Read();
   if(selected.datum!=datum)throw std::runtime_error("Coordinate editor selection changed");
   std::array<float,13> transform{};transform[0]=1;
   std::copy(pose.basis.begin(),pose.basis.end(),transform.begin()+1);
   std::copy(pose.position.begin(),pose.position.end(),transform.begin()+10);
   const auto applied=bridge->ApplyHeldCoordinatePose(*editor,datum,transform,NativeVariantBounds(base));
   std::copy_n(applied.begin()+1,9,pose.basis.begin());
   std::copy_n(applied.begin()+10,3,pose.position.begin());
   if(!coordinates.ReconcilePose(selected,pose,*bridge))
    throw std::runtime_error("Coordinate session changed during held update");
  }
 }
 auto call=ctx;call.r3.u32=datum;call.r7.u32=0;call.r8.u32=0;
 PoseArguments args(call,base,pose,true);
 // Use the original object transform function; no UI or saved-format substitute.
 __imp__sub_8232E8B8(call,base);
}
void FinishNumericPreview(PPCContext& ctx,uint8_t* base,uint32_t list,bool accept){
 auto it=numericPreviews.find(list);
 // Confirmation is delivered by the selected list-item widget, whereas
 // selection changes belong to its containing numeric list.
 if(it==numericPreviews.end()&&accept)
  it=numericPreviews.find(UICall(ctx,base,0x824a2918,{list}));
 if(it==numericPreviews.end()){
  if(accept)REXLOG_INFO("Advanced Forge preview confirmation has no list {:08X}",list);
  return;
 }
 const auto preview=it->second;numericPreviews.erase(it);
 uint32_t datum=0;
 if(!MenuObject(ctx,base,preview.screen,datum)||datum!=preview.datum){
  REXLOG_INFO("Advanced Forge preview finish discarded: selection changed, list {:08X}",list);return;
 }
 if(!coordinates.FinishPreview(preview.original,accept)){
  REXLOG_INFO("Advanced Forge preview finish discarded: session changed, list {:08X}",list);return;
 }
 if(!accept){
  if(preview.originalHeldTransform){
   auto* editor=OwnedOriginalSceneryEditor(datum);
   if(!editor)throw std::runtime_error("Coordinate preview lost held ownership");
   std::copy(preview.originalHeldTransform->begin(),preview.originalHeldTransform->end(),
             editor->bytes.begin()+84);
  }
  ShowNumericPose(ctx,base,datum,preview.original.pose,false);
  UICall(ctx,base,0x82284078,{0,datum});
 }
 REXLOG_INFO("Advanced Forge numeric preview {}: {:08X}",accept?"accepted":"cancelled",datum);
}
void PreviewNumericChoice(PPCContext& ctx,uint8_t* base,uint32_t list){
 const auto it=numericPreviews.find(list);if(it==numericPreviews.end())return;
 const auto preview=it->second;uint32_t datum=0;
 if(!MenuObject(ctx,base,preview.screen,datum)||datum!=preview.datum)return;
 const auto* menu=ScreenMenu(base,preview.screen);if(!menu)return;
 const auto choice=UICall(ctx,base,0x824fc850,{list});
 if(choice>=MenuChoiceCount(*menu,preview.row))return;
 const auto view=MenuCoordinates(base,*menu);
 if(view.generation!=preview.original.generation||view.map!=preview.original.map)return;
 auto position=view.pose.position,angles=view.angles;
 if(preview.row<=3)position[preview.row-1]=NumericChoice(*menu,preview.row,choice);
 else angles[preview.row-4]=NumericChoice(*menu,preview.row,choice);
 if(!coordinates.Queue(view,position,angles))return;
 const auto pose=coordinates.Update(physicsMap,datum,view.pose,*bridge);
 if(pose)ShowNumericPose(ctx,base,datum,*pose);
 REXLOG_INFO("Advanced Forge numeric preview: {:08X} row {} choice {}",datum,preview.row,choice);
}
void AddPhysicsMenu(PPCContext& ctx,uint8_t* base,uint32_t screen){
 uint32_t datum=0;if(!MenuObject(ctx,base,screen,datum))return;
 const auto count=U(base,screen+532);if(count>32-kEditorRows)return;
 uint32_t wrapper=0;
 for(uint32_t i=0;i<count;++i){auto source=U(base,screen+404+i*4);
  if(Ptr(source)&&U(base,source)==0x82056988&&U(base,source+12)==screen){wrapper=source;break;}}
 if(!wrapper)return;
 const auto underlying=U(base,wrapper+8);
 const auto rows=UIVirtual(ctx,base,underlying,0x6c);if(rows>64)return;
 Load();const auto ranges=bridge->CoordinateRanges();
 std::array<uint32_t,kEditorRows> sources{};
 for(unsigned row=0;row<kEditorRows;++row){
  const auto submenu=UICall(ctx,base,0x8249c140,{544,0,0});
  if(!Ptr(submenu)){
   for(auto source:sources)if(source)UICall(ctx,base,0x8249c238,{source});
   return;
  }
  sources[row]=submenu;std::memset(base+submenu,0,544);
  StoreUI(base,submenu,0x82056918);StoreUI(base,submenu+4,PropertyID(row));
  StoreUI(base,submenu+524,PropertyID(row));
  if(row>=1&&row<=6){StoreUI(base,submenu+520,screen);}
  else{
   const auto choices=3u;StoreUI(base,submenu+528,choices);
   constexpr uint32_t values[]={0,0x40,0xc0};
   for(unsigned i=0;i<choices;++i){
    StoreUI(base,submenu+268+i*8,values[i]);
    StoreUI(base,submenu+272+i*8,kPhysicsProperty+1+i);
   }
  }
 }
 // The screen owns this native allocation and destroys it with its existing
 // datasource list. The host registry owns only a non-owning screen identity.
 for(unsigned row=0;row<kEditorRows;++row)StoreUI(base,screen+404+(count+row)*4,sources[row]);
 StoreUI(base,screen+532,count+kEditorRows);
 physicsMenus[wrapper]={screen,datum,rows,ranges};
 REXLOG_INFO("Advanced Forge native editor rows: screen {:08X} object {:08X} first row {}",screen,datum,rows);
}
} }

#define AF_UI_IMPORT(name) extern "C" void __imp__##name(PPCContext& __restrict,uint8_t*)
AF_UI_IMPORT(sub_824C0140);AF_UI_IMPORT(sub_824C0128);AF_UI_IMPORT(sub_824C0110);
AF_UI_IMPORT(sub_824C00F8);AF_UI_IMPORT(sub_824F5148);AF_UI_IMPORT(sub_824F6970);
AF_UI_IMPORT(sub_824F6AC8);AF_UI_IMPORT(sub_824F6928);
AF_UI_IMPORT(sub_824F54B8);AF_UI_IMPORT(sub_824F5190);AF_UI_IMPORT(sub_821CF8C8);
AF_UI_IMPORT(sub_824F6268);AF_UI_IMPORT(sub_825040A8);AF_UI_IMPORT(sub_824C00B0);
AF_UI_IMPORT(sub_824FC6D0);AF_UI_IMPORT(sub_825017F0);

REX_HOOK_RAW(sub_824FC6D0){
 const auto list=ctx.r3.u32;
 const bool tracked=advanced_forge::numericPreviews.contains(list);
 const auto previous=tracked?advanced_forge::U(base,list+296):0;
 __imp__sub_824FC6D0(ctx,base);
 if(tracked&&previous!=advanced_forge::U(base,list+296)){
  try{advanced_forge::PreviewNumericChoice(ctx,base,list);}
  catch(const std::exception& e){REXLOG_ERROR("Advanced Forge numeric preview failed: {}",e.what());}
 }
}
// The native list-item close hides the expanded numeric list; it does not
// destroy it. Confirm removes the preview first; Back restores it here.
REX_HOOK_RAW(sub_825017F0){
 try{
  if(!advanced_forge::numericPreviews.empty()){
   const auto list=advanced_forge::UICall(ctx,base,0x824a2918,{ctx.r3.u32});
   if(advanced_forge::Ptr(list)&&base[list+0x13c])
    advanced_forge::FinishNumericPreview(ctx,base,list,false);
  }
 }
 catch(const std::exception& e){REXLOG_ERROR("Advanced Forge preview cancellation failed: {}",e.what());}
 __imp__sub_825017F0(ctx,base);
}

REX_HOOK_RAW(sub_824C0140){
 const bool extra=advanced_forge::MenuFor(base,ctx.r3.u32)!=nullptr;
 __imp__sub_824C0140(ctx,base);if(extra)ctx.r3.u64+=advanced_forge::kEditorRows;
}
REX_HOOK_RAW(sub_824C0128){
 const auto* menu=advanced_forge::MenuFor(base,ctx.r3.u32);
 const auto row=menu?menu->row:0xffffffff;
 __imp__sub_824C0128(ctx,base);if(ctx.r3.u32==0xffffffff)ctx.r3.u64=row;
}
REX_HOOK_RAW(sub_824C0110){
 const auto* menu=advanced_forge::MenuFor(base,ctx.r3.u32);
 if(advanced_forge::ExtraRow(menu,ctx.r4.u32)){
  ctx.r3.u64=ctx.r4.u32+1<menu->row+advanced_forge::kEditorRows?ctx.r4.u32+1:0xffffffff;return;
 }
 const auto row=menu?menu->row:0xffffffff;
 __imp__sub_824C0110(ctx,base);if(ctx.r3.u32==0xffffffff)ctx.r3.u64=row;
}
REX_HOOK_RAW(sub_824C00F8){
 const auto* menu=advanced_forge::MenuFor(base,ctx.r3.u32);
 if(advanced_forge::ExtraRow(menu,ctx.r4.u32)&&ctx.r4.u32>menu->row){ctx.r3.u64=ctx.r4.u32-1;return;}
 __imp__sub_824C00F8(ctx,base);
}
REX_HOOK_RAW(sub_824F5148){
 unsigned row=0;const auto* menu=advanced_forge::NumericMenu(base,ctx.r3.u32,row);
 if(menu){ctx.r3.u64=advanced_forge::MenuChoiceCount(*menu,row);return;}
 __imp__sub_824F5148(ctx,base);
}
REX_HOOK_RAW(sub_824F6970){
 unsigned row=0;const auto* menu=advanced_forge::NumericMenu(base,ctx.r3.u32,row);
 if(menu){
  if(ctx.r4.u32<advanced_forge::MenuChoiceCount(*menu,row)&&ctx.r5.u32==668){
   const auto value=advanced_forge::NumericChoice(*menu,row,ctx.r4.u32);
   const auto text=row<=3?fmt::format("{:.1f}",value):fmt::format("{:.0f}",value);
   advanced_forge::UIText(base,ctx.r6.u32,text.c_str());ctx.r3.u64=1;
  }else ctx.r3.u64=0;
  return;
 }
 __imp__sub_824F6970(ctx,base);
}
REX_HOOK_RAW(sub_824F6AC8){
 unsigned row=0;if(advanced_forge::NumericMenu(base,ctx.r3.u32,row)){ctx.r3.u64=0;return;}
 __imp__sub_824F6AC8(ctx,base);
}
REX_HOOK_RAW(sub_824F6928){
 unsigned row=0;const auto* menu=advanced_forge::NumericMenu(base,ctx.r3.u32,row);
 if(menu){
  if(ctx.r4.u32<advanced_forge::MenuChoiceCount(*menu,row)){
   advanced_forge::StoreUI(base,ctx.r5.u32,ctx.r4.u32);ctx.r3.u64=1;
  }else ctx.r3.u64=0;
  return;
 }
 __imp__sub_824F6928(ctx,base);
}
REX_HOOK_RAW(sub_824C00B0){
 if(advanced_forge::MenuFor(base,ctx.r3.u32)){
  // This virtual returns the visible row count, independently of selection.
  const auto object=ctx.r3.u32;
  ctx.r3.u64=advanced_forge::UIVirtual(ctx,base,object,0x14);return;
 }
 __imp__sub_824C00B0(ctx,base);
}
REX_HOOK_RAW(sub_824F54B8){
 const auto* menu=advanced_forge::MenuFor(base,ctx.r3.u32);
 if(advanced_forge::ExtraRow(menu,ctx.r4.u32)){
  if(ctx.r5.u32==668){advanced_forge::StoreUI(base,ctx.r6.u32,advanced_forge::PropertyID(ctx.r4.u32-menu->row));ctx.r3.u64=1;}
  else ctx.r3.u64=0;
  return;
 }
 __imp__sub_824F54B8(ctx,base);
}
REX_HOOK_RAW(sub_824F5190){
 const auto* menu=advanced_forge::MenuFor(base,ctx.r3.u32);
 if(advanced_forge::ExtraRow(menu,ctx.r4.u32)){
  if(ctx.r5.u32==266){
   const auto text=advanced_forge::MenuValue(base,*menu,ctx.r4.u32-menu->row);
   advanced_forge::UIText(base,ctx.r6.u32,text.c_str());
   ctx.r3.u64=1;
  }else ctx.r3.u64=0;
  return;
 }
 __imp__sub_824F5190(ctx,base);
}
REX_HOOK_RAW(sub_821CF8C8){
 if(spartan::video::PCVideoText(base,ctx.r4.u32,ctx.r5.u32)){ctx.r3.u64=1;return;}
 const auto sid=ctx.r4.u32;
 if(sid>=advanced_forge::kCoordinateProperty&&sid<advanced_forge::kCoordinateProperty+6){
  constexpr const char* labels[]={"Position X","Position Y","Position Z","Yaw","Pitch","Roll"};
  advanced_forge::UIText(base,ctx.r5.u32,labels[sid-advanced_forge::kCoordinateProperty]);ctx.r3.u64=1;return;
 }
 if(sid>=advanced_forge::kPhysicsProperty&&sid<=advanced_forge::kPhysicsHelp){
  constexpr const char* labels[]={"Physics","Normal","Fixed","Phased","Physics while editing. Saved maps use Halo 3 object physics."};
  advanced_forge::UIText(base,ctx.r5.u32,labels[sid-advanced_forge::kPhysicsProperty]);ctx.r3.u64=1;return;
 }
 __imp__sub_821CF8C8(ctx,base);
}
REX_HOOK_RAW(sub_825040A8){
 spartan::video::ForgetPCVideoSource(ctx.r3.u32);
 advanced_forge::physicsMenus.erase(ctx.r3.u32);
 __imp__sub_825040A8(ctx,base);
}
REX_HOOK_RAW(sub_824F6268){
 using namespace advanced_forge;
 const auto screen=ctx.r3.u32,list=ctx.r6.u32,source=ctx.r7.u32;
 const auto* main=MenuFor(base,source);
 const auto selectedRow=ctx.r5.u32==0x10539&&main?UIVirtual(ctx,base,list,0x14):0xffffffff;
 bool customMain=ExtraRow(main,selectedRow);
 const auto valueRow=ctx.r5.u32==0x10544&&Ptr(source)&&U(base,source)==0x82056918?PropertyRow(U(base,source+4)):-1;
 bool customValue=valueRow>=0;
 if(!customMain&&!customValue){__imp__sub_824F6268(ctx,base);return;}
 uint32_t datum=0;if(!MenuObject(ctx,base,screen,datum)){ctx.r3.u64=0;return;}
 const auto* menu=ScreenMenu(base,screen);
 if(!menu||menu->datum!=datum){ctx.r3.u64=0;return;}
 if(customMain){
  if(!(UIVirtual(ctx,base,list,0x1c)&255)){ctx.r3.u64=0;return;}
  const unsigned row=selectedRow-main->row;
  const auto choice=MenuChoice(base,*menu,row);
  const auto parent=UICall(ctx,base,0x824a2918,{list});
  UICall(ctx,base,0x824fcb30,{parent,0x10544,PropertyID(row),0});
  const auto submenu=UICall(ctx,base,0x824a3180,{screen,7,0x10544});
  if(submenu){
   UICall(ctx,base,0x824fc8f8,{submenu,choice,0});
   if(row>=1&&row<=6){
    const auto view=MenuCoordinates(base,*menu);
    if(coordinates.BeginPreview(view)){
     NumericPreview preview{screen,datum,row,view,std::nullopt};
     if(const auto* editor=OwnedOriginalSceneryEditor(datum)){
      preview.originalHeldTransform.emplace();
      std::copy_n(editor->bytes.begin()+84,52,preview.originalHeldTransform->begin());
     }
     numericPreviews[submenu]=std::move(preview);
     const auto item=UICall(ctx,base,0x824a30e8,{submenu});
     REXLOG_INFO("Advanced Forge preview list {:08X} item {:08X} close handler {:08X}",submenu,item,Ptr(item)?U(base,U(base,item)+0x6c):0);
    }
   }
  }
 }else{
  const auto choice=UIVirtual(ctx,base,list,0x14);
  const unsigned row=unsigned(valueRow);
  const auto count=row==0?3u:MenuChoiceCount(*menu,row);
  if(choice>=count){ctx.r3.u64=0;return;}
  constexpr PhysicsMode choices[]={PhysicsMode::Normal,PhysicsMode::Fixed,PhysicsMode::Phased};
  try{
   Load();auto& object=physicsObjects.at(datum);
   if(row){
    auto view=MenuCoordinates(base,*menu);
    auto position=view.pose.position,angles=view.angles;
    if(row<=3)position[row-1]=NumericChoice(*menu,row,choice);
    else if(row<=6)angles[row-4]=NumericChoice(*menu,row,choice);
    if(!coordinates.Queue(view,position,angles))throw std::runtime_error("Stale native coordinate selection");
    const auto applied=coordinates.Update(physicsMap,datum,view.pose,*bridge);
    if(applied)ShowNumericPose(ctx,base,datum,*applied);
    FinishNumericPreview(ctx,base,list,true);
    if(applied)UICall(ctx,base,0x82284078,{0,datum});
    coordinates.FinishMenuEdit();
    const auto result=coordinates.Read();
    REXLOG_INFO("Advanced Forge native coordinates selected: {:08X} row {} choice {} position {},{},{} angles {},{},{} locked {}",datum,row,choice,result.pose.position[0],result.pose.position[1],result.pose.position[2],result.angles[0],result.angles[1],result.angles[2],result.locked);
   }else{
   ChangeNativeSceneryPhysicsMode(ctx,base,datum,choices[choice]);
   physics.Publish(datum,*object.mode);
   REXLOG_INFO("Advanced Forge native Physics selected: {:08X} mode {:02X} flags {:08X} held {}",datum,static_cast<uint16_t>(*object.mode),U(base,object.pointer+0xac),PhysicsHeld(base,datum));
   }
  }catch(const std::exception& e){RestorePhysics(ctx,base);failed=true;REXLOG_ERROR("Advanced Forge native Physics failed: {}",e.what());}
  // Exactly the native submenu close/refresh operation, but deliberately no
  // call to 8227EEB0 (the serialized H3 property commit).
  UIVirtual(ctx,base,list,0x6c);
 }
 ctx.r3.u64=1;
}
#undef AF_UI_IMPORT
