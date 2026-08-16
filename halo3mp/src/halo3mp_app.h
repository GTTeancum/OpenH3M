// halo3mp - ReXGlue Recompiled Project
//
// Customize your app by overriding virtual hooks from rex::ReXApp.

#pragma once

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
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
REXCVAR_DEFINE_UINT32(halo3mp_capture_guest_output_after_ms, 0, "Halo3MP",
                      "Capture the internal guest output after this many milliseconds; 0 disables");
REXCVAR_DEFINE_STRING(halo3mp_capture_guest_output_path, "", "Halo3MP",
                      "Path for the internal guest-output BMP capture");

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

    // Halo 3 MP's menu background renders as a white wash on the D3D12 host-RT
    // path. Use the ROV path by default, while still allowing CLI/config
    // overrides such as --render_target_path_d3d12=rtv for diagnostics.
    if (rex::cvar::GetFlagSource("render_target_path_d3d12") == rex::cvar::Source::kDefault) {
      rex::cvar::SetFlagByName("render_target_path_d3d12", "rov");
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
  static void WriteLE16(std::ofstream& file, uint16_t value) {
    file.put(static_cast<char>(value & 0xFF));
    file.put(static_cast<char>((value >> 8) & 0xFF));
  }

  static void WriteLE32(std::ofstream& file, uint32_t value) {
    file.put(static_cast<char>(value & 0xFF));
    file.put(static_cast<char>((value >> 8) & 0xFF));
    file.put(static_cast<char>((value >> 16) & 0xFF));
    file.put(static_cast<char>((value >> 24) & 0xFF));
  }

  static bool SaveBmp(const std::filesystem::path& path, const rex::ui::RawImage& image) {
    if (!image.width || !image.height || image.stride < size_t(image.width) * 4 ||
        image.data.empty()) {
      return false;
    }

    const uint64_t row_bytes = uint64_t(image.width) * 3;
    const uint64_t padded_row_bytes = (row_bytes + 3) & ~uint64_t(3);
    const uint64_t pixel_data_size = padded_row_bytes * image.height;
    const uint64_t file_size = 14 + 40 + pixel_data_size;
    if (file_size > UINT32_MAX) {
      return false;
    }

    const std::filesystem::path parent_path = path.parent_path();
    if (!parent_path.empty()) {
      std::filesystem::create_directories(parent_path);
    }
    std::ofstream file(path, std::ios::binary);
    if (!file) {
      return false;
    }

    file.put('B');
    file.put('M');
    WriteLE32(file, static_cast<uint32_t>(file_size));
    WriteLE16(file, 0);
    WriteLE16(file, 0);
    WriteLE32(file, 14 + 40);

    WriteLE32(file, 40);
    WriteLE32(file, image.width);
    WriteLE32(file, image.height);
    WriteLE16(file, 1);
    WriteLE16(file, 24);
    WriteLE32(file, 0);
    WriteLE32(file, static_cast<uint32_t>(pixel_data_size));
    WriteLE32(file, 0);
    WriteLE32(file, 0);
    WriteLE32(file, 0);
    WriteLE32(file, 0);

    std::vector<uint8_t> row(size_t(padded_row_bytes), 0);
    for (uint32_t src_y = image.height; src_y > 0; --src_y) {
      const uint8_t* src = image.data.data() + size_t(src_y - 1) * image.stride;
      for (uint32_t x = 0; x < image.width; ++x) {
        row[size_t(x) * 3 + 0] = src[size_t(x) * 4 + 2];
        row[size_t(x) * 3 + 1] = src[size_t(x) * 4 + 1];
        row[size_t(x) * 3 + 2] = src[size_t(x) * 4 + 0];
      }
      file.write(reinterpret_cast<const char*>(row.data()), static_cast<std::streamsize>(row.size()));
    }

    return bool(file);
  }

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
      path = user_data_root() / "captures" / "halo3mp_guest_capture.bmp";
    }
    return path;
  }

  void StartHostTools() {
    host_tool_stop_.store(false, std::memory_order_release);
    auto* app_window = window();
    auto* app_presenter = presenter();
    if (!app_window || !app_presenter) {
      return;
    }

    if (REXCVAR_GET(halo3mp_title_fps) && !title_fps_thread_.joinable()) {
      StartTitleFpsThread(app_window, app_presenter);
    }

    if (REXCVAR_GET(halo3mp_capture_guest_output_after_ms) && !capture_thread_.joinable()) {
      StartCaptureThread(app_presenter);
    }
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
        const double fps = elapsed > 0.0 ? double(frame_count - last_frame_count) / elapsed : 0.0;
        last_time = now;
        last_frame_count = frame_count;

        std::ostringstream title;
        title << title_prefix << " | " << std::fixed << std::setprecision(1) << fps << " FPS";
        app_context().CallInUIThread([app_window, title = title.str()]() {
          ApplyHostWindowTitle(app_window, title);
        });
      }
    });
  }

  void StartCaptureThread(rex::ui::Presenter* app_presenter) {
    const uint32_t delay_ms = REXCVAR_GET(halo3mp_capture_guest_output_after_ms);
    const std::filesystem::path capture_path = GetCapturePath();
    capture_thread_ = std::thread([this, app_presenter, delay_ms, capture_path]() {
      if (!SleepForHostTool(delay_ms)) {
        return;
      }

      rex::ui::RawImage image;
      if (!app_presenter->CaptureGuestOutput(image)) {
        REXLOG_WARN("Halo3MP guest-output capture failed: no guest frame available");
        return;
      }
      if (!SaveBmp(capture_path, image)) {
        REXLOG_WARN("Halo3MP guest-output capture failed: couldn't write {}",
                    capture_path.string());
        return;
      }
      REXLOG_INFO("Halo3MP guest-output capture wrote {}", capture_path.string());
    });
  }

  std::atomic<bool> host_tool_stop_{false};
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
