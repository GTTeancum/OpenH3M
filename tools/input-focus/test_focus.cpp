#include <rex/input/input_system.h>
#include <rex/input/mnk/mnk_input_driver.h>
#include <rex/cvar.h>
#include <iostream>
#include <stdexcept>
using namespace rex;
using namespace rex::input;
static void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }

// Deliberately ignores the active callback to exercise the final guest gate.
class HeldPad final : public InputDriver {
 public:
  HeldPad() : InputDriver(nullptr, 0) {}
  X_INPUT_STATE state{};
  bool queued = false;
  unsigned resets = 0;
  X_STATUS Setup() override { return X_STATUS_SUCCESS; }
  void EnumerateDevices(std::vector<DeviceInfo>& out) override {
    DeviceInfo d; d.id = static_cast<DeviceId>(1); out.push_back(d);
  }
  X_RESULT GetDeviceState(DeviceId, X_INPUT_STATE* out) override { *out = state; return X_ERROR_SUCCESS; }
  X_RESULT GetDeviceCapabilities(DeviceId, uint32_t, X_INPUT_CAPABILITIES* out) override {
    *out = {}; out->sub_type = 1; return X_ERROR_SUCCESS;
  }
  X_RESULT SetDeviceVibration(DeviceId, X_INPUT_VIBRATION*) override { return X_ERROR_SUCCESS; }
  X_RESULT GetDeviceKeystroke(DeviceId, uint32_t, X_INPUT_KEYSTROKE* out) override {
    if (!queued) return X_ERROR_EMPTY;
    queued = false; *out = {}; out->virtual_key = 0x5800; return X_ERROR_SUCCESS;
  }
  void OnInputFocusChanged(bool) override { queued = false; ++resets; }
};

static InputSystem* current_input;
static InputSystem* input_system() { return current_input; }
static bool keys[256]{};
static unsigned key_polls;
static bool KeyDown(int key) { ++key_polls; return keys[key]; }
REXCVAR_DECLARE(bool, keyboard_controller);
// Exact production mapping; only its key source is replaced with a local array.
#include "keyboard_under_test.inl"

int main() {
 try {
  InputSystem input(nullptr); current_input = &input;
  input.SetDeviceAssignment(std::make_unique<SlotAssignment>());
  auto owned = std::make_unique<HeldPad>();
  auto* pad = owned.get(); input.AddDriver(std::move(owned));
  pad->state.packet_number = 7;
  pad->state.gamepad.buttons = X_INPUT_GAMEPAD_A;
  pad->state.gamepad.thumb_lx = 25000; pad->state.gamepad.thumb_ry = -20000;
  pad->state.gamepad.left_trigger = 180; pad->state.gamepad.right_trigger = 255;
  X_INPUT_STATE state{};
  require(input.GetState(0, &state) == X_ERROR_SUCCESS && state.gamepad.buttons == X_INPUT_GAMEPAD_A, "focused pad");
  uint32_t packet = state.packet_number;
  ui::UISetupEvent focus;
  pad->queued = true; input.OnLostFocus(focus);
  require(!input.IsActive() && !pad->queued && pad->resets == 1, "focus loss queue reset");
  require(input.GetState(0, &state) == X_ERROR_SUCCESS, "background connection");
  require(state.gamepad.buttons == 0 && state.gamepad.thumb_lx == 0 && state.gamepad.thumb_ry == 0 &&
          state.gamepad.left_trigger == 0 && state.gamepad.right_trigger == 0, "background neutral state");
  require(state.packet_number != packet, "release packet"); packet = state.packet_number;
  X_INPUT_CAPABILITIES caps{};
  require(input.GetCapabilities(0, 0, &caps) == X_ERROR_SUCCESS && caps.sub_type == 1, "background capabilities");
  require(input.GetState(1, &state) == X_ERROR_DEVICE_NOT_CONNECTED, "absent pad remains absent");
  X_INPUT_KEYSTROKE stroke{};
  pad->queued = true;
  require(input.GetKeystroke(0, 0, &stroke) == X_ERROR_EMPTY, "background keystroke gate");
  pad->queued = true; input.OnGotFocus(focus);
  require(!pad->queued && pad->resets == 2, "refocus queue reset");
  require(input.GetState(0, &state) == X_ERROR_SUCCESS && state.gamepad.buttons == X_INPUT_GAMEPAD_A &&
          state.packet_number != packet, "live pad resumes");
  pad->state.gamepad = {}; input.GetState(0, &state);
  require(state.gamepad.buttons == 0, "pad release");

  cvar::SetFlagByName("keyboard_controller", "true");
  keys['W'] = keys[VK_SPACE] = true;
  require(KeyboardControllerFor(0).ly == kStick, "focused keyboard mapping");
  input.OnLostFocus(focus); key_polls = 0;
  auto keyboard = KeyboardControllerFor(0);
  require(!keyboard.active && keyboard.buttons == 0 && keyboard.ly == 0 && key_polls == 0, "no background keyboard polling");
  keys['W'] = keys[VK_SPACE] = false; input.OnGotFocus(focus);
  require(!KeyboardControllerFor(0).active, "keyboard release while unfocused");
  keys['W'] = true;
  require(KeyboardControllerFor(0).ly == kStick, "fresh keyboard press");
  input.SetActiveCallback([] { return false; });
  require(!KeyboardControllerFor(0).active, "host UI keyboard gate");

  // Actual event driver, null window: no host input or UI is used.
  cvar::SetFlagByName("mnk_mode", "true"); cvar::SetFlagByName("keybind_a", "Space");
  mnk::MnkInputDriver mnk(nullptr, 0);
  std::vector<DeviceInfo> devices; mnk.EnumerateDevices(devices);
  require(devices.size() == 1, "MnK available");
  ui::KeyEvent down(nullptr, ui::VirtualKey::kSpace, 1, false, false, false, false, false);
  mnk.OnKeyDown(down); mnk.GetDeviceState(devices[0].id, &state);
  require((state.gamepad.buttons & X_INPUT_GAMEPAD_A) != 0, "MnK press");
  mnk.OnLostFocus(focus); mnk.OnKeyDown(down); mnk.GetDeviceState(devices[0].id, &state);
  require(state.gamepad.buttons == 0, "MnK background gate");
  mnk.OnGotFocus(focus); mnk.GetDeviceState(devices[0].id, &state);
  require(state.gamepad.buttons == 0, "MnK held key cleared");
  mnk.OnKeyDown(down); mnk.GetDeviceState(devices[0].id, &state);
  require((state.gamepad.buttons & X_INPUT_GAMEPAD_A) != 0, "MnK resumes");
  std::cout << "PASS: keyboard/MnK/controller focus, neutral state, packets, connections and queues\n";
  return 0;
 } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
