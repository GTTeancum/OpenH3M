"""Match exact type-0 PM4 bytes and addresses to native register flush calls."""
import argparse
import collections
import json
from pathlib import Path
import struct


def analyze(run):
    native=json.loads((run/'native-blend-analysis.json').read_text())
    gpu=json.loads((run/'command-witness-analysis.json').read_text())
    native_raw=(run/'native-blend.bin').read_bytes()
    rows=list(struct.iter_unpack('<72I',native_raw[32:]))
    packets=collections.defaultdict(list)
    skipped=[]
    for call in native['flushes']:
        mask=int(call['mask'],16)
        words=[int(w,16) for w in call['source_words']]
        address=int(call['command_begin'],16)
        end=int(call['command_end'],16)
        selected=[i for i in range(64) if mask&(1<<(63-i))]
        if not selected or max(selected)>=len(words):
            skipped.append(call['sequence']);continue
        runs=[]
        for i in selected:
            if not runs or i!=runs[-1][-1]+1:runs.append([])
            runs[-1].append(i)
        expected=sum(1+len(r) for r in runs)*4
        if end-address!=expected:
            skipped.append(call['sequence']);continue
        for indices in runs:
            values=[((len(indices)-1)<<16)|(0x2200+indices[0])]+[words[i] for i in indices]
            # Observed command pointers use the Xbox direct physical mapping.
            # Address alone is insufficient: require the complete packet bytes.
            packets[address&0x1fffffff].append((values,call))
            address+=4*len(values)
    matches=[]
    for draw in gpu['fabric_dynamic_draws']:
        w=draw['blend_writes'][0]
        prefix=[int(v,16) for v in w['prefix_words']]
        selected=[(v,c) for v,c in packets[int(w['packet_physical_address'],16)]
                  if len(v)<=len(prefix) and v==prefix[:len(v)]]
        matches.append(dict(frame=draw['frame'],draw_sequence=draw['sequence'],
            write=w,matches=[dict(native_sequence=c['sequence'],native_frame=c['frame'],
                caller=c['caller'],source=c['source'],device_blend=c['device_blend'],
                command_begin=c['command_begin'],packet=[hex(n) for n in v]) for v,c in selected]))
        if len(selected)==1:
            seq=selected[0][1]['sequence']
            chain=rows[seq-5:seq+1]
            valid=(len(chain)==6 and [r[0] for r in chain]==[1,2,5,6,7,8]
                and all(r[5]==chain[0][5] and r[4]==chain[0][4] for r in chain)
                and chain[0][24]==9 and chain[0][23]==0xbdcb3e70
                and chain[0][36]==2 and chain[1][28]==0x1010101
                and chain[2][6]==0x8217fdf4 and chain[2][9]==0
                and chain[2][28]==0x1010101 and chain[3][28]==0x10001
                and chain[4][28]==0x10001 and chain[4][6]==0x82184f28)
            matches[-1]['consecutive_native_chain_verified']=valid
            if valid:
                matches[-1]['native_chain']=dict(material_pointer=hex(chain[0][22]),
                    post_pointer=hex(chain[0][23]),stage=9,post_flags=chain[0][36],
                    material_blend_after=hex(chain[1][28]),
                    disable_blend_caller=hex(chain[2][6]),
                    blend_after_disable=hex(chain[3][28]),
                    native_sequences=[r[1] for r in chain])
    result=dict(fabric_draws=len(matches),unique_matches=sum(len(m['matches'])==1 for m in matches),
        unmatched=sum(not m['matches'] for m in matches),ambiguous=sum(len(m['matches'])>1 for m in matches),
        native_flushes=len(native['flushes']),skipped_flushes=skipped,draws=matches,
        consecutive_native_chains=sum(m.get('consecutive_native_chain_verified',False) for m in matches),
        limitations=['CPU and GPU frame IDs are not equated.',
                     'Joins require equal packet address and bytes; reused-address ambiguities remain explicit.'])
    (run/'native-command-join.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args()
    args.run.resolve().relative_to(Path(__file__).resolve().parents[5]/'work/sky-bridge')
    analyze(args.run)
