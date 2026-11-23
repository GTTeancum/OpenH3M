"""Read-only TagTool inspection on the hidden desktop (thin driver of the official TagTool).

Usage: python tagtool_read.py <cache .map> <out.log> <command> [<command> ...]
Commands are written to a temp file inside the repo and run with TagTool's command-file argument;
'quit' is appended. Only inspection commands are allowed (no save / import / poke commands).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit, hidden_run

TAGTOOL = kit.ROOT / '.local/asset-tools/TagTool/TagTool.exe'
FORBIDDEN = ('save', 'import', 'poke', 'inject', 'port', 'rebuild', 'delete', 'remove', 'add', 'set', 'paste', 'convert', 'generate', 'nametag')


def run(cache, out, cmds, timeout=600):
    for c in cmds:
        w = c.strip().split(' ')[0].lower()
        if any(w.startswith(f) for f in FORBIDDEN) and w not in ('setvariable',):
            raise SystemExit('refused non-read command: ' + c)
    out = Path(out).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    cf = out.with_suffix('.cmds.txt'); cf.write_text('\n'.join(list(cmds) + ['exit', 'exit', 'quit']) + '\n')
    rc, text = hidden_run.run([TAGTOOL, cache, 'RunCommands', cf], TAGTOOL.parent, out, timeout=timeout)
    return rc, text


if __name__ == '__main__':
    rc, text = run(sys.argv[1], sys.argv[2], sys.argv[3:])
    print(text[-20000:])
