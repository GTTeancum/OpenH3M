// Offline inspection of the original H4 shader through ReXGlue's decoder.
// No device, window, game process, or input is created.
#include <rex/graphics/pipeline/shader/shader.h>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

// The offline tool writes only the explicit output argument, never an SDK
// automatic shader-dump directory.
std::string& FLAGS_dump_shaders_storage_() {
  static std::string disabled;
  return disabled;
}

int main(int argc, char** argv) {
  try {
    if (argc != 4 || (std::string(argv[1]) != "vs" && std::string(argv[1]) != "ps"))
      throw std::runtime_error("Usage: h4_forge_shader_disasm vs|ps input.ucode output.txt");
    std::ifstream input(argv[2], std::ios::binary | std::ios::ate);
    const auto length = input.tellg();
    if (!input || length <= 0 || length > 1024 * 1024 || length % 4)
      throw std::runtime_error("Invalid shader microcode length");
    std::vector<uint32_t> code(static_cast<size_t>(length) / 4);
    input.seekg(0);
    input.read(reinterpret_cast<char*>(code.data()), length);
    if (!input) throw std::runtime_error("Truncated shader microcode");
    rex::graphics::Shader shader(std::string(argv[1]) == "vs"
        ? rex::graphics::xenos::ShaderType::kVertex
        : rex::graphics::xenos::ShaderType::kPixel, 0, code.data(), code.size());
    rex::string::StringBuffer buffer;
    shader.AnalyzeUcode(buffer);
    std::ofstream output(argv[3], std::ios::binary);
    output << shader.ucode_disassembly();
    if (!output) throw std::runtime_error("Could not write shader disassembly");
    std::cout << argv[1] << ": " << code.size() << " original microcode words\n";
  } catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
