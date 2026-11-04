#pragma once
// One bounded native-state read at the seated-view boundary. Never restores it.
#include <windows.h>
#include <cstdio>
#include <vector>

namespace sky_reproduction {
inline bool SaveNativeState(uint8_t* base,uint32_t tls,uint32_t guest_site,const std::filesystem::path& directory) {
  const auto path=directory/L"native-state.bin";
  FILE* output=_wfopen(path.c_str(),L"wbx");if(!output)return false;
  const uint32_t header[]{0x534e4b53,2};
  const uint64_t time_ns=uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::system_clock::now().time_since_epoch()).count());
  bool ok=fwrite(header,sizeof(header),1,output)==1&&fwrite(&time_ns,sizeof(time_ns),1,output)==1;
  const uint32_t context[]{guest_site,tls};ok=ok&&fwrite(context,sizeof(context),1,output)==1;
  size_t total=0;unsigned records=0;
  auto read=[&](uint32_t at,uint32_t size,std::vector<uint8_t>& data){
    if(at<0x10000||uint64_t(at)+size>0xe0000000ull||size>2*1024*1024)return false;
    data.resize(size);SIZE_T count=0;
    return ReadProcessMemory(GetCurrentProcess(),base+at,data.data(),size,&count)&&count==size;
  };
  auto word=[](const std::vector<uint8_t>& data,size_t at){
    uint32_t value;std::memcpy(&value,data.data()+at,4);return std::byteswap(value);
  };
  auto save=[&](const char* name,uint32_t at,uint32_t size,std::vector<uint8_t>& data){
    if(!ok||total+size>16*1024*1024||!read(at,size,data))return false;
    std::array<char,32> label{};std::snprintf(label.data(),label.size(),"%s",name);
    const uint32_t fields[]{at,size};
    ok=fwrite(label.data(),label.size(),1,output)==1&&fwrite(fields,sizeof(fields),1,output)==1&&
       fwrite(data.data(),size,1,output)==1;
    total+=size;++records;return ok;
  };
  std::vector<uint8_t> tls_data,data;
  bool required=save("tls",tls,0x800,tls_data);
  if(required){
    const uint32_t observer=word(tls_data,0x2cc),game=word(tls_data,0x80),engine=word(tls_data,0x64);
    required=save("observer",observer,0xf28,data)&&save("game_globals",game,0x1000,data)&&
      save("game_engine",engine,0x78,data)&&save("map_variant",engine+0x78,0xe090,data);
    for(uint32_t offset=0;offset<0x800;offset+=4){
      const uint32_t pointer=word(tls_data,offset);char name[32];
      std::snprintf(name,sizeof(name),"tls_block_0x%x",offset);
      if(!save(name,pointer,0x400,data))continue;
      const bool objects=std::memcmp(data.data(),"object\0",7)==0;
      const bool players=std::memcmp(data.data(),"players\0",8)==0;
      const bool effects=std::memcmp(data.data(),"effect\0",7)==0||
        std::memcmp(data.data(),"effect event\0",13)==0||
        std::memcmp(data.data(),"effect location\0",16)==0||
        std::memcmp(data.data(),"lights\0",7)==0||
        std::memcmp(data.data(),"particle_system\0",16)==0||
        std::memcmp(data.data(),"particle_emitter\0",17)==0||
        std::memcmp(data.data(),"particle_location\0",18)==0;
      if(!objects&&!players&&!effects)continue;
      const uint32_t count=word(data,0x20),stride=word(data,0x24),payload=word(data,0x44);
      if(!count||count>4096||!stride||stride>65536||uint64_t(count)*stride>2*1024*1024)continue;
      std::vector<uint8_t> table;
      std::snprintf(name,sizeof(name),"table_0x%x",offset);
      if(!save(objects?"object":players?"players":name,payload,count*stride,table))continue;
      if(objects&&stride==16)for(uint32_t i=0;i<count;++i){
        const uint32_t salt=word(table,i*16)>>16,body=word(table,i*16+12);
        if(!salt||body<0x80000000||body>=0xe0000000)continue;
        std::snprintf(name,sizeof(name),"object_0x%x",salt<<16|i);
        const uint32_t body_size=word(table,i*16+4)&65535;
        const bool full=table[i*16+3]<=1&&body_size>=0x400;
        save(name,body,full?body_size:0x400,data);
      }
    }
  }
  const uint32_t trailer[]{0x444e4553,uint32_t(required&&ok),records,uint32_t(total)};
  const bool complete=fwrite(trailer,sizeof(trailer),1,output)==1&&required&&ok;
  fclose(output);
  REXLOG_INFO("[sky-repro] native state saved complete={} records={} bytes={}",complete,records,total);
  return complete;
}
}
