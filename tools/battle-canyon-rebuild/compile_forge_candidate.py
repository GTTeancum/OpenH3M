"""Compile combined authoring once, restoring overlays and the previous MCC cache."""
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'work/battle-canyon/rebuild'
KIT=ROOT/'work/editing-kits/h3ek'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lighting-quality',choices=['low','medium','high'])
    parser.add_argument('--lighting-blob-id',default='115')
    parser.add_argument('--lighting-workers',type=int,default=4)
    parser.add_argument('--lighting-resume-final-gather',action='store_true')
    parser.add_argument('--stage-directory',type=Path,
                        help='Fresh repository-local evidence directory; preserves previous compile reports/cache')
    parser.add_argument('--restored-sky-colors',action='store_true',
                        help='Overlay the independently verified original-Reach sky RGB repair')
    args=parser.parse_args()
    if args.lighting_quality:
        if not args.lighting_blob_id.isdecimal() or ((KIT/'faux'/args.lighting_blob_id).exists() and not args.lighting_resume_final_gather):
            raise ValueError('Final lighting requires a new numeric farm dataset')
        if not 1<=args.lighting_workers<=os.cpu_count():
            raise ValueError('Invalid lightmapper worker count')
    stage=args.stage_directory.resolve() if args.stage_directory else WORK/'forge/compile-check'
    if not stage.is_relative_to(WORK.resolve()):
        raise ValueError('Compile evidence must remain inside Battle Canyon rebuild work')
    if args.stage_directory and stage.exists():
        raise FileExistsError('Explicit compile evidence directory must be new')
    stage.mkdir(parents=True,exist_ok=True)
    manifest=stage/'active-transaction.json'
    if manifest.exists():raise RuntimeError('Inspect unfinished overlay transaction before retrying')
    overlay={}
    # Same precedence as the authoring dependency audit; existing official tags
    # win over recovered stock tags, while intentional candidate overlays win.
    for path in (WORK/'forge/stock-assets/tags').rglob('*'):
        if path.is_file():
            rel=path.relative_to(WORK/'forge/stock-assets/tags')
            if not (KIT/'tags'/rel).exists():overlay[KIT/'tags'/rel]=path
    for root in (WORK/'placed-effects/tags',WORK/'supplemental-tags/tags',WORK/'forge/locale/tags',WORK/'forge/remaining-objects/tags'):
        for path in root.rglob('*'):
            if path.is_file():overlay[KIT/'tags'/path.relative_to(root)]=path
    if args.restored_sky_colors:
        proof=json.loads((WORK/'sky-color-repair/compiled-verification.json').read_text())
        restored=Path(proof['compiled_render_model']).resolve()
        assert restored.is_relative_to(KIT.resolve())
        assert hashlib.sha256(restored.read_bytes()).hexdigest()==proof['sha256']
        assert proof['vertices']==proof['source_vertices_matched']==6577
        assert proof['old_nonzero_vertices']==0 and proof['restored_nonzero_vertices']==3683
        assert proof['preserved_fields']['sky lights']==101
        assert proof['max_error']['source_color']<1e-6
        overlay[KIT/'tags/levels/dlc/cex_beaver_creek/beavercreek_sky/beavercreek_sky.render_model']=restored
    scenario=KIT/'tags/levels/mod_levels/battle_canyon/battle_canyon.scenario'
    overlay[scenario]=WORK/'forge/scenery-candidate.scenario'
    cache=KIT/'maps/battle_canyon.map'
    lighting_root=KIT/'tags/levels/mod_levels/battle_canyon'
    lighting_inputs=set(lighting_root.glob('*')) if args.lighting_quality else set()
    lighting_inputs={p for p in lighting_inputs if p.is_file() and p not in overlay}
    rows=[]
    for index,target in enumerate([*overlay,cache,*sorted(lighting_inputs)]):
        assert target.resolve().is_relative_to(KIT.resolve()),target
        backup=stage/f'backup-{index}.bin'
        exists=target.is_file()
        if exists:shutil.copy2(target,backup)
        rows.append({'target':str(target),'backup':str(backup),'existed':exists,
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest() if exists else None})
    manifest.write_text(json.dumps(rows,indent=2))
    result={}
    lighting_succeeded=False
    try:
        for target,source in overlay.items():
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        log=stage/'compiler.log';started=time.time()
        env=dict(os.environ,TEMP=str(WORK/'temp'),TMP=str(WORK/'temp'))
        if args.lighting_quality:
            lighting_log=stage/'final-lighting.log'
            lighting_started=time.time()
            expected=hashlib.sha256(overlay[scenario].read_bytes()).hexdigest()
            command=[sys.executable,'-B',str(ROOT/'tools/battle-canyon-rebuild/lightmap.py'),
                     '--quality',args.lighting_quality,'--workers',str(args.lighting_workers),
                     '--blob-id',args.lighting_blob_id,'--expected-scenario-sha256',expected]
            if args.lighting_resume_final_gather:
                command.append('--resume-final-gather')
            with lighting_log.open('w') as out:
                subprocess.run(command,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
            lighting_succeeded=True
            (stage/'final-lighting-result.json').write_text(json.dumps({
                'quality':args.lighting_quality,'blob_id':args.lighting_blob_id,
                'elapsed_seconds':time.time()-lighting_started,'scenario_sha256':expected,
                'output_files':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                                 'bytes':p.stat().st_size} for p in sorted(lighting_root.glob('*')) if p.is_file()],
                'scope':'Official bake completed; native visual acceptance still required'},indent=2))
            print('Official final lighting completed; compiling candidate',flush=True)
        with log.open('w') as out:
            proc=subprocess.run([str(KIT/'tool_fast.exe'),'build-cache-file',r'levels\mod_levels\battle_canyon\battle_canyon'],
                cwd=KIT,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=600)
        logtext=log.read_text(errors='replace')
        success=proc.returncode==0 and 'successfully built cache file.' in logtext and cache.is_file() and cache.stat().st_mtime>=started-2
        result={'exit_code':proc.returncode,'compiled':success,'elapsed_seconds':time.time()-started,
                'scenario_sha256':hashlib.sha256(overlay[scenario].read_bytes()).hexdigest(),
                'compiler_error_lines':[line for line in logtext.splitlines() if '-ERROR-' in line or line.startswith('ERROR:')],
                'lighting_quality':args.lighting_quality or 'existing',
                'restored_sky_colors':args.restored_sky_colors,
                'scope':'Combined authoring compile; native visual and performance acceptance remain separate.'}
        if success:
            output=stage/'battle_canyon.map';shutil.copy2(cache,output)
            result.update(cache=str(output),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    finally:
        for row in reversed(rows):
            target=Path(row['target']);backup=Path(row['backup'])
            # Successful lighting stays in the kit for reproducible subsequent
            # compiles. On a failed bake restore the pre-bake lighting inputs.
            # Always restore the temporary scenario/dependency overlays/cache.
            if lighting_succeeded and target in lighting_inputs:
                continue
            if row['existed']:
                shutil.copy2(backup,target)
                assert hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256'],target
            elif target.exists():target.unlink()
        for row in rows:
            backup=Path(row['backup'])
            if backup.exists():backup.unlink()
        manifest.unlink()
    result['explicit_overlays_and_previous_cache_restored']=True
    result['new_lighting_retained_in_kit']=lighting_succeeded
    (stage/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
