"""Verify teleporter event, loop and restored receiver binding against retail."""
import argparse
import json
from pathlib import Path
from cache_reader import Cache
from verify_native_resources import sound_data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--disc-maps', type=Path, required=True)
    args = p.parse_args()
    report = json.loads(args.report.read_text())
    c, donor = Cache(args.map), Cache(args.disc_maps / 'lockout.map')
    shared = {f'maps\\{name}': args.disc_maps / name for name in ('mainmenu.map', 'shared.map')}
    try:
        def find(cache, group, name):
            return next(i for i, tag in cache.tags.items() if tag['group'] == group and cache.name(i) == name)
        checked = 0
        for index, tag in donor.tags.items():
            name = donor.name(index) or ''
            if tag['group'] == 'snd!' and 'teleport' in name:
                target = find(c, 'snd!', name)
                if sound_data(c, target, shared) != sound_data(donor, index, shared):
                    raise ValueError('Teleporter audio differs from retail: ' + name)
                checked += 1
        if checked != 2:
            raise ValueError('Expected activation sound and ambient loop')
        def event(cache):
            root = next(t['offset'] for t in cache.tags.values() if t['group'] == 'mulg')
            return [bytes(cache.data[e:e + 260]) for r in cache.block(root + 12, 524)
                    for e in cache.block(r + 136, 260) if cache.unpack('h', e + 4)[0] == 22]
        if len(event(c)) != 1 or event(c) != event(donor):
            raise ValueError('Teleporter activation event differs from retail')
        original = find(donor, 'bloc', r'objects\multi\teleporter_reciever\teleporter_reciever')
        target = next(int(t['datum'], 16) & 65535 for t in report['tags']
                      if t['group'] == 'bloc' and t['source'] == r'levels\multi\warlock\fx\teleporter_reciever\teleporter_reciever')
        def loops(cache, index):
            root = cache.tags[index]['offset']
            return [bytes(cache.data[r:r + 32]) for r in cache.block(root + 188, 32)
                    if cache.data[r:r + 4] == b'lsnd']
        if len(loops(c, target)) != 1 or loops(c, target) != loops(donor, original):
            raise ValueError('Receiver hum is not the native attachment')
        print(json.dumps({'teleporter_audio_packets_verified': checked,
                          'native_activation_event_unchanged': True,
                          'receiver_hum_attachment_restored': True,
                          'audible_playback_verified': False}))
    finally:
        c.close()
        donor.close()


if __name__ == '__main__':
    main()
