#pragma once
// Read-only PM4 provenance for blend changes, saved only with bounded draw traces.
#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <rex/memory/ring_buffer.h>

namespace rex::graphics::sky_command_witness {
inline bool Enabled(){static const bool enabled=[](){
  const auto* value=std::getenv("OPENH3M_SKY_COMMAND_TRACE");
  return value&&std::strcmp(value,"1")==0;
}();return enabled;}
using Witness=std::array<uint64_t,16>;
inline thread_local Witness packet{};
inline thread_local std::array<Witness,4> blend{};
inline thread_local uint64_t writes=0;
struct Scope {
  Witness previous{};bool enabled=false;
  Scope(memory::RingBuffer* reader,const uint8_t* physical_base){
    enabled=Enabled();if(!enabled)return;
    previous=packet;packet={};
    const auto start=reader->read_offset();
    const uintptr_t at=reader->read_ptr(),base=reinterpret_cast<uintptr_t>(physical_base);
    packet[2]=at>=base&&at-base<0x20000000ull?at-base:UINT64_MAX;
    packet[3]=reader->read_count();
    const auto count=(std::min)(uint32_t(8),reader->read_count()/4);
    packet[4]=count;
    for(uint32_t i=0;i<count;++i){uint32_t value;
      std::memcpy(&value,reader->buffer()+(start+i*4)%reader->capacity(),4);
      packet[5+i]=std::byteswap(value);
    }
  }
  ~Scope(){if(enabled)packet=previous;}
};
inline void Write(uint32_t index,uint32_t value){
  if(index!=0x2201||!Enabled())return;
  for(unsigned i=3;i;--i)blend[i]=blend[i-1];
  blend[0]=packet;blend[0][0]=++writes;blend[0][1]=value;
}
}
