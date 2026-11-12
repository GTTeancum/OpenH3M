// Execute original retail pixel microcode with ReXGlue's existing ALU/control
// flow interpreter and explicit, repository-local texture inputs. No window,
// device, host input or automatic shader dump is created.
#include <rex/graphics/pipeline/shader/interpreter.h>
#include <rex/graphics/registers.h>
#include <rex/system/xmemory.h>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

std::string& FLAGS_dump_shaders_storage_() { static std::string disabled; return disabled; }
using namespace rex::graphics;
using V = std::array<float,4>;
template<class T> void Read(std::istream& stream,T* destination,size_t count) {
 stream.read(reinterpret_cast<char*>(destination),sizeof(T)*count);
 if(!stream)throw std::runtime_error("Truncated shader input");
}
struct Texture {
 unsigned width,height;bool wrap;std::vector<unsigned char> bytes;
 Texture(const std::filesystem::path& directory,unsigned id,unsigned w,unsigned h,bool repeat)
 :width(w),height(h),wrap(repeat),bytes(w*h*4) {
  std::ifstream stream(directory/(std::to_string(id)+".rgba"),std::ios::binary);
  Read(stream,bytes.data(),bytes.size());
  if(stream.peek()!=std::ifstream::traits_type::eof())throw std::runtime_error("Unexpected texture length");
 }
 V Texel(int x,int y)const {
  auto index=[&](int value,int size){return wrap?(value%size+size)%size:std::clamp(value,0,size-1);};
  const auto at=(index(y,height)*width+index(x,width))*4;
  return {bytes[at]/255.f,bytes[at+1]/255.f,bytes[at+2]/255.f,bytes[at+3]/255.f};
 }
 V Sample(float u,float v)const {
  float x=u*width-.5f,y=v*height-.5f;int ix=int(std::floor(x)),iy=int(std::floor(y));
  x-=ix;y-=iy;const auto a=Texel(ix,iy),b=Texel(ix+1,iy),c=Texel(ix,iy+1),d=Texel(ix+1,iy+1);
  V value;for(unsigned i=0;i<4;++i)value[i]=std::lerp(std::lerp(a[i],b[i],x),std::lerp(c[i],d[i],x),y);
  return value;
 }
};
struct Textures final:ShaderInterpreter::TextureFetchSource {
 std::vector<Texture> textures;size_t fetches=0;unsigned mask=0;
 Textures(const std::filesystem::path& directory,bool plasma) {
  if(plasma){textures.emplace_back(directory,7748,256,256,false);textures.emplace_back(directory,16659,256,1,false);
   textures.emplace_back(directory,419,128,128,true);textures.emplace_back(directory,341,128,128,true);}
  else textures.emplace_back(directory,16661,512,512,true);
 }
 V Fetch(ucode::TextureFetchInstruction instruction,const std::array<float,3>& uv)override {
  ++fetches;const auto slot=instruction.fetch_constant_index();mask|=1u<<slot;
  if(slot==14)return {.75f,.75f,.75f,.75f}; // Explicit synthetic depth fixture only.
  if(slot>=textures.size()||instruction.unnormalized_coordinates()||instruction.offset_x()||instruction.offset_y()||instruction.offset_z())
   throw std::runtime_error("Unsupported texture operation in marker shader");
  for(auto value:uv)if(!std::isfinite(value))throw std::runtime_error("Nonfinite texture coordinate");
  return textures[slot].Sample(uv[0],uv[1]); // Original marker volumes have a single slice.
 }
};
struct Output final:ShaderInterpreter::ExportSink {
 V color{};unsigned mask=0;
 void Export(ucode::ExportRegister reg,const float* value,uint32_t written)override {
  if(unsigned(reg)!=0)throw std::runtime_error("Unexpected shader export");
  for(unsigned i=0;i<4;++i)if(written&(1u<<i))color[i]=value[i];
  mask|=written;
 }
};
int main(int argc,char** argv)try {
 if(argc!=6)throw std::runtime_error("Usage: h4_forge_marker_shader_check 331|16 code.ucode cases.bin bitmap-directory output.bin");
 const bool plasma=std::string(argv[1])=="331";
 const bool fade=std::string(argv[1])=="fade";
 if(!plasma&&!fade&&std::string(argv[1])!="16")throw std::runtime_error("Unknown marker material");
 std::ifstream codeFile(argv[2],std::ios::binary|std::ios::ate);const auto size=codeFile.tellg();
 if(!codeFile||size<=0||size>65536||size%4)throw std::runtime_error("Invalid shader length");
 std::vector<uint32_t> code(size_t(size)/4);codeFile.seekg(0);Read(codeFile,code.data(),code.size());
 Shader shader(xenos::ShaderType::kPixel,0,code.data(),code.size());
 RegisterFile registers;reg::SQ_PS_CONST ps{};ps.base=0;ps.size=255;registers[XE_GPU_REG_SQ_PS_CONST]=ps.value;
 rex::memory::Memory memory;ShaderInterpreter interpreter(registers,memory);
 interpreter.SetShader(xenos::ShaderType::kPixel,shader.ucode_dwords());
 Textures textures(argv[4],plasma);Output output;
 interpreter.SetTextureFetchSource(&textures);interpreter.SetExportSink(&output);
 std::ifstream cases(argv[3],std::ios::binary);uint32_t count;Read(cases,&count,1);
 if(!count||count>100000)throw std::runtime_error("Invalid shader case count");
 std::ofstream results(argv[5],std::ios::binary|std::ios::trunc);
 for(unsigned i=0;i<count;++i){
  Read(cases,&registers[XE_GPU_REG_SHADER_CONSTANT_000_X],256*4);
  Read(cases,&registers[XE_GPU_REG_SHADER_CONSTANT_BOOL_000_031],8);
  std::fill_n(interpreter.temp_registers(),xenos::kMaxShaderTempRegisters*4,0.f);
  Read(cases,interpreter.temp_registers(),8*4);
  output={};interpreter.Execute();
  if(fade){std::copy_n(interpreter.temp_registers()+4*4,4,output.color.begin());output.mask=15;}
  if(output.mask!=15)throw std::runtime_error("Incomplete pixel output");
  for(float channel:output.color)if(!std::isfinite(channel))throw std::runtime_error("Nonfinite pixel output");
  results.write(reinterpret_cast<const char*>(output.color.data()),sizeof(output.color));
 }
 if(cases.peek()!=std::ifstream::traits_type::eof()||!results)throw std::runtime_error("Shader case/output length mismatch");
 std::cout<<"PASS original marker shader: "<<count<<" cases, "<<textures.fetches<<" texture fetches, sampler mask "<<textures.mask<<"\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
