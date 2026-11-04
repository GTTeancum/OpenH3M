"""Compare numeric observer inputs and outputs, resolving each snapshot's TLS."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def read_observer(snapshot):
    tls = bytes.fromhex(snapshot['blobs']['tls']['bytes'])
    address = struct.unpack_from('>I', tls, 0x2cc)[0]
    record = snapshot['blobs']['observer']
    delta = address - int(record['guest_address'], 16)
    data = bytes.fromhex(record['bytes'])
    if delta < 0 or delta + 448 > len(data):
        raise ValueError('Observer extends outside captured allocation')
    data = data[delta:]
    def floats(offset, count):
        return list(struct.unpack_from('>'+str(count)+'f', data, offset))
    result = {'captured_blob_offset': delta,
        'result_position': floats(0x110, 3),
        'result_location_bytes': data[0x11c:0x120].hex(),
        'result_motion_vector_0': floats(0x120, 3),
        'result_motion_vector_1': floats(0x12c, 3),
        'result_forward': floats(0x138, 3),
        'result_up': floats(0x144, 3),
        'result_horizontal_fov': floats(0x150, 1)[0],
        'result_aspect_ratio': floats(0x168, 1)[0],
        'command_focus': floats(0x180, 3),
        'command_local_offset': floats(0x18c, 3),
        'command_window_shift': floats(0x198, 2),
        'command_distance': floats(0x1a0, 1)[0],
        'command_horizontal_fov': floats(0x1a4, 1)[0],
        'command_forward': floats(0x1a8, 3),
        'command_up': floats(0x1b4, 3),
        'motion_input_user_496': floats(4+496, 3),
        'motion_input_user_536': floats(4+536, 3),
        'result_sha256': hashlib.sha256(data[0x110:0x180]).hexdigest(),
        'command_sha256': hashlib.sha256(data[0x180:0x1c0]).hexdigest()}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    ref = Path(__file__).resolve().parent
    repo = ref.parents[4]
    args.run.resolve().relative_to(repo/'work/sky-bridge')
    human_path = repo/'work/sky-bridge/pixel-probe-20261103-203123/reproduction-view-full/guest-snapshot.json'
    human = read_observer(json.loads(human_path.read_text()))
    replay = read_observer(json.loads((args.run/'guest-snapshot.json').read_text()))
    report = {'human': human, 'replay': replay,
        'same_result': human['result_sha256'] == replay['result_sha256'],
        'same_command': human['command_sha256'] == replay['command_sha256'],
        'position_max_abs_delta': max(abs(a-b) for a,b in zip(human['result_position'], replay['result_position'])),
        'limitation': 'One saved native snapshot per run; not proof that the symptom occurred or every rendered frame matched.'}
    (args.run/'native-observer-comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k,v in report.items() if k not in ('human','replay')}))
