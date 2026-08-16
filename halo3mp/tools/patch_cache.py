p = r"C:\Programming\GitHub\Halo-3-MP\work\rexglue-sdk\src\system\runtime.cpp"
s = open(p, encoding="utf-8").read()

if "REXGLUE_CACHE_PARTITIONS" in s:
    print("already patched")
    raise SystemExit(0)

anchor = """  file_system_->RegisterSymbolicLink("game:", mount_path);
  file_system_->RegisterSymbolicLink("d:", mount_path);
"""

add = anchor + """
  // REXGLUE_CACHE_PARTITIONS
  // Halo 3 probes cache0:/cache1: for cache000.map .. cache014.map and uses
  // them for its streaming/decompression cache. With no device the probes fail
  // and the streaming system is fed nothing, so its bit-stream decoder asserts.
  // Register real writable directories, BEFORE the NullDevice below so these
  // win the registration-order lookup.
  {
    auto cache_base = std::filesystem::current_path() / "cache";
    const char* cache_mounts[] = {"\\\\Device\\\\Harddisk0\\\\Cache0",
                                  "\\\\Device\\\\Harddisk0\\\\Cache1"};
    const char* cache_links[] = {"cache0:", "cache1:"};
    for (int i = 0; i < 2; ++i) {
      auto dir = cache_base / (i == 0 ? "cache0" : "cache1");
      std::error_code ec;
      std::filesystem::create_directories(dir, ec);
      auto dev = std::make_unique<rex::filesystem::HostPathDevice>(cache_mounts[i], dir, false);
      if (dev->Initialize() && file_system_->RegisterDevice(std::move(dev))) {
        file_system_->RegisterSymbolicLink(cache_links[i], cache_mounts[i]);
        REXSYS_INFO("  Mounted {} at {}", dir.string(), cache_links[i]);
      } else {
        REXSYS_WARN("  Failed to mount cache partition {}", cache_links[i]);
      }
    }
  }
"""

assert anchor in s, "symlink anchor missing"
s = s.replace(anchor, add, 1)
open(p, "w", encoding="utf-8").write(s)
print("patched runtime.cpp with cache partitions")
