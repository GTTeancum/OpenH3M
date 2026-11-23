"""Run the official H3 Editing Kit tools (tool.exe) or the ManagedBlam-based MaterialSwap.exe on a hidden desktop.

Usage: kit_run.py swap <args...>      -> MaterialSwap.exe <kit> <args...>
       kit_run.py tool <args...>      -> tool.exe <args...> (run inside the kit folder)
Prints the program's output and exits with its exit code. Any dialog stays on the hidden desktop.
"""
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/asset-library'))
import hidden_run

KIT = ROOT / '.local/h3ek-source'
SWAP = ROOT / '.local/material-swap/MaterialSwap.exe'
LOGS = ROOT / '.local/material-swap/logs'

def run(kind, args, timeout=1800, log_name='kit_run.log'):
    env = os.environ.copy(); env['TEMP'] = env['TMP'] = str(KIT / 'temp')
    cmd = [str(SWAP), str(KIT), *args] if kind == 'swap' else [str(KIT / 'tool.exe'), *args]
    return hidden_run.run(cmd, str(KIT), str(LOGS / log_name), timeout=timeout, env=env)

if __name__ == '__main__':
    rc, out = run(sys.argv[1], sys.argv[2:])
    print(out)
    sys.exit(rc)
