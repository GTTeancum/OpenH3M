"""Read-only prerequisite/source inventory for the editing-kit Halo 4 workflow.

This does not decode or convert game assets, run an installer, or modify a kit.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[4]
STEAM = Path('C:/Program Files (x86)/Steam')
APPS = {'976730': 'MCC', '1695791': 'H3EK', '1695792': 'H4EK', '1695793': 'HREK'}

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    libraries = [Path(p.replace('\\\\', '\\')) for p in re.findall(
        r'"path"\s+"([^"]+)"', (STEAM/'steamapps/libraryfolders.vdf').read_text())]
    installed = []
    for library in libraries:
        for app, name in APPS.items():
            manifest = library/'steamapps'/f'appmanifest_{app}.acf'
            if not manifest.exists():
                continue
            fields = dict(re.findall(r'"([^"\r\n]+)"\s+"([^"\r\n]*)"', manifest.read_text()))
            installed.append(dict(app_id=app, kit=name, name=fields.get('name'),
                build_id=fields.get('buildid'), state_flags=fields.get('StateFlags'),
                install_dir=str(library/'steamapps/common'/fields['installdir']),
                manifest=str(manifest), manifest_sha256=digest(manifest)))
    source = Path('D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo4/maps/wraparound.map')
    info = source.parent/'info/wraparound.mapinfo'
    info_data = info.read_bytes()
    title_offsets = {encoding: info_data.find('Haven'.encode(encoding))
                     for encoding in ('utf-16-be', 'utf-16-le', 'utf-8')}
    assert any(offset >= 0 for offset in title_offsets.values()), 'Haven title not found in supplied mapinfo'
    report = dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),
        selected_map='Haven', source_game='Halo 4', internal_cache='wraparound',
        source_scope='Installed original MCC map and paired mapinfo; editable H4EK source evidence is tracked separately',
        source_files=[dict(path=str(p), bytes=p.stat().st_size, sha256=digest(p)) for p in (source,info)],
        haven_title_offsets=title_offsets, installed_apps=installed,
        h4ek_installed=any(a['kit']=='H4EK' and int(a['state_flags'] or '0') & 4 for a in installed),
        h4ek_store='https://store.steampowered.com/app/1695792/Halo_4_Mod_Tools__MCC/',
        repository_kits=[str(p.relative_to(ROOT)) for p in (ROOT/'work/editing-kits').iterdir()
                         if p.is_dir() and p.name.lower() in ('h3ek','hrek','h4ek')],
        selected_tools={
            'foundry_revision':'5dc085e4432b6b57b2bf97e02a442ecc6edc985f',
            'general101_revision':'81e86bf98aee4607a2159ff9a22a223a1a91c9d7',
            'blender':'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe',
            'note':'Reuse existing pinned unmodified tool sources; H4 import has not yet been tested'},
        conversion_status='prerequisites only; no H4 assets converted or H3 map compiled')
    output=ROOT/'work/halo4-to-h3/haven/environment.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'selected_map':report['selected_map'],'h4ek_installed':report['h4ek_installed'],
        'installed_kits':[a['kit'] for a in installed], 'source_files':report['source_files'],
        'title_offsets':title_offsets}))

if __name__=='__main__':
    main()
