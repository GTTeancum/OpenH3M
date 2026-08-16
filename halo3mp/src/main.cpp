// halo3mp - ReXGlue Recompiled Project

#include "generated/default/halo3mp_init.h"

#include "halo3mp_app.h"

// --- fault diagnostics -------------------------------------------------------
// Records faulting RIP, module base and RVA (Release has no PDB, so the RVA is
// symbolized offline against out/build/dbg/halo3mp.pdb), the enclosing guest
// function from the module's own func_mappings table, and a host backtrace.
// Writes halo3mp_fault.txt next to the executable.
#ifdef _WIN32
#include <windows.h>
#include <cstdio>
#include <cstdint>

namespace {

LONG CALLBACK Halo3mpFaultFilter(EXCEPTION_POINTERS* ep) {
  const auto code = ep->ExceptionRecord->ExceptionCode;
  if (code != EXCEPTION_ACCESS_VIOLATION && code != EXCEPTION_IN_PAGE_ERROR &&
      code != EXCEPTION_BREAKPOINT && code != EXCEPTION_ILLEGAL_INSTRUCTION &&
      code != EXCEPTION_STACK_OVERFLOW && code != 0xC0000409u) {
    return EXCEPTION_CONTINUE_SEARCH;
  }

  const auto rip = static_cast<uintptr_t>(ep->ContextRecord->Rip);
  uint64_t best_guest = 0;
  uintptr_t best_host = 0;
  for (const auto* m = PPCImageConfig.func_mappings; m && m->host; ++m) {
    const auto h = reinterpret_cast<uintptr_t>(m->host);
    if (h <= rip && h > best_host) {
      best_host = h;
      best_guest = static_cast<uint64_t>(m->guest);
    }
  }

  const bool is_av = (code == EXCEPTION_ACCESS_VIOLATION || code == EXCEPTION_IN_PAGE_ERROR);
  const auto op = is_av ? ep->ExceptionRecord->ExceptionInformation[0] : 0;
  const auto addr = is_av ? ep->ExceptionRecord->ExceptionInformation[1] : 0;
  const auto mod_base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));

  MEMORY_BASIC_INFORMATION mbi{};
  uintptr_t mod_end = mod_base;
  if (VirtualQuery(reinterpret_cast<void*>(mod_base), &mbi, sizeof(mbi))) {
    mod_end = mod_base + 0x8000000;  // generous upper bound for the .exe image
  }

  void* frames[48] = {};
  const USHORT n = RtlCaptureStackBackTrace(0, 48, frames, nullptr);

  if (FILE* f = std::fopen("halo3mp_fault.txt", "a")) {
    std::fprintf(f,
                 "code=0x%08lX %s fault_addr=0x%llX rip=0x%llX "
                 "module_base=0x%llX rva=0x%llX guest_fn=0x%08llX\n",
                 static_cast<unsigned long>(code),
                 op == 1 ? "write" : (op == 0 ? "read" : "exec"),
                 static_cast<unsigned long long>(addr),
                 static_cast<unsigned long long>(rip),
                 static_cast<unsigned long long>(mod_base),
                 static_cast<unsigned long long>(rip - mod_base),
                 static_cast<unsigned long long>(best_guest));
    for (USHORT i = 0; i < n; ++i) {
      const auto a = reinterpret_cast<uintptr_t>(frames[i]);
      if (a >= mod_base && a < mod_end) {
        std::fprintf(f, "  frame[%02u] rva=0x%llX\n", i,
                     static_cast<unsigned long long>(a - mod_base));
      } else {
        char name[MAX_PATH] = "?";
        HMODULE hm = nullptr;
        if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                   GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                               reinterpret_cast<LPCSTR>(a), &hm) &&
            hm) {
          GetModuleFileNameA(hm, name, MAX_PATH);
        }
        std::fprintf(f, "  frame[%02u] ext=0x%llX  %s+0x%llX\n", i,
                     static_cast<unsigned long long>(a), name,
                     static_cast<unsigned long long>(a - reinterpret_cast<uintptr_t>(hm)));
      }
    }
    std::fclose(f);
  }
  return EXCEPTION_CONTINUE_SEARCH;
}

struct FaultHandlerInstaller {
  FaultHandlerInstaller() { AddVectoredExceptionHandler(1, &Halo3mpFaultFilter); }
};

FaultHandlerInstaller g_halo3mp_fault_handler_installer;

}  // namespace
#endif
// -----------------------------------------------------------------------------

REX_DEFINE_APP(halo3mp, Halo3mpApp::Create)
