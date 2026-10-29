# Input focus

Spartan's host input now follows its window focus. The legacy keyboard-controller
mapping checks the input gate before polling keys. SDL, XInput and MnK return
neutral gameplay state in the background without disconnecting guest controllers.
Focus transitions change the state packet number, clear cached MnK keys and mouse
deltas, reset SDL repeats, and discard queued native XInput keystrokes. Mouse
capture updates recheck focus when they run on the UI thread.

The original bindings, controller assignment, gameplay, maps and saved variants
are unchanged. Explicit process-local diagnostic scripts/replays retain their
existing behavior; they are not live keyboard/controller input.

Apply `halo3mp/patches/rexglue-sdk-input-focus.patch` to the existing patched SDK,
after the input-script and input-state-replay patches. It is an incremental patch
against the local device-assignment/MnK SDK baseline, not pristine upstream.
Rebuild the runtime and app together because the host input classes changed.

From the repository root:

```powershell
./tools/input-focus/build.ps1
```

The check uses the actual InputSystem and MnK driver, plus the exact production
legacy keyboard mapping with a process-local key array. It covers focus loss and
regain, background input, release while unfocused, fresh presses, packet changes,
controller presence/capabilities, queue clearing and the host UI keyboard gate.
It does not create a window or generate desktop input. Physical SDL/XInput
devices and interactive Alt-Tab behavior are left to the user's in-game testing.

2026-10-28: the runtime/app build and process-local focus check passed. Candidate
binaries are in `work/rexglue-sdk/out/win-amd64`; build/test logs are in
`work/input-focus`.
