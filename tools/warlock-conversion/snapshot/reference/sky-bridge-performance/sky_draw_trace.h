#pragma once
// Opt-in, bounded CPU-side draw evidence. Never modifies guest/render state.
#include <array>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <unordered_set>
#include <vector>
#include <windows.h>

namespace rex::graphics::d3d12 {
class SkyDrawTrace {
 public:
  static SkyDrawTrace& Get() { static SkyDrawTrace instance; return instance; }
  uint64_t ActiveSequence() const { return active_draw_ ? sequence_ : 0; }
  ~SkyDrawTrace() { Finish(4); }
  void Draw(uint64_t frame, const RegisterFile& regs, const Shader* vs,
            const Shader* ps, uint32_t primitive, uint32_t count,
            uint32_t index_address, uint32_t index_length, uint32_t index_format,
            uint32_t index_endian, memory::Memory* memory) {
    active_draw_=false;
    if (directory_.empty() || finished_) return;
    if (targets_only_ && (count!=28632 && count!=21858)) return;
    auto now = std::chrono::steady_clock::now();
    if (!file_) {
      if (now < poll_) return;
      poll_ = now + std::chrono::seconds(1);
      std::error_code ec;
      if (!std::filesystem::exists(directory_ / "arm", ec)) return;
      file_ = _wfopen((directory_ / "draws.bin").c_str(), L"wbx");
      if (!file_) { finished_ = true; return; }
      setvbuf(file_, nullptr, _IOFBF, 1024 * 1024);
      start_ = now; first_frame_ = frame;
      const uint32_t version[] = {1, RegisterFile::kRegisterCount};
      Packet(0, version, sizeof(version));
    }
    if (frame - first_frame_ >= 300 || now - start_ >= std::chrono::seconds(15)) {
      Finish(1); return;
    }
    if (bytes_ >= 512ull * 1024 * 1024) { Finish(2); return; }
    Program(vs); Program(ps);
    active_draw_=true;
    const uint64_t header[] = {++sequence_, frame,
      uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(now-start_).count()),
      vs ? vs->ucode_data_hash() : 0, ps ? ps->ucode_data_hash() : 0,
      primitive, count, index_address, index_length, index_format, index_endian};
    Packet(1, header, sizeof(header));
    changes_.clear();
    for (uint32_t i = 0; i < RegisterFile::kRegisterCount; ++i) {
      if (sequence_ == 1 || previous_[i] != regs[i]) {
        changes_.push_back(i); changes_.push_back(regs[i]); previous_[i] = regs[i];
      }
    }
    Packet(2, changes_.data(), uint32_t(changes_.size() * 4));
    // CPU-visible byte prefixes identify buffers, not GPU-resolved texture content.
    Prefix(index_address, index_length, memory);
    for (uint32_t i = targets_only_ ? 95 : 0; i < 96; ++i) {
      const uint32_t at = 0x4800 + i * 2;
      if ((regs[at] & 3) == 3) {
        Prefix((regs[at] >> 2) << 2, ((regs[at+1] >> 2) & 0xffffff) * 4, memory);
      }
    }
    if (file_ && frame != last_frame_) { fflush(file_); last_frame_ = frame; }
  }
  void Emitted(uint64_t frame) {
    if (file_ && active_draw_) { const uint64_t row[] = {sequence_, frame}; Packet(5, row, sizeof(row)); }
    active_draw_=false;
  }
 private:
  SkyDrawTrace() {
    const auto* targets=_wgetenv(L"OPENH3M_SKY_TRACE_TARGETS");
    targets_only_=targets && wcscmp(targets,L"1")==0;
    const wchar_t* requested = _wgetenv(L"OPENH3M_SKY_TRACE_DIR");
    if (!requested || !*requested) return;
    std::error_code ec;
    auto root = std::filesystem::canonical(
      L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge", ec);
    if (ec) return;
    auto dir = std::filesystem::canonical(requested, ec);
    if (ec || dir == root) return;
    auto relative = dir.lexically_relative(root);
    if (relative.empty() || relative.is_absolute()) return;
    for (auto& part : relative) if (part == L"..") return;
    directory_ = dir;
    changes_.reserve(RegisterFile::kRegisterCount * 2);
  }
  void Packet(uint32_t kind, const void* data, uint32_t size) {
    if (!file_) return;
    const uint32_t header[] = {kind, size};
    if (fwrite(header, 1, 8, file_) != 8 || fwrite(data, 1, size, file_) != size) {
      fclose(file_); file_ = nullptr; finished_ = true; return;
    }
    bytes_ += 8 + size;
  }
  void Program(const Shader* shader) {
    if (!shader || !programs_.insert(shader->ucode_data_hash()).second) return;
    const uint64_t header[] = {shader->ucode_data_hash(), uint64_t(shader->type())};
    Packet(3, header, sizeof(header));
    Packet(4, shader->ucode_dwords(), uint32_t(shader->ucode_dword_count()*4));
  }
  void Prefix(uint32_t address, uint32_t length, memory::Memory* memory) {
    if (!address || !length || address >= 0x20000000) return;
    const uint32_t size = (std::min)({length, uint32_t(512), 0x20000000u-address});
    std::array<uint8_t, 512> data{};
    SIZE_T read = 0;
    if (!ReadProcessMemory(GetCurrentProcess(), memory->TranslatePhysical(address),
                           data.data(), size, &read) || read != size) return;
    uint64_t hash = 14695981039346656037ull;
    for (uint32_t i=0; i<size; ++i) hash = (hash ^ data[i]) * 1099511628211ull;
    hash ^= uint64_t(address) << 32;
    if (!prefixes_.insert(hash).second) return;
    const uint64_t header[] = {sequence_, address, length, size};
    Packet(6, header, sizeof(header)); Packet(7, data.data(), size);
  }
  void Finish(uint64_t reason) {
    if (file_) { Packet(9, &reason, sizeof(reason)); if (file_) fclose(file_); file_=nullptr; }
    finished_ = true;
  }
  std::filesystem::path directory_;
  FILE* file_ = nullptr;
  bool finished_ = false;
  bool targets_only_=false,active_draw_=false;
  uint64_t sequence_=0, first_frame_=0, last_frame_=0, bytes_=0;
  std::chrono::steady_clock::time_point start_, poll_;
  std::array<uint32_t, RegisterFile::kRegisterCount> previous_{};
  std::vector<uint32_t> changes_;
  std::unordered_set<uint64_t> programs_, prefixes_;
};
}  // namespace rex::graphics::d3d12
