"""Partition triangle-list index ranges for original H3 ushort metadata.

This preserves vertex numbers and triangle order. Callers must remap mesh
references, visibility and lighting when installing the resulting meshes.
"""
from copy import deepcopy


def select_triangle_ranges(indices,parts,subparts,selected):
    """Build one spatial partition, retaining source identity for every draw."""
    selected=list(selected)
    if selected!=sorted(set(selected)) or any(i<0 or i*3+3>len(indices) for i in selected):
        raise ValueError('Invalid spatial triangle selection')
    if len(selected)>21845:raise ValueError('Spatial partition exceeds native end-index width')
    wanted=set(selected);output=[];new_parts=[];new_subs=[];mapping={};claimed=set()
    for pi,p in enumerate(parts):
        if p['first']%3 or p['count']%3:raise ValueError('Non-triangle part range')
        chosen=[i for i in selected if p['first']//3<=i<(p['first']+p['count'])//3]
        if not chosen:continue
        if claimed&set(chosen):raise ValueError('Overlapping source parts')
        claimed.update(chosen);first=len(output)
        for old in chosen:
            mapping[old]=len(output)//3
            output.extend(indices[old*3:old*3+3])
        new=deepcopy(p);new.update(first=first,count=len(chosen)*3,source_part=pi,
                                  subpart_start=len(new_subs))
        subclaimed=set()
        for si in range(p['subpart_start'],p['subpart_start']+p['subpart_count']):
            s=subparts[si]
            if s['part']!=pi or s['first']%3 or s['count']%3:raise ValueError('Invalid source subpart')
            kept=[i for i in chosen if s['first']//3<=i<(s['first']+s['count'])//3]
            if not kept:continue
            if subclaimed&set(kept):raise ValueError('Overlapping source subparts')
            subclaimed.update(kept)
            starts=[mapping[i] for i in kept]
            if starts!=list(range(starts[0],starts[0]+len(starts))):raise ValueError('Noncontiguous selected subpart')
            ns=deepcopy(s);ns.update(first=starts[0]*3,count=len(kept)*3,part=len(new_parts),source_subpart=si)
            new_subs.append(ns)
        if subclaimed!=set(chosen):raise ValueError('Selected triangles lack subparts')
        new['subpart_count']=len(new_subs)-new['subpart_start'];new_parts.append(new)
    if claimed!=wanted:raise ValueError('Selected triangles lack parts')
    return dict(indices=output,parts=new_parts,subparts=new_subs,old_to_new_triangle=mapping)


def relocate_triangle_ranges(indices,parts,subparts,movable_parts):
    """Keep mesh/part/subpart identities while moving one index span to the end.

    Native fields bound start and count independently, not their sum. Return an
    explicit triangle permutation for collision/other index-based consumers.
    A caller must approve which parts may move and apply that permutation.
    """
    if len(indices)%3 or any(not 0<=v<=65535 for v in indices):
        raise ValueError('Expected ushort triangle-list indices')
    ordered=sorted(range(len(parts)),key=lambda i:parts[i]['first'])
    cursor=0
    for i in ordered:
        p=parts[i]
        if p['first']!=cursor or p['count']<=0 or p['count']%3:
            raise ValueError('Part spans must partition the full triangle buffer')
        cursor+=p['count']
    if cursor!=len(indices):raise ValueError('Unowned mesh indices')
    for candidate in sorted(set(movable_parts),key=lambda i:parts[i]['count'],reverse=True):
        order=[i for i in ordered if i!=candidate]+[candidate]
        output=[];new_parts=deepcopy(parts);new_subs=deepcopy(subparts);permutation={}
        valid=True;owned=set()
        for i in order:
            p=parts[i];first=len(output);count=p['count']
            if first>65535 or count>65535:valid=False;break
            output.extend(indices[p['first']:p['first']+count])
            new_parts[i]['first']=first
            for j in range(count//3):permutation[p['first']//3+j]=first//3+j
            begin,n=p['subpart_start'],p['subpart_count']
            if begin<0 or begin+n>len(subparts):raise ValueError('Part subrange outside mesh')
            for si in range(begin,begin+n):
                s=subparts[si]
                if si in owned or s['part']!=i or s['first']<p['first'] or s['first']+s['count']>p['first']+count:
                    raise ValueError('Subpart ownership/range mismatch')
                owned.add(si)
                sf=first+s['first']-p['first']
                if sf>65535 or s['count']>65535:valid=False;break
                new_subs[si]['first']=sf
            if not valid:break
        if valid and owned==set(range(len(subparts))):
            return dict(indices=output,parts=new_parts,subparts=new_subs,
                        old_to_new_triangle=permutation,moved_part=candidate,
                        requires_triangle_reference_remap=True)
    raise ValueError('No approved relocation fits native part/subpart fields')


def split_triangle_ranges(indices, parts, subparts, limit=65535):
    if not 3<=limit<=65535:raise ValueError('Invalid native index limit')
    limit-=limit%3
    if len(indices)%3 or any(not 0<=v<=65535 for v in indices):
        raise ValueError('Expected ushort triangle-list indices')
    for part_index,part in enumerate(parts):
        first,count=part['first'],part['count']
        if first<0 or count<0 or first%3 or count%3 or first+count>len(indices):
            raise ValueError('Part is outside triangle-list indices')
        start,n=part['subpart_start'],part['subpart_count']
        if start<0 or n<0 or start+n>len(subparts):raise ValueError('Invalid subpart range')
        for sub in subparts[start:start+n]:
            if (sub['part']!=part_index or sub['first']<first or sub['count']<0
                    or sub['first']%3 or sub['count']%3 or sub['first']+sub['count']>first+count):
                raise ValueError('Subpart does not belong to its part')
    result=[]
    for base in range(0,len(indices),limit):
        end=min(base+limit,len(indices));new_parts=[];new_subparts=[]
        for part_index,part in enumerate(parts):
            lo=max(base,part['first']);hi=min(end,part['first']+part['count'])
            if hi<=lo:continue
            new=deepcopy(part);new.update(first=lo-base,count=hi-lo,source_part=part_index,
                                          subpart_start=len(new_subparts))
            for source_sub in range(part['subpart_start'],part['subpart_start']+part['subpart_count']):
                sub=subparts[source_sub];a=max(lo,sub['first']);b=min(hi,sub['first']+sub['count'])
                if b<=a:continue
                converted=deepcopy(sub)
                converted.update(first=a-base,count=b-a,part=len(new_parts),source_subpart=source_sub)
                new_subparts.append(converted)
            new['subpart_count']=len(new_subparts)-new['subpart_start']
            new_parts.append(new)
        result.append({'source_first':base,'indices':indices[base:end],
                       'parts':new_parts,'subparts':new_subparts})
    return result
