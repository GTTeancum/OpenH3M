"""Install only a reviewed Battle Canyon payload after a specific game exits.

This is file deployment, not a game/control harness. It never starts a game,
sends input, attaches a debugger, captures a frame, or terminates a process.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/battle-canyon/rebuild'
BUNDLE = ROOT / 'work/dlc/installed-corrections/0000000000000000/4D5307E6/00000002/E3C216511E5A0ED8A2E37F70BC65E407C481C510'
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from warlock_handoff import preflight


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--candidate', required=True)
    p.add_argument('--expected-current-sha256', required=True)
    p.add_argument('--wait-pid', type=int)
    a = p.parse_args()
    assert a.candidate and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.candidate)
    source = a.source.resolve(strict=True)
    assert source.is_relative_to(WORK)
    report = WORK / 'native' / (a.candidate+'-installation.json')
    assert not report.exists(), 'Review the previous attempt before creating another installer'
    proof = preflight(source, Path('C:/X360/ISOs/H3M/default.xex'))
    cache = Cache(source)
    try:
        scenario = next(t['offset'] for t in cache.tags.values() if t['group'] == 'scnr')
        assert cache.u(scenario+8) == 1733
        assert cache.data[0x18c:0x1ac].split(b'\0')[0] == b'battle_canyon'
    finally:
        cache.close()
    state = dict(status='preflight_passed', source=proof, candidate=a.candidate,
                 visual_acceptance='pending user testing', waiting_for_pid=a.wait_pid)
    def save():
        report.write_text(json.dumps(state, indent=2))
    save()
    try:
        if a.wait_pid:
            kernel = C.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
            kernel.OpenProcess.restype = W.HANDLE
            kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
            kernel.WaitForSingleObject.restype = W.DWORD
            kernel.CloseHandle.argtypes = [W.HANDLE]
            handle = kernel.OpenProcess(0x100000, False, a.wait_pid)
            if handle:
                state['status'] = 'waiting_for_game_exit'
                save()
                try:
                    while True:
                        result = kernel.WaitForSingleObject(handle, 30000)
                        if result == 0:
                            break
                        if result != 258:
                            raise C.WinError(C.get_last_error())
                finally:
                    kernel.CloseHandle(handle)
            elif C.get_last_error() != 87:
                raise C.WinError(C.get_last_error())
        active = subprocess.check_output(['powershell', '-NoProfile', '-Command',
            "Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('OpenH3M.exe','halo3mp.exe') } | Select-Object -ExpandProperty ProcessId"],
            text=True, cwd=ROOT).strip()
        if active:
            raise RuntimeError('Another game is running; map not replaced: '+active)
        target = BUNDLE / 'battle_canyon.map'
        before = {f.name:sha(f) for f in BUNDLE.iterdir() if f.is_file()}
        assert before[target.name] == a.expected_current_sha256, 'Installed map changed since preparation'
        assert sha(source) == proof['sha256'], 'Candidate changed while waiting'
        backup = WORK / 'native' / ('installed-before-'+a.candidate+'.map')
        assert not backup.exists()
        shutil.copyfile(target, backup)
        assert sha(backup) == a.expected_current_sha256
        temporary = BUNDLE / ('battle_canyon.map.'+a.candidate+'.tmp')
        assert not temporary.exists()
        shutil.copyfile(source, temporary)
        assert sha(temporary) == proof['sha256']
        assert sha(target) == a.expected_current_sha256
        os.replace(temporary, target)
        after = {f.name:sha(f) for f in BUNDLE.iterdir() if f.is_file()}
        changed = [name for name in set(before)|set(after) if before.get(name) != after.get(name)]
        assert changed == ['battle_canyon.map'], changed
        state.update(status='installed_for_user_testing', installed_map=str(target),
                     installed_sha256=after[target.name], backup=str(backup),
                     previous_sha256=before[target.name], changed_bundle_files=changed,
                     other_bundle_files_unchanged=True, runtime_and_settings='not modified',
                     launched_game=False)
        save()
    except BaseException as error:
        state.update(status='failed', error=str(error))
        save()
        raise
    print(json.dumps(state, indent=2))


if __name__ == '__main__':
    main()
