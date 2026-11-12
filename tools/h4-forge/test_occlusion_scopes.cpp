// Headless D3D12 regression: an emulator maintenance draw must not turn a
// hidden guest probe visible. No window, swap chain, or host input is created.
#include <windows.h>
#include <d3d12.h>
#include <d3dcompiler.h>
#include <wrl/client.h>
#include <array>
#include <cstdio>
#include <cstring>
#include <stdexcept>
using Microsoft::WRL::ComPtr;
static void Check(HRESULT hr) {
  if (FAILED(hr)) { std::fprintf(stderr,"HRESULT %08lx\n",hr); throw std::runtime_error("D3D12 failure"); }
}
static void Run(ID3D12Device* device, unsigned msaa) {
  D3D12_FEATURE_DATA_MULTISAMPLE_QUALITY_LEVELS quality{DXGI_FORMAT_D32_FLOAT,msaa};
  Check(device->CheckFeatureSupport(D3D12_FEATURE_MULTISAMPLE_QUALITY_LEVELS,&quality,sizeof(quality)));
  if (!quality.NumQualityLevels) throw std::runtime_error("Required MSAA unsupported");
  ComPtr<ID3D12CommandQueue> queue;
  D3D12_COMMAND_QUEUE_DESC qd{};
  Check(device->CreateCommandQueue(&qd,IID_PPV_ARGS(&queue)));
  ComPtr<ID3D12CommandAllocator> allocator;
  Check(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator)));
  ComPtr<ID3D12GraphicsCommandList> list;
  Check(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),nullptr,IID_PPV_ARGS(&list)));
  D3D12_ROOT_PARAMETER param{};
  param.ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;
  param.Constants.Num32BitValues=1;
  param.ShaderVisibility=D3D12_SHADER_VISIBILITY_VERTEX;
  D3D12_ROOT_SIGNATURE_DESC rd{1,&param};
  ComPtr<ID3DBlob> blob,error;
  Check(D3D12SerializeRootSignature(&rd,D3D_ROOT_SIGNATURE_VERSION_1,&blob,&error));
  ComPtr<ID3D12RootSignature> root;
  Check(device->CreateRootSignature(0,blob->GetBufferPointer(),blob->GetBufferSize(),IID_PPV_ARGS(&root)));
  const char* source=R"(
    cbuffer Depth : register(b0) { float z; }
    float4 main(uint id:SV_VertexID):SV_Position {
      float2 p[3]={float2(-1,-1),float2(-1,3),float2(3,-1)};
      return float4(p[id],z,1);
    })";
  ComPtr<ID3DBlob> vs;
  Check(D3DCompile(source,std::strlen(source),nullptr,nullptr,nullptr,"main","vs_5_0",0,0,&vs,&error));
  D3D12_GRAPHICS_PIPELINE_STATE_DESC pd{};
  pd.pRootSignature=root.Get();
  pd.VS={vs->GetBufferPointer(),vs->GetBufferSize()};
  pd.SampleMask=UINT_MAX;
  pd.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;
  pd.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;
  pd.RasterizerState.DepthClipEnable=TRUE;
  pd.DepthStencilState.DepthEnable=TRUE;
  pd.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ZERO;
  pd.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_LESS;
  pd.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
  pd.DSVFormat=DXGI_FORMAT_D32_FLOAT;
  pd.SampleDesc.Count=msaa;
  ComPtr<ID3D12PipelineState> pipeline;
  Check(device->CreateGraphicsPipelineState(&pd,IID_PPV_ARGS(&pipeline)));
  D3D12_HEAP_PROPERTIES hp{};hp.Type=D3D12_HEAP_TYPE_DEFAULT;
  D3D12_RESOURCE_DESC td{};
  td.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;td.Width=64;td.Height=64;
  td.DepthOrArraySize=1;td.MipLevels=1;td.Format=DXGI_FORMAT_D32_FLOAT;
  td.SampleDesc.Count=msaa;td.Flags=D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL;
  D3D12_CLEAR_VALUE cv{};cv.Format=td.Format;cv.DepthStencil.Depth=.5f;
  ComPtr<ID3D12Resource> depth;
  Check(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&td,D3D12_RESOURCE_STATE_DEPTH_WRITE,&cv,IID_PPV_ARGS(&depth)));
  D3D12_DESCRIPTOR_HEAP_DESC hd{};hd.Type=D3D12_DESCRIPTOR_HEAP_TYPE_DSV;hd.NumDescriptors=1;
  ComPtr<ID3D12DescriptorHeap> heap;
  Check(device->CreateDescriptorHeap(&hd,IID_PPV_ARGS(&heap)));
  auto dsv=heap->GetCPUDescriptorHandleForHeapStart();device->CreateDepthStencilView(depth.Get(),nullptr,dsv);
  constexpr unsigned count=5;
  D3D12_QUERY_HEAP_DESC qh{};qh.Type=D3D12_QUERY_HEAP_TYPE_OCCLUSION;qh.Count=count;
  ComPtr<ID3D12QueryHeap> queries;
  Check(device->CreateQueryHeap(&qh,IID_PPV_ARGS(&queries)));
  D3D12_RESOURCE_DESC bd{};bd.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;bd.Width=8*count;
  bd.Height=1;bd.DepthOrArraySize=1;bd.MipLevels=1;bd.SampleDesc.Count=1;bd.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
  hp.Type=D3D12_HEAP_TYPE_READBACK;
  ComPtr<ID3D12Resource> readback;
  Check(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&bd,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&readback)));
  D3D12_VIEWPORT vp{0,0,64,64,0,1};D3D12_RECT sc{0,0,64,64};
  auto bind=[&] {
    list->SetGraphicsRootSignature(root.Get());list->SetPipelineState(pipeline.Get());
    list->RSSetViewports(1,&vp);list->RSSetScissorRects(1,&sc);
    list->OMSetRenderTargets(0,nullptr,FALSE,&dsv);
    list->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
  };
  auto draw=[&](float z) {list->SetGraphicsRoot32BitConstants(0,1,&z,0);list->DrawInstanced(3,1,0,0);};
  auto begin=[&](unsigned i) {list->BeginQuery(queries.Get(),D3D12_QUERY_TYPE_OCCLUSION,i);};
  auto end=[&](unsigned i) {list->EndQuery(queries.Get(),D3D12_QUERY_TYPE_OCCLUSION,i);};
  bind();list->ClearDepthStencilView(dsv,D3D12_CLEAR_FLAG_DEPTH,.5f,0,0,nullptr);
  // Old scope includes a visible host-only transfer and a hidden game draw.
  begin(0);draw(.25f);draw(.75f);end(0);
  // Correct scope excludes the identical host-only work.
  draw(.25f);begin(1);draw(.75f);end(1);
  // A visible game draw must still contribute its samples.
  draw(.25f);begin(2);draw(.25f);end(2);
  // One title interval may contain multiple draws across submissions.
  begin(3);draw(.75f);end(3);
  list->ResolveQueryData(queries.Get(),D3D12_QUERY_TYPE_OCCLUSION,0,4,readback.Get(),0);
  Check(list->Close());ID3D12CommandList* lists[]={list.Get()};queue->ExecuteCommandLists(1,lists);
  ComPtr<ID3D12Fence> fence;Check(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence)));
  HANDLE event=CreateEvent(nullptr,FALSE,FALSE,nullptr);
  if(!event) throw std::runtime_error("CreateEvent failed");
  auto wait=[&](UINT64 value) {
    Check(queue->Signal(fence.Get(),value));Check(fence->SetEventOnCompletion(value,event));
    if(WaitForSingleObject(event,10000)!=WAIT_OBJECT_0) throw std::runtime_error("GPU timeout");
  };
  wait(1);Check(allocator->Reset());Check(list->Reset(allocator.Get(),nullptr));bind();
  draw(.25f);begin(4);draw(.25f);end(4);
  list->ResolveQueryData(queries.Get(),D3D12_QUERY_TYPE_OCCLUSION,4,1,readback.Get(),32);
  Check(list->Close());queue->ExecuteCommandLists(1,lists);wait(2);CloseHandle(event);
  D3D12_RANGE range{0,8*count};void* mapped=nullptr;Check(readback->Map(0,&range,&mapped));
  std::array<UINT64,count> result;std::memcpy(result.data(),mapped,sizeof(result));
  D3D12_RANGE no_write{0,0};readback->Unmap(0,&no_write);
  const UINT64 expected=64*64*msaa;
  if(result[0]!=expected || result[1]!=0 || result[2]!=expected || result[3]+result[4]!=expected)
    throw std::runtime_error("Visibility query sample mismatch");
  std::printf("%ux MSAA: polluted=%llu hidden=%llu visible=%llu split=%llu PASS\n",
      msaa,result[0],result[1],result[2],result[3]+result[4]);
}
int main() {
  try {
    ComPtr<ID3D12Device> device;
    Check(D3D12CreateDevice(nullptr,D3D_FEATURE_LEVEL_11_0,IID_PPV_ARGS(&device)));
    Run(device.Get(),1);Run(device.Get(),4);return 0;
  } catch(const std::exception& e) {std::fprintf(stderr,"%s\n",e.what());return 1;}
}
