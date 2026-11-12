// Headless compute verification of generated original-material HLSL. WARP
// supplies an independent shader compiler/executor without a window or input.
#include <d3d11.h>
#include <d3dcompiler.h>
#include <wrl/client.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <stdexcept>
using Microsoft::WRL::ComPtr;
void Check(HRESULT result){if(FAILED(result))throw std::runtime_error("D3D shader check failed: "+std::to_string(unsigned(result)));}
std::vector<char> Read(const std::filesystem::path& path){
 std::ifstream input(path,std::ios::binary|std::ios::ate);auto size=input.tellg();
 if(!input||size<=0||size>1024*1024*128)throw std::runtime_error("Invalid input: "+path.string());
 std::vector<char> data(size_t(size),0);input.seekg(0);input.read(data.data(),size);
 if(!input)throw std::runtime_error("Short input");return data;
}
int main(int argc,char** argv)try{
 if(argc!=6)throw std::runtime_error("Usage: h4_forge_marker_shader_gpu 331|16 generated.hlsl cases.bin bitmap-directory output.bin");
 bool plasma=std::string(argv[1])=="331";if(!plasma&&std::string(argv[1])!="16"&&std::string(argv[1])!="fade")throw std::runtime_error("Unknown material");
 const auto program=Read(argv[2]),cases=Read(argv[3]);uint32_t count;std::memcpy(&count,cases.data(),4);
 constexpr unsigned stride=(256*4+8+8*4)*4;
 if(!count||count>100000||cases.size()!=4+size_t(count)*stride)throw std::runtime_error("Invalid case data");
 const char* prefix=R"(
 Texture2D<float4> textures[4] : register(t0);
 StructuredBuffer<float4> cases : register(t8);
 RWStructuredBuffer<float4> results : register(u0);
 float4 texel(uint slot,int2 p) {
  uint w,h;textures[slot].GetDimensions(w,h);int2 size=int2(w,h);
  bool wrap=WRAP_BASE || slot>=2;
  p=wrap?((p%size)+size)%size:clamp(p,0,size-1);
  return textures[slot].Load(int3(p,0));
 }
 float4 H4Fetch(uint slot,float3 uv) {
  if(slot==14)return .75;
  uint w,h;textures[slot].GetDimensions(w,h);float2 location=uv.xy*float2(w,h)-.5;
  int2 p=int2(floor(location));float2 f=frac(location);
  return lerp(lerp(texel(slot,p),texel(slot,p+int2(1,0)),f.x),
              lerp(texel(slot,p+int2(0,1)),texel(slot,p+1),f.x),f.y);
 }
 )";
 const char* suffix=R"(
 [numthreads(1,1,1)] void main(uint3 tid:SV_DispatchThreadID) {
  uint offset=tid.x*266;float4 c[256],r[8];uint b[8];
  [unroll]for(uint i=0;i<256;++i)c[i]=cases[offset+i];
  [unroll]for(uint i=0;i<8;++i){b[i]=asuint(cases[offset+256+i/4][i%4]);r[i]=cases[offset+258+i];}
  results[tid.x]=H4MarkerPixel(c,b,r);
 })";
 std::string source=std::string("#define WRAP_BASE ")+(plasma?"false\n":"true\n")+prefix+std::string(program.begin(),program.end())+suffix;
 ComPtr<ID3DBlob> shader,error;
 const auto compile=D3DCompile(source.data(),source.size(),"original_h4_marker_check",nullptr,nullptr,"main","cs_5_0",D3DCOMPILE_OPTIMIZATION_LEVEL3|D3DCOMPILE_IEEE_STRICTNESS,0,&shader,&error);
 if(FAILED(compile))throw std::runtime_error(error?static_cast<const char*>(error->GetBufferPointer()):"Shader compilation failed");
 ComPtr<ID3D11Device> device;ComPtr<ID3D11DeviceContext> context;D3D_FEATURE_LEVEL level;
 Check(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,&level,&context));
 ComPtr<ID3D11ComputeShader> compute;Check(device->CreateComputeShader(shader->GetBufferPointer(),shader->GetBufferSize(),nullptr,&compute));
 D3D11_BUFFER_DESC bd{};bd.ByteWidth=UINT(cases.size()-4);bd.Usage=D3D11_USAGE_IMMUTABLE;bd.BindFlags=D3D11_BIND_SHADER_RESOURCE;bd.MiscFlags=D3D11_RESOURCE_MISC_BUFFER_STRUCTURED;bd.StructureByteStride=16;
 D3D11_SUBRESOURCE_DATA initial{cases.data()+4,0,0};ComPtr<ID3D11Buffer> input;Check(device->CreateBuffer(&bd,&initial,&input));
 ComPtr<ID3D11ShaderResourceView> inputView;Check(device->CreateShaderResourceView(input.Get(),nullptr,&inputView));
 bd.ByteWidth=count*16;bd.Usage=D3D11_USAGE_DEFAULT;bd.BindFlags=D3D11_BIND_UNORDERED_ACCESS;
 ComPtr<ID3D11Buffer> output;Check(device->CreateBuffer(&bd,nullptr,&output));
 ComPtr<ID3D11UnorderedAccessView> outputView;Check(device->CreateUnorderedAccessView(output.Get(),nullptr,&outputView));
 bd.Usage=D3D11_USAGE_STAGING;bd.BindFlags=0;bd.CPUAccessFlags=D3D11_CPU_ACCESS_READ;bd.MiscFlags=0;bd.StructureByteStride=0;
 ComPtr<ID3D11Buffer> staging;Check(device->CreateBuffer(&bd,nullptr,&staging));
 const unsigned ids[]={plasma?7748u:16661u,16659,419,341},widths[]={plasma?256u:512u,256,128,128},heights[]={plasma?256u:512u,1,128,128};
 ComPtr<ID3D11Texture2D> textures[4];ComPtr<ID3D11ShaderResourceView> views[4];ID3D11ShaderResourceView* rawViews[4];
 for(unsigned i=0;i<4;++i){
  const auto bytes=Read(std::filesystem::path(argv[4])/(std::to_string(ids[i])+".rgba"));
  if(bytes.size()!=widths[i]*heights[i]*4)throw std::runtime_error("Texture dimensions mismatch");
  D3D11_TEXTURE2D_DESC td{};td.Width=widths[i];td.Height=heights[i];td.ArraySize=1;td.MipLevels=1;td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.SampleDesc.Count=1;td.Usage=D3D11_USAGE_IMMUTABLE;td.BindFlags=D3D11_BIND_SHADER_RESOURCE;
  initial={bytes.data(),widths[i]*4,0};Check(device->CreateTexture2D(&td,&initial,&textures[i]));Check(device->CreateShaderResourceView(textures[i].Get(),nullptr,&views[i]));rawViews[i]=views[i].Get();
 }
 context->CSSetShader(compute.Get(),nullptr,0);context->CSSetShaderResources(0,4,rawViews);
 auto* inputRaw=inputView.Get();context->CSSetShaderResources(8,1,&inputRaw);
 auto* outputRaw=outputView.Get();context->CSSetUnorderedAccessViews(0,1,&outputRaw,nullptr);
 context->Dispatch(count,1,1);context->CopyResource(staging.Get(),output.Get());
 D3D11_MAPPED_SUBRESOURCE mapped;Check(context->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped));
 std::ofstream result(argv[5],std::ios::binary|std::ios::trunc);result.write(static_cast<const char*>(mapped.pData),count*16);context->Unmap(staging.Get(),0);
 if(!result)throw std::runtime_error("Could not write compute results");
 std::cout<<"Executed generated HLSL on WARP: "<<count<<" cases, "<<shader->GetBufferSize()<<" compiled bytes\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
