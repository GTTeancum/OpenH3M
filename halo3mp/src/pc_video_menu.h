#pragma once
#include <cstdint>
#include <filesystem>
namespace spartan::video {
void InitializePCVideoMenu(const std::filesystem::path&);
void ForgetPCVideoSource(uint32_t source);
bool PCVideoText(uint8_t* base,uint32_t string_id,uint32_t output);
}
