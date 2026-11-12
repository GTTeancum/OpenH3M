// Offline compilation only. No device, game window, host input or shader dump.
#include <rex/graphics/d3d12/scene_marker_shader.h>
#include <d3dcompiler.h>
#include <wrl/client.h>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
using Microsoft::WRL::ComPtr;
int main(int argc,char** argv)try {
  if(argc!=4||std::string(argv[3])!="3")throw std::runtime_error("material HLSL, output prefix and ABI 3 required");
  std::ifstream input(argv[1],std::ios::binary);
  if(!input)throw std::runtime_error("Missing private material HLSL");
  std::string source{std::istreambuf_iterator<char>(input),std::istreambuf_iterator<char>()};
  if(source.empty()||source.size()>256*1024)throw std::runtime_error("Invalid material extent");
  source+=rex::graphics::d3d12::kSceneMarkerKernel;
  for(unsigned msaa=0;msaa<2;++msaa){
    const D3D_SHADER_MACRO defines[]={{"MULTISAMPLED","1"},{nullptr,nullptr}};
    ComPtr<ID3DBlob> shader,error;
    if(FAILED(D3DCompile(source.data(),source.size(),"scene_markers",msaa?defines:nullptr,nullptr,
        "main","cs_5_0",D3DCOMPILE_OPTIMIZATION_LEVEL3|D3DCOMPILE_IEEE_STRICTNESS,0,&shader,&error)))
      throw std::runtime_error(error?static_cast<const char*>(error->GetBufferPointer()):"Compilation failed");
    std::ofstream output(std::string(argv[2])+"."+std::to_string(msaa)+".dxbc",std::ios::binary);
    output.write(static_cast<const char*>(shader->GetBufferPointer()),shader->GetBufferSize());
    if(!output)throw std::runtime_error("Failed to save compiled program");
    std::cout<<"Compiled marker program msaa="<<msaa<<" bytes="<<shader->GetBufferSize()<<'\n';
  }
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
