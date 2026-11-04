#pragma once
// Opt-in, process-local reproduction of the user-recorded view. Not a game fix.
#include <array>
#include <atomic>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string_view>

extern "C" void __imp__sub_8232F3D8(PPCContext&, uint8_t*);
extern "C" void __imp__sub_8232E8B8(PPCContext&, uint8_t*);
extern "C" void __imp__sub_82598838(PPCContext&, uint8_t*);
extern "C" void __imp__sub_8213BC50(PPCContext&, uint8_t*);
namespace sky_reproduction {
inline uint32_t U(const uint8_t* base,uint32_t at) {
  uint32_t v;std::memcpy(&v,base+at,4);return std::byteswap(v);
}
inline uint16_t H(const uint8_t* base,uint32_t at) {
  uint16_t v;std::memcpy(&v,base+at,2);return std::byteswap(v);
}
inline bool Ptr(uint32_t at) {return at>=0x10000&&at<0xc0000000;}
inline float F(const uint8_t* base,uint32_t at) {return std::bit_cast<float>(U(base,at));}
inline void Put(uint8_t* base,uint32_t at,float value) {
  auto bits=std::byteswap(std::bit_cast<uint32_t>(value));std::memcpy(base+at,&bits,4);
}
class Reproduction {
 public:
  static Reproduction& Get(){static Reproduction instance;return instance;}
  bool World(const PPCContext& ctx,uint8_t* base,uint32_t& tls) {
    if(directory_.empty()||rex::cvar::GetFlagByName("input_state_replay").empty()||!Ptr(ctx.r13.u32))return false;
    tls=U(base,ctx.r13.u32);if(!Ptr(tls))return false;
    const auto game=U(base,tls+0x80);if(!Ptr(game))return false;
    return std::string_view(reinterpret_cast<char*>(base+game+0x34),260).find("sky_bridge")!=std::string_view::npos;
  }
  uint32_t Object(uint8_t* base,uint32_t tls,uint32_t datum) {
    if(datum==0xffffffff)return 0;
    const auto table=U(base,tls+0xa8);if(!Ptr(table))return 0;
    if((datum&65535)>=U(base,table+0x20))return 0;
    const auto headers=U(base,table+0x44);if(!Ptr(headers))return 0;
    const auto header=headers+(datum&65535)*16;
    const auto object=U(base,header+12);
    return H(base,header)==datum>>16&&Ptr(object)?object:0;
  }
  void Created(PPCContext& ctx,uint8_t* base) {
    uint32_t tls;if(!World(ctx,base,tls))return;
    const uint32_t datum=ctx.r3.u32,object=Object(base,tls,datum);
    if(!object||U(base,object+0x10)!=0xffffffff)return;
    const auto tag=U(base,object);
    bool vehicle=tag==vehicle_tag_&&vehicle_.load()==0xffffffff;
    bool player=tag==player_tag_&&player_.load()==0xffffffff;
    if(!vehicle&&!player)return;
    std::array<float,9> pose=vehicle_pose_;
    if(player){
      // Stand beside the driver; native RB interaction performs seat entry.
      pose[0]-=vehicle_pose_[4]*.8f;pose[1]+=vehicle_pose_[3]*.8f;pose[2]+=.35f;
      pose[3]=vehicle_pose_[3];pose[4]=vehicle_pose_[4];pose[5]=0;
      const float n=std::sqrt(pose[3]*pose[3]+pose[4]*pose[4]);pose[3]/=n;pose[4]/=n;
      pose[6]=pose[7]=0;pose[8]=1;
    }
    // Native object_set_position wrapper, at the original creation call site.
    // Use a private guest-stack frame and restore its input storage afterward.
    PPCContext call=ctx;call.r1.u32-=0x200;
    const uint32_t scratch=call.r1.u32+0x100;
    std::array<uint8_t,36> saved;std::memcpy(saved.data(),base+scratch,saved.size());
    for(unsigned i=0;i<9;++i)Put(base,scratch+i*4,pose[i]);
    call.r3.u32=datum;call.r4.u32=scratch;call.r5.u32=scratch+12;call.r6.u32=scratch+24;
    call.r7.u32=0;call.r8.u32=0;
    __imp__sub_8232E8B8(call,base);
    std::memcpy(base+scratch,saved.data(),saved.size());
    if(vehicle)vehicle_=datum;else player_=datum;
    REXLOG_INFO("[sky-repro] placed {} {:08X} tag {:08X} position {},{},{}",vehicle?"vehicle":"player",datum,tag,
                F(base,object+0x54),F(base,object+0x58),F(base,object+0x5c));
  }
  void Camera(PPCContext& ctx,uint8_t* base) {
    uint32_t tls;if(!World(ctx,base,tls))return;
    const auto player=Object(base,tls,player_.load()),vehicle=Object(base,tls,vehicle_.load());
    if(!player||!vehicle)return;
    // Native observer globals: sub_82098CD0 proves TLS+716, user stride
    // 968, and result at +4+268. TLS+604 is a different allocation.
    const auto observer=U(base,tls+0x2cc);if(!Ptr(observer))return;
    const auto camera=observer+0x110;
    const bool seated=U(base,player+0x10)==vehicle_.load();
    float error=0;
    for(unsigned i=0;i<3;++i){const float d=F(base,vehicle+0x54+i*4)-vehicle_pose_[i];error+=d*d;}
    if(seated){
      // Exact diagnostic camera, including static BSP/cluster location. This
      // affects only the opted-in test process, and does not freeze simulation.
      std::memcpy(base+camera,observer_result_.data(),observer_result_.size());
      // Native suspension settles the fresh vehicle 0.025 units from the
      // recorded pose; retain and report that measured difference.
      stable_=error<.0009f?stable_+1:0;
      if(stable_==60){std::ofstream(directory_/"arm").put('\n');REXLOG_INFO("[sky-repro] stable seated view armed");}
    }
    if(++frames_%60==0)REXLOG_INFO("[sky-repro] view seated={} vehicle_error={} camera={},{},{} parent={:08X}",
      seated,std::sqrt(error),F(base,camera),F(base,camera+4),F(base,camera+8),U(base,player+0x10));
  }
  void Input(PPCContext& ctx,uint8_t* base,uint32_t user,uint32_t destination) {
    uint32_t tls;
    if(user!=0||ctx.r3.u32!=0||!Ptr(destination)||!World(ctx,base,tls))return;
    const auto player=Object(base,tls,player_.load()),vehicle=Object(base,tls,vehicle_.load());
    const auto observer=U(base,tls+0x2cc);
    if(!player||!vehicle||!Ptr(observer))return;
    const auto camera=observer+0x110;
    std::memset(base+destination+4,0,12);
    const uint32_t packet=std::byteswap(++input_packets_);std::memcpy(base+destination,&packet,4);
    if(U(base,player+0x10)==vehicle_.load())return;
    const float x=F(base,vehicle+0x20)-F(base,camera),y=F(base,vehicle+0x24)-F(base,camera+4);
    const float fx=F(base,camera+0x28),fy=F(base,camera+0x2c);
    const float yaw_error=std::atan2(fx*y-fy*x,fx*x+fy*y);
    int16_t rx=0;uint16_t buttons=0;
    if(std::sqrt(x*x+y*y)<1.7f){
      if(std::abs(yaw_error)>.08f)
        // The measured 0.30 stick value turns only about 0.025 rad/s after
        // the game's dead zone. Keep the feedback turn outside that range.
        rx=int16_t(-std::copysign(std::clamp(std::abs(yaw_error)*.65f,.55f,.7f),yaw_error)*32767);
      else {
        const auto now=std::chrono::steady_clock::now();
        if(now>entry_pulse_+std::chrono::seconds(3))entry_pulse_=now;
        if(now<entry_pulse_+std::chrono::seconds(2))buttons=0x200;
      }
    }
    auto be_buttons=std::byteswap(buttons);auto be_rx=std::byteswap(uint16_t(rx));
    std::memcpy(base+destination+4,&be_buttons,2);std::memcpy(base+destination+12,&be_rx,2);
    if(input_packets_%30==0)REXLOG_INFO("[sky-repro] entry yaw_error={} right_x={} buttons={:04X}",yaw_error,rx,buttons);
  }
 private:
  Reproduction(){
    const auto requested=_wgetenv(L"OPENH3M_SKY_REPRO_DIR");if(!requested||!*requested)return;
    std::error_code ec;
    auto root=std::filesystem::canonical(L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge",ec);if(ec)return;
    auto directory=std::filesystem::canonical(requested,ec);if(ec||directory==root)return;
    auto relative=directory.lexically_relative(root);if(relative.empty()||relative.is_absolute())return;
    for(auto& part:relative)if(part==L"..")return;
    std::ifstream input(directory/"pose.bin",std::ios::binary);std::array<uint32_t,5> header{};
    input.read(reinterpret_cast<char*>(header.data()),sizeof(header));
    if(header[0]!=0x52594b53||header[1]!=1||header[2]!=1747)return;
    input.read(reinterpret_cast<char*>(observer_result_.data()),observer_result_.size());
    input.read(reinterpret_cast<char*>(vehicle_pose_.data()),sizeof(vehicle_pose_));
    if(!input||input.peek()!=std::ifstream::traits_type::eof())return;
    for(float v:vehicle_pose_)if(!std::isfinite(v))return;
    vehicle_tag_=header[3];player_tag_=header[4];directory_=directory;
    REXLOG_INFO("[sky-repro] diagnostic pose loaded; exclusive process-local replay required");
  }
  std::filesystem::path directory_;
  std::array<uint8_t,112> observer_result_{};
  std::array<float,9> vehicle_pose_{};
  uint32_t vehicle_tag_=0,player_tag_=0,frames_=0,stable_=0;
  uint32_t input_packets_=0;
  std::chrono::steady_clock::time_point entry_pulse_{};
  std::atomic<uint32_t> vehicle_{0xffffffff},player_{0xffffffff};
};
}
REX_HOOK_RAW(sub_8232F3D8){
  __imp__sub_8232F3D8(ctx,base);
  sky_reproduction::Reproduction::Get().Created(ctx,base);
}
REX_HOOK_RAW(sub_82598838){
  const uint32_t user=ctx.r3.u32,destination=ctx.r4.u32;
  __imp__sub_82598838(ctx,base);
  sky_reproduction::Reproduction::Get().Input(ctx,base,user,destination);
}
REX_HOOK_RAW(sub_8213BC50){
  // Observer update calls 82213198 (final basis) then 822136F0 (collision
  // position). Override only after both native stages have completed.
  __imp__sub_8213BC50(ctx,base);
  sky_reproduction::Reproduction::Get().Camera(ctx,base);
}
