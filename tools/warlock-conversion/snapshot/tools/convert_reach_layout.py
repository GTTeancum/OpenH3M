"""Translate an authored Reach layout to the shared native Halo 3 base.

Every source slot is either mapped or named in the exclusion report. No tag
or object limit is raised. No game assets are embedded in the saved layout.
"""
import argparse
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from cache_reader import Cache
from reach_forge_palette import ReachCache
from reach_forge_variant import read_variant
from forge_variant_pose import reach_axes
from h3_saved_layout import write

ENGINE = {'ctf':1,'ctf_flag_return':1,'ctf_res_zone':1,'ctf_res_zone_away':1,
          'slayer':2,'oddball':4,'oddball_ball':4,'koth_hill':8,'juggernaut':16,
          'terr_object':32,'assault':64,'as_goal':64,'as_bomb':64,'vip':128,
          'inf_spawn':256,'inf_haven':256}
UNSUPPORTED = {'stp_goal','stp_flag','hh_drop_point','headhunter','race_flag',
    'race_spawn','inv_slayer_drop','slayer_drop','inv_slayer','inv_slayer_res_zone',
    'race','rally_flag','bro_spawn_loc','speedpile_goal','flag_spawn_loc',
    'inv_slayer_respawn_zone','stockpile','inf_haven'}
WEAPONS = {'dmr':'battle_rifle','needle_rifle':'covenant_carbine',
    'plasma_repeater':'plasma_rifle','concussion_rifle':'brute_shot',
    'grenade_launcher':'brute_shot','plasma_launcher':'flak_cannon',
    'energy_sword':'energy_blade'}
VEHICLES = {'falcon':'hornet','revenant':'mauler','machinegun':'machinegun_turret'}
UTILITIES = {'ff_grav_lift':'gravlift_permanent','ff_man_cannon_forge':'man_cannon_forge',
    'ff_man_cannon_forge_light':'man_cannon_forge','ff_man_cannon_forge_heavy':'man_cannon_forge',
    'ff_teleporter_sender':'teleporter_sender','ff_teleporter_receiver':'teleporter_reciever',
    'ff_teleporter_2way':'teleporter_2way','ff_light_red':'sandbox_light_red',
    'ff_light_blue':'sandbox_light_blue','ff_light_flash_red':'sandbox_light_red'}
GOALS = {'as_goal':('assault_bomb_goal_area',),'as_bomb':('assault_bomb_spawn_point',),
    'oddball_ball':('oddball_ball_spawn_point',),'terr_object':('territory_static',),
    'ctf_flag_return':('ctf_flag_return_area','ctf_flag_spawn_point'),
    'koth_hill':('koth_hill_static',)}


def choose(tag,obj,palette):
    label,name = obj['label'],tag['name']
    leaf = name.split('\\')[-1]
    if label in UNSUPPORTED:
        return [],'Reach-only mode/label: '+label
    if name.startswith('objects\\multi\\boundaries\\'):
        return [],'Reach scripted safe/kill volume; shared base retains its native world/divider boundaries'
    if leaf=='mp_cinematic_camera':
        return [],'Reach cinematic camera marker has no saved-layout counterpart'
    if leaf in ('health_station','jet_pack','hologram'):
        return [],'Reach-only health/armor ability; no imported gameplay implementation'
    if leaf.startswith('mp_') and label in GOALS:
        names=GOALS[label]
    elif leaf=='initial_spawn_point':
        names=({'ctf':'ctf_initial_spawn_point','inf_spawn':'infection_initial_spawn_point',
                'oddball':'oddball_initial_spawn_point','vip':'vip_initial_spawn_point'}
               .get(label,'slayer_initial_spawn_point'),)
    elif leaf=='respawn_zone':
        names=({'ctf_res_zone':'ctf_flag_at_home_respawn_zone',
                'ctf_res_zone_away':'ctf_flag_away_respawn_zone',
                'assault':'assault_respawn_zone'}.get(label,'slayer_respawn_zone'),)
    elif leaf in UTILITIES:
        names=(UTILITIES[leaf],)
    elif tag['group']=='vehi':
        names=(VEHICLES.get(leaf,leaf),)
    elif tag['group']=='weap':
        names=(WEAPONS.get(leaf,leaf),)
    else:
        exact=[p for p in palette if p['name']==name]
        if len(exact)==1:return exact,None
        names=(leaf,)
    result=[]
    for selected in names:
        found=[p for p in palette if (p['name'] or '').split('\\')[-1]==selected]
        if len(found)!=1:
            raise ValueError(f'No unique native match for {name}, {label}: {selected}')
        result.append(found[0])
    return result,None


def thin_spawns(objects,quotas):
    """Retain authored spawn positions spread across each team/mode group.

    This is a conversion-time reduction, not a change to the native palette
    limits. Never remove scenery, objectives, weapons or vehicles this way.
    """
    removed=[]
    for index,q in enumerate(quotas):
        candidates=[o for o in objects if o['quota']==index]
        limit=min(255,q['maximum'])
        if len(candidates)<=limit:continue
        if any(o['object_type']!=12 for o in candidates):
            raise ValueError(f'Native quota exceeded: {q["name"]} {len(candidates)}/{limit}')
        groups={}
        for o in candidates:
            groups.setdefault((o['team'],o['engine_flags']),[]).append(o)
        if len(groups)>limit:raise ValueError('Cannot retain every spawn team/mode within stock quota')
        selected=[]
        def distance(a,b):return sum((x-y)**2 for x,y in zip(a['position'],b['position']))
        # Start near each group's center, then add its most isolated remaining
        # point. All selected positions are original valid source placements.
        for rows in groups.values():
            center={'position':[sum(o['position'][k] for o in rows)/len(rows) for k in range(3)]}
            selected.append(min(rows,key=lambda o:(distance(o,center),o['source_slot'])))
        while len(selected)<limit:
            remaining=[o for o in candidates if o not in selected]
            selected.append(max(remaining,key=lambda o:(min(distance(o,s) for s in selected
                if (s['team'],s['engine_flags'])==(o['team'],o['engine_flags'])),-o['source_slot'])))
        removed.extend(o for o in candidates if o not in selected)
        q['count']=len(selected)
    return [o for o in objects if o not in removed],removed


def convert(args):
    repo=Path(__file__).resolve().parents[4]
    for p in (args.output,args.report):
        if not p.resolve().is_relative_to(repo):raise ValueError('Output outside repository')
    source=ReachCache(args.reach)
    target=Cache(args.map)
    try:
        v=read_variant(args.layout.read_bytes())
        source_palette=source.palette()
        assets=json.loads(args.assets.read_text())
        if hashlib.sha256(args.map.read_bytes()).hexdigest()!=assets['sha256']:
            raise ValueError('Base map does not match palette manifest')
        with args.sandbox.open('rb') as file:
            file.seek(0x344);signature=file.read(256)
        if target.data[0x344:0x444]!=signature or not any(signature):
            raise ValueError('Base does not retain the original Sandbox RSA identity')
        root=next(t['offset'] for t in target.tags.values() if t['group']=='scnr')
        schema=ET.parse(Path(__file__).resolve().parents[1]/'reference/plugins/scnr.xml').getroot()
        starts=[-1]*14;scenario_count=0
        for kind,label in ((1,'Vehicles'),(2,'Weapons'),(3,'Equipment'),(6,'Scenery'),(10,'Crates')):
            field=next(f for f in schema if f.get('name')==label)
            count=target.u(root+int(field.get('offset'),0))
            if count:starts[kind]=scenario_count
            scenario_count+=count
        # The Cage's shipped +/-20000 bounds unnecessarily lose placement
        # precision when encoded; use the common authored world extent instead.
        bounds=[-203.6004638671875,277.6636047363281,-360.8264465332031,
                324.9248352050781,-25.010116577148438,117.79051208496094]
        objects,quotas,quota_index,excluded,coverage=[],[],{},[],[]
        for obj in v['objects']:
            tag=source_palette[obj['folder']][obj['item']]
            chosen,reason=choose(tag,obj,assets['palette'])
            if reason:
                excluded.append(dict(slot=obj['slot'],source=tag['name'],reason=reason));continue
            if obj['parent']!=-1:
                raise ValueError('Relative authored placement needs explicit conversion')
            if obj['label'] not in (None,'team_only','ffa_only') and obj['label'] not in ENGINE:
                raise ValueError('Unreviewed mode label '+obj['label'])
            forward,up=reach_axes(obj)
            dims=[0. if q==0 else 200. if q==2047 else (q-.5)*200/2046
                  for q in obj['boundary_quantized']]
            boundary=([0.,0.,0.,0.] if obj['shape']==0 else
                      [dims[0],0.,0.,0.] if obj['shape']==1 else
                      [dims[0],0.,dims[1],dims[2]] if obj['shape']==2 else dims)
            for entry in chosen:
                datum=entry['datum']
                if datum not in quota_index:
                    quota_index[datum]=len(quotas)
                    quotas.append(dict(datum=datum,name=entry['name'],count=0,
                        maximum=entry['maximum'] if entry['maximum']>0 else 255,price=entry['price']))
                quota=quota_index[datum];quotas[quota]['count']+=1
                rows=target.block(target.tags[datum&65535]['offset']+0xec,196)
                kind=target.data[next(iter(rows))+2] if rows else 0
                shared=(obj.get('spare_clips',0) if kind==1 else
                        obj.get('channel',0) if kind in (9,10,11) else obj['sequence']&255)
                native=dict(source_slot=obj['slot'],quota=quota,position=obj['position'],
                    forward=forward,up=up,engine_flags=ENGINE.get(obj['label'],0x3ff),
                    mp_flags=obj['placement']&15,team=obj['team'],shared_storage=shared,
                    spawn_time=obj['respawn'],object_type=kind,shape=obj['shape'],boundary=boundary)
                # The separate native flag spawn is a point, not another return cylinder.
                if entry['name'].endswith('ctf_flag_spawn_point'):
                    native.update(shape=0,boundary=[0.,0.,0.,0.])
                objects.append(native)
                coverage.append(dict(slot=obj['slot'],source=tag['name'],target=entry['name']))
        objects,trimmed=thin_spawns(objects,quotas)
        for o in trimmed:
            excluded.append(dict(slot=o['source_slot'],source=quotas[o['quota']]['name'],
                                 reason='Redundant spawn pruned to retain stock Halo 3 palette limit'))
        retained={o['source_slot'] for o in objects}
        coverage=[row for row in coverage if row['slot'] in retained]
        for q in quotas:
            if q['count']>min(255,q['maximum']):
                raise ValueError(f'Native quota exceeded: {q["name"]} {q["count"]}/{q["maximum"]}')
        spent=sum(q['count']*q['price'] for q in quotas)
        maximum=target.unpack('f',root+16)[0]
        if spent>maximum:raise ValueError(f'Native Forge budget exceeded: {spent}/{maximum}')
        layout=dict(name=args.name,description=f'Reach {args.name}, adapted for Halo 3 on {args.home}.',
            unique_id=int.from_bytes(hashlib.sha256(('OpenH3M:'+args.name).encode()).digest()[:8],'big'),
            date=1792713600,map_id=target.u(root+8),signature_hash=0x59a2a65c,
            scenario_count=scenario_count,type_starts=starts,bounds=bounds,
            maximum_budget=maximum,spent_budget=spent,objects=objects,quotas=quotas)
        data=write(layout)
        report=dict(name=args.name,home=args.home,map_sha256=assets['sha256'],
            source_sha256=hashlib.sha256(args.layout.read_bytes()).hexdigest(),
            bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
            layout=layout,coverage=coverage,excluded=excluded,
            notes=['Stock Halo 3 movement/force/vehicle behavior retained.',
                   'Native team-spawn rules replace Reach team_only/ffa_only labels.',
                   'Reach color overrides and physics-mode flags are not added to the H3 engine.',
                   'Saved-content packaging and native gameplay not yet verified.'])
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_bytes(data);args.report.write_text(json.dumps(report,indent=2))
        print(f'{args.name}: {len(objects)} placements, {len(excluded)} explicit exclusions, '
              f'{spent:g}/{maximum:g} Forge budget, {len(data):,} bytes')
    finally:
        source.close();target.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('layout','reach','map','assets','sandbox','output','report'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--name',required=True);p.add_argument('--home',required=True)
    convert(p.parse_args())
