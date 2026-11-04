"""Package the installed correction with its completed, limited visual review."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    assert Path.cwd().resolve() == REPO
    os.environ['TEMP'] = os.environ['TMP'] = str(REPO / '.local/build-temp')
    original = REPO / '.local/releases/sky-bridge-candidate36-20261104'
    release = REPO / '.local/releases/sky-bridge-corrected-20261104'
    native = read(REF / 'candidate36-native-live-result.json')
    visual = read(REF / 'candidate36-visual-review-result.json')
    installed = read(REF / 'candidate36-install-result.json')
    manifest = read(original / 'manifest.json')
    assert sha(REPO / native['archive']['path']) == native['archive']['sha256']
    assert sha(Path(installed['target'])) == installed['sha256'] == manifest['payload']['sky_bridge.map']['sha256']
    assert sha(Path(installed['backup'])) == installed['old_sha256']
    assert sha(REF / 'candidate36-visual-review-result.json') == installed['visual_report_sha256']
    assert len(visual['frames']) == 6 and all(f['inspected_individually'] for f in visual['frames'])
    assert all(sha(REPO / f['path']) == f['sha256'] for f in visual['frames'])
    source = original / manifest['package']['path']
    assert sha(source) == manifest['package']['sha256']
    assert not release.exists(), 'Retain earlier release artifacts; never overwrite them'
    destination = release / manifest['package']['path']
    destination.parent.mkdir(parents=True)
    shutil.copyfile(source, destination)
    assert sha(destination) == manifest['package']['sha256']
    manifest['status'] = 'Candidate36 correction installed; six saved-view native frames reviewed; overall goal remains open'
    manifest['verified'] += [
        'All six authorized native frames inspected individually: transparent rain, shaded fabric, changing billboard content.',
        'Saved native observer command/result match exactly; eleven native header checks pass.',
        'Only the existing shared Sky Bridge map changed; 85 other content files, two cache files, runtime and bootstrap preserved.']
    manifest['pending'] = visual['limitations']
    manifest['visual_findings'] = visual['findings']
    manifest['shared_installation'] = {
        'changed_files': installed['changed_files'],
        'unchanged_content_files': installed['unchanged_content_files'],
        'runtime_and_bootstrap_unchanged': installed['runtime_and_bootstrap_unchanged'],
        'external_writes': installed['external_writes']}
    manifest['timing'] = native['timing']
    manifest['evidence_sha256'] = {
        name: sha(REF / name) for name in (
            'candidate36-native-live-result.json', 'candidate36-visual-review-result.json',
            'candidate36-install-result.json')}
    (release / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (release / 'README.txt').write_text('''SKY BRIDGE - CANDIDATE36 CORRECTION, 2026-11-04

Native LIVE/STFS package:
Content/0000000000000000/4D5307E6/00000002/5DC3487BF1633DF162B829AF5609E7687F169DE8

Retains the human-confirmed rain/card fix, corrects measured fabric black
overwrites, and restores two billboard textures' native mip addressing.
The OpenH3M native installer extracted all seven files byte-for-byte and
loaded Sky Bridge with the exact saved observer. Eleven header checks passed.
All six authorized game-native frames were inspected individually. Rain is
transparent, upper fabric stays shaded, and the billboard content changes.
The measured stationary replay runs at 29.9698 FPS; this is not traversal FPS.

The six stills cannot independently exclude a one-frame flicker. Separate
300-frame traces report zero sampled fabric black overwrites. Close-up ad
legibility, the small protruding feature, full-map traversal/audio, physical
Xbox 360 and system-link testing remain unverified. See manifest.json for scope.
The overall goal remains open; this is not complete-map final acceptance.

The existing shared OpenH3M installation now contains this corrected map.
Only its sky_bridge.map changed; other content, saves, settings, cache and
runtime files were preserved. The previous map is retained for rollback.
No new runtime DLL or bootstrap settings are required.

For a console installation, replace the older Sky Bridge package rather than
keeping duplicate packages with map ID1747. Preserve other map packages.
Unsigned content targets OpenH3M and RGH/JTAG; no retail acceptance is claimed.

Source: Sky Bridge, Halo Online; General Heed / Priception,
Halo Online Map Pack For Halo 3:
https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190
Original individual creator unspecified. This project supplies the
Xbox 360/OpenH3M adaptation.
''')
    archive_path = release / 'Sky-Bridge-Corrected-LIVE-DLC.zip'
    names = [manifest['package']['path'], 'manifest.json', 'README.txt']
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in names:
            archive.write(release / name, name)
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == names and archive.testzip() is None
        for name in names:
            with archive.open(name) as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == sha(release / name)
    result = dict(status=manifest['status'], credit=manifest['credit'],
        archive=dict(path=str(archive_path.relative_to(REPO)), bytes=archive_path.stat().st_size,
                     sha256=sha(archive_path), all_entries_byte_exact=True),
        package=manifest['package'],
        package_unchanged_from_native_verified_candidate=True,
        original_candidate_archive_preserved=sha(REPO / native['archive']['path']) == native['archive']['sha256'],
        manifest_sha256=sha(release / 'manifest.json'), readme_sha256=sha(release / 'README.txt'),
        evidence_sha256=manifest['evidence_sha256'], remaining=manifest['pending'])
    assert result['original_candidate_archive_preserved']
    (REF / 'candidate36-release-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], archive=result['archive'])))


if __name__ == '__main__':
    main()
