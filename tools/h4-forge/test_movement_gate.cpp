#include "forge_original.h"
#include <windows.h>
#include <array>
#include <bit>
#include <cmath>
#include <iostream>
#include <stdexcept>
static unsigned configResult, resolverCalls;
namespace h4_forge_original {
void sub_82582178(PPCContext&,uint8_t*);
void sub_82340E60(PPCContext& c,uint8_t*) {
    ++resolverCalls;
    if(c.r3.u32!=123 || c.r4.u32!=456) throw std::runtime_error("config resolver arguments");
    c.r3.u32=configResult;
}
}
int main() {
 try {
    auto base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ULL,MEM_RESERVE,PAGE_READWRITE));
    if(!base) throw std::runtime_error("reserve failed");
    auto storeFloat=[&](uint32_t address,float value){REX_STORE_U32(address,std::bit_cast<uint32_t>(value));};
    for(auto region: {std::array<size_t,2>{0,0x200000}, {0x82128000,0x2000}, {0x8405d000,0x1000}})
        if(!VirtualAlloc(base+region[0],region[1],MEM_COMMIT,PAGE_READWRITE)) throw std::runtime_error("commit failed");
    REX_STORE_U32(0x10000,0x11000);
    REX_STORE_U32(0x11000+24,0x20000);
    REX_STORE_U32(0x11000+4432,0x21000);
    REX_STORE_U32(0x20000+68,0x30000);
    REX_STORE_U32(0x21000+68,0x40000);
    REX_STORE_U32(0x30000+4144+36,2);
    REX_STORE_U32(0x40000+2*16+12,0x50000);
    storeFloat(0x821289e0+40,0.5f);
    int cases=0;
    // Four configuration paths: absent globals, invalid tag, null resolver, valid tag.
    for(int mode=0;mode<4;++mode) for(float threshold: {0.25f,0.5f,0.75f}) {
        REX_STORE_U32(0x8405d340,mode==0?0:0x60000);
        REX_STORE_U32(0x60000+504,mode==1?0xffffffff:456);
        REX_STORE_U32(0x60000+492,123);
        configResult=mode==3?0x70000:0;
        storeFloat(0x70000+36,threshold);
        float limit=mode==3?threshold:0.5f;
        for(int axis=0;axis<3;++axis) for(float magnitude: {0.0f,limit-0.01f,limit,limit+0.01f,-limit,-limit-0.01f}) {
            for(int j=0;j<3;++j) storeFloat(0x50000+1348+4*j,j==axis?magnitude:0.0f);
            PPCContext c{};c.r1.u32=0x180000;c.r13.u32=0x10000;c.r3.u32=0xABCD0001;
            c.r31.u64=0x123456789abcdef0ULL;c.lr=0x12345678;
            resolverCalls=0;
            h4_forge_original::sub_82582178(c,base);
            if(c.r3.u32!=(std::abs(magnitude)>limit) || c.r1.u32!=0x180000 ||
               c.r31.u64!=0x123456789abcdef0ULL || c.lr!=0x12345678 ||
               resolverCalls!=(mode>=2?1u:0u)) throw std::runtime_error("movement gate mismatch");
            ++cases;
        }
    }
    // Two components individually below the threshold still combine to exceed it.
    REX_STORE_U32(0x8405d340,0);
    storeFloat(0x50000+1348,0.4f);storeFloat(0x50000+1352,0.4f);storeFloat(0x50000+1356,0);
    PPCContext c{};c.r1.u32=0x180000;c.r13.u32=0x10000;c.r3.u32=1;
    h4_forge_original::sub_82582178(c,base);
    if(c.r3.u32!=1) throw std::runtime_error("combined axes mismatch");
    std::cout<<"PASS "<<cases<<" original movement predicate cases plus combined axes. Exact threshold does not suppress alignment. Native input and detach sequences untested.\n";
    VirtualFree(base,0,MEM_RELEASE);
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
