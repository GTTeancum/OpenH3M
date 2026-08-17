// halo3mp - ReXGlue Recompiled Project
//
// Customize your app by overriding virtual hooks from rex::ReXApp.

#pragma once

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <iomanip>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <objbase.h>
#include <wincodec.h>
#endif

#include <rex/cvar.h>
#include <rex/logging/macros.h>
#include <rex/rex_app.h>
#include <rex/runtime.h>
#include <rex/system/interfaces/graphics.h>
#include <rex/system/gpu_plugin.h>
#include <rex/ui/imgui_drawer.h>
#include <rex/ui/presenter.h>
#include <rex/ui/window.h>
#include <rex/ui/windowed_app_context.h>

REXCVAR_DEFINE_BOOL(halo3mp_title_fps, true, "Halo3MP",
                    "Show guest output FPS in the host window title bar");
REXCVAR_DEFINE_UINT32(halo3mp_title_fps_interval_ms, 1000, "Halo3MP",
                      "Host title-bar FPS update interval in milliseconds");
REXCVAR_DEFINE_BOOL(halo3mp_log_fps, false, "Halo3MP",
                    "Log host-measured guest output FPS at the title-bar FPS interval");
REXCVAR_DEFINE_UINT32(halo3mp_capture_guest_output_after_ms, 0, "Halo3MP",
                      "Capture the internal guest output after this many milliseconds; 0 disables");
REXCVAR_DEFINE_STRING(halo3mp_capture_guest_output_times_ms, "", "Halo3MP",
                      "Comma-separated internal guest-output capture times in milliseconds");
REXCVAR_DEFINE_STRING(halo3mp_capture_guest_output_path, "", "Halo3MP",
                      "Path for the internal guest-output capture; defaults to PNG");
REXCVAR_DEFINE_STRING(halo3mp_smoke_route, "", "Halo3MP",
                      "Short name for an automated smoke route, included in FPS logs");
REXCVAR_DEFINE_STRING(halo3mp_smoke_expected_state, "", "Halo3MP",
                      "Expected state for an automated smoke route, included in FPS logs");
REXCVAR_DEFINE_UINT32(halo3mp_smoke_players, 0, "Halo3MP",
                      "Expected local player count for an automated smoke route");

class Halo3mpApp : public rex::ReXApp {
 public:
  using rex::ReXApp::ReXApp;

  static std::unique_ptr<rex::ui::WindowedApp> Create(
      rex::ui::WindowedAppContext& ctx) {
    return std::unique_ptr<Halo3mpApp>(new Halo3mpApp(ctx, "halo3mp",
        PPCImageConfig));
  }

  void OnPreSetup(rex::RuntimeConfig& config) override {
    if (!config.graphics && !config.gpu_plugin.empty()) {
      config.graphics = rex::system::LoadGpuPlugin(config.gpu_plugin);
    }
    if (!config.graphics) {
      return;
    }

    // Halo 3 MP's four-player split-screen load is substantially faster on the
    // D3D12 host-RT path. Keep command-line and config overrides available for
    // graphics debugging.
    if (rex::cvar::GetFlagSource("render_target_path_d3d12") == rex::cvar::Source::kDefault) {
      rex::cvar::SetFlagByName("render_target_path_d3d12", "rtv");
    }
    // The 16-bit host representation currently washes Halo 3's gamma render
    // targets to white on RTV. The original 8-bit path renders them correctly.
    if (rex::cvar::GetFlagSource("gamma_render_target_as_unorm16") ==
        rex::cvar::Source::kDefault) {
      rex::cvar::SetFlagByName("gamma_render_target_as_unorm16", "false");
    }
    // Halo 3's memexport writes are consumed on the GPU in the validated
    // gameplay paths. Synchronous CPU readback adds GPU/CPU stalls without
    // changing the observed menu or four-player output.
    if (rex::cvar::GetFlagSource("readback_memexport") == rex::cvar::Source::kDefault) {
      rex::cvar::SetFlagByName("readback_memexport", "false");
    }

    if (rex::cvar::GetFlagSource("gpu_allow_invalid_fetch_constants") ==
        rex::cvar::Source::kDefault) {
      rex::cvar::SetFlagByName("gpu_allow_invalid_fetch_constants", "true");
    }
  }

  void OnCreateDialogs(rex::ui::ImGuiDrawer* drawer) override {
    (void)drawer;
    StartHostTools();
  }

  void OnPostLaunchModule(rex::system::XThread* thread) override {
    (void)thread;
    StartHostTools();
  }

  void OnShutdown() override {
    host_tool_stop_.store(true, std::memory_order_release);
    if (title_fps_thread_.joinable()) {
      title_fps_thread_.join();
    }
    if (capture_thread_.joinable()) {
      capture_thread_.join();
    }
    app_context().CallInUIThreadSynchronous([]() {});
  }

 private:
#if defined(_WIN32)
  static bool SavePng(const std::filesystem::path& path, const rex::ui::RawImage& image) {
    if (!image.width || !image.height || image.stride < size_t(image.width) * 4 ||
        image.data.empty()) {
      return false;
    }

    const std::filesystem::path parent_path = path.parent_path();
    if (!parent_path.empty()) {
      std::filesystem::create_directories(parent_path);
    }

    const HRESULT co_init = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    const bool co_uninit = SUCCEEDED(co_init);

    IWICImagingFactory* factory = nullptr;
    IWICBitmapEncoder* encoder = nullptr;
    IWICBitmapFrameEncode* frame = nullptr;
    IWICStream* stream = nullptr;
    bool ok = false;

    const HRESULT factory_hr =
        CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER,
                         IID_PPV_ARGS(&factory));
    if (SUCCEEDED(factory_hr) &&
        SUCCEEDED(factory->CreateStream(&stream)) &&
        SUCCEEDED(stream->InitializeFromFilename(path.wstring().c_str(), GENERIC_WRITE)) &&
        SUCCEEDED(factory->CreateEncoder(GUID_ContainerFormatPng, nullptr, &encoder)) &&
        SUCCEEDED(encoder->Initialize(stream, WICBitmapEncoderNoCache)) &&
        SUCCEEDED(encoder->CreateNewFrame(&frame, nullptr)) &&
        SUCCEEDED(frame->Initialize(nullptr))) {
      UINT width = image.width;
      UINT height = image.height;
      WICPixelFormatGUID format = GUID_WICPixelFormat24bppBGR;
      std::vector<uint8_t> bgr(size_t(image.width) * image.height * 3);
      for (uint32_t y = 0; y < image.height; ++y) {
        const uint8_t* src = image.data.data() + size_t(y) * image.stride;
        uint8_t* dst = bgr.data() + size_t(y) * image.width * 3;
        for (uint32_t x = 0; x < image.width; ++x) {
          dst[size_t(x) * 3 + 0] = src[size_t(x) * 4 + 2];
          dst[size_t(x) * 3 + 1] = src[size_t(x) * 4 + 1];
          dst[size_t(x) * 3 + 2] = src[size_t(x) * 4 + 0];
        }
      }

      const UINT bgr_stride = image.width * 3;
      const UINT bgr_size = static_cast<UINT>(bgr.size());
      ok = SUCCEEDED(frame->SetSize(width, height)) &&
           SUCCEEDED(frame->SetPixelFormat(&format)) &&
           IsEqualGUID(format, GUID_WICPixelFormat24bppBGR) &&
           SUCCEEDED(frame->WritePixels(height, bgr_stride, bgr_size, bgr.data())) &&
           SUCCEEDED(frame->Commit()) && SUCCEEDED(encoder->Commit());
    }

    if (frame) frame->Release();
    if (encoder) encoder->Release();
    if (stream) stream->Release();
    if (factory) factory->Release();
    if (co_uninit) {
      CoUninitialize();
    }
    return ok;
  }
#else
  static bool SavePng(const std::filesystem::path& path, const rex::ui::RawImage& image) {
    (void)path;
    (void)image;
    return false;
  }
#endif

  bool SleepForHostTool(uint32_t milliseconds) const {
    using namespace std::chrono_literals;
    uint32_t remaining = milliseconds;
    while (remaining && !host_tool_stop_.load(std::memory_order_acquire)) {
      const uint32_t chunk = std::min<uint32_t>(remaining, 50);
      std::this_thread::sleep_for(std::chrono::milliseconds(chunk));
      remaining -= chunk;
    }
    return !host_tool_stop_.load(std::memory_order_acquire);
  }

  rex::ui::Presenter* presenter() const {
    auto* rt = runtime();
    auto* graphics_system = rt ? rt->graphics_system() : nullptr;
    return graphics_system ? graphics_system->presenter() : nullptr;
  }

  static void ApplyHostWindowTitle(rex::ui::Window* app_window, const std::string& title) {
    if (!app_window) {
      return;
    }
    app_window->SetTitle(title);
#if defined(_WIN32)
    if (HWND hwnd = static_cast<HWND>(app_window->GetNativeWindowHandle())) {
      SetWindowTextA(hwnd, title.c_str());
    }
#endif
  }

  std::filesystem::path GetCapturePath() const {
    std::filesystem::path path(REXCVAR_GET(halo3mp_capture_guest_output_path));
    if (path.empty()) {
      path = user_data_root() / "captures" / "halo3mp_guest_capture.png";
    }
    return path;
  }

  static std::vector<uint32_t> ParseCaptureTimes() {
    std::vector<uint32_t> times;
    const uint32_t single_delay_ms = REXCVAR_GET(halo3mp_capture_guest_output_after_ms);
    const std::string spec = REXCVAR_GET(halo3mp_capture_guest_output_times_ms);

    size_t pos = 0;
    while (pos < spec.size()) {
      size_t comma = spec.find(',', pos);
      std::string tok =
          spec.substr(pos, comma == std::string::npos ? std::string::npos : comma - pos);
      try {
        if (!tok.empty()) {
          times.push_back(static_cast<uint32_t>(std::stoul(tok)));
        }
      } catch (...) {
      }
      if (comma == std::string::npos) {
        break;
      }
      pos = comma + 1;
    }

    if (times.empty() && single_delay_ms) {
      times.push_back(single_delay_ms);
    }
    std::sort(times.begin(), times.end());
    times.erase(std::unique(times.begin(), times.end()), times.end());
    return times;
  }

  static std::filesystem::path CapturePathForTime(const std::filesystem::path& base_path,
                                                  uint32_t capture_time_ms,
                                                  size_t capture_count) {
    if (capture_count <= 1) {
      return base_path;
    }

    auto parent = base_path.parent_path();
    auto stem = base_path.stem().wstring();
    auto extension = base_path.extension().wstring();
    if (extension.empty()) {
      extension = L".png";
    }

    std::wostringstream name;
    name << stem << L"_" << std::setw(6) << std::setfill(L'0') << capture_time_ms << L"ms"
         << extension;
    return parent / name.str();
  }

  void StartHostTools() {
    host_tool_stop_.store(false, std::memory_order_release);
    auto* app_window = window();
    auto* app_presenter = presenter();
    if (!app_window || !app_presenter) {
      return;
    }

    LogSmokeContextOnce();

    if (REXCVAR_GET(halo3mp_title_fps) && !title_fps_thread_.joinable()) {
      StartTitleFpsThread(app_window, app_presenter);
    }

    if (!ParseCaptureTimes().empty() && !capture_thread_.joinable()) {
      StartCaptureThread(app_presenter);
    }
  }

  void LogSmokeContextOnce() {
    if (smoke_context_logged_.exchange(true, std::memory_order_acq_rel)) {
      return;
    }
    const std::string route = REXCVAR_GET(halo3mp_smoke_route);
    const std::string expected_state = REXCVAR_GET(halo3mp_smoke_expected_state);
    if (route.empty() && expected_state.empty()) {
      return;
    }
    REXLOG_INFO(
        "Halo3MP smoke context route='{}' expected_state='{}' players={} fps_log={} "
        "capture_after_ms={} capture_times_ms='{}' capture_path='{}'",
        route, expected_state, REXCVAR_GET(halo3mp_smoke_players),
        REXCVAR_GET(halo3mp_log_fps), REXCVAR_GET(halo3mp_capture_guest_output_after_ms),
        REXCVAR_GET(halo3mp_capture_guest_output_times_ms),
        REXCVAR_GET(halo3mp_capture_guest_output_path));
  }

  void StartTitleFpsThread(rex::ui::Window* app_window, rex::ui::Presenter* app_presenter) {
    const uint32_t interval_ms =
        std::max<uint32_t>(100, REXCVAR_GET(halo3mp_title_fps_interval_ms));
    const std::string title_prefix = std::string(GetName());
    REXLOG_INFO("Halo3MP title-bar FPS started with {} ms interval", interval_ms);
    app_context().CallInUIThread([app_window, title = title_prefix + " | FPS starting"]() {
      ApplyHostWindowTitle(app_window, title);
    });
    title_fps_thread_ = std::thread([this, app_window, app_presenter, interval_ms, title_prefix]() {
      using Clock = std::chrono::steady_clock;
      auto last_time = Clock::now();
      uint64_t last_frame_count = app_presenter->guest_output_frame_count();
      while (SleepForHostTool(interval_ms)) {
        const auto now = Clock::now();
        const uint64_t frame_count = app_presenter->guest_output_frame_count();
        const double elapsed =
            std::chrono::duration<double>(now - last_time).count();
        const uint64_t frame_delta = frame_count - last_frame_count;
        const double fps = elapsed > 0.0 ? double(frame_delta) / elapsed : 0.0;
        last_time = now;
        last_frame_count = frame_count;

        std::ostringstream title;
        title << title_prefix << " | " << std::fixed << std::setprecision(1) << fps << " FPS";
        if (REXCVAR_GET(halo3mp_log_fps)) {
          const std::string route = REXCVAR_GET(halo3mp_smoke_route);
          const std::string expected_state = REXCVAR_GET(halo3mp_smoke_expected_state);
          if (!route.empty() || !expected_state.empty()) {
            REXLOG_INFO(
                "Halo3MP guest-output FPS {:.1f} ({} frames / {:.3f}s) route='{}' "
                "expected_state='{}' players={}",
                fps, frame_delta, elapsed, route, expected_state,
                REXCVAR_GET(halo3mp_smoke_players));
          } else {
            REXLOG_INFO("Halo3MP guest-output FPS {:.1f} ({} frames / {:.3f}s)", fps,
                        frame_delta, elapsed);
          }
        }
        app_context().CallInUIThread([app_window, title = title.str()]() {
          ApplyHostWindowTitle(app_window, title);
        });
      }
    });
  }

  void StartCaptureThread(rex::ui::Presenter* app_presenter) {
    const std::vector<uint32_t> capture_times_ms = ParseCaptureTimes();
    const std::filesystem::path base_capture_path = GetCapturePath();
    capture_thread_ = std::thread([this, app_presenter, capture_times_ms, base_capture_path]() {
      uint32_t elapsed_ms = 0;
      for (const uint32_t capture_time_ms : capture_times_ms) {
        if (capture_time_ms < elapsed_ms) {
          continue;
        }
        if (!SleepForHostTool(capture_time_ms - elapsed_ms)) {
          return;
        }
        elapsed_ms = capture_time_ms;

        rex::ui::RawImage image;
        if (!app_presenter->CaptureGuestOutput(image)) {
          REXLOG_WARN("Halo3MP guest-output capture at {} ms failed: no guest frame available",
                      capture_time_ms);
          continue;
        }

        const std::filesystem::path capture_path =
            CapturePathForTime(base_capture_path, capture_time_ms, capture_times_ms.size());
        if (!SavePng(capture_path, image)) {
          REXLOG_WARN("Halo3MP guest-output capture at {} ms failed: couldn't write {}",
                      capture_time_ms, capture_path.string());
          continue;
        }
        REXLOG_INFO("Halo3MP guest-output capture at {} ms wrote {}", capture_time_ms,
                    capture_path.string());
      }
    });
  }

  std::atomic<bool> host_tool_stop_{false};
  std::atomic<bool> smoke_context_logged_{false};
  std::thread title_fps_thread_;
  std::thread capture_thread_;

  // Override virtual hooks for customization:
  // void OnPostInitLogging() override {}
  // void OnLoadXexImage(std::string& xex_image) override {}
  // void OnPostLoadXexImage() override {}
  // std::unique_ptr<rex::ui::ImGuiDialog> CreateAchievementsOverlay() override;
  // std::unique_ptr<rex::ui::AchievementNotificationDialog>
  // CreateAchievementNotificationDialog() override;
  // void OnConfigurePaths(rex::PathConfig& paths) override {}
};
