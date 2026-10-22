#include <cstdio>
#include <memory>
#include <rex/graphics/pipeline/texture/cache.h>
#include <rex/graphics/register_file.h>
#include <rex/system/xmemory.h>
#include <rex/logging.h>
using namespace rex::graphics;
class TestShared final : public SharedMemory {
 public:
  bool invalidate_during_upload = true;
  unsigned uploads = 0;
  explicit TestShared(rex::memory::Memory& m) : SharedMemory(m) { InitializeCommon(); }
 protected:
  bool UploadRanges(const std::vector<std::pair<uint32_t,uint32_t>>& ranges) override {
    ++uploads;
    for (auto range : ranges) {
      auto address = range.first << page_size_log2();
      auto size = range.second << page_size_log2();
      MakeRangeValid(address,size,false);
      // Deterministic CPU write notification after the upload snapshot but
      // before TextureCache installs its per-texture watch. No sleep/thread race.
      if (invalidate_during_upload) MemoryInvalidationCallback(address,size,true);
    }
    invalidate_during_upload = false;
    return true;
  }
};
class TestCache final : public TextureCache {
  class TestTexture final : public Texture {
   public:
    TestTexture(TextureCache& cache, TextureKey key) : Texture(cache,key) {}
  };
 public:
  unsigned loads = 0;
  TestCache(const RegisterFile& regs, SharedMemory& shared) : TextureCache(regs,shared,1,1) {}
 protected:
  uint32_t GetHostFormatSwizzle(TextureKey) const override { return 0x688; }
  uint32_t GetMaxHostTextureWidthHeight(rex::graphics::xenos::DataDimension) const override { return 8192; }
  uint32_t GetMaxHostTextureDepthOrArraySize(rex::graphics::xenos::DataDimension) const override { return 2048; }
  std::unique_ptr<Texture> CreateTexture(TextureKey key) override { return std::make_unique<TestTexture>(*this,key); }
  bool LoadTextureDataFromResidentMemoryImpl(Texture&,bool,bool) override { ++loads; return true; }
};
bool run_case(rex::memory::Memory& memory, bool inject) {
  RegisterFile regs;
  const uint32_t fetch[6] = {0x0406dbfe,0x03ec704f,0x003fe1ff,0x00000c14,0,0x218};
  std::memcpy(regs.values+0x4800,fetch,sizeof(fetch));
  TestShared shared(memory);
  shared.invalidate_during_upload = inject;
  TestCache cache(regs,shared);
  cache.BeginSubmission(1);
  cache.RequestTextures(1);
  const unsigned first = cache.loads;
  cache.RequestTextures(1);
  const unsigned second = cache.loads;
  cache.RequestTextures(1);
  const unsigned stable = cache.loads;
  const unsigned expected = inject ? 2 : 1;
  // Also verify ordinary writes after the watch is registered, followed by
  // a stable draw. Both paths use the real SharedMemory and TextureCache.
  shared.MemoryInvalidationCallback(0x03ec7000,4096,true);
  cache.RequestTextures(1);
  const unsigned later = cache.loads;
  cache.RequestTextures(1);
  std::printf("inject=%u first=%u second=%u stable=%u later=%u final=%u uploads=%u\n",
              inject,first,second,stable,later,cache.loads,shared.uploads);
  return first == 1 && second == expected && stable == expected &&
         later == expected+1 && cache.loads == later && shared.uploads == later;
}
int main() {
  rex::InitLogging();
  rex::memory::Memory memory;
  if (!memory.Initialize()) return 2;
  return run_case(memory,false) && run_case(memory,true) ? 0 : 1;
}
