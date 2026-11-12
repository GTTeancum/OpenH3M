#include "forge_original.h"
#include <windows.h>
#include <iostream>
#include <stdexcept>
namespace h4_forge_original { void sub_8244A6A8(PPCContext&,uint8_t*); }
int main() {
 try {
    auto base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ULL,MEM_RESERVE,PAGE_READWRITE));
    if(!base || !VirtualAlloc(base,0x200000,MEM_COMMIT,PAGE_READWRITE) ||
       !VirtualAlloc(base+0x83625000,0x1000,MEM_COMMIT,PAGE_READWRITE)) throw std::runtime_error("memory allocation");
    REX_STORE_U32(0x10000,0x11000);
    REX_STORE_U32(0x11000+4432,0x20000);
    REX_STORE_U32(0x20000+68,0x30000);
    REX_STORE_U32(0x30000+16+12,0x40000);
    REX_STORE_U32(0x83625160,0x50000);
    REX_STORE_U32(0x50000+68,0x60000);
    REX_STORE_U32(0x60000+48,0x70000);
    REX_STORE_U32(0x70000+52,0x80000);
    REX_STORE_U32(0x70000+60+52,0x81000);
    int count=0;
    for(int type:{0,15}) for(int flag:{0,1}) for(int valid:{0,1})
    for(int instanceFlag:{0,1}) for(int bodies:{0,1,2}) for(int fixedBody:{0,1}) {
        REX_STORE_U8(0x40000+178,type);
        REX_STORE_U64(0x40000+256,flag?0x100:0);
        REX_STORE_U32(0x40000+240,valid?0:0xffffffff);
        REX_STORE_U32(0x60000+16,instanceFlag?0x80:0);
        REX_STORE_U32(0x60000+52,bodies);
        REX_STORE_U8(0x80000+232,4);
        REX_STORE_U8(0x81000+232,fixedBody?5:4);
        PPCContext c{};c.r13.u32=0x10000;c.r3.u32=1;
        h4_forge_original::sub_8244A6A8(c,base);
        // This is the blocking predicate: zero permits rotation in its caller.
        bool permits=type==0 && flag && valid &&
            (bodies==0 || (!instanceFlag && !(bodies==2 && fixedBody)));
        if(c.r3.u32!=unsigned(!permits)) throw std::runtime_error("rotation gate mismatch");
        ++count;
    }
    std::cout<<"PASS "<<count<<" original rotation gate cases. Two object types and selected body states covered; live physics and full rotation untested.\n";
    VirtualFree(base,0,MEM_RELEASE);
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
