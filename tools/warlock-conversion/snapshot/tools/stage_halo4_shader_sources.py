"""Stage official H4 shader source files with 7-Zip; verify archive size/CRC.

Read-only source reference for material mapping, not a shader compiler/patch.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import zlib

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'work/halo4-to-h3/haven'
KIT=ROOT/'work/editing-kits/h4ek'
ARCHIVE=Path('Z:/SteamLibrary/steamapps/common/H4EK/H4EK.7z')
rows=[r for r in json.loads((OUT/'h4ek-archive-index.json').read_text())
    if r['path'].startswith('data/shaders/material_shaders/')]
assert len(rows)==758 and sum(r['size'] for r in rows)==2670829
listing=OUT/'h4-shader-source-files.txt'
listing.write_text('\n'.join(r['path'].replace('/','\\') for r in rows)+'\n',encoding='utf-8')
env=os.environ.copy();env['TEMP']=env['TMP']=str(OUT/'temp')
with (OUT/'h4-shader-source-extract.log').open('wb') as log:
    result=subprocess.run(['C:/Program Files/7-Zip/7z.exe','x','-aos','-y','-bb0','-bsp0',
        '-o'+str(KIT),str(ARCHIVE),'@'+str(listing)],cwd=ROOT,env=env,
        stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert result.returncode==0
verified=[]
for row in rows:
    path=(KIT/row['path']).resolve()
    assert path.is_relative_to((KIT/'data/shaders/material_shaders').resolve())
    data=path.read_bytes()
    assert len(data)==row['size'] and f'{zlib.crc32(data):08X}'==row['crc'].upper(),row['path']
    verified.append(dict(path=row['path'],sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),archive_crc_verified=True))
report=dict(status='verified',archive=str(ARCHIVE),files=verified,
    purpose='Original official shader source reference; all files unmodified.')
(OUT/'h4-shader-source-staging.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('H4_OFFICIAL_SHADER_SOURCES_STAGED',len(verified),sum(r['bytes'] for r in verified),flush=True)
