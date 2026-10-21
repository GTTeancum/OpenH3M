"""Check a staged runtime's complete export table against adjacent PE imports."""
import argparse
import hashlib
import json
from pathlib import Path
import pefile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory', type=Path)
args = parser.parse_args()
runtime = args.directory / 'rexruntime.dll'
pe = pefile.PE(str(runtime), fast_load=True, max_symbol_exports=65536)
pe.parse_data_directories(directories=[0])
exports = {s.name for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
if len(exports) != pe.DIRECTORY_ENTRY_EXPORT.struct.NumberOfNames:
    raise SystemExit('Export table truncated; cannot establish import compatibility')
missing = []
for path in args.directory.iterdir():
    if path.suffix.lower() not in ('.dll', '.exe') or path == runtime:
        continue
    module = pefile.PE(str(path), fast_load=True)
    module.parse_data_directories(directories=[1])
    for library in getattr(module, 'DIRECTORY_ENTRY_IMPORT', []):
        if library.dll.lower() == b'rexruntime.dll':
            for symbol in library.imports:
                if symbol.name is None or symbol.name not in exports:
                    missing.append((path.name, symbol.name.decode() if symbol.name else f'ordinal:{symbol.ordinal}'))
result = {'runtime_sha256': hashlib.sha256(runtime.read_bytes()).hexdigest(),
          'exports': len(exports), 'missing_imports': missing,
          'limitation': 'Checks exported names, not C++ object layout or runtime behavior.'}
content = json.dumps(result, indent=2)
(args.directory / 'import-audit.json').write_text(content + '\n')
print(content)
raise SystemExit(bool(missing))
