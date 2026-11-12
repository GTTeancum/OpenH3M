#include "forge_original.h"
#include <algorithm>
#include <iostream>
#include <vector>
#include <stdexcept>
namespace h4_forge_original { void sub_8244A538(PPCContext&,uint8_t*); }
int main() {
 try {
    std::vector<uint8_t> memory(0x20000,0);auto base=memory.data();int cases=0;
    for(int limit:{-1,0,1,32,254,255,256})
    for(int count:{0,1,31,32,254,255})
    for(int minimum:{0,1,31,32,254,255})
    for(int maximum:{0,1,31,32,254,255}) {
        REX_STORE_U8(0x1000,minimum);REX_STORE_U8(0x1001,maximum);REX_STORE_U8(0x1002,count);
        REX_STORE_U8(0xfff,0xA5);REX_STORE_U8(0x1003,0x5A);
        PPCContext c{};c.r1.u32=0x18000;c.r3.u32=0x1000;c.r4.s32=limit;
        h4_forge_original::sub_8244A538(c,base);
        int cap=(limit>0 && limit<=255)?limit:255;
        int expectedMax=std::min(std::max(maximum,count),std::max(cap,count));
        if(REX_LOAD_U8(0x1000)!=std::min(minimum,count) || REX_LOAD_U8(0x1001)!=expectedMax ||
           REX_LOAD_U8(0x1002)!=count || REX_LOAD_U8(0xfff)!=0xA5 || REX_LOAD_U8(0x1003)!=0x5A)
            throw std::runtime_error("quota clamp mismatch");
        ++cases;
    }
    std::cout<<"PASS "<<cases<<" original quota-clamp edge combinations. Count and adjacent bytes preserved; full lifecycle untested.\n";
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
