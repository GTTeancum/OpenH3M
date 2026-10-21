"""Compare serialized Forge normal mip chains with MCC via TagTool's decoder."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

import numpy as np
from cache_reader import Cache
from mcc_bitmap_source import BitmapSource
from resource_reader import Resource


def audit(source_path, candidate_path):
    repo = Path(__file__).resolve().parents[4]
    validator = repo/'work/forge-world/tools/mip-validator/Validate.dll'
    temp = repo/'work/forge-world/temp'
    temp.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), DOTNET_CLI_HOME=str(repo/'.local/dotnet'),
               NUGET_PACKAGES=str(repo/'.local/nuget'), DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',
               DOTNET_GENERATE_ASPNET_CERTIFICATE='false', DOTNET_CLI_TELEMETRY_OPTOUT='1')
    project = Path(__file__).parent/'validate_bitmap_mips/Validate.csproj'
    if not validator.exists() or any(p.stat().st_mtime > validator.stat().st_mtime for p in project.parent.iterdir() if p.is_file()):
        with (temp/'mip-validator-build.log').open('w') as log:
            subprocess.run(['C:/Program Files/dotnet/dotnet.exe', 'build', str(project), '-o', str(validator.parent),
                '-p:BaseIntermediateOutputPath='+str(repo/'.local/build-temp/mip-validator')+os.sep, '--nologo'],
                cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
    dependency = validator.parent/'TagTool.dll'
    if hashlib.sha256(dependency.read_bytes()).hexdigest() != '0080eb49cc22dae4d0854c33db42863539b784776aea2124543fc90c96f68623':
        raise ValueError('Independent decoder dependency differs from pinned TagTool')
    source, candidate = Cache(source_path, True), Cache(candidate_path)
    payload_path = temp/'mip-audit.bin'
    try:
        expected = {}
        bitmaps = BitmapSource(source)
        for index, tag in source.tags.items():
            if tag['group'] != 'bitm':
                continue
            infos = bitmaps.info(index)
            if len(infos) != 1 or infos[0]['format'] != 33:
                continue
            info = infos[0]
            data, offset, hashes = bitmaps.pixels(index), 0, []
            w, h = info['width'], info['height']
            for level in range(info['mips']):
                length = ((w+3)//4)*((h+3)//4)*16
                if max(w, h) <= 512:
                    block = np.frombuffer(data[offset:offset+length], dtype=np.uint8).reshape(-1, 16).astype(np.uint16)
                    for column in (0, 1, 8, 9):
                        block[:, column] = (block[:, column]+128) % 256
                    hashes.append(hashlib.sha256(block.astype(np.uint8).tobytes()).hexdigest())
                offset += length
                w, h = max(1, w//2), max(1, h//2)
            if hashes:
                expected[hashes[0]] = (source.name(index), hashes)
        results, pages = [], {}
        for index, tag in candidate.tags.items():
            if tag['group'] != 'bitm' or candidate.name(index) is not None:
                continue
            for row, entry in zip(candidate.block(tag['offset']+96, 48), candidate.block(tag['offset']+140, 8)):
                if candidate.unpack('H', row+12)[0] != 33:
                    continue
                resource = Resource(candidate, candidate.u(entry), decoded_pages=pages)
                w, h = resource.unpack('HH', 40)
                count = resource.data[45]
                if count <= 1 or count != candidate.data[row+20]+1 or resource.data[47] != 0:
                    raise ValueError(f'Custom normal {index} does not retain a unified mip chain')
                gpu = resource.unpack('I', 48)[0]
                if gpu != 0x1a215571:
                    raise ValueError('Non-native normal fetch format')
                size = resource.unpack('I', 0)[0]
                payload_path.write_bytes(resource.raw[0][:size])
                run = subprocess.run(['C:/Program Files/dotnet/dotnet.exe', str(validator), str(payload_path),
                    str(w), str(h), str(count), f'{gpu:x}'], cwd=repo, env=env, capture_output=True,
                    text=True, check=True, timeout=30)
                hashes = json.loads(run.stdout)
                name, reference = expected[hashes[0]]
                if hashes != reference:
                    raise ValueError(f'Mip bytes differ from authored source: {name}')
                results.append({'source': name, 'candidate_tag': index, 'mips': count,
                                'resident_bytes': size, 'sha256_per_mip': hashes})
        if not results:
            raise ValueError('No custom normal mip chains found')
        return results
    finally:
        source.close()
        candidate.close()
        payload_path.unlink(missing_ok=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True)
    p.add_argument('--candidate', required=True)
    p.add_argument('--report', required=True, type=Path)
    args = p.parse_args()
    result = audit(args.source, args.candidate)
    args.report.write_text(json.dumps(result, indent=2))
    print(f'Independent decoder verified {len(result)} normal textures / {sum(r["mips"] for r in result)} mips')
