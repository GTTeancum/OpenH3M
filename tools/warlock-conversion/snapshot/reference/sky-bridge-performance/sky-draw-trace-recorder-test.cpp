#include <algorithm>
#include <chrono>
#include <cstdint>
#include <vector>
namespace rex::memory {
struct Memory { uint8_t* TranslatePhysical(uint32_t) { return nullptr; } };
}
namespace rex::graphics {
struct RegisterFile {
  static constexpr uint32_t kRegisterCount = 0x5003;
  uint32_t values[kRegisterCount]{};
  uint32_t operator[](uint32_t i) const { return values[i]; }
};
struct Shader {
  std::vector<uint32_t> code{0x11223344, 0xaabbccdd};
  uint64_t ucode_data_hash() const { return 123; }
  uint32_t type() const { return 0; }
  const uint32_t* ucode_dwords() const { return code.data(); }
  size_t ucode_dword_count() const { return code.size(); }
};
}
#include "sky_draw_trace.h"
int main() {
  rex::graphics::RegisterFile regs;
  rex::graphics::Shader shader;
  rex::memory::Memory memory;
  auto& trace = rex::graphics::d3d12::SkyDrawTrace::Get();
  trace.Draw(20, regs, &shader, nullptr, 4, 6, 0, 0, 0, 0, &memory);
  trace.Emitted(20);
  regs.values[0x4400] = 0x3f800000;
  trace.Draw(21, regs, &shader, nullptr, 4, 6, 0, 0, 0, 0, &memory);
  trace.Emitted(21);
  trace.Draw(320, regs, &shader, nullptr, 4, 6, 0, 0, 0, 0, &memory);
  trace.Emitted(320);
}

