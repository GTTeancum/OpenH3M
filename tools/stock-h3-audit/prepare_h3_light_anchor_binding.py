"""Reuse the original Standoff invisible shader for nonvisible light anchors."""
import hashlib,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
source=r'fx\fx_anchor\shaders\invisible.shader';target=r'fx\null_object\shaders\invisible.shader'
stock=next(r for r in json.loads((OUT/'stock-shader-configurations.json').read_text(encoding='utf-8')) if r['path']==target)
assert sha(KIT/'tags'/target)==stock['sha256']
assert any(line.endswith('] '+target) for line in (OUT/'standoff-all-tags.txt').read_text(encoding='utf-8-sig').splitlines())
cache=Path('C:/X360/ISOs/H3M/maps/bunkerworld.map');before=sha(cache)
commands=OUT/'light-anchor-stock.commands';commands.write_text('EditTag '+target+'\nForEach Options ListFields OptionIndex\n',encoding='utf-8')
env=os.environ.copy();env['DOTNET_ROLL_FORWARD']='Major'
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
with (OUT/'light-anchor-stock.log').open('wb') as log:
    result=subprocess.run([str(OUT/'bin/TagTool.exe'),str(cache),'RunCommands',str(commands)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert result.returncode==0 and sha(cache)==before
options=[int(v) for v in re.findall(rb'OptionIndex: Int16 = (\d+)',(OUT/'light-anchor-stock.log').read_bytes())]
assert len(options)==10 and options==stock['options'][:10] and not any(stock['options'][10:])
report=dict(source=source,source_sha256=sha(ROOT/'work/editing-kits/hrek/tags'/source),target=target,target_sha256=stock['sha256'],
    original_cache=str(cache),original_cache_sha256=before,stock_options=options,
    scope='Only the two original nonvisible attachment-anchor models for placed lights; no visible artwork is replaced.')
(OUT/'h3-light-anchor-binding.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('STOCK_LIGHT_ANCHOR_BINDING_VERIFIED',target,flush=True)
