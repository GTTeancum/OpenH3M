#include <windows.h>
#include <d3dx9.h>
#include <xgraphics.h>
#include <fstream>
#include <iterator>
#include <vector>
#include <cstdio>
#include <cstring>

static void save(const char* path, const void* data, size_t size) {
  std::ofstream out(path, std::ios::binary);
  out.write(static_cast<const char*>(data), size);
  if (!out) throw "write failed";
}
int main(int argc, char** argv) {
  if (argc != 4) return 2;
  std::ifstream file(argv[2], std::ios::binary);
  std::vector<char> input((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
  if (input.empty()) return 3;
  ID3DXBuffer *result=NULL, *errors=NULL;
  HRESULT hr;
  if (!std::strcmp(argv[1], "disassemble")) {
    hr=D3DXDisassembleShader(reinterpret_cast<const DWORD*>(&input[0]), FALSE, NULL, &result);
  } else if (!std::strcmp(argv[1], "assemble")) {
    hr=D3DXAssembleShader(&input[0], static_cast<UINT>(input.size()), NULL, NULL, 0, &result, &errors);
  } else return 4;
  if (errors) { fwrite(errors->GetBufferPointer(),1,errors->GetBufferSize(),stderr); errors->Release(); }
  if (FAILED(hr)) { fprintf(stderr,"HRESULT %08lx\n",hr); return 5; }
  save(argv[3],result->GetBufferPointer(),result->GetBufferSize());
  printf("%s: %lu bytes\n",argv[1],result->GetBufferSize());
  result->Release();
  return 0;
}
