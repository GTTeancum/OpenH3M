#pragma once
// Opt-in, bounded CPU-side draw evidence. Never modifies guest/render state.
#include <array>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <unordered_set>
#include <vector>
#include <windows.h>
#include "sky_command_witness.h"

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
    if(cylinder_only_){
      if(count!=1761&&count!=3522)return;
      const uint32_t address=regs[0x48be]&0xfffffffcu;
      if(!address||address>0x20000000u-512)return;
      std::array<uint8_t,512> bytes{};SIZE_T read=0;
      if(!ReadProcessMemory(GetCurrentProcess(),memory->TranslatePhysical(address),
          bytes.data(),bytes.size(),&read)||read!=bytes.size())return;
      uint64_t hash=14695981039346656037ull;
      for(auto value:bytes)hash=(hash^value)*1099511628211ull;
      // Native sLdT9894 meshes121/357, full SHA256 checked by offline decoder.
      if(hash!=15479487708123365866ull&&hash!=14777336781968831334ull)return;
    }
    if(model_only_){
      if(!vs)return;
      switch(vs->ucode_data_hash()){
        case 1802336714319958646ull:case 7141575655502862876ull:
        case 10556403050914701579ull:case 11600849241261448272ull:
        case 12627602885350085323ull:case 15518101065676308936ull:break;
        default:return;
      }
      const uint32_t address=regs[0x48be]&0xfffffffcu;
      if(!address||address>0x20000000u-512)return;
      std::array<uint8_t,512> bytes{};SIZE_T read=0;
      if(!ReadProcessMemory(GetCurrentProcess(),memory->TranslatePhysical(address),
            bytes.data(),bytes.size(),&read)||read!=bytes.size())return;
      uint64_t hash=14695981039346656037ull;
      for(auto value:bytes)hash=(hash^value)*1099511628211ull;
      // Candidate32 custom skinned fabric/searchlight buffers. Decoder also
      // requires exact SHA256 index/vertex bytes and material references.
      switch(hash){
        case 9662007140038914464ull:case 10229115344860097749ull:
        case 10870458500461632232ull:case 11433928260866509930ull:
        case 18034727321692321148ull:case 13483863012266607246ull:
        case 12605106421409165796ull:case 14266292004935899496ull:
        case 15321219261967389672ull:case 8029256831735778222ull:break;
        default:return;
      }
    }
    if(screen_only_){
      if(!ps||(ps->ucode_data_hash()!=3413622546942440597ull&&
               ps->ucode_data_hash()!=10494309294728871449ull&&
               ps->ucode_data_hash()!=8658708157452486949ull))return;
      const uint32_t address=regs[0x48be]&0xfffffffcu;
      if(!address||address>0x20000000u-512)return;
      std::array<uint8_t,512> bytes{};SIZE_T read=0;
      if(!ReadProcessMemory(GetCurrentProcess(),memory->TranslatePhysical(address),
            bytes.data(),bytes.size(),&read)||read!=bytes.size())return;
      uint64_t hash=14695981039346656037ull;
      for(auto value:bytes)hash=(hash^value)*1099511628211ull;
      if(hash!=8328660242665232542ull)return; // Candidate32 mesh 144 vertex witness.
    }
    if (rain_only_ && (!ps || ps->ucode_data_hash()!=13459420923560293274ull)) return;
    if (water_only_ && (!ps || ps->ucode_data_hash()!=11015601269670120444ull)) return;
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
      if(compact_){const uint32_t ranges[]={1,0x2000,0x2400,0x4000,RegisterFile::kRegisterCount};Packet(8,ranges,sizeof(ranges));}
    }
    if (frame - first_frame_ >= frame_limit_ || now - start_ >= std::chrono::seconds(15)) {
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
    if(sky_command_witness::Enabled()){
      std::array<uint64_t,82> command{};command[0]=sequence_;command[1]=frame;
      std::copy(sky_command_witness::packet.begin(),sky_command_witness::packet.end(),command.begin()+2);
      for(unsigned i=0;i<4;++i)std::copy(sky_command_witness::blend[i].begin(),
        sky_command_witness::blend[i].end(),command.begin()+18+i*16);
      Packet(10,command.data(),uint32_t(sizeof(command)));
    }
    changes_.clear();
    auto capture=[&](uint32_t begin,uint32_t end){for (uint32_t i = begin; i < end; ++i) {
      if (sequence_ == 1 || previous_[i] != regs[i]) {
        changes_.push_back(i); changes_.push_back(regs[i]); previous_[i] = regs[i];
      }
    }};
    if(compact_){capture(0x2000,0x2400);capture(0x4000,RegisterFile::kRegisterCount);}
    else capture(0,RegisterFile::kRegisterCount);
    Packet(2, changes_.data(), uint32_t(changes_.size() * 4));
    // CPU-visible byte prefixes identify buffers, not GPU-resolved texture content.
    if(!compact_)Prefix(index_address, index_length, memory);
    // Rain uses texture sampler 0; retain a bounded CPU payload witness.
    // This identifies the uploaded asset, not GPU sampling correctness.
    if(screen_only_)for(uint32_t sampler=0;sampler<32;++sampler)
      if((regs[0x4800+sampler*6]&3)==2)Prefix(regs[0x4801+sampler*6]&0xfffff000u,512,memory);
    if(rain_only_)Prefix(regs[0x4801]&0xfffff000u,512,memory);
    for (uint32_t i = compact_?96:(targets_only_ ? 95 : 0); i < 96; ++i) {
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
    const auto* water=_wgetenv(L"OPENH3M_SKY_TRACE_WATER");
    water_only_=water && wcscmp(water,L"1")==0;
    const auto* screen=_wgetenv(L"OPENH3M_SKY_TRACE_SCREEN");
    screen_only_=screen && wcscmp(screen,L"1")==0;
    const auto* cylinder=_wgetenv(L"OPENH3M_SKY_TRACE_CYLINDER");
    cylinder_only_=cylinder && wcscmp(cylinder,L"1")==0;
    const auto* model=_wgetenv(L"OPENH3M_SKY_TRACE_MODEL");
    model_only_=model && wcscmp(model,L"1")==0;
    const auto* rain=_wgetenv(L"OPENH3M_SKY_TRACE_RAIN");
    rain_only_=rain && wcscmp(rain,L"1")==0;
    const auto* compact=_wgetenv(L"OPENH3M_SKY_TRACE_COMPACT");
    compact_=compact && wcscmp(compact,L"1")==0;
    const auto* limit=_wgetenv(L"OPENH3M_SKY_TRACE_FRAME_LIMIT");
    if(limit){wchar_t* end=nullptr;const auto n=wcstoul(limit,&end,10);if(end!=limit&&!*end&&n>=1&&n<=300)frame_limit_=uint32_t(n);}
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
  bool targets_only_=false,active_draw_=false,compact_=false,water_only_=false,rain_only_=false,screen_only_=false,model_only_=false,cylinder_only_=false;
  uint32_t frame_limit_=300;
  uint64_t sequence_=0, first_frame_=0, last_frame_=0, bytes_=0;
  std::chrono::steady_clock::time_point start_, poll_;
  std::array<uint32_t, RegisterFile::kRegisterCount> previous_{};
  std::vector<uint32_t> changes_;
  std::unordered_set<uint64_t> programs_, prefixes_;
};
}  // namespace rex::graphics::d3d12
