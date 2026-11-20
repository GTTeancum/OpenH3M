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
#include "pc_video_menu.h"
#include "pc_video_settings.h"
#include <fstream>
#include <map>

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
#include <rex/filesystem.h>
#include <rex/logging/macros.h>
#include <rex/rex_app.h>
#include <rex/runtime.h>
#include <rex/graphics/graphics_system.h>
#include <rex/filesystem/devices/stfs_container_device.h>
#include <rex/system/kernel_state.h>
#include <rex/system/xam/content_manager.h>
#include <rex/system/interfaces/graphics.h>
#include <rex/system/gpu_plugin.h>
#include <rex/ui/imgui_drawer.h>
#include <rex/ui/keybinds.h>
#include <rex/input/input_system.h>
#ifdef OPENH3M_ADVANCED_FORGE
#include "advanced_forge.h"
#endif
#include <rex/ui/presenter.h>
#include <rex/ui/window.h>
#include <rex/ui/windowed_app_context.h>

#include "system_link.h"
#ifdef OPENH3M_DEVELOPER_BUILD
#include "developer_framerate.h"
REXCVAR_DEFINE_BOOL(fpsunlock, false, "Halo3MP/Developer",
                    "Keep FPS unlocked for this process; simulation timing is unchanged");
REXCVAR_DEFINE_BOOL(halo3mp_dev_unlock_test, false, "Halo3MP/Developer",
                    "Log read-only simulation diagnostics");
REXCVAR_DECLARE(std::string, halo3mp_benchmark_points);
#endif

REXCVAR_DEFINE_BOOL(halo3mp_title_fps, false, "Halo3MP",
                    "Legacy compatibility option; title FPS display has been removed");
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
REXCVAR_DEFINE_STRING(halo3mp_video_validation, "", "Halo3MP/Developer",
    "Opt-in process-local video validation TSV: capture_ms option_index choice_index; requires exclusive replay").debug_only();
REXCVAR_DEFINE_STRING(halo3mp_smoke_route, "", "Halo3MP",
                      "Short name for an automated smoke route, included in FPS logs");
REXCVAR_DEFINE_STRING(halo3mp_smoke_expected_state, "", "Halo3MP",
                      "Expected state for an automated smoke route, included in FPS logs");
REXCVAR_DEFINE_UINT32(halo3mp_smoke_players, 0, "Halo3MP",
                      "Expected local player count for an automated smoke route");
REXCVAR_DEFINE_STRING(halo3mp_install_content, "", "Halo3MP",
                     "Install a Halo 3 LIVE package into the configured user-data root before launch");

class Halo3mpApp : public rex::ReXApp {
 public:
  using rex::ReXApp::ReXApp;

  std::string_view GetWindowTitleName() const override { return "Spartan"; }

  static std::unique_ptr<rex::ui::WindowedApp> Create(
      rex::ui::WindowedAppContext& ctx) {
    SetDefaultFlag("fullscreen", "false");
    SetDefaultFlag("window_width", "0");
    SetDefaultFlag("window_height", "0");
    SetDefaultFlag("video_mode_width", "1280");
    SetDefaultFlag("video_mode_height", "720");
    SetDefaultFlag("anisotropic_override", "3");
    SetDefaultFlag("keyboard_controller", "true");
    SetDefaultFlag("keyboard_controller_log", "false");
    return std::unique_ptr<Halo3mpApp>(new Halo3mpApp(ctx, "OpenH3M",
        PPCImageConfig));
  }

  void OnConfigurePaths(rex::PathConfig& paths) override {
    pc_video_config_path_ = paths.config_path;
    if (paths.game_data_root.empty()) {
      paths.game_data_root = rex::filesystem::GetExecutableFolder() / "game";
    }
  }

  void OnPreSetup(rex::RuntimeConfig& config) override {
#ifdef OPENH3M_DEVELOPER_BUILD
    // Session starts OFF, even if a previous config saved an uncapped rate.
    rex::cvar::SetFlagByName("host_guest_output_fps", "30");
    rex::cvar::SetFlagByName("host_guest_output_frame_timing", "false");
#endif
    if (config.gpu_plugin.empty()) {
      config.gpu_plugin = "xenos";
    }
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

    // Publish real GPU visibility results after their fences complete without
    // stalling command production at each query. Explicit overrides still win;
    // the backend retains its synchronous fallback if the worker cannot start.
    if (rex::cvar::GetFlagSource("d3d12_async_occlusion_readback") ==
        rex::cvar::Source::kDefault) {
      rex::cvar::SetFlagByName("d3d12_async_occlusion_readback", "true");
    }

    // Native auto-exposure reads a small resolved brightness texture on the
    // CPU. Without feedback it stays at zero stops, even in dark rooms. Keep
    // delayed D3D12 feedback for small surfaces, not full-size color targets.
    // Explicit shared or legacy readback overrides retain their semantics.
    if (rex::cvar::GetFlagSource("readback_resolve") == rex::cvar::Source::kDefault &&
        rex::cvar::GetFlagSource("d3d12_readback_resolve") == rex::cvar::Source::kDefault) {
      rex::cvar::SetFlagByName("d3d12_readback_resolve", "true");
      if (rex::cvar::GetFlagSource("d3d12_readback_resolve_max_bytes") ==
          rex::cvar::Source::kDefault) {
        rex::cvar::SetFlagByName("d3d12_readback_resolve_max_bytes", "8192");
      }
    }

    if (rex::cvar::GetFlagSource("gpu_allow_invalid_fetch_constants") ==
        rex::cvar::Source::kDefault) {
      rex::cvar::SetFlagByName("gpu_allow_invalid_fetch_constants", "true");
    }
  }

  void OnPostSetup() override {
    if (!open_h3m::system_link::Install(runtime())) {
      REXLOG_ERROR("OpenH3M System Link hooks were not fully installed");
    }
  }

  void OnCreateDialogs(rex::ui::ImGuiDrawer* drawer) override {
    spartan::video::InitializePCVideoMenu(pc_video_config_path_);
    // The achievements overlay and its F7 binding are not used by Spartan.
    rex::ui::UnregisterBind("bind_achievements");
#ifdef OPENH3M_ADVANCED_FORGE
    advanced_forge::AttachControls(drawer);
#else
    (void)drawer;
#endif
    StartHostTools();
  }

  std::unique_ptr<rex::ui::ImGuiDialog> CreateAchievementsOverlay() override {
    return nullptr;
  }

  void OnPostLaunchModule(rex::system::XThread* thread) override {
    (void)thread;
#ifdef OPENH3M_ADVANCED_FORGE
    if(auto* graphics=static_cast<rex::graphics::GraphicsSystem*>(runtime()->graphics_system()))
      advanced_forge::AttachRenderer(graphics->command_processor());
    // Preserve the SDK's input gate for its remaining host UI.
    // Input is filtered in-process; this never generates host input events.
    if (auto* input = static_cast<rex::input::InputSystem*>(runtime()->input_system())) {
      input->SetActiveCallback([this]() {
        auto* drawer = imgui_drawer();
        return !drawer || !(drawer->GetIO().WantCaptureMouse || drawer->GetIO().WantCaptureKeyboard);
      });
    }
#endif
    StartHostTools();
  }

  void OnPreLaunchModule() override {
#ifdef OPENH3M_DEVELOPER_BUILD
    developer_sync_interval_ = rex::cvar::GetFlagByName("d3d12_host_sync_interval");
    developer_vsync_ = rex::cvar::GetFlagByName("vsync");
    const bool enabled = REXCVAR_GET(fpsunlock) &&
        rex::cvar::GetFlagSource("fpsunlock") == rex::cvar::Source::kCommandLine;
    developer_uncapped_.store(enabled);
    if (enabled) {
      rex::cvar::SetFlagByName("host_guest_output_fps", "0");
      rex::cvar::SetFlagByName("d3d12_host_sync_interval", "0");
      rex::cvar::SetFlagByName("vsync", "false");
    }
    REXLOG_INFO("Developer FPS unlock command line: {}", enabled);
#endif
    const auto package = REXCVAR_GET(halo3mp_install_content);
    if (package.empty()) return;
    auto path = std::filesystem::u8path(package);
    const auto filename = path.filename().string();
    // The game mounts the container under its file name and strips a first extension from
    // it, so the name must be extensionless. Any such name of safe characters is accepted
    // (a map name such as Reactor_20261119, or the 40-digit content ID); 42 characters is
    // the Xbox 360 content file-name limit.
    const bool mountable_name = !filename.empty() && filename.size() <= 42 &&
        filename.find_first_not_of(
            "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-") == std::string::npos;
    auto header = rex::filesystem::StfsContainerDevice::ReadPackageHeader(path);
    if (!header || header->header.magic != rex::filesystem::XContentPackageType::kLive ||
        header->metadata.execution_info.title_id != 0x4D5307E6 ||
        header->metadata.content_type != rex::system::XContentType::kMarketplaceContent ||
        !mountable_name) {
      throw std::runtime_error("DLC installation requires a Halo 3 LIVE package with an extensionless file name of letters, digits, '_' or '-' (42 characters at most)");
    }
    const auto result = runtime()->kernel_state()->content_manager()->InstallContent(path);
    if (result != 0) {
      REXLOG_ERROR("DLC installation failed: {} result={:#x}", package, result);
      throw std::runtime_error("DLC installation failed; guest launch stopped");
    }
    REXLOG_INFO("DLC installation completed: {} (container install only; not a gameplay pass)", package);
  }

  void OnShutdown() override {
#ifdef OPENH3M_DEVELOPER_BUILD
    rex::cvar::SetFlagByName("host_guest_output_fps", "30");
    rex::cvar::SetFlagByName("host_guest_output_frame_timing", "false");
    if (developer_uncapped_.load(std::memory_order_relaxed)) {
      rex::cvar::SetFlagByName("d3d12_host_sync_interval", developer_sync_interval_);
      rex::cvar::SetFlagByName("vsync", developer_vsync_);
    }
#endif
    host_tool_stop_.store(true, std::memory_order_release);
    if (frame_stats_thread_.joinable()) {
      frame_stats_thread_.join();
    }
    if (capture_thread_.joinable()) {
      capture_thread_.join();
    }
    app_context().CallInUIThreadSynchronous([]() {});
  }

 private:
  std::filesystem::path pc_video_config_path_;
#ifdef OPENH3M_DEVELOPER_BUILD
  std::atomic<bool>& developer_uncapped_ = open_h3m::developer::uncapped;
  std::string developer_sync_interval_;
  std::string developer_vsync_;
#endif
  static void SetDefaultFlag(std::string_view name, std::string_view value) {
    if (rex::cvar::GetFlagSource(name) == rex::cvar::Source::kDefault) {
      rex::cvar::SetFlagByName(name, value);
    }
  }

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

    if (!frame_stats_thread_.joinable()) {
      StartFrameStatsThread(app_window, app_presenter);
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

  void StartFrameStatsThread(rex::ui::Window* app_window, rex::ui::Presenter* app_presenter) {
#ifdef OPENH3M_DEVELOPER_BUILD
    open_h3m::developer::presenter.store(app_presenter);
#endif
    const uint32_t interval_ms =
        std::max<uint32_t>(100, REXCVAR_GET(halo3mp_title_fps_interval_ms));
    const std::string title_prefix = std::string(GetWindowTitleName()) +
        (REXCVAR_GET(halo3mp_smoke_route) == "advanced-forge-replay"
             ? " | Automated Forge test - live controls disabled" : "");
    REXLOG_INFO("Halo3MP frame statistics started with {} ms interval", interval_ms);
    app_context().CallInUIThread([app_window, title = title_prefix]() {
      ApplyHostWindowTitle(app_window, title);
    });
    frame_stats_thread_ = std::thread([this, app_presenter, interval_ms]() {
      using Clock = std::chrono::steady_clock;
      auto last_time = Clock::now();
      uint64_t last_frame_count = app_presenter->guest_output_frame_count();
      while (SleepForHostTool(interval_ms)) {
#ifdef OPENH3M_DEVELOPER_BUILD
        const int capture = open_h3m::developer::capture_request.exchange(0);
        if (capture > 0) {
          rex::ui::RawImage image;
          const auto path = std::filesystem::path(REXCVAR_GET(halo3mp_benchmark_points)).parent_path() /
              ("spawn-" + std::to_string(capture) + ".png");
          const bool saved = app_presenter->CaptureGuestOutput(image) && SavePng(path, image);
          open_h3m::developer::capture_done.store(saved ? capture : -capture);
        }
#endif
        const auto now = Clock::now();
        const uint64_t frame_count = app_presenter->guest_output_frame_count();
        const double elapsed =
            std::chrono::duration<double>(now - last_time).count();
        const uint64_t frame_delta = frame_count - last_frame_count;
        const double fps = elapsed > 0.0 ? double(frame_delta) / elapsed : 0.0;
        last_time = now;
        last_frame_count = frame_count;

        const bool log_fps = REXCVAR_GET(halo3mp_log_fps);
        if (log_fps) {
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
      }
    });
  }

  void StartCaptureThread(rex::ui::Presenter* app_presenter) {
    const std::vector<uint32_t> capture_times_ms = ParseCaptureTimes();
    const std::filesystem::path base_capture_path = GetCapturePath();
    capture_thread_ = std::thread([this, app_presenter, capture_times_ms, base_capture_path]() {
      using CaptureClock = std::chrono::steady_clock;
      const auto capture_start = CaptureClock::now();
      std::map<uint32_t,std::pair<int,int>> validation;
      const auto validation_path=REXCVAR_GET(halo3mp_video_validation);
      if(!validation_path.empty()&&!rex::cvar::GetFlagByName("input_state_replay").empty()){
        std::ifstream input(validation_path);uint32_t at;int option,choice;
        while(input>>at>>option>>choice)validation.emplace(at,std::pair{option,choice});
      }
      spartan::video::PCSettings probe;
      const auto baseline=probe.values;
      std::ofstream evidence;
      if(!validation.empty()){
        evidence.open(validation_path+".csv");
        evidence<<"capture_ms,option,choice,apply_ok,guest_width,guest_height,window_width,window_height,fullscreen,frames,elapsed_ms\n";
      }
      auto until=[&](uint32_t deadline){
        const auto elapsed=std::chrono::duration_cast<std::chrono::milliseconds>(CaptureClock::now()-capture_start).count();
        return elapsed>=deadline||SleepForHostTool(uint32_t(deadline-elapsed));
      };
      for (const uint32_t capture_time_ms : capture_times_ms) {
        bool applied=true;
        auto action=validation.find(capture_time_ms);
        if(action!=validation.end()){
          if(!until(capture_time_ms>4000?capture_time_ms-4000:0))return;
          auto [option,choice]=action->second;
          if(option>=0||option==-2||option==-3){
            probe.values=baseline;
            if(option==-2)probe.Preset(choice);
            else if(option==-3)probe.Defaults();
            else if(size_t(option)<spartan::video::PCOptions().size()&&choice>=0&&size_t(choice)<spartan::video::PCOptions()[option].choices.size())
              probe.values[option]=spartan::video::PCOptions()[option].choices[choice].value;
            else applied=false;
            std::string error;
            if(applied)app_context().CallInUIThreadSynchronous([&]{applied=probe.Apply(pc_video_config_path_,error);});
            if(!applied)REXLOG_ERROR("Video validation Apply failed: {}",error);
          }
        }
        if(!until(capture_time_ms))return;

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
        if(action!=validation.end()){
          uint32_t width=0,height=0;bool fullscreen=false;
          app_context().CallInUIThreadSynchronous([&]{width=window()->GetActualPhysicalWidth();height=window()->GetActualPhysicalHeight();fullscreen=window()->IsFullscreen();});
          evidence<<capture_time_ms<<','<<action->second.first<<','<<action->second.second<<','<<applied<<','<<image.width<<','<<image.height<<','<<width<<','<<height<<','<<fullscreen<<','<<app_presenter->guest_output_frame_count()<<','<<std::chrono::duration_cast<std::chrono::milliseconds>(CaptureClock::now()-capture_start).count()<<'\n';
          evidence.flush();
        }

      }
    });
  }

  std::atomic<bool> host_tool_stop_{false};
  std::atomic<bool> smoke_context_logged_{false};
  std::thread frame_stats_thread_;
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
