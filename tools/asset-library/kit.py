"""Shared helpers: run the official H3EK tool.exe from the private asset kit.

The asset kit (.local/asset-kit-h3) holds copies of the official executables
and junctions to the shared H3EK tags tree, so runs do not share cwd, temp or
report files with other sessions. New tags are written only under the
namespaces listed in NEW_TAG_ROOTS.
"""
import os, subprocess, json, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / os.environ.get('OPENH3M_ASSET_KIT', '.local/asset-kit-h3')  # optional private exe folder (tags/fmod junctions to h3ek-source), e.g. the vehicle session's .local/asset-kit-h3-veh (removed after use)
TAGS = KIT / 'tags'
DATA = KIT / 'data'
WORK = ROOT / 'work/asset-library/_work'
LIB = ROOT / 'work/asset-library'
NEW_TAG_ROOTS = [
    r'objects\weapons\pistol\ce_magnum',
    r'objects\weapons\rifle\reach_dmr',
    r'objects\vehicles\reach_falcon',
    r'objects\vehicles\reach_revenant',
    r'levels\test\asset_library_test',
]
def env():
    e = os.environ.copy()
    for k, p in [('APPDATA', 'profile/roaming'), ('LOCALAPPDATA', 'profile/local'), ('TEMP', 'temp'), ('TMP', 'temp')]:
        e[k] = str(KIT / p)
    return e
def _tool_visible_unused(*args, log=None, timeout=1800, exe='tool.exe'):
    r = subprocess.run([str(KIT / exe), *map(str, args)], cwd=KIT, env=env(), capture_output=True, timeout=timeout)
    out = (r.stdout + r.stderr).decode('utf-8', 'replace')
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True); Path(log).write_text(out, encoding='utf-8')
    return r.returncode, out
def to_xml(tag_rel, xml_path):
    xml_path = Path(xml_path); xml_path.parent.mkdir(parents=True, exist_ok=True)
    rc, out = htool('export-tag-to-xml', TAGS / tag_rel, xml_path, log=WORK / 'logs' / (xml_path.name + '.log'), timeout=300)
    if rc != 0 or not xml_path.exists():
        raise RuntimeError(f'export failed {tag_rel}: {out[-2000:]}')
    return xml_path
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
import re as _re
import xml.etree.ElementTree as _ET
def parse_xml(path):
    """Parse tool.exe XML exports; they contain raw bytes for some fields."""
    text = Path(path).read_bytes().decode('latin-1')
    text = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '?', text)
    text = text.replace('<unavailable>', '&lt;unavailable&gt;')
    text = _re.sub(r'&(?!(amp|lt|gt|quot|apos|#\d+);)', '&amp;', text)
    return _ET.fromstring(text)
def fields(elem):
    return {f.get('name'): f.get('value') for f in elem.findall('field')}
TAGEDIT = ROOT / '.local/asset-tools/mbcs/TagEdit.exe'
def build_tagedit():
    import shutil
    d = TAGEDIT.parent; d.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(KIT / 'bin/ManagedBlam.dll', d / 'ManagedBlam.dll')
    r = subprocess.run([r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe', '/nologo', '/platform:x64', '/highentropyva-',
                        '/target:exe', '/out:' + str(TAGEDIT), '/reference:' + str(d / 'ManagedBlam.dll'),
                        '/reference:System.Web.Extensions.dll', str(Path(__file__).with_name('TagEdit.cs'))], capture_output=True)
    if r.returncode: raise RuntimeError(r.stdout.decode(errors='replace'))
_edit_n = [0]
def edit(ops, name='edit', timeout=300):
    """Run TagEdit ops on the hidden desktop. Raises on failure."""
    import hidden_run
    _edit_n[0] += 1
    plan = WORK / 'logs' / f'{name}-{_edit_n[0]}.json'; plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(json.dumps({'ops': ops}, indent=1))
    rc, out = hidden_run.run([TAGEDIT, KIT, plan], KIT, plan.with_suffix('.log'), timeout=timeout, env=env())
    if rc != 0 or 'TAGEDIT_OK' not in out:
        raise RuntimeError(f'TagEdit failed rc={rc}: {out[-3000:]}')
    return out
def dump(tag_rel, out=None):
    from pathlib import PureWindowsPath
    out = Path(out or WORK / 'dumps' / (PureWindowsPath(tag_rel).name + '.txt')); out.parent.mkdir(parents=True, exist_ok=True)
    edit([{'op': 'dump', 'tag': tag_rel, 'out': str(out)}], 'dump')
    return out
def htool(*args, log, timeout=1800, exe='tool.exe'):
    """tool.exe on the hidden desktop."""
    import hidden_run
    return hidden_run.run([KIT / exe, *args], KIT, log, timeout=timeout, env=env())
RKIT = ROOT / '.local/asset-kit-hrek'
def renv():
    e = os.environ.copy()
    for k, p in [('APPDATA', 'profile/roaming'), ('LOCALAPPDATA', 'profile/local'), ('TEMP', 'temp'), ('TMP', 'temp')]:
        e[k] = str(RKIT / p)
    return e
def rtool(*args, log, timeout=900):
    """Reach (HREK) tool.exe on the hidden desktop, cwd = repo-local Reach project."""
    import hidden_run
    return hidden_run.run([RKIT / 'tool.exe', *args], RKIT, log, timeout=timeout, env=renv())
def rxml(tag_rel, xml_path):
    xml_path = Path(xml_path); xml_path.parent.mkdir(parents=True, exist_ok=True)
    rc, out = rtool('export-tag-to-xml', RKIT / 'tags' / tag_rel, xml_path, log=WORK / 'logs' / (xml_path.name + '.log'), timeout=300)
    if rc != 0 or not xml_path.exists(): raise RuntimeError(f'reach export failed {tag_rel}: {out[-1500:]}')
    return xml_path
