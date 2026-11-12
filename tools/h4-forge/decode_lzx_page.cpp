// Decode a private retail H4 XMem resource stream with ReXGlue's LZX decoder.
#include <rex/system/lzx.h>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>
#include <algorithm>
int main(int argc,char** argv){try{
 if(argc!=4)throw std::runtime_error("input output decompressed-size required");
 const auto expected=std::stoul(argv[3]);
 if(!expected||expected>64*1024*1024)throw std::runtime_error("Invalid page size");
 std::ifstream in(argv[1],std::ios::binary);
 if(!in)throw std::runtime_error("Cannot open compressed page");
 std::vector<unsigned char> framed((std::istreambuf_iterator<char>(in)),{}),payload;
 size_t at=0,total=0;
 auto word=[&](){if(at+2>framed.size())throw std::runtime_error("Truncated XMem frame");auto v=(framed[at]<<8)|framed[at+1];at+=2;return unsigned(v);};
 while(at<framed.size()){
  unsigned decoded=0x8000,compressed=0;
  if(framed[at]==0xff){++at;decoded=word();compressed=word();}else compressed=word();
  if(!compressed&&total==expected&&framed.size()-at<=6&&
     std::all_of(framed.begin()+at,framed.end(),[](auto v){return v==0;}))break;
  if(!compressed||!decoded||decoded>0x8000||at+compressed>framed.size())throw std::runtime_error("Invalid XMem frame bounds at "+std::to_string(at)+" compressed="+std::to_string(compressed)+" decoded="+std::to_string(decoded)+" total="+std::to_string(total));
  payload.insert(payload.end(),framed.begin()+at,framed.begin()+at+compressed);at+=compressed;total+=decoded;
 }
 if(total!=expected)throw std::runtime_error("XMem frame output sizes disagree");
 std::vector<unsigned char> output(expected);
 if(lzx_decompress(payload.data(),payload.size(),output.data(),output.size(),0x20000,nullptr,0))throw std::runtime_error("LZX decoding failed");
 std::ofstream out(argv[2],std::ios::binary|std::ios::trunc);out.write(reinterpret_cast<const char*>(output.data()),output.size());
 if(!out)throw std::runtime_error("Cannot write decoded page");
 std::cout<<"Decoded "<<expected<<" bytes; caller must verify original page checksum\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
