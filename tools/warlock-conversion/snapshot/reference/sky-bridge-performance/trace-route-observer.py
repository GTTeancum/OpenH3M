"""Use the verified native observer allocation in the existing bounded tracer.

The shared tracer has unrelated pending work. Apply these exact reader and
logging-window changes in memory, preserving its contents and module path.
"""
import hashlib
from pathlib import Path
import sys

reference = Path(__file__).resolve().parent
source = reference.parents[1] / 'tools/trace_loading.py'
text = source.read_text()
old = """                pointer = observer_word(tls+0x25c)
                if not 0x80000000 <= pointer < 0xe0000000:
                    raise ValueError('Observer pointer outside expected guest range')
                data = read(guest_memory_base+pointer+0x1cc, 96)"""
new = """                pointer = observer_word(tls+0x2cc)
                if not 0x80000000 <= pointer < 0xe0000000:
                    raise ValueError('Observer pointer outside expected guest range')
                result_address = pointer + 0x110
                legacy_address = observer_word(tls+0x25c) + 0x1cc
                data = read(guest_memory_base+result_address, 96)"""
old_log = """                log('observer_position', position=position, location=data[12:16].hex(),"""
new_log = """                log('observer_position', position=position, location=data[12:16].hex(),
                    observer_allocation=hex(pointer), result_address=hex(result_address),
                    legacy_address=hex(legacy_address), legacy_alias_matches=legacy_address==result_address,"""
old_timing = """    args += ['--d3d12_log_present_timing=true', '--d3d12_slow_preparation_ms=8']"""
new_timing = """    args += ['--d3d12_log_present_timing=true', '--d3d12_slow_preparation_ms=8',
             '--d3d12_present_timing_end_ms=180000']"""
if text.count(old) != 1 or text.count(old_log) != 1 or text.count(old_timing) != 1:
    raise SystemExit('Observer reader source changed; review before patching')
patched = text.replace(old, new).replace(old_log, new_log).replace(old_timing, new_timing)
print('Native observer reader: TLS+0x2cc/+0x110; source SHA256=' +
      hashlib.sha256(source.read_bytes()).hexdigest(), flush=True)
sys.path.insert(0, str(source.parent))
sys.argv[0] = str(source)
exec(compile(patched, str(source), 'exec'),
     {'__name__': '__main__', '__file__': str(source), '__builtins__': __builtins__})
