REXCVAR_DEFINE_BOOL(d3d12_debug_wireframe, false, "GPU/D3D12",
                    "Debug: draw geometry as white wireframe on black, unlit; culling unchanged");
REXCVAR_DEFINE_DOUBLE(d3d12_debug_wireframe_level, 1.0, "GPU/D3D12",
                      "Debug wireframe: value written by the wires (lower it if the game's HDR/bloom washes out)");
REXCVAR_DEFINE_UINT32(d3d12_debug_draw_log_frame, 0, "GPU/D3D12",
                      "Debug: log every draw's pipeline state for this frame number (0 = off)");
REXCVAR_DEFINE_BOOL(d3d12_debug_draw_count, false, "GPU/D3D12",
                    "Debug: log the number of scene draws per frame");
REXCVAR_DEFINE_UINT32(d3d12_debug_wireframe_flags, 7, "GPU/D3D12",
                      "Debug wireframe: 1 = wires overwrite (no blending), 2 = drop blended full-screen passes, 4 = zero the bloom chain, 8 = white into every target, 16 = only depth-tested draws become wires (screen-space passes keep their shaders)");
namespace {
uint64_t reach360_count_frame = 0;
uint32_t reach360_count_all = 0, reach360_count_scene = 0;
// Constant-white pixel shader for the debug wireframe, compiled once through the system shader compiler.
std::vector<uint8_t> Reach360ConstPixelShader(double value) {
  return [value] {
    std::vector<uint8_t> out;
    HMODULE m = LoadLibraryW(L"d3dcompiler_47.dll");
    if (!m) return out;
    using Compile = HRESULT(WINAPI*)(LPCVOID, SIZE_T, LPCSTR, const D3D_SHADER_MACRO*, ID3DInclude*, LPCSTR,
                                     LPCSTR, UINT, UINT, ID3DBlob**, ID3DBlob**);
    auto compile = reinterpret_cast<Compile>(GetProcAddress(m, "D3DCompile"));
    static const char src[] =
        "struct O{float4 a:SV_Target0;float4 b:SV_Target1;float4 c:SV_Target2;float4 d:SV_Target3;};"
        "O main(){O o;o.a=float4(L,L,L,1);o.b=B;o.c=B;o.d=B;return o;}";
    // Only target 0 gets white: Halo 3 splits HDR colour across two targets and the second one is the high range.
    const std::string level = "#define L " + std::to_string(value) +
                              std::string(1, char(10)) +  // (no backslash escapes: CMake rewrites them)
        "#define B " + std::string((REXCVAR_GET(d3d12_debug_wireframe_flags) & 8) ? "o.a" : "0") + std::string(1, char(10));
    const std::string full = level + src;
    ID3DBlob* code = nullptr;
    ID3DBlob* err = nullptr;
    if (compile && SUCCEEDED(compile(full.data(), full.size(), "reach360_wire", nullptr, nullptr, "main", "ps_5_1",
                                     0, 0, &code, &err)) && code) {
      auto p = static_cast<const uint8_t*>(code->GetBufferPointer());
      out.assign(p, p + code->GetBufferSize());
      code->Release();
    }
    if (err) err->Release();
    REXGPU_INFO("[reach360] debug constant pixel shader: {} bytes, value {}", out.size(), value);
    return out;
  }();
}
const std::vector<uint8_t>& Reach360WhitePixelShader() {
  static const std::vector<uint8_t> blob = Reach360ConstPixelShader(REXCVAR_GET(d3d12_debug_wireframe_level));
  return blob;
}
const std::vector<uint8_t>& Reach360BlackPixelShader() {
  static const std::vector<uint8_t> blob = Reach360ConstPixelShader(0.0);
  return blob;
}
}  // namespace
