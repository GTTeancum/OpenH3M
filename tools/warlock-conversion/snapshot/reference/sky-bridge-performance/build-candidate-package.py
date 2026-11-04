"""Build a private candidate LIVE container; never promote it to the release."""
from pathlib import Path
import sys,json,hashlib,argparse
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from build_dlc_live import build
from verify_dlc_stfs import verify,verify_payload
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate',type=int,choices=(29,32,34),default=29)
args=parser.parse_args()
root=Path.cwd();payload=root/f'work/sky-bridge/payload-{args.candidate}';out=root/f'work/sky-bridge/live-candidate-{args.candidate}'
assert not out.exists()
expected={29:'506cdc953bed8c2a80c751b8ddbc8422a61549e9143d73446276947707d06e36',
          32:'311ad88580c5e099546c029f07f93976c346a8bb9bf9b12c1d48f72f5e0c3e5d',
          34:'70e5c7aaed939be2c8c718535d8113deb334cd66ed428bd995c7b8573e93aa59'}[args.candidate]
assert hashlib.sha256((payload/'sky_bridge.map').read_bytes()).hexdigest()==expected
result=build(payload,out/'candidate')
container=Path(result['package'])
with container.open('r+b') as f:
 header=bytearray(f.read(0xb000));assert header[:4]==b'LIVE'
 def label(offset,size,text):
  encoded=text.encode('utf-16-be');assert len(encoded)+2<=size
  header[offset:offset+size]=encoded.ljust(size,b'\0')
 for locale in range(9):
  label(0x411+locale*256,256,f'Sky Bridge candidate {args.candidate}')
  label(0xd11+locale*256,256,'Private test candidate; visual verification pending.')
 label(0x1611,128,'GeneralHeed / Priception; OpenH3M adaptation')
 header[0x32c:0x340]=hashlib.sha1(header[0x344:]).digest();f.seek(0);f.write(header)
final=container.with_name(header[0x32c:0x340].hex().upper());container.rename(final)
with final.open('rb') as f:integrity=verify(f)
files=verify_payload(final,payload)
assert len(files)==7 and next(x['sha256'] for x in files if x['name']=='sky_bridge.map')==expected
report=dict(status='Private test candidate, not accepted or released',package=str(final),
 sha256=hashlib.sha256(final.read_bytes()).hexdigest(),integrity=integrity,payload_files=files,
 credit='Sky Bridge from Halo Online; upstream Halo 3 conversion GeneralHeed / Priception, Halo Online Map Pack For Halo 3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190 . Original individual creator unspecified. This project supplies Xbox 360/OpenH3M adaptation.',
 limitations=['Human panel/exposure verification pending.','Physical Xbox 360 and system-link acceptance not tested.','Host performance correction requires the patched runtime and asynchronous occlusion setting.'])
(out/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(package=str(final),files=len(files),sha256=report['sha256']),indent=2))
