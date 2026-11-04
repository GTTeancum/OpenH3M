#include <windows.h>
#include <algorithm>
#include <d3d12.h>
#include <dxgi1_6.h>
#include <wrl/client.h>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
namespace rex::ui::d3d12::util {
inline constexpr D3D12_HEAP_PROPERTIES kHeapPropertiesReadback={D3D12_HEAP_TYPE_READBACK};
inline void FillBufferResourceDesc(D3D12_RESOURCE_DESC& d,UINT64 size,D3D12_RESOURCE_FLAGS flags) {
 d={};d.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;d.Width=size;d.Height=1;d.DepthOrArraySize=1;
 d.MipLevels=1;d.SampleDesc.Count=1;d.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;d.Flags=flags;
}
}
#include "sky_pixel_probe.h"
using Microsoft::WRL::ComPtr;
void check(HRESULT hr) {if(FAILED(hr)) throw std::runtime_error("D3D12 failure");}
int main() {
 ComPtr<IDXGIFactory4> factory;check(CreateDXGIFactory1(IID_PPV_ARGS(&factory)));
 ComPtr<IDXGIAdapter> adapter;check(factory->EnumWarpAdapter(IID_PPV_ARGS(&adapter)));
 ComPtr<ID3D12Device> device;check(D3D12CreateDevice(adapter.Get(),D3D_FEATURE_LEVEL_11_0,IID_PPV_ARGS(&device)));
 ComPtr<ID3D12CommandQueue> queue;D3D12_COMMAND_QUEUE_DESC q{};check(device->CreateCommandQueue(&q,IID_PPV_ARGS(&queue)));
 ComPtr<ID3D12CommandAllocator> allocator;check(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator)));
 ComPtr<ID3D12GraphicsCommandList> list;check(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),nullptr,IID_PPV_ARGS(&list)));
 D3D12_HEAP_PROPERTIES normal{D3D12_HEAP_TYPE_DEFAULT},upload{D3D12_HEAP_TYPE_UPLOAD};
 D3D12_RESOURCE_DESC td{};td.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;td.Width=32;td.Height=18;
 td.DepthOrArraySize=1;td.MipLevels=1;td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.SampleDesc.Count=1;
 ComPtr<ID3D12Resource> texture;check(device->CreateCommittedResource(&normal,D3D12_HEAP_FLAG_NONE,&td,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&texture)));
 D3D12_RESOURCE_DESC bd;rex::ui::d3d12::util::FillBufferResourceDesc(bd,256*18,D3D12_RESOURCE_FLAG_NONE);
 ComPtr<ID3D12Resource> source;check(device->CreateCommittedResource(&upload,D3D12_HEAP_FLAG_NONE,&bd,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&source)));
 uint8_t* mapped;D3D12_RANGE none{0,0};check(source->Map(0,&none,reinterpret_cast<void**>(&mapped)));
 for(unsigned y=0;y<18;++y) for(unsigned x=0;x<32;++x) {
  uint32_t value=0xffc80000u|(y<<8)|x;std::memcpy(mapped+y*256+x*4,&value,4);
 }
 source->Unmap(0,nullptr);
 D3D12_TEXTURE_COPY_LOCATION dst{};dst.pResource=texture.Get();dst.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
 D3D12_TEXTURE_COPY_LOCATION src{};src.pResource=source.Get();src.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
 src.PlacedFootprint.Footprint={DXGI_FORMAT_R8G8B8A8_UNORM,32,18,1,256};
 list->CopyTextureRegion(&dst,0,0,0,&src,nullptr);
 auto barrier=[&](D3D12_RESOURCE_STATES before,D3D12_RESOURCE_STATES after) {
  D3D12_RESOURCE_BARRIER b{};b.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;b.Transition.pResource=texture.Get();
  b.Transition.Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;b.Transition.StateBefore=before;b.Transition.StateAfter=after;list->ResourceBarrier(1,&b);
 };
 barrier(D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
 auto& probe=rex::graphics::d3d12::SkyPixelProbe::Get();bool copied=false;
 probe.Record(device.Get(),texture.Get(),DXGI_FORMAT_R8G8B8A8_UNORM,D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING,32,18,10,1,0,[&](ID3D12Resource* target) {
  copied=true;barrier(D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_COPY_SOURCE);
  D3D12_TEXTURE_COPY_LOCATION a{};a.pResource=target;a.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;a.PlacedFootprint.Footprint={DXGI_FORMAT_R8G8B8A8_UNORM,1,1,1,256};
  D3D12_TEXTURE_COPY_LOCATION b{};b.pResource=texture.Get();b.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
  for(unsigned row=0;row<9;++row) for(unsigned col=0;col<16;++col) {
   unsigned x=probe.SampleX(col,32),y=probe.SampleY(row,18);D3D12_BOX box{x,y,0,x+1,y+1,1};a.PlacedFootprint.Offset=(row*16+col)*512;
   list->CopyTextureRegion(&a,0,0,0,&b,&box);
  }
  barrier(D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
 });
 if(!copied)throw std::runtime_error("Probe did not arm");
 probe.Poll(0);
 std::ifstream before(std::filesystem::path(_wgetenv(L"OPENH3M_SKY_PIXEL_PROBE_DIR"))/"pixels.csv");
 std::string text((std::istreambuf_iterator<char>(before)),{});
 if(text.find("sample,")!=std::string::npos)throw std::runtime_error("Read before completion");
 before.close();
 check(list->Close());ID3D12CommandList* submit=list.Get();queue->ExecuteCommandLists(1,&submit);
 ComPtr<ID3D12Fence> fence;check(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence)));
 HANDLE event=CreateEvent(nullptr,FALSE,FALSE,nullptr);check(queue->Signal(fence.Get(),1));check(fence->SetEventOnCompletion(1,event));
 if(WaitForSingleObject(event,10000)!=WAIT_OBJECT_0)throw std::runtime_error("GPU wait failed");CloseHandle(event);
 probe.Poll(fence->GetCompletedValue());
 probe.Record(device.Get(),texture.Get(),DXGI_FORMAT_R8G8B8A8_UNORM,0,32,18,310,2,1,[](ID3D12Resource*){throw std::runtime_error("Limit failed");});
 probe.Shutdown(1);puts("Native WARP probe test completed; verify all 144 numeric pixels.");
}

