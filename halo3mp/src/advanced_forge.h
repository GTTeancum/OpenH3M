#pragma once
namespace rex::ui { class ImGuiDrawer; }
namespace rex::graphics { class CommandProcessor; }
namespace advanced_forge { void AttachControls(rex::ui::ImGuiDrawer*); void AttachRenderer(rex::graphics::CommandProcessor*); }
