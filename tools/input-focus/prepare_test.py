"""Compile the actual legacy keyboard mapping with process-local key data."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
source = (root/'work/rexglue-sdk/src/kernel/xam/xam_input.cpp').read_text(encoding='utf-8')
state = source[source.index('struct ScriptedState {'):source.index('constexpr int16_t kStick = 30000;') + len('constexpr int16_t kStick = 30000;')]
mapping = source[source.index('void AddKeyboardButton('):source.index('void LogKeyboardTransitions(')]
out = root/'work/input-focus/keyboard_under_test.inl'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(state+'\n'+mapping, encoding='utf-8', newline='\n')
print(out)
