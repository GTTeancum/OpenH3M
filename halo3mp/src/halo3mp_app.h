// halo3mp - ReXGlue Recompiled Project
//
// Customize your app by overriding virtual hooks from rex::ReXApp.

#pragma once

#include <rex/cvar.h>
#include <rex/rex_app.h>
#include <rex/system/gpu_plugin.h>

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

  // Override virtual hooks for customization:
  // void OnPostInitLogging() override {}
  // void OnLoadXexImage(std::string& xex_image) override {}
  // void OnPostLoadXexImage() override {}
  // void OnPostSetup() override {}
  // void OnCreateDialogs(rex::ui::ImGuiDrawer* drawer) override {}
  // std::unique_ptr<rex::ui::ImGuiDialog> CreateAchievementsOverlay() override;
  // std::unique_ptr<rex::ui::AchievementNotificationDialog>
  // CreateAchievementNotificationDialog() override;
  // void OnShutdown() override {}
  // void OnConfigurePaths(rex::PathConfig& paths) override {}
};
