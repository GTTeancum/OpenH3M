#include <windows.h>
#include <d3d12.h>
#include <d3d12sdklayers.h>
#include <d3dcompiler.h>
#include <dxgi1_6.h>
#include <wrl/client.h>
#include <fstream>
#include <stdexcept>
#include <string>
#include "sky_coverage_probe.h"
using Microsoft::WRL::ComPtr;
void check(HRESULT hr) { if (FAILED(hr)) { char message[80];snprintf(message,sizeof(message),"D3D12 HRESULT 0x%08lx",static_cast<unsigned long>(hr));throw std::runtime_error(message); } }
struct Commands {
  ID3D12GraphicsCommandList* list;
  void D3DBeginQuery(ID3D12QueryHeap* h,D3D12_QUERY_TYPE t,UINT i){list->BeginQuery(h,t,i);}
  void D3DEndQuery(ID3D12QueryHeap* h,D3D12_QUERY_TYPE t,UINT i){list->EndQuery(h,t,i);}
  void D3DResolveQueryData(ID3D12QueryHeap* h,D3D12_QUERY_TYPE t,UINT i,UINT n,ID3D12Resource* b,UINT64 o){list->ResolveQueryData(h,t,i,n,b,o);}
};
int test() {
  ComPtr<ID3D12Debug> debug;
  const HRESULT debug_result=D3D12GetDebugInterface(IID_PPV_ARGS(&debug));
  if(SUCCEEDED(debug_result))debug->EnableDebugLayer();
  else if(debug_result==DXGI_ERROR_SDK_COMPONENT_MISSING)puts("D3D12 debug layer unavailable; debug-message validation skipped.");
  else check(debug_result);
  ComPtr<IDXGIFactory4> factory;check(CreateDXGIFactory1(IID_PPV_ARGS(&factory)));
  ComPtr<IDXGIAdapter> adapter;check(factory->EnumWarpAdapter(IID_PPV_ARGS(&adapter)));
  ComPtr<ID3D12Device> device;check(D3D12CreateDevice(adapter.Get(),D3D_FEATURE_LEVEL_11_0,IID_PPV_ARGS(&device)));
  ComPtr<ID3D12InfoQueue> info;if(debug)check(device.As(&info));
  ComPtr<ID3D12CommandQueue> queue;D3D12_COMMAND_QUEUE_DESC q{};check(device->CreateCommandQueue(&q,IID_PPV_ARGS(&queue)));
  ComPtr<ID3D12CommandAllocator> allocator;check(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator)));
  ComPtr<ID3D12GraphicsCommandList> list;check(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),nullptr,IID_PPV_ARGS(&list)));
  Commands commands{list.Get()};
  D3D12_ROOT_SIGNATURE_DESC rd{};ComPtr<ID3DBlob> serialized,error;
  check(D3D12SerializeRootSignature(&rd,D3D_ROOT_SIGNATURE_VERSION_1,&serialized,&error));
  ComPtr<ID3D12RootSignature> root;check(device->CreateRootSignature(0,serialized->GetBufferPointer(),serialized->GetBufferSize(),IID_PPV_ARGS(&root)));
  const char* shader="float4 main(uint id:SV_VertexID):SV_Position { float2 p=float2((id<<1)&2,id&2); return float4(p*float2(2,-2)+float2(-1,1),0.5,1); }";
  ComPtr<ID3DBlob> vs;check(D3DCompile(shader,strlen(shader),nullptr,nullptr,nullptr,"main","vs_5_0",0,0,&vs,&error));
  D3D12_GRAPHICS_PIPELINE_STATE_DESC pd{};pd.pRootSignature=root.Get();pd.VS={vs->GetBufferPointer(),vs->GetBufferSize()};
  pd.SampleMask=UINT_MAX;pd.SampleDesc.Count=1;pd.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
  pd.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;pd.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;pd.RasterizerState.DepthClipEnable=TRUE;
  pd.DepthStencilState.DepthEnable=TRUE;pd.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ALL;
  pd.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_LESS;pd.DSVFormat=DXGI_FORMAT_D32_FLOAT;
  ComPtr<ID3D12PipelineState> pipeline;check(device->CreateGraphicsPipelineState(&pd,IID_PPV_ARGS(&pipeline)));
  D3D12_HEAP_PROPERTIES hp{};hp.Type=D3D12_HEAP_TYPE_DEFAULT;
  D3D12_RESOURCE_DESC td{};td.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;td.Width=td.Height=8;
  td.DepthOrArraySize=td.MipLevels=1;td.Format=DXGI_FORMAT_D32_FLOAT;td.SampleDesc.Count=1;td.Flags=D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL;
  D3D12_CLEAR_VALUE clear{};clear.Format=td.Format;clear.DepthStencil.Depth=1;
  ComPtr<ID3D12Resource> depth;check(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&td,D3D12_RESOURCE_STATE_DEPTH_WRITE,&clear,IID_PPV_ARGS(&depth)));
  D3D12_DESCRIPTOR_HEAP_DESC hd{};hd.Type=D3D12_DESCRIPTOR_HEAP_TYPE_DSV;hd.NumDescriptors=1;
  ComPtr<ID3D12DescriptorHeap> heap;check(device->CreateDescriptorHeap(&hd,IID_PPV_ARGS(&heap)));
  auto dsv=heap->GetCPUDescriptorHandleForHeapStart();device->CreateDepthStencilView(depth.Get(),nullptr,dsv);
  list->ClearDepthStencilView(dsv,D3D12_CLEAR_FLAG_DEPTH,1,0,0,nullptr);list->OMSetRenderTargets(0,nullptr,FALSE,&dsv);
  list->SetGraphicsRootSignature(root.Get());list->SetPipelineState(pipeline.Get());list->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
  D3D12_VIEWPORT viewport{0,0,8,8,0,1};D3D12_RECT scissor{0,0,8,8};list->RSSetViewports(1,&viewport);list->RSSetScissorRects(1,&scissor);
  auto& probe=rex::graphics::d3d12::SkyCoverageProbe::Get();
  for(UINT sequence=1;sequence<=2;++sequence){
    auto index=probe.Begin(device.Get(),commands,false,10,sequence,42,3,1,0);
    if(index==probe.kInvalid)throw std::runtime_error("Probe did not arm");
    list->DrawInstanced(3,1,0,0);probe.End(commands,index);
  }
  // The first draw covers 64 samples; the identical second draw fails LESS.
  // A guest query is active for the third draw. The diagnostic must skip it.
  D3D12_QUERY_HEAP_DESC qh{};qh.Type=D3D12_QUERY_HEAP_TYPE_OCCLUSION;qh.Count=1;
  ComPtr<ID3D12QueryHeap> guest;check(device->CreateQueryHeap(&qh,IID_PPV_ARGS(&guest)));
  list->BeginQuery(guest.Get(),D3D12_QUERY_TYPE_OCCLUSION,0);
  if(probe.Begin(device.Get(),commands,true,10,3,42,3,1,0)!=probe.kInvalid)throw std::runtime_error("Nested guest query");
  list->DrawInstanced(3,1,0,0);list->EndQuery(guest.Get(),D3D12_QUERY_TYPE_OCCLUSION,0);
  if(probe.Begin(device.Get(),commands,false,10,0,0,0,1,0)!=probe.kInvalid)throw std::runtime_error("Unarmed query");
  auto path=std::filesystem::path(_wgetenv(L"OPENH3M_SKY_TRACE_DIR"))/"coverage.csv";
  {std::ifstream input(path);std::string text((std::istreambuf_iterator<char>(input)),{});
   if(text.find("sample,")!=std::string::npos)throw std::runtime_error("Read before completed fence");}
  check(list->Close());ID3D12CommandList* submit=list.Get();queue->ExecuteCommandLists(1,&submit);
  ComPtr<ID3D12Fence> fence;check(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence)));
  HANDLE event=CreateEvent(nullptr,FALSE,FALSE,nullptr);check(queue->Signal(fence.Get(),1));check(fence->SetEventOnCompletion(1,event));
  if(WaitForSingleObject(event,10000)!=WAIT_OBJECT_0)throw std::runtime_error("GPU wait failed");CloseHandle(event);
  // A zero sequence still drains completed queries after the trace has stopped.
  probe.Begin(device.Get(),commands,false,11,0,0,0,2,fence->GetCompletedValue());probe.Shutdown(1);
  std::ifstream input(path);std::string text((std::istreambuf_iterator<char>(input)),{});
  if(text.find("sample,10,1,42,3,0,1,64\n")==std::string::npos || text.find("sample,10,2,42,3,1,1,0\n")==std::string::npos ||
     text.find("guest_query_active,10,3,")==std::string::npos || text.find("pending,")!=std::string::npos)throw std::runtime_error("Unexpected query result");
  for(UINT64 i=0;info && i<info->GetNumStoredMessages();++i){
    SIZE_T size=0;check(info->GetMessage(i,nullptr,&size));std::vector<uint8_t> bytes(size);
    auto* message=reinterpret_cast<D3D12_MESSAGE*>(bytes.data());check(info->GetMessage(i,message,&size));
    if(message->Severity<=D3D12_MESSAGE_SEVERITY_ERROR)throw std::runtime_error(message->pDescription);
  }
  puts("WARP coverage: 64 visible samples, zero depth-rejected samples, guest-query skip, completed-fence guard, and post-trace drain passed.");
  if(info)puts("D3D12 debug layer: no errors.");
  return 0;
}
int main(){try{return test();}catch(const std::exception& e){fprintf(stderr,"Coverage fixture failed: %s\n",e.what());return 1;}}
