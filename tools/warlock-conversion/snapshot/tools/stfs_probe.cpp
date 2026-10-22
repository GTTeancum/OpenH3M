// Read through the actual runtime STFS device without extracting or launching a game.
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <set>
#include <vector>
#include <rex/filesystem/devices/stfs_container_device.h>
#include <rex/filesystem/entry.h>
#include <rex/filesystem/file.h>
#include <rex/logging.h>
using rex::X_STATUS;

int main(int argc, char** argv) {
  if (argc != 3) {
    std::fprintf(stderr, "Usage: stfs_probe package.live expected-payload-directory\n");
    return 2;
  }
  rex::InitLogging(nullptr, spdlog::level::err);
  try {
    rex::filesystem::StfsContainerDevice device("", std::filesystem::path(argv[1]));
    if (!device.Initialize()) throw std::runtime_error("STFS initialization failed");
    const auto& header = device.header();
    if (header.header.magic != rex::filesystem::XContentPackageType::kLive ||
        header.metadata.execution_info.title_id != 0x4D5307E6 ||
        header.metadata.content_type != rex::system::XContentType::kMarketplaceContent)
      throw std::runtime_error("Unexpected title or package type");
    auto* root = device.ResolvePath("");
    if (!root) throw std::runtime_error("No root directory");
    std::set<std::string> expected_names;
    for (const auto& file : std::filesystem::directory_iterator(argv[2])) {
      if (!file.is_regular_file()) throw std::runtime_error("Expected flat payload");
      expected_names.insert(file.path().filename().string());
    }
    std::vector<uint8_t> actual(1024 * 1024), expected(actual.size());
    uint64_t total = 0;
    for (const auto& entry : root->children()) {
      if (entry->attributes() & rex::filesystem::kFileAttributeDirectory ||
          !expected_names.erase(entry->name()))
        throw std::runtime_error("Unexpected package entry");
      auto path = std::filesystem::path(argv[2]) / entry->name();
      if (entry->size() != std::filesystem::file_size(path))
        throw std::runtime_error("File length mismatch");
      std::ifstream input(path, std::ios::binary);
      rex::filesystem::File* raw = nullptr;
      if (entry->Open(rex::filesystem::FileAccess::kFileReadData, &raw) != X_STATUS_SUCCESS)
        throw std::runtime_error("Cannot open packaged file");
      auto destroy = [](rex::filesystem::File* f) { f->Destroy(); };
      std::unique_ptr<rex::filesystem::File, decltype(destroy)> file(raw, destroy);
      for (size_t offset = 0; offset < entry->size(); offset += actual.size()) {
        size_t length = std::min(actual.size(), entry->size() - offset), read = 0;
        if (file->ReadSync(std::span(actual.data(), length), offset, &read) != X_STATUS_SUCCESS || read != length)
          throw std::runtime_error("Runtime read failed or truncated");
        input.read(reinterpret_cast<char*>(expected.data()), length);
        if (input.gcount() != static_cast<std::streamsize>(length) ||
            !std::equal(actual.begin(), actual.begin() + length, expected.begin()))
          throw std::runtime_error("Runtime bytes differ from payload");
      }
      total += entry->size();
      std::printf("PASS %s %zu bytes\n", entry->name().c_str(), entry->size());
    }
    if (!expected_names.empty()) throw std::runtime_error("Missing package entries");
    std::printf("PASS runtime STFS reader: %zu files, %llu payload bytes; no signature or gameplay validation\n",
                root->child_count(), static_cast<unsigned long long>(total));
  } catch (const std::exception& error) {
    std::fprintf(stderr, "FAIL: %s\n", error.what());
    return 1;
  }
  return 0;
}
