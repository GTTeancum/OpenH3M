// Execute the packaged runtime compute shader, including alpha wiring and
// scene-depth rejection, on headless WARP. No game window or host input.
#include <d3d11.h>
#include <wrl/client.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using Microsoft::WRL::ComPtr;
void Check(HRESULT hr){if(FAILED(hr))throw std::runtime_error("D3D failure "+std::to_string(unsigned(hr)));}
int main(int argc,char** argv)try {
  if(argc!=2)throw std::runtime_error("private material pack required");
  std::ifstream in(argv[1],std::ios::binary);uint32_t header[5]{};
  in.read(reinterpret_cast<char*>(header),sizeof(header));
  if(!in||header[0]!=0x504d3448||header[1]!=2||header[2]>1024*1024||header[3]>1024*1024||header[4]>16*1024*1024)
    throw std::runtime_error("invalid pack");
  std::array<std::vector<char>,3> payload;
  for(unsigned i=0;i<3;++i){payload[i].resize(header[i+2]);in.read(payload[i].data(),payload[i].size());}
  if(!in||in.peek()!=EOF)throw std::runtime_error("invalid payload length");
  ComPtr<ID3D11Device> device;ComPtr<ID3D11DeviceContext> context;
  Check(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context));
  D3D11_BUFFER_DESC pixelsDesc{};pixelsDesc.ByteWidth=header[4];pixelsDesc.Usage=D3D11_USAGE_IMMUTABLE;
  pixelsDesc.BindFlags=D3D11_BIND_SHADER_RESOURCE;pixelsDesc.MiscFlags=D3D11_RESOURCE_MISC_BUFFER_ALLOW_RAW_VIEWS;
  D3D11_SUBRESOURCE_DATA pixelsInitial{payload[2].data(),0,0};ComPtr<ID3D11Buffer> pixels;
  Check(device->CreateBuffer(&pixelsDesc,&pixelsInitial,&pixels));
  D3D11_SHADER_RESOURCE_VIEW_DESC pixelViewDesc{};pixelViewDesc.Format=DXGI_FORMAT_R32_TYPELESS;
  pixelViewDesc.ViewDimension=D3D11_SRV_DIMENSION_BUFFEREX;pixelViewDesc.BufferEx.NumElements=header[4]/4;
  pixelViewDesc.BufferEx.Flags=D3D11_BUFFEREX_SRV_FLAG_RAW;
  ComPtr<ID3D11ShaderResourceView> pixelsView;Check(device->CreateShaderResourceView(pixels.Get(),&pixelViewDesc,&pixelsView));
  constexpr unsigned extent=64;
  D3D11_TEXTURE2D_DESC td{};td.Width=td.Height=extent;td.MipLevels=td.ArraySize=1;td.SampleDesc.Count=1;
  td.Format=DXGI_FORMAT_R32G32B32A32_FLOAT;td.Usage=D3D11_USAGE_DEFAULT;td.BindFlags=D3D11_BIND_UNORDERED_ACCESS;
  ComPtr<ID3D11Texture2D> target;Check(device->CreateTexture2D(&td,nullptr,&target));
  ComPtr<ID3D11UnorderedAccessView> targetView;Check(device->CreateUnorderedAccessView(target.Get(),nullptr,&targetView));
  td.Usage=D3D11_USAGE_STAGING;td.BindFlags=0;td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
  ComPtr<ID3D11Texture2D> staging;Check(device->CreateTexture2D(&td,nullptr,&staging));
  struct Constants {
    float center[2]{32,32},radius=16,depth=.75f;uint32_t origin[2]{0,0},size[2]{extent,extent};
    float scale[2]{1,1},offset[2]{0,0},color[4]{};uint32_t samples=1;float epsilon=0,elapsed=.375f,viewDepth=2;
  } constants;
  static_assert(sizeof(constants)==80);
  D3D11_BUFFER_DESC cbDesc{};cbDesc.ByteWidth=sizeof(constants);cbDesc.Usage=D3D11_USAGE_DEFAULT;
  cbDesc.BindFlags=D3D11_BIND_CONSTANT_BUFFER;ComPtr<ID3D11Buffer> cb;
  Check(device->CreateBuffer(&cbDesc,nullptr,&cb));
  auto* cbRaw=cb.Get();context->CSSetConstantBuffers(0,1,&cbRaw);
  const float background[4]{.1f,.2f,.3f,1};
  const std::array<float,9> distances{.2f,.4031650126f,.5039560124f,.6047470123f,2,21,22,23,26};
  std::array<double,10> reference{};
  for(unsigned variant=0;variant<2;++variant) {
    ComPtr<ID3D11ComputeShader> shader;
    Check(device->CreateComputeShader(payload[variant].data(),payload[variant].size(),nullptr,&shader));
    td.Usage=D3D11_USAGE_DEFAULT;td.CPUAccessFlags=0;td.Format=DXGI_FORMAT_R32_FLOAT;
    td.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;td.SampleDesc.Count=variant?4:1;
    ComPtr<ID3D11Texture2D> depth;Check(device->CreateTexture2D(&td,nullptr,&depth));
    ComPtr<ID3D11RenderTargetView> depthTarget;Check(device->CreateRenderTargetView(depth.Get(),nullptr,&depthTarget));
    ComPtr<ID3D11ShaderResourceView> depthView;Check(device->CreateShaderResourceView(depth.Get(),nullptr,&depthView));
    const float sceneDepth[4]{.5f,.5f,.5f,.5f};context->ClearRenderTargetView(depthTarget.Get(),sceneDepth);
    ID3D11ShaderResourceView* views[]{depthView.Get(),pixelsView.Get()};context->CSSetShaderResources(0,2,views);
    context->CSSetShader(shader.Get(),nullptr,0);constants.samples=td.SampleDesc.Count;
    std::array<double,10> energy{};
    for(unsigned test=0;test<10;++test) {
      constants.viewDepth=test<distances.size()?distances[test]:2;
      constants.depth=test==9?.25f:.75f;
      context->UpdateSubresource(cb.Get(),0,nullptr,&constants,0,0);
      context->ClearUnorderedAccessViewFloat(targetView.Get(),background);
      auto* targetRaw=targetView.Get();context->CSSetUnorderedAccessViews(0,1,&targetRaw,nullptr);
      context->Dispatch(extent/8,extent/8,1);
      ID3D11UnorderedAccessView* none=nullptr;context->CSSetUnorderedAccessViews(0,1,&none,nullptr);
      context->CopyResource(staging.Get(),target.Get());D3D11_MAPPED_SUBRESOURCE mapped{};
      Check(context->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped));
      for(unsigned y=0;y<extent;++y){auto* row=reinterpret_cast<const float*>(static_cast<const char*>(mapped.pData)+y*mapped.RowPitch);
        for(unsigned x=0;x<extent;++x)for(unsigned c=0;c<4;++c){
          const float value=row[x*4+c];
          if(!std::isfinite(value)||value<background[c]-1e-6f)throw std::runtime_error("invalid composed output");
          if(c==3&&value!=background[3])throw std::runtime_error("target alpha changed");
          if(c<3)energy[test]+=value-background[c];
        }
      }
      context->Unmap(staging.Get(),0);
      std::cout<<"msaa="<<variant<<" depth="<<constants.viewDepth<<" occluded="<<(test==9)<<" light="<<energy[test]<<'\n';
    }
    for(unsigned test:{0u,1u,7u,8u,9u})if(std::abs(energy[test])>1e-5)throw std::runtime_error("hidden/faded marker contributed light");
    if(energy[4]<=1||energy[2]<=0||energy[2]>=energy[4]||energy[6]<=0||energy[6]>=energy[4])
      throw std::runtime_error("missing full/partial fade behavior");
    if(std::abs(energy[3]-energy[4])>1e-4||std::abs(energy[5]-energy[4])>1e-4)
      throw std::runtime_error("full-visibility plateau changed");
    if(!variant)reference=energy;
    else for(unsigned i=0;i<10;++i)if(std::abs(energy[i]-reference[i])>1e-4)
      throw std::runtime_error("MSAA composed output differs");
    ID3D11ShaderResourceView* none[2]{};context->CSSetShaderResources(0,2,none);
  }
  std::cout<<"PASS packaged original material: near/far fades, scene occlusion, target alpha and single/MSAA agreement\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
