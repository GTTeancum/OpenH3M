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
#include "sky_stage_probe.h"
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
 D3D12_RESOURCE_DESC td{};td.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;td.Width=1088;td.Height=288;
 td.DepthOrArraySize=1;td.MipLevels=1;td.Format=DXGI_FORMAT_R16G16B16A16_FLOAT;td.SampleDesc.Count=1;
 ComPtr<ID3D12Resource> texture;check(device->CreateCommittedResource(&normal,D3D12_HEAP_FLAG_NONE,&td,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&texture)));
 D3D12_RESOURCE_DESC bd;rex::ui::d3d12::util::FillBufferResourceDesc(bd,8704*288*2,D3D12_RESOURCE_FLAG_NONE);
 ComPtr<ID3D12Resource> source;check(device->CreateCommittedResource(&upload,D3D12_HEAP_FLAG_NONE,&bd,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&source)));
 uint8_t* mapped;D3D12_RANGE none{0,0};check(source->Map(0,&none,reinterpret_cast<void**>(&mapped)));
 for(unsigned phase=0;phase<2;++phase) for(unsigned y=0;y<288;++y) for(unsigned x=0;x<1088;++x) {
  uint32_t value[2]={(x+phase)|((y+phase*2)<<16),phase?0x3c003400u:0x3c003800u};
  std::memcpy(mapped+phase*8704*288+y*8704+x*8,value,8);
 }
 source->Unmap(0,nullptr);
 D3D12_TEXTURE_COPY_LOCATION dst{};dst.pResource=texture.Get();dst.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
 D3D12_TEXTURE_COPY_LOCATION src{};src.pResource=source.Get();src.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
 src.PlacedFootprint.Footprint={DXGI_FORMAT_R16G16B16A16_FLOAT,1088,288,1,8704};
 list->CopyTextureRegion(&dst,0,0,0,&src,nullptr);
 auto barrier=[&](D3D12_RESOURCE_STATES before,D3D12_RESOURCE_STATES after) {
  D3D12_RESOURCE_BARRIER b{};b.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;b.Transition.pResource=texture.Get();
  b.Transition.Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;b.Transition.StateBefore=before;b.Transition.StateAfter=after;list->ResourceBarrier(1,&b);
 };
 barrier(D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
 auto& probe=rex::graphics::d3d12::SkyStageProbe::Get();bool copied=false;
 auto copy=[&](ID3D12Resource* target) {
  copied=true;barrier(D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_COPY_SOURCE);
  D3D12_TEXTURE_COPY_LOCATION a{};a.pResource=target;a.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
  a.PlacedFootprint.Footprint={DXGI_FORMAT_R16G16B16A16_FLOAT,1,1,1,256};
  D3D12_TEXTURE_COPY_LOCATION b{};b.pResource=texture.Get();b.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
  for(unsigned i=0;i<probe.PointCount();++i) {
   auto p=probe.points[i];D3D12_BOX box{p[0],p[1],0,p[0]+1,p[1]+1,1};a.PlacedFootprint.Offset=i*512;
   list->CopyTextureRegion(&a,0,0,0,&b,&box);
  }
  barrier(D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
 };
 probe.Record(device.Get(),texture.Get(),DXGI_FORMAT_R16G16B16A16_FLOAT,10,1,14617156369365479079ull,21858,0,1,0,copy);
 barrier(D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_COPY_DEST);
 src.PlacedFootprint.Offset=8704*288;
 list->CopyTextureRegion(&dst,0,0,0,&src,nullptr);
 barrier(D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
 probe.Record(device.Get(),texture.Get(),DXGI_FORMAT_R16G16B16A16_FLOAT,10,1,14617156369365479079ull,21858,1,1,0,copy);
 if(!copied)throw std::runtime_error("Probe did not arm");
 probe.Poll(0);
 std::ifstream before(std::filesystem::path(_wgetenv(L"OPENH3M_SKY_STAGE_PROBE_DIR"))/"stages.csv");
 std::string text((std::istreambuf_iterator<char>(before)),{});
 if(text.find("sample,")!=std::string::npos)throw std::runtime_error("Read before completion");
 before.close();
 check(list->Close());ID3D12CommandList* submit=list.Get();queue->ExecuteCommandLists(1,&submit);
 ComPtr<ID3D12Fence> fence;check(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence)));
 HANDLE event=CreateEvent(nullptr,FALSE,FALSE,nullptr);check(queue->Signal(fence.Get(),1));check(fence->SetEventOnCompletion(1,event));
 if(WaitForSingleObject(event,10000)!=WAIT_OBJECT_0)throw std::runtime_error("GPU wait failed");CloseHandle(event);
 probe.Poll(fence->GetCompletedValue());
 probe.Record(device.Get(),texture.Get(),DXGI_FORMAT_R16G16B16A16_FLOAT,310,0,14617156369365479079ull,21858,0,2,1,[](ID3D12Resource*){throw std::runtime_error("Limit failed");});
 probe.Shutdown(1);printf("Native WARP probe test completed; verify both phases and %u numeric points.\n",probe.PointCount());
}
