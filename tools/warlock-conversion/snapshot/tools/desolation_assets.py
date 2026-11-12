"""Audited asset decisions for MythicJaqui's April-2022 Desolation source."""
from pathlib import Path


def configure(importer, disc_maps):
    from source_schema import profile
    source = importer.source
    names = [source.name(n) for n,t in source.tags.items() if t['group']=='scnr']
    if names != [r'levels\multi\derelict\derelict'] or profile(source) != 'mcc-2022':
        raise ValueError('Desolation profile requires the verified April-2022 derelict scenario')
    if getattr(importer,'slot',None) != 'zanzibar':
        raise ValueError('Desolation profile requires the original Last Resort assembly basis')
    importer.desolation = True
    importer.stock_forge_palette = True
    # User clarification 2026-11-04: gameplay editing (spawns, objectives,
    # weapons, etc.), no Forge scenery; use Construct as the native template.
    importer.stock_forge_donor_maps = [Path(disc_maps)/'construct.map']
    importer.stock_forge_preferred_donor = 'construct'
    importer.stock_forge_excluded_categories = {'Scenery'}
    importer.audited_bitmap_recoveries = BITMAP_RECOVERIES
    importer.stock_asset_aliases = weapon_equivalents()
    for group,name,variant in importer.stock_asset_aliases.values():
        if (group,name) not in importer.native_assets.paths:
            raise ValueError('Required Desolation stock weapon donor is absent: '+name)
    # User 2026-11-04: remove the two corpse placements rather than import the
    # package's overhauled Brute/Grunt models or require campaign-only donors.
    importer.omitted_assets = {
        ('bipd',r'objects\characters\brute\brute'),
        ('bipd',r'objects\characters\grunt\grunt'),
    }
    return dict(forge_palette='Original Construct gameplay palette; no Forge scenery or overhaul entries',
                forge_template='construct.map',forge_excluded_categories=['Scenery'],
                source_scenario=names[0],source_schema=profile(source),
                preserved='Authored geometry, placement, atmosphere and native H3 budgets',
                audited_bitmap_recoveries=list(BITMAP_RECOVERIES),
                placed_weapons='User 2026-11-04: stock H3 counterparts throughout; preserve spawn positions',
                omitted_corpses=[name for group,name in sorted(importer.omitted_assets)],
                weapon_equivalents=[dict(source=key[1],stock=value[1])
                                    for key,value in importer.stock_asset_aliases.items()])


def weapon_equivalents():
    """Explicit source identities; no substring-based automatic replacement.

    User approved stock H3 counterparts by role for placed weapons, including
    DMR -> BR, needle rifle -> carbine and railgun -> Spartan laser. Entire
    native dependency graphs/behavior are reused; source tuning is not copied.
    """
    names = {
        r'pistol\magnum_h2a\magnum_h2a': r'pistol\magnum\magnum',
        r'pistol\magnum_reach\magnum_reach': r'pistol\magnum\magnum',
        r'pistol\sidekick\sidekick': r'pistol\magnum\magnum',
        r'pistol\mangler\mangler': r'pistol\excavator\excavator',
        r'rifle\shotgun_h2a\shotgun_h2a': r'rifle\shotgun\shotgun',
        r'rifle\battle_rifle_tac_h2a\battle_rifle_tac_h2a': r'rifle\battle_rifle\battle_rifle',
        r'rifle\dmr\dmr': r'rifle\battle_rifle\battle_rifle',
        r'rifle\needle_rifle\needle_rifle': r'rifle\covenant_carbine\covenant_carbine',
        r'rifle\ma5k\ma5k': r'rifle\assault_rifle\assault_rifle',
        r'rifle\plasma_repeater\plasma_repeater': r'rifle\plasma_rifle\plasma_rifle',
        r'rifle\brute_plasma_repeater\brute_plasma_repeater': r'rifle\plasma_rifle\plasma_rifle',
        r'support_low\concussion_rifle\concussion_rifle': r'support_low\brute_shot\brute_shot',
        r'support_high\rail_gun_h4\rail_gun_h4': r'support_high\spartan_laser\spartan_laser',
        r'support_high\machine_gun_h2a\machine_gun_h2a': r'turret\machinegun_turret\machinegun_turret',
        r'melee\fantasy_sword\fantasy_sword': r'melee\energy_blade\energy_blade',
    }
    result = {('weap','mythicjaqui\\weapons\\'+source):('weap','objects\\weapons\\'+target,None)
              for source,target in names.items()}
    result['weap',r'objects\weapons\support_low\sentinel_gun\sentinel_gun_major'] = (
        'weap',r'objects\weapons\support_low\sentinel_gun\sentinel_gun',None)
    return result

# work/desolation/decal-dependencies.json traces the native postprocess texture
# reference, rather than an unused editor parameter. The all-disc candidate
# search has no intact same-name resource; oil-bitmap-reuse.json also finds no
# identical base payload under another name. This recovers missing storage only.
BITMAP_RECOVERIES = {
    r'levels\shared\decals\stains\bitmaps\ustdamage_old_oil': dict(
        width=512, height=512, depth=1, kind=0, format=14, mips=10, curve=3,
        source_sha256='ba117a9163ff9fcff377bf1101d79069562b1ed45cde72ed6dec3b1414d45d7a'),
}
