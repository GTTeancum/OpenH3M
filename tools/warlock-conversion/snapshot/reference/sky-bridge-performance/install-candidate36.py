"""Prepare or apply the verified single-map Sky Bridge update inside the repository."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib

REF=Path(__file__).resolve().parent
REPO=REF.parents[4]
SHARED=REPO/'work/dlc/installed-corrections'
CACHE=REPO/'work/dlc/cache'
WORK=REPO/'work/sky-bridge/candidate36-install'
TARGET=SHARED/'0000000000000000/4D5307E6/00000002/C337EBA990B40F54512D18E8AB31188A2B040540/sky_bridge.map'
SOURCE=REPO/'work/sky-bridge/payload-36/sky_bridge.map'
BOOTSTRAP=Path('C:/X360/ISOs/H3M/OpenH3M.bootstrap.toml')
OLD='311ad88580c5e099546c029f07f93976c346a8bb9bf9b12c1d48f72f5e0c3e5d'
NEW='39873291ea89a3225a53ecda3f9811f7429ab46c8760ebc07a9938fcf8dd0245'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def entry(path):return dict(bytes=path.stat().st_size,sha256=sha(path))


def inventory(root):
    result={}
    for path in sorted(root.rglob('*')):
        assert not path.is_symlink(),path
        if path.is_file():result[path.relative_to(root).as_posix()]=entry(path)
    return result


def idle():
    subprocess.run(['powershell','-NoProfile','-Command',
        'if (Get-Process OpenH3M,halo3mp -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }'],
        check=True,cwd=REPO,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)


def validate():
    assert Path.cwd().resolve()==REPO.resolve()
    for path in (SHARED,CACHE,WORK,TARGET,SOURCE):
        assert path.resolve().is_relative_to(REPO.resolve()),path
    assert TARGET.resolve().is_relative_to(SHARED.resolve())
    idle()
    settings=tomllib.loads(BOOTSTRAP.read_text())
    assert Path(settings['user_data_root']).resolve()==SHARED.resolve()
    assert Path(settings['cache_root']).resolve()==CACHE.resolve()
    baseline=read(REPO/'work/sky-bridge/promotion-candidate36/shared-before.json')
    assert inventory(SHARED)==baseline['files'],'Shared content changed since the prepared plan; inspect and rebase without restoring old files'
    runtime={str(Path('C:/X360/ISOs/H3M')/name):entry(Path('C:/X360/ISOs/H3M')/name)
        for name in baseline['shared_runtime']}
    assert {Path(name).name:v for name,v in runtime.items()}==baseline['shared_runtime'],'Runtime or settings changed'
    assert sha(TARGET)==OLD and sha(SOURCE)==NEW
    review=read(REF/'candidate36-visual-review-result.json')
    assert len(review['frames'])==6 and all(f['inspected_individually'] for f in review['frames'])
    assert review['native_observer_exact'] and review['native_headers']['failed']==0
    assert all(sha(REPO/f['path'])==f['sha256'] for f in review['frames'])
    live=read(REF/'candidate36-native-live-result.json')
    assert live['native_map_id']==1747 and live['native_headers']['passed']==11 and live['native_headers']['failed']==0
    assert live['configuration']['map_sha256']==NEW
    assert all(sha(p)==sha(TARGET.parent/p.name) for p in SOURCE.parent.iterdir() if p.name!='sky_bridge.map')
    return baseline,runtime,review


def prepare():
    baseline,runtime,review=validate()
    assert not WORK.exists(),'Prepared directory already exists; do not overwrite its rollback/evidence'
    WORK.mkdir()
    shutil.copyfile(TARGET,WORK/'sky_bridge.previous.map')
    shutil.copyfile(SOURCE,WORK/'sky_bridge.pending.map')
    assert sha(WORK/'sky_bridge.previous.map')==OLD
    assert sha(WORK/'sky_bridge.pending.map')==NEW
    state=dict(status='Prepared; no shared write',target=str(TARGET),source=str(SOURCE),
        before=baseline['files'],cache_before=inventory(CACHE),runtime_before=runtime,
        old_sha256=OLD,new_sha256=NEW,visual_report_sha256=sha(REF/'candidate36-visual-review-result.json'),
        credit=review['credit'])
    (WORK/'prepared.json').write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps(dict(status=state['status'],backup=str(WORK/'sky_bridge.previous.map'),
        content_files=len(state['before']),cache_files=len(state['cache_before']))))


def apply():
    baseline,runtime,review=validate()
    state=read(WORK/'prepared.json')
    assert not (WORK/'installed.json').exists(),'This promotion has already been recorded'
    assert state['before']==baseline['files'] and state['runtime_before']==runtime
    assert state['cache_before']==inventory(CACHE),'Shared cache changed after preparation'
    assert state['visual_report_sha256']==sha(REF/'candidate36-visual-review-result.json')
    previous,pending=WORK/'sky_bridge.previous.map',WORK/'sky_bridge.pending.map'
    assert sha(previous)==OLD and sha(pending)==NEW
    idle()
    assert sha(TARGET)==OLD
    os.replace(pending,TARGET)
    after=inventory(SHARED)
    expected=dict(state['before']);key=TARGET.relative_to(SHARED).as_posix()
    expected[key]=entry(SOURCE)
    assert after==expected,'Unexpected shared-content change; inspect concurrent work, never restore unrelated files'
    assert inventory(CACHE)==state['cache_before'],'Shared cache changed concurrently'
    assert {path:entry(Path(path)) for path in runtime}==runtime,'Runtime/settings changed concurrently'
    result=dict(status='Candidate36 installed in the existing shared Sky Bridge map; overall goal remains open',
        target=str(TARGET),sha256=sha(TARGET),old_sha256=OLD,backup=str(previous),backup_sha256=sha(previous),
        changed_files=[key],unchanged_content_files=len(after)-1,cache_files_unchanged=len(state['cache_before']),
        runtime_and_bootstrap_unchanged=True,runtime_hashes={p:v['sha256'] for p,v in runtime.items()},
        bootstrap_sha256=sha(BOOTSTRAP),external_writes=[],
        native_live_package=read(REF/'candidate36-native-live-result.json')['release']['package'],
        visual_report_sha256=state['visual_report_sha256'],
        visual_scope='Six saved-view native images plus existing paired numeric traces; not a complete map walkthrough',
        remaining=review['limitations'],before=state['before'],after=after,credit=review['credit'])
    (WORK/'installed.json').write_text(json.dumps(result,indent=2)+'\n')
    compact={k:v for k,v in result.items() if k not in ('before','after')}
    compact['preservation_report']=str((WORK/'installed.json').relative_to(REPO))
    compact['preservation_report_sha256']=sha(WORK/'installed.json')
    (REF/'candidate36-install-result.json').write_text(json.dumps(compact,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','sha256','changed_files','unchanged_content_files','cache_files_unchanged','external_writes')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='Apply the already prepared and revalidated one-map update')
    args=parser.parse_args()
    os.environ['TEMP']=os.environ['TMP']=str(REPO/'.local/build-temp')
    apply() if args.apply else prepare()
