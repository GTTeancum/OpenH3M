// Diagnostic only, for the hash-checked owned OpenH3M child. Load and call
// PrepareProbe before the debugger stops the owned child at its presenter
// entry; the debugger installs the jump only while all threads are stopped.
// Never attach this probe to a user's running game.
// No file changes, guest-memory writes, host input, or desktop capture.
// This is NOT a shipping hook: a successful trial must become a source patch.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

using Refresh = bool (*)(void*, unsigned, unsigned, unsigned, unsigned, void*);
static Refresh original;
static LONGLONG frequency, activated_at, deadline;
struct Stats {
  unsigned version, installed;
  unsigned long long calls, paced, waits, late;
};
extern "C" __declspec(dllexport) Stats ProbeState = {1, 0, 0, 0, 0, 0};

extern "C" __declspec(dllexport) bool RefreshPaced(void* presenter, unsigned width, unsigned height,
                         unsigned aspect_x, unsigned aspect_y, void* refresher) {
  ++ProbeState.calls;
  LARGE_INTEGER now;
  QueryPerformanceCounter(&now);
  // Keep the recorded menu route unchanged; enable only after match startup.
  if (now.QuadPart >= activated_at && width && height) {
    ++ProbeState.paced;
    const LONGLONG period = frequency / 30;
    if (!deadline) deadline = now.QuadPart;
    while (now.QuadPart < deadline) {
      ++ProbeState.waits;
      const LONGLONG remaining_ms = (deadline - now.QuadPart) * 1000 / frequency;
      Sleep(remaining_ms > 1 ? static_cast<DWORD>(remaining_ms - 1) : 0);
      QueryPerformanceCounter(&now);
    }
    if (now.QuadPart - deadline > period) {
      ++ProbeState.late;
      deadline = now.QuadPart;
    }
    deadline += period;
  }
  return original(presenter, width, height, aspect_x, aspect_y, refresher);
}

static void Jump(volatile unsigned char* at, const void* destination) {
  at[0] = 0xff; at[1] = 0x25;
  for (int i = 2; i < 6; ++i) at[i] = 0;
  const auto address = reinterpret_cast<unsigned long long>(destination);
  for (int i = 0; i < 8; ++i) at[6 + i] = static_cast<unsigned char>(address >> (i * 8));
}

extern "C" __declspec(dllexport) DWORD WINAPI PrepareProbe(void*) {
  if (ProbeState.installed) return 1;
  HMODULE runtime = GetModuleHandleW(L"rexruntime.dll");
  if (!runtime) return 2;
  auto entry = reinterpret_cast<unsigned char*>(GetProcAddress(runtime,
    "?RefreshGuestOutput@Presenter@ui@rex@@QEAA_NIIIIV?$function@$$A6A_NAEAVGuestOutputRefreshContext@Presenter@ui@rex@@@Z@std@@@Z"));
  if (!entry) return 3;
  // Entire 15-byte prologue: pushes and stack reservation, no relative operands.
  const unsigned char expected[] = {0x55,0x41,0x57,0x41,0x56,0x56,0x57,0x53,
                                   0x48,0x81,0xec,0x88,0,0,0};
  for (unsigned i = 0; i < sizeof(expected); ++i) if (entry[i] != expected[i]) return 4;
  auto trampoline = static_cast<unsigned char*>(VirtualAlloc(nullptr, 32,
      MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE));
  if (!trampoline) return 5;
  for (unsigned i = 0; i < sizeof(expected); ++i) trampoline[i] = entry[i];
  Jump(trampoline + sizeof(expected), entry + sizeof(expected));
  DWORD previous;
  if (!VirtualProtect(trampoline, 32, PAGE_EXECUTE_READ, &previous)) {
    VirtualFree(trampoline, 0, MEM_RELEASE); return 6;
  }
  FlushInstructionCache(GetCurrentProcess(), trampoline, 32);
  LARGE_INTEGER counter;
  QueryPerformanceFrequency(&counter); frequency = counter.QuadPart;
  QueryPerformanceCounter(&counter); activated_at = counter.QuadPart + 95 * frequency;
  original = reinterpret_cast<Refresh>(trampoline);
  // No live code writes here. The debugger arms the prepared target.
  ProbeState.installed = 1;
  return 0;
}

extern "C" BOOL WINAPI DllMain(HINSTANCE, DWORD, LPVOID) { return TRUE; }
