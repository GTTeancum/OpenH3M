// Advanced Forge rows in Halo 3's object-properties screen. Runtime only: no
// tag, variant property or original row is replaced. Rows: physics mode,
// magnets, magnet strength, rotation snap, then the coordinate panel
// (spec 04 5: X, Y, Z, Pitch, Yaw, Roll; edits apply live, no restore on Back).
namespace advanced_forge { namespace {
constexpr uint32_t kRowProperty=0x00fe0100;
enum Row : unsigned {kPhysicsRow,kMagnetsRow,kStrengthRow,kSnapRow,kXRow,kYRow,kZRow,kPitchRow,kYawRow,kRollRow,kEditorRows};
constexpr const char* kRowLabels[kEditorRows]={"Physics","Magnets","Magnet Strength","Rotation Snap","X","Y","Z","Pitch","Yaw","Roll"};
struct EditorMenu {
 uint32_t screen,datum,row,player,rows;  // rows: 4, or all 10 when the piece is held
 forge::CoordinatePanel working,applied;  // spec 04 5.2 working / applied blocks
};
std::unordered_map<uint32_t,EditorMenu> editorMenus;
void StoreUI(uint8_t* base,uint32_t address,uint32_t value){PutU(base,address,value);}
uint32_t UICall(PPCContext& source,uint8_t* base,uint32_t address,std::initializer_list<uint32_t> args){
 auto call=source;
 PPCRegister* registers[]={&call.r3,&call.r4,&call.r5,&call.r6,&call.r7,&call.r8};
 unsigned i=0;for(auto value:args)registers[i++]->u64=value;
 auto* function=REX_KERNEL_STATE()->function_dispatcher()->GetFunction(address);
 if(!function)throw std::runtime_error("Missing native Forge UI function");
 function(call,base);return call.r3.u32;
}
uint32_t UIVirtual(PPCContext& ctx,uint8_t* base,uint32_t object,uint32_t offset,std::initializer_list<uint32_t> args={}){
 auto call=ctx;call.r3.u64=object;
 PPCRegister* registers[]={&call.r4,&call.r5,&call.r6,&call.r7};
 unsigned i=0;for(auto value:args)registers[i++]->u64=value;
 auto* function=REX_KERNEL_STATE()->function_dispatcher()->GetFunction(U(base,U(base,object)+offset));
 if(!function)throw std::runtime_error("Missing native Forge datasource function");
 function(call,base);return call.r3.u32;
}
void UIText(uint8_t* base,uint32_t output,const std::string& text){
 // Native callers provide a 1024-code-unit buffer; write big-endian UTF-16.
 const size_t n=std::min<size_t>(text.size(),127);
 for(size_t i=0;i<=n;++i){
  const uint16_t value=std::byteswap(uint16_t(i<n?static_cast<unsigned char>(text[i]):0));
  std::memcpy(base+output+i*2,&value,2);
 }
}
int PropertyRow(uint32_t sid){return sid>=kRowProperty&&sid<kRowProperty+kEditorRows?int(sid-kRowProperty):-1;}
uint32_t PropertyID(unsigned row){return kRowProperty+row;}
bool ExtraRow(const EditorMenu* menu,uint32_t row){return menu&&row>=menu->row&&row-menu->row<menu->rows;}
// The menu object must be a Forge scenery piece. The editor is the one holding
// it, else the local player's editor (preferences and physics apply anyway).
NativeEditorSlot* MenuEditor(PPCContext& ctx,uint8_t* base,uint32_t screen,uint32_t& datum){
 if(!enabled.load()||failed||!PhysicsWorld(ctx,base))return nullptr;
 const auto slot=U(base,screen+0x1a8c);if(slot>=640)return nullptr;
 datum=U(base,physicsEngine+0x1ac+slot*0x54);
 const auto pointer=ObjectPointer(base,physicsHeaders,datum);if(!pointer)return nullptr;
 const auto definition=TagDefinition(base,U(base,pointer));
 if(!SceneryType(ObjectType(base,datum))||!definition||(H(base,definition+2)&(1u<<11)))return nullptr;
 if(!(U(base,pointer+0xac)&kConnected)&&!physicsObjects.contains(datum))return nullptr;
 auto* owner=OwnedSceneryEditorSlot(datum);
 if(!owner){
  for(auto& slot:nativeEditors)if(slot.player!=kNone&&slot.editor){owner=&slot;break;}
  if(!owner)return nullptr;
 }
 CapturePhysics(base,datum,pointer);
 return owner;
}
EditorMenu* MenuFor(uint8_t* base,uint32_t wrapper){
 auto it=editorMenus.find(wrapper);
 if(it==editorMenus.end()||U(base,wrapper)!=0x82056988||U(base,wrapper+12)!=it->second.screen)return nullptr;
 return &it->second;
}
EditorMenu* ScreenMenu(uint8_t* base,uint32_t screen){
 for(auto& [wrapper,menu]:editorMenus)if(menu.screen==screen&&MenuFor(base,wrapper))return &menu;
 return nullptr;
}
forge::Editor* MenuHeldEditor(const EditorMenu& menu){
 auto* e=OwnedSceneryEditor(menu.datum);
 return e&&e->held==menu.datum?e:nullptr;
}
// The menu's editor for preferences (held editor, else the opening player's).
NativeEditorSlot* MenuSlot(const EditorMenu& menu){
 if(auto* slot=OwnedSceneryEditorSlot(menu.datum))return slot;
 const auto index=menu.player&65535;
 if(index<nativeEditors.size()&&nativeEditors[index].player==menu.player&&nativeEditors[index].editor)return &nativeEditors[index];
 return nullptr;
}
// Populate (spec 04 5.2): sandbox origin is zero for Halo 3 scenarios.
void PopulateMenu(EditorMenu& menu){
 if(auto* e=MenuHeldEditor(menu)){menu.working=forge::PopulateCoordinates(e->target,{});menu.applied=menu.working;}
}
forge::CoordinateRange RowRange(const EditorMenu& menu,unsigned row){
 if(row<=kZRow)return forge::PositionRange();
 const auto* e=MenuHeldEditor(menu);
 return forge::AngleRange(e?e->rotationSnapMode:0);
}
uint32_t RowChoiceCount(const EditorMenu& menu,unsigned row){
 switch(row){
  case kPhysicsRow:return 3;
  case kMagnetsRow:return 2;
  case kStrengthRow:return uint32_t(forge::tuning::kSnapRadiusFactor.size());
  case kSnapRow:return uint32_t(forge::tuning::kRotationSnapDegrees.size());
  default:return forge::RangeChoiceCount(RowRange(menu,row));
 }
}
float& PanelValue(forge::CoordinatePanel& p,unsigned row){
 switch(row){
  case kXRow:return p.position[0];case kYRow:return p.position[1];case kZRow:return p.position[2];
  case kPitchRow:return p.angles[1];case kYawRow:return p.angles[0];default:return p.angles[2];
 }
}
std::string ChoiceText(const EditorMenu& menu,unsigned row,uint32_t choice){
 static constexpr const char* physics[]={"Normal","Fixed","Phased"};
 static constexpr const char* strength[]={"Lowest","Low","Medium","High","Highest"};
 switch(row){
  case kPhysicsRow:return physics[std::min<uint32_t>(choice,2)];
  case kMagnetsRow:return choice?"On":"Off";
  case kStrengthRow:return strength[std::min<uint32_t>(choice,4)];
  case kSnapRow:{const int d=forge::tuning::kRotationSnapDegrees[std::min<uint32_t>(choice,5)];return d?fmt::format("{} Degrees",d):std::string("Off");}
  default:{
   const float v=forge::RangeChoice(RowRange(menu,row),choice);
   return row<=kZRow?fmt::format("{:.1f}",v):fmt::format("{:.0f}",v);
  }
 }
}
uint32_t CurrentChoice(PPCContext&,uint8_t* base,EditorMenu& menu,unsigned row){
 auto* slot=MenuSlot(menu);
 const forge::Editor* e=slot?&*slot->editor:nullptr;
 switch(row){
  case kPhysicsRow:{
   const auto it=physicsObjects.find(menu.datum);
   const auto mode=it!=physicsObjects.end()&&PhysicsValid(base,menu.datum,it->second)?ModeOf(it->second):forge::PhysicsMode::Normal;
   return mode==forge::PhysicsMode::Normal?0:mode==forge::PhysicsMode::Fixed?1:2;
  }
  case kMagnetsRow:return e&&e->magnetsEnabled?1:0;
  case kStrengthRow:return e?std::min<unsigned>(e->sensitivity,4):forge::tuning::kDefaultSensitivity;
  case kSnapRow:return e?e->rotationSnapMode:0;
  default:return forge::RangeIndex(RowRange(menu,row),PanelValue(menu.working,row));
 }
}
// Apply one choice. Coordinate rows commit live (spec 04 5.4-5.6).
void ApplyChoice(PPCContext& ctx,uint8_t* base,EditorMenu& menu,unsigned row,uint32_t choice){
 auto* slot=MenuSlot(menu);
 if(!slot)return;
 auto& e=*slot->editor;
 switch(row){
  case kPhysicsRow:{
   static constexpr forge::PhysicsMode modes[]={forge::PhysicsMode::Normal,forge::PhysicsMode::Fixed,forge::PhysicsMode::Phased};
   ChangeNativeSceneryPhysicsMode(ctx,base,menu.datum,modes[std::min<uint32_t>(choice,2)]);
   return;
  }
  case kMagnetsRow:{
   const bool on=choice!=0;
   if(on==e.magnetsEnabled)return;
   e.magnetsEnabled=on;
   // Enabling shows the held piece and target; disabling hides all (spec 04 6).
   ApplyVisibility(*slot,on?forge::UpdateVisibility(e,kNone,kNone):forge::UpdateVisibility(e,e.held,e.magnetTarget));
   if(!on)slot->shown.clear();
   return;
  }
  case kStrengthRow:e.sensitivity=std::min<uint32_t>(choice,4);return;
  case kSnapRow:e.rotationSnapMode=std::min<uint32_t>(choice,5);return;
  default:break;
 }
 // Coordinates apply only to the held piece (spec 04 5.5).
 if(!MenuHeldEditor(menu))return;
 PanelValue(menu.working,row)=forge::RangeChoice(RowRange(menu,row),choice);
 if(std::memcmp(&menu.working,&menu.applied,sizeof(menu.working))==0)return;
 const auto pose=forge::CommitCoordinates(menu.working,e.target.scale,{});
 forge::ApplyCoordinatePose(e,pose,NativeVariantBounds(base));
 menu.applied=menu.working;
}
void AddEditorMenu(PPCContext& ctx,uint8_t* base,uint32_t screen){
 uint32_t datum=0;auto* owner=MenuEditor(ctx,base,screen,datum);
 if(!owner)return;
 const bool held=owner->editor->held==datum&&owner->ownsMonitorContact;
 const unsigned extra=held?kEditorRows:kXRow;
 const auto count=U(base,screen+532);if(count>32-extra)return;
 uint32_t wrapper=0;
 for(uint32_t i=0;i<count;++i){auto source=U(base,screen+404+i*4);
  if(Ptr(source)&&U(base,source)==0x82056988&&U(base,source+12)==screen){wrapper=source;break;}}
 if(!wrapper)return;
 const auto underlying=U(base,wrapper+8);
 const auto rows=UIVirtual(ctx,base,underlying,0x6c);if(rows>64)return;
 std::array<uint32_t,kEditorRows> sources{};
 for(unsigned row=0;row<extra;++row){
  const auto submenu=UICall(ctx,base,0x8249c140,{544,0,0});
  if(!Ptr(submenu)){for(auto source:sources)if(source)UICall(ctx,base,0x8249c238,{source});return;}
  sources[row]=submenu;std::memset(base+submenu,0,544);
  StoreUI(base,submenu,0x82056918);StoreUI(base,submenu+4,PropertyID(row));
  StoreUI(base,submenu+524,PropertyID(row));StoreUI(base,submenu+520,screen);
 }
 for(unsigned row=0;row<extra;++row)StoreUI(base,screen+404+(count+row)*4,sources[row]);
 StoreUI(base,screen+532,count+extra);
 EditorMenu menu{screen,datum,rows,owner->player,extra,{},{}};
 PopulateMenu(menu);
 editorMenus[wrapper]=menu;
}
EditorMenu* NumericMenu(uint8_t* base,uint32_t source,unsigned& row){
 if(!Ptr(source)||U(base,source)!=0x82056918)return nullptr;
 const auto property=PropertyRow(U(base,source+4));
 if(property<0)return nullptr;
 row=unsigned(property);
 return ScreenMenu(base,U(base,source+520));
}
// Lists whose highlighted choice is applied live (coordinate rows).
std::unordered_map<uint32_t,std::pair<uint32_t,unsigned>> liveLists;  // list -> (screen,row)
} }

#define AF_UI_IMPORT(name) extern "C" void __imp__##name(PPCContext& __restrict,uint8_t*)
AF_UI_IMPORT(sub_824C0140);AF_UI_IMPORT(sub_824C0128);AF_UI_IMPORT(sub_824C0110);
AF_UI_IMPORT(sub_824C00F8);AF_UI_IMPORT(sub_824F5148);AF_UI_IMPORT(sub_824F6970);
AF_UI_IMPORT(sub_824F6AC8);AF_UI_IMPORT(sub_824F6928);
AF_UI_IMPORT(sub_824F54B8);AF_UI_IMPORT(sub_824F5190);AF_UI_IMPORT(sub_821CF8C8);
AF_UI_IMPORT(sub_824F6268);AF_UI_IMPORT(sub_825040A8);AF_UI_IMPORT(sub_824C00B0);
AF_UI_IMPORT(sub_824FC6D0);

// Highlight change in an open choice list: coordinate rows apply live.
REX_HOOK_RAW(sub_824FC6D0){
 const auto list=ctx.r3.u32;
 const auto tracked=advanced_forge::liveLists.find(list);
 const auto previous=tracked!=advanced_forge::liveLists.end()?advanced_forge::U(base,list+296):0;
 __imp__sub_824FC6D0(ctx,base);
 if(tracked==advanced_forge::liveLists.end()||previous==advanced_forge::U(base,list+296))return;
 try{
  auto* menu=advanced_forge::ScreenMenu(base,tracked->second.first);
  if(!menu)return;
  const auto choice=advanced_forge::UICall(ctx,base,0x824fc850,{list});
  if(choice<advanced_forge::RowChoiceCount(*menu,tracked->second.second))
   advanced_forge::ApplyChoice(ctx,base,*menu,tracked->second.second,choice);
 }catch(const std::exception& e){REXLOG_ERROR("Advanced Forge live coordinate failed: {}",e.what());}
}
REX_HOOK_RAW(sub_824C0140){
 const auto* menu=advanced_forge::MenuFor(base,ctx.r3.u32);
 const uint32_t extra=menu?menu->rows:0;
 __imp__sub_824C0140(ctx,base);ctx.r3.u64+=extra;
}
REX_HOOK_RAW(sub_824C0128){
 const auto* menu=advanced_forge::MenuFor(base,ctx.r3.u32);
 const auto row=menu?menu->row:0xffffffff;
 __imp__sub_824C0128(ctx,base);if(ctx.r3.u32==0xffffffff)ctx.r3.u64=row;
}
REX_HOOK_RAW(sub_824C0110){
 const auto* menu=advanced_forge::MenuFor(base,ctx.r3.u32);
 if(advanced_forge::ExtraRow(menu,ctx.r4.u32)){
  ctx.r3.u64=ctx.r4.u32+1<menu->row+menu->rows?ctx.r4.u32+1:0xffffffff;return;
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
 if(menu){ctx.r3.u64=advanced_forge::RowChoiceCount(*menu,row);return;}
 __imp__sub_824F5148(ctx,base);
}
REX_HOOK_RAW(sub_824F6970){
 unsigned row=0;const auto* menu=advanced_forge::NumericMenu(base,ctx.r3.u32,row);
 if(menu){
  if(ctx.r4.u32<advanced_forge::RowChoiceCount(*menu,row)&&ctx.r5.u32==668){
   advanced_forge::UIText(base,ctx.r6.u32,advanced_forge::ChoiceText(*menu,row,ctx.r4.u32));ctx.r3.u64=1;
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
  if(ctx.r4.u32<advanced_forge::RowChoiceCount(*menu,row)){advanced_forge::StoreUI(base,ctx.r5.u32,ctx.r4.u32);ctx.r3.u64=1;}
  else ctx.r3.u64=0;
  return;
 }
 __imp__sub_824F6928(ctx,base);
}
REX_HOOK_RAW(sub_824C00B0){
 if(advanced_forge::MenuFor(base,ctx.r3.u32)){ctx.r3.u64=advanced_forge::UIVirtual(ctx,base,ctx.r3.u32,0x14);return;}
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
// Row value text.
REX_HOOK_RAW(sub_824F5190){
 auto* menu=advanced_forge::MenuFor(base,ctx.r3.u32);
 if(advanced_forge::ExtraRow(menu,ctx.r4.u32)){
  if(ctx.r5.u32==266){
   const unsigned row=ctx.r4.u32-menu->row;
   advanced_forge::UIText(base,ctx.r6.u32,advanced_forge::ChoiceText(*menu,row,advanced_forge::CurrentChoice(ctx,base,*menu,row)));
   ctx.r3.u64=1;
  }else ctx.r3.u64=0;
  return;
 }
 __imp__sub_824F5190(ctx,base);
}
// Row labels.
REX_HOOK_RAW(sub_821CF8C8){
 if(spartan::video::PCVideoText(base,ctx.r4.u32,ctx.r5.u32)){ctx.r3.u64=1;return;}
 const auto row=advanced_forge::PropertyRow(ctx.r4.u32);
 if(row>=0){advanced_forge::UIText(base,ctx.r5.u32,advanced_forge::kRowLabels[row]);ctx.r3.u64=1;return;}
 __imp__sub_821CF8C8(ctx,base);
}
REX_HOOK_RAW(sub_825040A8){
 spartan::video::ForgetPCVideoSource(ctx.r3.u32);
 advanced_forge::editorMenus.erase(ctx.r3.u32);
 advanced_forge::liveLists.erase(ctx.r3.u32);
 __imp__sub_825040A8(ctx,base);
}
// Row activation (open its choice list) and choice confirmation.
REX_HOOK_RAW(sub_824F6268){
 using namespace advanced_forge;
 const auto screen=ctx.r3.u32,list=ctx.r6.u32,source=ctx.r7.u32;
 const auto* main=MenuFor(base,source);
 const auto selectedRow=ctx.r5.u32==0x10539&&main?UIVirtual(ctx,base,list,0x14):0xffffffff;
 const bool customMain=ExtraRow(main,selectedRow);
 const auto valueRow=ctx.r5.u32==0x10544&&Ptr(source)&&U(base,source)==0x82056918?PropertyRow(U(base,source+4)):-1;
 const bool customValue=valueRow>=0;
 if(!customMain&&!customValue){__imp__sub_824F6268(ctx,base);return;}
 uint32_t datum=0;
 if(!MenuEditor(ctx,base,screen,datum)){ctx.r3.u64=0;return;}
 auto* menu=ScreenMenu(base,screen);
 if(!menu||menu->datum!=datum){ctx.r3.u64=0;return;}
 try{
  if(customMain){
   if(!(UIVirtual(ctx,base,list,0x1c)&255)){ctx.r3.u64=0;return;}
   const unsigned row=selectedRow-main->row;
   // Opening a page refreshes the panel from the held pose (spec 04 5.2).
   PopulateMenu(*menu);
   const auto choice=CurrentChoice(ctx,base,*menu,row);
   const auto parent=UICall(ctx,base,0x824a2918,{list});
   UICall(ctx,base,0x824fcb30,{parent,0x10544,PropertyID(row),0});
   const auto submenu=UICall(ctx,base,0x824a3180,{screen,7,0x10544});
   if(submenu){
    UICall(ctx,base,0x824fc8f8,{submenu,choice,0});
    if(row>=kXRow)liveLists[submenu]={screen,row};
   }
  }else{
   const auto choice=UIVirtual(ctx,base,list,0x14);
   const unsigned row=unsigned(valueRow);
   if(choice>=RowChoiceCount(*menu,row)){ctx.r3.u64=0;return;}
   ApplyChoice(ctx,base,*menu,row,choice);
   liveLists.erase(list);
   // Close the choice list without Halo 3's serialized property commit.
   UIVirtual(ctx,base,list,0x6c);
  }
 }catch(const std::exception& e){Fail(ctx,base,"menu choice",e);}
 ctx.r3.u64=1;
}
#undef AF_UI_IMPORT
