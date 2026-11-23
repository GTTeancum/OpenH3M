"""Bake a scenario BSP's lighting with the H3 Editing Kit's own lighting farm, using a fixed number of worker
processes instead of one per CPU core. Mirrors the kit's calc_lm_farm_local.py step for step (same tool_fast
commands, same order); only the worker count differs.

Usage: bake.py <scenario> <bsp name> <quality> [--workers N] [--log path]
quality: high, medium, low, direct_only, super_slow, draft, debug
"""
import argparse, os, subprocess, sys, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / '.local/h3ek-source'
p = argparse.ArgumentParser(); p.add_argument('scenario'); p.add_argument('bsp'); p.add_argument('quality')
p.add_argument('--workers', type=int, default=4); p.add_argument('--light-group', default='all')
p.add_argument('--log', type=Path, default=ROOT / '.local/geometry-rebuild/bake.log')
a = p.parse_args()
env = os.environ.copy(); env['TEMP'] = env['TMP'] = str(KIT / 'temp')
TOOL = str(KIT / 'tool_fast.exe'); BLOB_NAME = '111'; BLOB = 'faux\\' + BLOB_NAME
a.log.parent.mkdir(parents=True, exist_ok=True); log = open(a.log, 'w', encoding='utf-8', errors='replace')
start = datetime.datetime.now()
NO_WINDOW = 0x08000000 | 0x00000040   # no window, idle priority (only spare CPU time)

def say(text):
    line = f'*** {text} *** ({datetime.datetime.now() - start})'; print(line, flush=True); log.write(line + '\n'); log.flush()

def run(*args):
    r = subprocess.run([TOOL, *args], cwd=KIT, env=env, stdout=log, stderr=log, creationflags=NO_WINDOW)
    if r.returncode != 0: raise SystemExit(f'{args[0]} failed with {r.returncode}; see {a.log}')

def farm(stage):
    say(f'farm stage: {stage} ({a.workers} workers)')
    logs = []
    procs = []
    for i in range(a.workers):
        lp = KIT / BLOB / 'logs' / f'{stage}{i}.txt'; lp.parent.mkdir(parents=True, exist_ok=True)
        f = open(lp, 'w'); logs.append(f)
        procs.append(subprocess.Popen([TOOL, 'faux_farm_' + stage, BLOB, str(i), str(a.workers)], cwd=KIT, env=env, stdout=f, stderr=f, creationflags=NO_WINDOW))
    codes = [pr.wait() for pr in procs]
    for f in logs: f.close()
    if any(codes): raise SystemExit(f'{stage} worker failed: {codes}')
    run('faux_farm_' + stage + '_merge', BLOB, str(a.workers))

say('faux_data_sync'); run('faux_data_sync', a.scenario, a.bsp)
say('faux_farm_begin'); run('faux_farm_begin', a.scenario, a.bsp, a.light_group, a.quality, BLOB_NAME)
for stage in ('dillum', 'pcast', 'radest', 'extillum', 'fgather'): farm(stage)
say('faux_farm_finish'); run('faux_farm_finish', BLOB)
run('faux-build-linear-textures-with-intensity-from-quadratic', a.scenario, a.bsp)
run('faux-compress-scenario-bitmaps-dxt5', a.scenario, a.bsp)
run('faux-farm-compression-merge', a.scenario, a.bsp)
say('finished')
