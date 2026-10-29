"""Independently decode every converted lightmap layer and compare MCC bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from cache_reader import Cache
from mcc_bitmap_source import BitmapSource
from resource_reader import Resource


def inventory(path):
    cache = Cache(path)
    try:
        result = []
        for tag in cache.tags.values():
            if tag['group'] != 'sLdT':
                continue
            for bsp in cache.block(tag['offset'] + 4, 436):
                for label, offset in [('lightprobe', 224), ('dominant', 240)]:
                    datum = cache.u(bsp + offset + 12)
                    if datum == 0xffffffff:
                        continue
                    bitmap = cache.tags[datum & 65535]
                    for row in cache.block(bitmap['offset'] + 96, 48):
                        width, height = cache.unpack('HH', row + 4)
                        result.append({'role': label, 'width': width, 'height': height,
                                       'layers': cache.data[row+8], 'format': cache.unpack('H', row+12)[0],
                                       'mips': cache.data[row+20]+1, 'tiled_bytes': cache.u(row+28)})
        return {'map': str(path.resolve()), 'arrays': result}
    finally:
        cache.close()


def audit(source_path, candidate_path):
    repo = Path(__file__).resolve().parents[4]
    decoder = repo / 'work/forge-world/tools/mip-validator/Validate.dll'
    if hashlib.sha256((decoder.parent / 'TagTool.dll').read_bytes()).hexdigest() != '0080eb49cc22dae4d0854c33db42863539b784776aea2124543fc90c96f68623':
        raise ValueError('Independent decoder dependency differs from pinned TagTool')
    if decoder.stat().st_mtime < (Path(__file__).parent / 'validate_bitmap_mips/Program.cs').stat().st_mtime:
        raise ValueError('Rebuild validate_bitmap_mips before running this audit')
    temp = repo / 'work/forge-world/temp'
    temp.mkdir(parents=True, exist_ok=True)
    payload = temp / 'lightmap-audit.bin'
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp),
               DOTNET_CLI_HOME=str(repo / '.local/dotnet'),
               NUGET_PACKAGES=str(repo / '.local/nuget'),
               DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_CLI_TELEMETRY_OPTOUT='1')
    source, target = Cache(source_path, True), Cache(candidate_path)
    try:
        sr = next(t['offset'] for t in source.tags.values() if t['group'] == 'sLdT')
        tr = next(t['offset'] for t in target.tags.values() if t['group'] == 'sLdT')
        source_bsps = source.block(sr + 4, 16)
        target_bsps = target.block(tr + 4, 436)
        if len(source_bsps) != len(target_bsps):
            raise ValueError('Lightmap BSP count differs')
        bitmaps = BitmapSource(source)
        result = []
        for bsp_index, (source_row, target_row) in enumerate(zip(source_bsps, target_bsps)):
            source_row = source.tags[source.u(source_row + 12) & 65535]['offset']
            if source.unpack('h', source_row + 2)[0] != bsp_index or target.unpack('h', target_row + 2)[0] != bsp_index:
                raise ValueError('Lightmap BSP order differs')
            if source.unpack('54f', source_row + 8) != target.unpack('54f', target_row + 8):
                raise ValueError('Lightmap compression coefficients differ')
            for label, offset in [('lightprobe', 224), ('dominant', 240)]:
                src = source.u(source_row + offset + 12) & 65535
                dst = target.u(target_row + offset + 12) & 65535
                info = bitmaps.info(src)
                rows = target.block(target.tags[dst]['offset'] + 96, 48)
                refs = target.block(target.tags[dst]['offset'] + 140, 8)
                if len(info) != 1 or len(rows) != 1 or len(refs) != 1:
                    raise ValueError('Expected one array per bitmap')
                info = info[0]
                sr_bitmap = source.block(source.tags[src]['offset'] + 96, 56)[0]
                depth = source.data[sr_bitmap + 8]
                width, height = target.unpack('HH', rows[0] + 4)
                if (width, height, target.data[rows[0]+8], target.unpack('H', rows[0]+10)[0],
                        target.unpack('H', rows[0]+12)[0], target.data[rows[0]+20]+1) != (
                        info['width'], info['height'], depth, 3, 16, 1):
                    raise ValueError('Lightmap dimensions/format differ')
                original = bitmaps.pixels(src)
                slice_bytes = ((width+3)//4)*((height+3)//4)*16
                if len(original) != slice_bytes*depth:
                    raise ValueError('Source lightmap layer size mismatch')
                resource = Resource(target, target.u(refs[0]))
                size = resource.unpack('I', 0)[0]
                gpu_format = resource.unpack('I', 48)[0]
                if resource.unpack('HHBBBB', 40) != (width, height, depth, 1, 3, 0):
                    raise ValueError('Serialized resource differs from bitmap metadata')
                payload.write_bytes(resource.raw[0][:size])
                hashes = []
                for layer in range(depth):
                    expected = hashlib.sha256(original[layer*slice_bytes:(layer+1)*slice_bytes]).hexdigest()
                    run = subprocess.run(['dotnet', str(decoder), str(payload), str(width), str(height),
                        '1', f'{gpu_format:x}', str(depth), '3', str(layer)], cwd=repo, env=env,
                        capture_output=True, text=True, timeout=30, check=True)
                    decoded = json.loads(run.stdout)
                    if decoded != [expected]:
                        raise ValueError(f'BSP {bsp_index} {label} layer {layer}: decoder differs from source')
                    hashes.append(expected)
                result.append({'bsp': bsp_index, 'role': label, 'source': source.name(src),
                               'target': hex(dst), 'width': width, 'height': height, 'layers': depth,
                               'tiled_bytes': size, 'decoded_layer_sha256': hashes})
        return {'status': 'passed', 'arrays': result, 'total_layers': sum(x['layers'] for x in result),
                'scope': 'Exact compressed layer bytes and lighting coefficients; not visual fidelity or memory occupancy'}
    finally:
        source.close()
        target.close()
        payload.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--stock-dir', type=Path, help='Inventory original playable maps, excluding shared/mainmenu caches')
    args = parser.parse_args()
    report = args.report.resolve()
    report.relative_to(Path(__file__).resolve().parents[4])
    result = audit(args.source, args.candidate)
    if args.stock_dir:
        result['stock_inventory'] = [inventory(path) for path in sorted(args.stock_dir.glob('*.map'))
                                     if path.stem not in ('shared', 'mainmenu', 'campaign')]
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Verified', result['total_layers'], 'layers across', len(result['arrays']), 'arrays')
