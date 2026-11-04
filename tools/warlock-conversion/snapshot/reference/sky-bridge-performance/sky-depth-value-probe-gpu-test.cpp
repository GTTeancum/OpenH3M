#include <windows.h>
#include <d3d12.h>
#include <d3d12sdklayers.h>
#include <d3dcompiler.h>
#include <dxgi1_6.h>
#include <wrl/client.h>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include "sky_depth_value_probe.h"
using Microsoft::WRL::ComPtr;
using Probe=rex::graphics::d3d12::SkyDepthValueProbe;
void check(HRESULT hr){if(FAILED(hr)){char s[80];snprintf(s,sizeof(s),"D3D12 HRESULT 0x%08lx",static_cast<unsigned long>(hr));throw std::runtime_error(s);}}
struct Commands{
  ID3D12GraphicsCommandList* list;
  void D3DSetComputeRootSignature(ID3D12RootSignature* r){list->SetComputeRootSignature(r);}
  void D3DSetComputeRootDescriptorTable(UINT i,D3D12_GPU_DESCRIPTOR_HANDLE h){list->SetComputeRootDescriptorTable(i,h);}
  void D3DSetComputeRootUnorderedAccessView(UINT i,D3D12_GPU_VIRTUAL_ADDRESS a){list->SetComputeRootUnorderedAccessView(i,a);}
  void D3DSetComputeRoot32BitConstants(UINT i,UINT n,const void* v,UINT o){list->SetComputeRoot32BitConstants(i,n,v,o);}
  void D3DDispatch(UINT x,UINT y,UINT z){list->Dispatch(x,y,z);}
  void D3DCopyBufferRegion(ID3D12Resource* d,UINT64 a,ID3D12Resource* s,UINT64 b,UINT64 n){list->CopyBufferRegion(d,a,s,b,n);}
};
int test(){
  ComPtr<ID3D12Debug> debug;const auto debug_result=D3D12GetDebugInterface(IID_PPV_ARGS(&debug));
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
  D3D12_DESCRIPTOR_HEAP_DESC hd{};hd.Type=D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV;hd.NumDescriptors=16;hd.Flags=D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;
  ComPtr<ID3D12DescriptorHeap> views;check(device->CreateDescriptorHeap(&hd,IID_PPV_ARGS(&views)));
  auto* view_heap=views.Get();list->SetDescriptorHeaps(1,&view_heap);
  UINT allocated=0;const auto increment=device->GetDescriptorHandleIncrementSize(hd.Type);
  auto allocate=[&](D3D12_CPU_DESCRIPTOR_HANDLE& cpu,D3D12_GPU_DESCRIPTOR_HANDLE& gpu){
    if(allocated==16)throw std::runtime_error("Too many descriptors");
    cpu=views->GetCPUDescriptorHandleForHeapStart();gpu=views->GetGPUDescriptorHandleForHeapStart();
    cpu.ptr+=allocated*increment;gpu.ptr+=allocated*increment;++allocated;return true;
  };
  auto forbidden=[](D3D12_CPU_DESCRIPTOR_HANDLE&,D3D12_GPU_DESCRIPTOR_HANDLE&)->bool{throw std::runtime_error("Unsafe scope accessed descriptors");};
  bool guest_pipeline_valid=true;
  auto set_pipeline=[&](ID3D12PipelineState* p){guest_pipeline_valid=false;list->SetPipelineState(p);};
  auto barrier=[&](ID3D12Resource* r,D3D12_RESOURCE_STATES before,D3D12_RESOURCE_STATES after){
    if(before==after)return;D3D12_RESOURCE_BARRIER b{};b.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    b.Transition={r,D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES,before,after};list->ResourceBarrier(1,&b);
  };
  auto flush=[](){};
  D3D12_ROOT_SIGNATURE_DESC rd{};ComPtr<ID3DBlob> serialized,error;
  check(D3D12SerializeRootSignature(&rd,D3D_ROOT_SIGNATURE_VERSION_1,&serialized,&error));
  ComPtr<ID3D12RootSignature> root;check(device->CreateRootSignature(0,serialized->GetBufferPointer(),serialized->GetBufferSize(),IID_PPV_ARGS(&root)));
  const char* shader="float4 main(uint id:SV_VertexID):SV_Position {float2 p=float2((id<<1)&2,id&2);return float4(p*float2(2,-2)+float2(-1,1),0.5,1);}";
  ComPtr<ID3DBlob> vs;check(D3DCompile(shader,strlen(shader),nullptr,nullptr,nullptr,"main","vs_5_0",0,0,&vs,&error));
  D3D12_GRAPHICS_PIPELINE_STATE_DESC pd{};pd.pRootSignature=root.Get();pd.VS={vs->GetBufferPointer(),vs->GetBufferSize()};
  pd.SampleMask=UINT_MAX;pd.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
  pd.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;pd.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;pd.RasterizerState.DepthClipEnable=TRUE;
  pd.DepthStencilState.DepthEnable=TRUE;pd.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ALL;
  pd.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_GREATER_EQUAL;pd.DSVFormat=DXGI_FORMAT_D32_FLOAT_S8X24_UINT;
  pd.DepthStencilState.StencilEnable=TRUE;pd.DepthStencilState.StencilReadMask=255;pd.DepthStencilState.StencilWriteMask=255;
  pd.DepthStencilState.FrontFace={D3D12_STENCIL_OP_KEEP,D3D12_STENCIL_OP_KEEP,D3D12_STENCIL_OP_INCR_SAT,D3D12_COMPARISON_FUNC_EQUAL};
  pd.DepthStencilState.BackFace=pd.DepthStencilState.FrontFace;
  D3D12_QUERY_HEAP_DESC qh{};qh.Type=D3D12_QUERY_HEAP_TYPE_OCCLUSION;qh.Count=2;
  ComPtr<ID3D12QueryHeap> queries;check(device->CreateQueryHeap(&qh,IID_PPV_ARGS(&queries)));
  D3D12_HEAP_PROPERTIES hp{};hp.Type=D3D12_HEAP_TYPE_READBACK;
  D3D12_RESOURCE_DESC bd{};bd.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;bd.Width=16;bd.Height=bd.DepthOrArraySize=bd.MipLevels=1;bd.SampleDesc.Count=1;bd.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
  ComPtr<ID3D12Resource> counts;check(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&bd,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&counts)));
  hd.Type=D3D12_DESCRIPTOR_HEAP_TYPE_DSV;hd.NumDescriptors=2;hd.Flags=D3D12_DESCRIPTOR_HEAP_FLAG_NONE;
  ComPtr<ID3D12DescriptorHeap> dsv_heap;check(device->CreateDescriptorHeap(&hd,IID_PPV_ARGS(&dsv_heap)));
  std::array<ComPtr<ID3D12Resource>,2> depths;std::array<ComPtr<ID3D12PipelineState>,2> pipelines;
  auto& probe=Probe::Get();constexpr uint64_t ps_hash=8562590739555380577ull;
  for(UINT test=0;test<2;++test){
    const UINT samples=test?4:1;pd.SampleDesc.Count=samples;
    check(device->CreateGraphicsPipelineState(&pd,IID_PPV_ARGS(&pipelines[test])));
    hp.Type=D3D12_HEAP_TYPE_DEFAULT;
    D3D12_RESOURCE_DESC td{};td.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;td.Width=1024;td.Height=256;
    td.DepthOrArraySize=td.MipLevels=1;td.Format=DXGI_FORMAT_R32G8X24_TYPELESS;td.SampleDesc.Count=samples;td.Flags=D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL;
    D3D12_CLEAR_VALUE clear{};clear.Format=pd.DSVFormat;clear.DepthStencil.Depth=0;clear.DepthStencil.Stencil=5;
    check(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&td,D3D12_RESOURCE_STATE_DEPTH_WRITE,&clear,IID_PPV_ARGS(&depths[test])));
    auto dsv=dsv_heap->GetCPUDescriptorHandleForHeapStart();dsv.ptr+=test*device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_DSV);
    D3D12_DEPTH_STENCIL_VIEW_DESC dv{};dv.Format=pd.DSVFormat;dv.ViewDimension=test?D3D12_DSV_DIMENSION_TEXTURE2DMS:D3D12_DSV_DIMENSION_TEXTURE2D;
    device->CreateDepthStencilView(depths[test].Get(),&dv,dsv);
    list->ClearDepthStencilView(dsv,D3D12_CLEAR_FLAGS(D3D12_CLEAR_FLAG_DEPTH|D3D12_CLEAR_FLAG_STENCIL),0,5,0,nullptr);
    for(UINT p=0;p<4;++p){D3D12_RECT rect{LONG(Probe::points[p][0]),LONG(Probe::points[p][1]),LONG(Probe::points[p][0]+1),LONG(Probe::points[p][1]+1)};
      list->ClearDepthStencilView(dsv,D3D12_CLEAR_FLAG_DEPTH,float(p+1)*.25f,5,1,&rect);}
    list->OMSetRenderTargets(0,nullptr,FALSE,&dsv);
    probe.Record(device.Get(),commands,depths[test].Get(),DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS,D3D12_RESOURCE_STATE_DEPTH_WRITE,
      10,test+1,ps_hash,562,0,false,false,true,1,0,allocate,set_pipeline,barrier,flush);
    if(guest_pipeline_valid)throw std::runtime_error("Caller PSO cache was not invalidated");
    list->SetGraphicsRootSignature(root.Get());list->SetPipelineState(pipelines[test].Get());guest_pipeline_valid=true;
    list->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);list->OMSetStencilRef(5);
    D3D12_VIEWPORT viewport{0,0,1024,256,0,1};D3D12_RECT scissor{0,0,1024,256};list->RSSetViewports(1,&viewport);list->RSSetScissorRects(1,&scissor);
    list->BeginQuery(queries.Get(),D3D12_QUERY_TYPE_OCCLUSION,test);list->DrawInstanced(3,1,0,0);list->EndQuery(queries.Get(),D3D12_QUERY_TYPE_OCCLUSION,test);
    list->ResolveQueryData(queries.Get(),D3D12_QUERY_TYPE_OCCLUSION,test,1,counts.Get(),test*8);
    probe.Record(device.Get(),commands,depths[test].Get(),DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS,D3D12_RESOURCE_STATE_DEPTH_WRITE,
      10,test+1,ps_hash,562,1,false,false,true,1,0,allocate,set_pipeline,barrier,flush);
  }
  for(UINT guard=0;guard<3;++guard)
    probe.Record(device.Get(),commands,depths[0].Get(),DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS,D3D12_RESOURCE_STATE_DEPTH_WRITE,
      10,3+guard,ps_hash,562,0,guard==0,guard==1,guard!=2,1,0,forbidden,set_pipeline,barrier,flush);
  probe.Poll(0);auto path=std::filesystem::path(_wgetenv(L"OPENH3M_SKY_TRACE_DIR"))/"depth-values.csv";
  {std::ifstream f(path);std::string data((std::istreambuf_iterator<char>(f)),{});if(data.find("\nsample,")!=std::string::npos)throw std::runtime_error("Read before completed fence");}
  check(list->Close());ID3D12CommandList* submit=list.Get();queue->ExecuteCommandLists(1,&submit);
  ComPtr<ID3D12Fence> fence;check(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence)));
  HANDLE event=CreateEvent(nullptr,FALSE,FALSE,nullptr);check(queue->Signal(fence.Get(),1));check(fence->SetEventOnCompletion(1,event));
  if(WaitForSingleObject(event,10000)!=WAIT_OBJECT_0)throw std::runtime_error("GPU wait failed");CloseHandle(event);
  void* mapping=nullptr;D3D12_RANGE range{0,16};check(counts->Map(0,&range,&mapping));
  auto* coverage=static_cast<uint64_t*>(mapping);
  if(coverage[0]!=262142||coverage[1]!=262142*4)throw std::runtime_error("Sparse read changed guest depth/stencil coverage");
  D3D12_RANGE none{0,0};counts->Unmap(0,&none);
  probe.Record(device.Get(),commands,nullptr,DXGI_FORMAT_UNKNOWN,D3D12_RESOURCE_STATE_COMMON,
    11,0,ps_hash,562,0,false,false,true,2,1,forbidden,set_pipeline,barrier,flush);probe.Shutdown(1);
  std::ifstream f(path);std::string line;UINT rows=0,guards=0;
  while(std::getline(f,line)){
    if(line.rfind("unsafe_scope,",0)==0){++guards;continue;}
    if(line.rfind("sample,",0)!=0){if(line.rfind("event,",0)&&line.rfind("end,",0))throw std::runtime_error(line);continue;}
    std::stringstream parts(line);std::vector<std::string> columns;std::string value;while(std::getline(parts,value,','))columns.push_back(value);
    if(columns.size()!=17)throw std::runtime_error("Bad depth CSV");
    UINT phase=std::stoul(columns[3]),x=std::stoul(columns[13]),y=std::stoul(columns[14]);
    UINT point=0;while(point<4&&(Probe::points[point][0]!=x||Probe::points[point][1]!=y))++point;
    if(point==4)throw std::runtime_error("Bad depth coordinate");
    float expected=phase&&point<2?.5f:float(point+1)*.25f;uint32_t bits;memcpy(&bits,&expected,4);
    if(std::stoul(columns[16])!=bits)throw std::runtime_error("Sparse GPU depth bits differ");++rows;
  }
  if(rows!=40||guards!=3||allocated!=4)throw std::runtime_error("Wrong record/guard/descriptor count");
  for(UINT64 i=0;info&&i<info->GetNumStoredMessages();++i){SIZE_T size=0;check(info->GetMessage(i,nullptr,&size));std::vector<uint8_t> bytes(size);
    auto* message=reinterpret_cast<D3D12_MESSAGE*>(bytes.data());check(info->GetMessage(i,message,&size));
    if(message->Severity<=D3D12_MESSAGE_SEVERITY_ERROR)throw std::runtime_error(message->pDescription);}
  puts("WARP sparse depth passed: exact 1x/4x samples before/after actual draws; unchanged depth/stencil coverage; PSO-cache invalidation; fence-gated drain; guest-query/memexport/non-host guards.");
  return 0;
}
int main(){try{return test();}catch(const std::exception& e){fprintf(stderr,"Depth-value fixture failed: %s\n",e.what());return 1;}}
