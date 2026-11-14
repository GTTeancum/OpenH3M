"""Exact-map opt-in policy without silent omissions or global name heuristics."""
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest import mock
from mythic_audio import BUILD, SCENARIOS, replacements, configure, applied_replacements


def importer(scenario, build=BUILD, names=(), mcc=True):
    identities=[('scnr',scenario)]+[('snd!',name) for name in names]
    data=bytearray(0xC0);data[0xA0:0xA0+len(build)]=build.encode('ascii')
    source=SimpleNamespace(mcc=mcc,data=data,
        tags={n:{'group':g} for n,(g,name) in enumerate(identities)},
        name=lambda n:identities[n][1])
    return SimpleNamespace(source=source,added=[])


class MythicAudioTests(unittest.TestCase):
    def test_warlock_five_explicit_native_leaves(self):
        p=replacements('warlock')
        self.assertEqual(len(p),5)
        self.assertEqual(p[r'sound\visual_fx\cascading_stream_splash\cascading_stream_splash\loop']['target'],
            r'sound\levels\riverworld\sound_scenery\water_against_surface\water_against_surface\loop')
        for phase in ('in','loop','out'):
            self.assertEqual(p['sound\\weapons\\autoturret\\autoturret_fire_loop\\track1\\'+phase]['target'],
                'sound\\characters\\sentinel\\sentinel_gun\\sent_gun\\'+phase)
        self.assertTrue(all(row['target'] and row['difference'] for row in p.values()))

    def test_configuration_is_exact_scoped_and_does_not_import(self):
        name=next(iter(replacements('warlock')))
        i=importer(r'levels\multi\warlock\warlock',names=[name,'unknown\\sound'])
        configure(i)
        self.assertEqual(set(i.stock_asset_aliases),{('snd!',name)})
        self.assertEqual(i.added,[])
        self.assertEqual(applied_replacements(i),[])
        self.assertFalse(hasattr(i,'omitted_assets'))

    def test_unknown_scenarios_builds_and_retail_are_rejected(self):
        for i in (importer(r'elsewhere\warlock'),
                  importer(r'levels\multi\warlock\warlock','other build'),
                  importer(r'levels\multi\warlock\warlock',mcc=False)):
            with self.subTest(source=i.source),self.assertRaises(ValueError):configure(i)
            self.assertFalse(hasattr(i,'stock_asset_aliases'))

    def test_existing_non_audio_aliases_preserved_and_conflicts_rejected(self):
        name=next(iter(replacements('warlock')))
        i=importer(r'levels\multi\warlock\warlock',names=[name])
        keep={('vehi','custom') : ('vehi','stock',None)}
        i.stock_asset_aliases=keep.copy();configure(i)
        self.assertEqual(i.stock_asset_aliases[('vehi','custom')],keep[('vehi','custom')])
        j=importer(r'levels\multi\warlock\warlock',names=[name]);j.stock_asset_aliases={('snd!',name):('snd!','other',None)}
        with self.assertRaisesRegex(ValueError,'Conflicting'):configure(j)
        self.assertEqual(j.stock_asset_aliases,{('snd!',name):('snd!','other',None)})

    def test_fresh_policy_results_and_no_self_aliases(self):
        for map_name,build in SCENARIOS.values():
            rows=replacements(map_name)
            for source,item in rows.items():
                self.assertNotEqual(source,item['target'])
                self.assertTrue(item['difference'])
            rows.clear();self.assertTrue(replacements(map_name))
        self.assertEqual(replacements('unreviewed_map'),{})

    def test_unapplied_and_unrelated_aliases_are_not_reported(self):
        i=importer(r'levels\multi\warlock\warlock',names=replacements('warlock'))
        configure(i);i.added=[dict(source='unknown',source_group='snd!',stock_equivalent='native')]
        self.assertEqual(applied_replacements(i),[])

    def test_dune_requires_its_u13_identity(self):
        scenario=r'levels\multi\dune\dune'
        with self.assertRaisesRegex(ValueError,'cache build'):
            configure(importer(scenario))
        i=importer(scenario,'Jun 27 2023 08:39:36',names=replacements('dune'))
        configure(i)
        self.assertEqual(len(i.stock_asset_aliases),31)
        # Existing complete H3 weapon/vehicle roots, not their subordinate
        # unavailable H2 sounds, are the correct policy boundary.
        self.assertNotIn(('snd!',r'h2\sound\vehicles\wraith\wraith_open'),i.stock_asset_aliases)

    def test_separate_surround_roles_and_loop_phases_remain(self):
        p=replacements('sancr')
        front=p[r'sound\levels\010_jungle\jungle4\front_speakers\loop']['target']
        rear=p[r'sound\levels\010_jungle\jungle4\rear_speakers\loop']['target']
        self.assertNotEqual(front,rear)
        self.assertIn('front_speakers',front)
        self.assertIn('rear_speakers',rear)

    def test_applied_report_uses_basis_donor_when_already_resident(self):
        name=next(iter(replacements('warlock')))
        i=importer(r'levels\multi\warlock\warlock',names=[name]);configure(i)
        target=i.mythic_audio_policy[('snd!',name)]['target']
        i.added=[dict(source_group='snd!',source=name,stock_equivalent=target,datum='0x12340003')]
        cache=SimpleNamespace(file=SimpleNamespace(name='/native/basis.map'),
            tags={3:{'group':'snd!','offset':64}},name=lambda n:target,u=lambda n:0x91000004)
        i.registry=SimpleNamespace(cache=cache);i.sounds=SimpleNamespace(report=[])
        row=applied_replacements(i)[0]
        self.assertEqual((row['donor'],row['donor_tag_index'],row['donor_resource']),
                         ('basis.map',3,'0x91000004'))
        self.assertFalse(row['source_waveform_identical'])
        self.assertFalse(row['serialized_packet_identity_verified'])

    def test_imported_report_opens_actual_native_donor_and_closes(self):
        name=next(iter(replacements('warlock')))
        i=importer(r'levels\multi\warlock\warlock',names=[name]);configure(i)
        target=i.mythic_audio_policy[('snd!',name)]['target']
        i.added=[dict(source_group='snd!',source=name,stock_equivalent=target,datum='0x12340003')]
        cache=SimpleNamespace(file=SimpleNamespace(name='/native/bunkerworld.map'),
            tags={7:{'group':'snd!','offset':64}},name=lambda n:target,u=lambda n:0x92000004,close=mock.Mock())
        path=Path('/native/bunkerworld.map')
        i.sounds=SimpleNamespace(report=[dict(datum='0x12340003',encoding='native retail',donor=path.name)],
            native=SimpleNamespace(paths={target:(path,7)}))
        with mock.patch('mythic_audio.Cache',return_value=cache) as opened:
            row=applied_replacements(i)[0]
        opened.assert_called_once_with(path);cache.close.assert_called_once()
        self.assertEqual(row['donor'],'bunkerworld.map')
        self.assertEqual(row['donor_resource'],'0x92000004')
        i.sounds.report[0]['encoding']='PCM16 big endian'
        with self.assertRaisesRegex(ValueError,'native sound packets'):applied_replacements(i)


if __name__=='__main__':unittest.main()
