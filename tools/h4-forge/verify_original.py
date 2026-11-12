"""Verify the integrated H4 function bodies still match ReXGlue output exactly."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];research=ROOT/'work/h4-forge-research'
report=json.loads((research/'isolated/extraction.json').read_text());bodies={}
for filename in {entry['source'] for entry in report['functions'].values()}:
 text=(research/'generated'/filename).read_text()
 matches=list(re.finditer(r'^DEFINE_REX_FUNC\((\w+)\) \{',text,re.M))
 for i,m in enumerate(matches):
  end=matches[i+1].start() if i+1<len(matches) else len(text)
  bodies[m[1]]=text[m.start():end].strip()
source=['#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx, uint8_t* base)',
 '#include "forge_original.h"','namespace h4_forge_original {']
for name,entry in sorted(report['functions'].items()):
 body=bodies[name]
 if hashlib.sha256(body.encode()).hexdigest()!=entry['sha256']:raise ValueError('ReXGlue body hash changed: '+name)
 source.append(body)
source.append('}')
if '\n\n'.join(source)+'\n'!=(research/'isolated/forge_original.cpp').read_text():raise ValueError('Integrated original bodies differ')
print('PASS:',len(report['functions']),'original H4 function bodies match ReXGlue output exactly')
