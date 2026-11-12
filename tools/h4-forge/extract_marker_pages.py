"""Read only the marker texture pages from the repository's private H4 ISO."""
import hashlib
import json
import struct
import subprocess
import zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
research=ROOT/'work/h4-forge-research'
inventory=json.loads((research/'disc-inventory.json').read_text())
iso=(research/inventory['iso']).resolve(strict=True)
iso.relative_to(research)
entry=next(e for e in inventory['entries'] if e['path']=='maps/shared.map')
resources=json.loads((research/'isolated/marker-resource-pages.json').read_text())
pages={part['page']:part for resource in resources for part in resource['parts']}
out=research/'isolated/marker-pages';out.mkdir(exist_ok=True)
report=[]
with iso.open('rb') as stream:
    stream.seek(entry['offset']);header=stream.read(0x500)
    if header[:4]!=b'head':raise ValueError('Unexpected original shared cache header')
    # Retail Gen4 uses section-relative pages and XMem/LZX (TagTool
    # ResourceCacheGen4.ReadPageData), unlike the Gen3 Deflate path.
    base=(struct.unpack_from('>I',header,0x480)[0]+struct.unpack_from('>I',header,0x494)[0])&0xffffffff
    for index,page in pages.items():
        if page['shared']!='maps\\shared.map':raise ValueError('Unmapped resource source')
        at=base+page['block']
        if at<0 or at+page['compressed']>entry['bytes']:
            raise ValueError(('Page outside original shared cache',hex(base),{hex(n):hex(struct.unpack_from('>I',header,n)[0]) for n in range(0x460,0x4b0,4)}))
        stream.seek(entry['offset']+at);compressed=stream.read(page['compressed'])
        if len(compressed)!=page['compressed']:raise ValueError('Truncated original page')
        if page['codec']==0:
            compressed_path=out/f'{index}.xmem';decoded_path=out/f'{index}.unchecked'
            compressed_path.write_bytes(compressed)
            subprocess.run([str(ROOT/'work/rexglue-sdk/out/win-amd64/h4_forge_lzx_decode.exe'),
                str(compressed_path),str(decoded_path),str(page['uncompressed'])],cwd=ROOT,check=True)
            raw=decoded_path.read_bytes()
        elif page['codec']==255:raw=compressed
        else:raise ValueError('Unsupported original page codec')
        if len(raw)!=page['uncompressed']:raise ValueError('Decoded page size mismatch')
        if zlib.crc32(raw)^0xffffffff!=int(page['crc'],16):raise ValueError('Original page checksum mismatch')
        (out/f'{index}.bin').write_bytes(raw)
        report.append(dict(page=index,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),crc=page['crc']))
(out/'extraction.json').write_text(json.dumps(dict(source_iso=iso.name,source_cache=entry,verified_pages=report),indent=2)+'\n')
print(json.dumps(report,indent=2))
