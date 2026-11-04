#include "sky_command_witness.h"
#include <cassert>
#include <cstdio>
int main(){
  using namespace rex::graphics::sky_command_witness;
  _putenv_s("OPENH3M_SKY_COMMAND_TRACE","1");
  std::array<uint32_t,16> storage{};
  for(unsigned i=0;i<storage.size();++i)storage[i]=std::byteswap(100u+i);
  auto* bytes=reinterpret_cast<uint8_t*>(storage.data());
  rex::memory::RingBuffer outer(bytes,64),inner(bytes+16,32);
  outer.set_read_offset(56);outer.set_write_offset(16);
  inner.set_read_offset(0);inner.set_write_offset(8);
  const auto saved=storage;
  {
    Scope first(&outer,bytes);
    assert(outer.read_offset()==56&&outer.write_offset()==16);
    assert(packet[2]==56&&packet[3]==24&&packet[4]==6);
    assert(packet[5]==114&&packet[6]==115&&packet[7]==100&&packet[10]==103);
    Write(0x2201,0x01010101);
    {
      Scope second(&inner,bytes);
      assert(packet[2]==16&&packet[4]==2&&packet[5]==104);
      Write(0x2201,0x00010001);
      assert(inner.read_offset()==0);
    }
    assert(packet[2]==56&&packet[5]==114);
    Write(0x2200,0x12345678);
    assert(writes==2&&blend[0][1]==0x10001&&blend[0][2]==16);
    assert(blend[1][1]==0x1010101&&blend[1][2]==56);
  }
  assert(packet==Witness{}&&storage==saved);
  assert(outer.read_offset()==56&&inner.read_offset()==0);
  std::puts("PASS: wrapped packet, nested buffer restoration, exact blend history, unchanged bytes/cursors");
}
