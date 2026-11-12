"""Coordinated single-instance native test using existing process-local tooling."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/video-options'))
from single_instance import acquire,ensure_no_game
acquire()
import subprocess
subprocess.run(['powershell','-NoProfile','-Command','if (Get-Process Spartan -ErrorAction SilentlyContinue) { exit 1 }'],cwd=ROOT,check=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
TOOLS=ROOT/'tools/warlock-conversion/snapshot/tools'
sys.path.insert(0,str(TOOLS))
from prepare_powerhouse_battle_rifle import sha

out=ROOT/'work/sky-bridge-battle-rifle'
forge='--forge' in sys.argv
proof=json.loads((out/'proof.json').read_text())
assert sha(out/'sky_bridge.map')==proof['candidate_sha256']
stage=ROOT/'work/map-review-20261105/powerhouse-cache-native-01'
exe=stage/'bin/OpenH3M.exe'
config=stage/'bin/OpenH3M.toml'
original=config.read_bytes()
payload=out/'native-payload'
payload.mkdir(exist_ok=False)
installed=Path(proof['source'])
for p in installed.parent.iterdir():
    if p.name=='sky_bridge.map':os.link(out/'sky_bridge.map',payload/p.name)
    elif p.name=='sky_bridge.mapinfo' or p.name.startswith('dlc_sky_bridge'):os.link(p,payload/p.name)
points=ROOT/'.local/map-benchmarks'/('sky-bridge-battle-rifle-forge' if forge else 'sky-bridge-battle-rifle')
points.mkdir(exist_ok=True)
(points/'points.txt').write_text('24.9804573 110.6094589 -0.52149874 0\n')
settings=original.decode()
script=TOOLS/'trace_loading.py'
source=script.read_text()
# Extend the existing read-only snapshot to weapon objects; no runtime edits.
old="sampled_groups += ('bipd',)"
assert source.count(old)==1
source=source.replace(old,"sampled_groups += ('bipd', 'weap')")
marker="(RUN / 'launch-command.json').write_text"
assert source.count(marker)==1
flags=['--halo3mp_benchmark_map=sky_bridge',
       '--halo3mp_benchmark_points='+str(points/'points.txt'),
       '--halo3mp_benchmark_seconds=5']
source=source.replace(marker,'args += '+repr(flags)+'\n'+marker)
marker="log('observer_position', position=position,"
assert source.count(marker)==1
source=source.replace(marker,"log('observer_position', internal_path=read(guest_memory_base+observer_word(tls+0x80)+0x34,260).split(bytes(1))[0].decode('ascii',errors='replace'), position=position,")
actions='128000:RB+1800,140000:RT+100,142000:RT+100,150000:RB+200'
args=['--project',str(ROOT/'../..'),'--exe',str(exe),'--expected-exe-sha256',sha(exe),
      '--game',str(stage/'game'),'--slot','zanzibar','--seconds','180',
      '--exclusive-input','--sample-observer','--quiet-timing',
      '--dlc-payload',str(payload),'--dlc-map','sky_bridge',
      '--inspection-input',actions,'--capture','--capture-times-ms','125000,140000,150000',
      '--audio-frames','800','--audio-after-seconds','138',
      '--sample-object-map',str(out/'sky_bridge.map'),'--sample-player-objects',
      '--sample-object-body-bytes','1024','--sample-object-interval','1']
seed=ROOT/'work/powerhouse-battle-rifle/native-shader-cache'
if seed.exists():args+=['--shader-cache-seed',str(seed)]
# Audio follows actual native replay firing, independent of startup time.
helper="""def audio_fire_seen():
    path=RUN/'trace-runtime.log'
    if not path.exists(): return False
    with path.open('rb') as stream:
        stream.seek(max(0,path.stat().st_size-131072))
        tail=stream.read()
    return b'rt=255' in tail

"""
source=source.replace('audio_address = None',helper+'audio_address = None',1)
source=source.replace('now - started >= options.audio_after_seconds','audio_fire_seen()')
source=source.replace('time.monotonic() - started >= options.audio_after_seconds','audio_fire_seen()')
if forge:
    args+=['--forge-palette-check']
    marker="input_steps.extend(['118000:UP+200', '121000:X+200'])"
    assert source.count(marker)==1
    source=source.replace(marker,"input_steps.extend(['126000:UP+200', '129000:X+200'])")
    args[args.index('--inspection-input')+1]='131000:DOWN+200,148000:A+200,154000:A+200,155000:RSDOWN+300'
if forge or '--visual-only' in sys.argv:
    for flag in ('--audio-frames','--audio-after-seconds'):
        index=args.index(flag);del args[index:index+2]
before=set((ROOT/'.local/loading-traces').iterdir())
(out/'native-launch.json').write_text(json.dumps(dict(args=args,source_extension=old+' -> include weap',candidate_sha256=proof['candidate_sha256']),indent=2)+'\n')
try:
    ensure_no_game()
    config.write_text(settings)
    sys.argv=[str(script)]+args
    exec(compile(source,str(script),'exec'),{'__name__':'__main__','__file__':str(script)})
finally:
    config.write_bytes(original)
    runs=sorted(str(p) for p in set((ROOT/'.local/loading-traces').iterdir())-before)
    (out/'native-runs.json').write_text(json.dumps(runs,indent=2)+'\n')
    assert sha(installed)==proof['before_sha256']
    assert payload.resolve().is_relative_to(out.resolve())
    for p in payload.iterdir():p.unlink()
    payload.rmdir()
    print('Private configuration restored; shared map unchanged; runs:',runs,flush=True)

