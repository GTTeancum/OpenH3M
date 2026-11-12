"""Deploy the tested DLC host beside the original disc, retaining one rollback set."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def advanced_forge_settings(data):
    """Configure private editor inputs without copying them into DLC or layouts."""
    if data is None:
        return {}
    data = data.resolve(strict=True)
    if not data.is_relative_to(ROOT):
        raise ValueError('Advanced Forge inputs must stay in this repository')
    for relative, size in (('h4-image.bin', 0x2f38000),
                           ('isolated/forge-globals.bin', 80)):
        path = data / relative
        if not path.is_file() or path.stat().st_size != size:
            raise ValueError(f'Invalid Advanced Forge input: {relative}')
    markers = (data / 'isolated/markers.bin').read_bytes()
    if len(markers) < 8 or markers[:4] != b'AFM2':
        raise ValueError('Invalid Advanced Forge marker bindings')
    # Opt-in through F7; never carry exclusive replay or diagnostic drag into
    # the user's direct launch. Runtime performs full binding validation.
    return {'halo3mp_advanced_forge_data': data.as_posix(),
            'halo3mp_advanced_forge': False}


def deploy(install, build, content, advanced_forge_data=None):
    editor_settings = advanced_forge_settings(advanced_forge_data)
    install, build, content = (p.resolve(strict=True) for p in (install, build, content))
    for p in (build, content):
        if not p.is_relative_to(ROOT):
            raise ValueError('Build and installed content must stay in this repository')
    if digest(install / 'default.xex') != '18816c1da58b1371e440741fadab1df8e6e6ecca7c5b81952f2d23ceec797313':
        raise ValueError('Unexpected original disc XEX')
    listing = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if '"openh3m.exe"' in listing or '"halo3mp.exe"' in listing:
        raise ValueError('Close the game before deployment')
    names = {'OpenH3M.exe': 'halo3mp.exe', **{n: n for n in (
        'rexruntime.dll', 'rexgpu-xenos.dll', 'halo3mp_l360.dll', 'halo3mp_q10.dll',
        'halo3mp_waveshell-xbox.dll', 'halo3mp_waveslibdll.dll')}}
    for name in names.values():
        if not (build / name).is_file():
            raise ValueError(f'Missing build file: {name}')
    if len(list(content.rglob('forge_gulch.map'))) != 1:
        raise ValueError('Expected exactly one installed DLC bundle')
    rollback = ROOT / 'work/dlc/rollback'
    rollback.mkdir(exist_ok=True)
    before = {}
    for name in (*names, 'OpenH3M.bootstrap.toml'):
        source, backup = install / name, rollback / name
        if source.exists():
            before[name] = digest(source)
            if not backup.exists():
                os.link(source, backup)
    # Replacements are atomic: rollback hardlinks must retain their old bytes.
    for target, name in names.items():
        temporary = rollback / (target + '.deploy')
        shutil.copyfile(build / name, temporary)
        os.replace(temporary, install / target)
    settings = {
        'game_data_root': install.as_posix(), 'user_data_root': content.as_posix(),
        'cache_root': (ROOT / 'work/dlc/cache').as_posix(),
        'log_file': (ROOT / '.local/runtime-logs/OpenH3M.log').as_posix(),
    }
    settings.update(editor_settings)
    (ROOT / '.local/runtime-logs').mkdir(exist_ok=True)
    text = '# Managed by deploy_dlc_host.py\n' + ''.join(f'{k} = {json.dumps(v)}\n' for k, v in settings.items())
    text += ('host_guest_output_fps = 30\nlog_max_file_size_mb = 5\nlog_max_files = 3\n'
             'host_present_from_non_ui_thread = false\nd3d12_host_sync_interval = 1\n'
             'd3d12_host_waitable_presentation = true\nd3d12_host_maximum_frame_latency = 2\n'
             'host_output_display_phase = true\nd3d12_async_occlusion_readback = true\n')
    temporary = rollback / 'bootstrap.deploy'
    temporary.write_text(text)
    os.replace(temporary, install / 'OpenH3M.bootstrap.toml')
    report = dict(install=str(install), before=before, rollback=str(rollback),
                  files={n: digest(install / n) for n in names}, settings=settings,
                  status='deployed; direct-launch check required')
    (ROOT / 'work/dlc/deployment.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', required=True, type=Path)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--content', required=True, type=Path)
    parser.add_argument('--advanced-forge-data', type=Path,
                        help='Private H4 research directory; magnets remain off until enabled with F7')
    args = parser.parse_args()
    deploy(args.install, args.build, args.content, args.advanced_forge_data)
