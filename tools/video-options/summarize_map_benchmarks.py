"""Build the per-map FPS report from native results and explicit visual reviews."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / '.local/map-benchmarks'


def main():
    inventory = json.loads((OUTPUT/'inventory.json').read_text())
    attempts = {}
    for result in sorted(OUTPUT.glob('20*/*/result.json')):
        report = json.loads(result.read_text())
        run = result.parent
        manifest = run/'run.json'
        name = json.loads(manifest.read_text())['map']['name'] if manifest.exists() else report['map']
        review = run/'visual-review.json'
        reviewed = json.loads(review.read_text()) if review.exists() else {}
        samples = report.get('results', [])
        verified = (len(samples) == 3 and all(s['position_valid'] for s in samples)
                    and reviewed.get('map_and_locations_confirmed') is True
                    and reviewed.get('facing_verified') is True
                    and set(reviewed.get('reviewed_images', [])) == {'spawn-1.png', 'spawn-2.png', 'spawn-3.png'})
        record = dict(name=name, report=report, evidence=str(run), review=reviewed, verified=verified)
        # A failed retry must not erase an earlier complete, visually checked run.
        if verified or name not in attempts or not attempts[name]['verified']:
            attempts[name] = record
    machine = json.loads((OUTPUT/'machine.json').read_text(encoding='utf-8-sig'))
    lines = ['# Installed-map FPS benchmarks', '',
             'Developer unlock ON; no simulation timing compensation. Ten-second samples unless specified in evidence.',
             'Counts newly rendered guest outputs, excluding repeated display presentations.', '',
             f"Machine: {machine['cpu'][0]['Name'].strip()}; {machine['gpu'][0]['Name']}; "
             f"{machine['memory']/2**30:.1f} GiB RAM; {machine['os']}.",
             'Native capture resolution: 1152 × 640. Exact launch settings and executable SHA-256 are in each run.json.', '',
             '| Map/layout | Spawn 1 FPS | Spawn 2 FPS | Spawn 3 FPS | Status |',
             '|---|---:|---:|---:|---|']
    records = []
    for row in inventory:
        attempt = attempts.get(row['name'])
        values = ['—']*3
        status = 'Pending'
        if attempt:
            for sample in attempt['report'].get('results', []):
                values[sample['point']-1] = f"{sample['fps']:.2f}" if sample['position_valid'] else 'Invalid position'
            status = 'Verified locations' if attempt['verified'] else attempt['report']['status']
            records.append(attempt)
        lines.append(f"| {row['title']} | {' | '.join(values)} | {status} |")
    lines += ['', '## Evidence and view limitations', '',
              'These are fixed-view samples, not worst-case FPS or predictions for older hardware.', '']
    for attempt in records:
        lines.append(f"- [{attempt['name']}]({attempt['evidence'].replace(chr(92), '/')}/result.json): "
                     + ' '.join(attempt['review'].get('notes', ['Visual review pending.'])))
    (OUTPUT/'FPS-REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    (OUTPUT/'verified-results.json').write_text(json.dumps(records, indent=2))
    print(f"{sum(r['verified'] for r in records)}/{len(inventory)} maps/layouts visually reviewed with three valid samples")


if __name__ == '__main__':
    main()
