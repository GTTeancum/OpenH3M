#pragma once
#include <rex/cvar.h>
#include <array>
#include <filesystem>
#include <functional>
#include <string>
#include <vector>

namespace spartan::video {
struct Choice { const char* label; const char* value; };
struct Option {
  const char* label;
  const char* flag;
  const char* default_value;
  bool restart;
  std::vector<Choice> choices;
};
const std::vector<Option>& PCOptions();
// Edits remain local until Apply. Cancel never writes cvars or configuration.
class PCSettings {
 public:
  PCSettings();
  std::vector<std::string> values;
  void Defaults();
  void Preset(int index);
  int PresetIndex() const;
  bool Dirty() const;
  bool RestartRequired() const;
  void Cancel();
  void Reload();
  bool Apply(const std::filesystem::path& path, std::string& error);
 private:
  std::vector<std::string> saved_;
  std::array<std::string, 3> startup_;
};
}
