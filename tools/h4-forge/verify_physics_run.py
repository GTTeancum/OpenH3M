"""Check native mode transitions/restoration and unchanged H3 save properties."""
import argparse
import csv
import json
import math
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run", type=Path)
parser.add_argument("--reference", type=Path, required=True,
                    help="Reference run directory or captured native variant file")
parser.add_argument("--modes", default="normal,phased,fixed")
parser.add_argument("--expect-motion", action="store_true")
parser.add_argument("--original-controller", action="store_true",
                    help="Check the integrated H4 controller: connected dynamic/keyframed bodies, not the legacy Phased-disconnect workaround")
parser.add_argument("--native-menu", action="store_true", help="Require choices from the native property handler")
parser.add_argument("--native-position", action="store_true", help="Require a native position-menu edit retained in the saved pose")
parser.add_argument("--native-yaw", action="store_true", help="Require a native yaw-menu edit retained in the saved basis")
parser.add_argument("--native-resume", action="store_true", help="Require native precise-position lock followed by Free movement and a changed saved pose")
parser.add_argument("--native-lifecycle", action="store_true", help="Require three native properties opens and one retained position commit after canceling a preview")
parser.add_argument("--automatic", action="store_true", help="Reject launch-time enable/data-path overrides")
parser.add_argument("--adjacent-inputs", action="store_true", help="Require successful loading from the build's adjacent private-input directory")
args = parser.parse_args()


def confined(path):
    path = path.resolve(strict=True)
    path.relative_to(ROOT)
    return path


run, reference = confined(args.run), confined(args.reference)
log = (run / "trace-runtime.log").read_text(errors="replace")
selection = "native Physics" if args.native_menu else "physics"
events = [dict(datum=int(datum, 16), mode=int(mode, 16), flags=int(flags, 16))
          for datum, mode, flags in re.findall(
              rf"Advanced Forge {selection} selected: ([0-9A-F]+) mode ([0-9A-F]+) flags ([0-9A-F]+) held true", log)]
mode_values = {"normal": 0, "phased": 0xc0, "fixed": 0x40}
expected_modes = [mode_values[name] for name in args.modes.split(",")]
if [event["mode"] for event in events] != expected_modes:
    raise ValueError(f"Expected {args.modes} native sequence, got {events}")
if len({event["datum"] for event in events}) != 1:
    raise ValueError("Sequence changed object")
for event in events:
    flags, mode = event["flags"], event["mode"]
    if args.original_controller:
        # Original held states 1/2 both force native dynamic ownership and
        # remain connected. State2 selects keyframed motion6 separately;
        # H4's keyframed request is not an H3 saved/frozen flag.
        if flags & 0x1000c0 != 0x100080:
            raise ValueError(f"Unexpected original-controller held flags: {event}")
        continue
    if not flags & (1 << 20) or bool(flags & 0x40) != (mode != 0):
        raise ValueError(f"Unexpected motion flags: {event}")
    if bool(flags & 0x80) != (mode != 0xc0):
        raise ValueError(f"Unexpected physics connection state: {event}")
restored = [dict(datum=int(datum, 16), flags=int(flags, 16), original=int(original, 16))
            for datum, flags, original in re.findall(
                r"Advanced Forge physics restored: ([0-9A-F]+) flags ([0-9A-F]+) original ([0-9A-F]+)", log)]
restored = [event for event in restored if event["datum"] == events[0]["datum"]]
if len(restored) != 1 or (restored[0]["flags"] ^ restored[0]["original"]) & 0x1000c0:
    raise ValueError(f"Original motion/connection state not restored: {restored}")
if args.original_controller:
    bodies = [(int(datum, 16), int(motion)) for datum, motion in re.findall(
        r"Forge rebuilt body: datum ([0-9A-F]+) index \d+ selected \d+ address [0-9A-F]+ motion (\d+)", log)]
    if 0xc0 in expected_modes and (events[0]["datum"], 6) not in bodies:
        raise ValueError("Phased selection never constructed a native keyframed body")
    if 0 in expected_modes and (events[0]["datum"], 4) not in bodies:
        raise ValueError("Normal selection never constructed a native dynamic body")
if re.search(r"Original scenery[^\n]*failed:", log) or any(error in log for error in ("Advanced Forge disabled:", "Advanced Forge native Physics failed:", "Advanced Forge native menu unavailable:")):
    raise ValueError("Runtime reported an Advanced Forge error")
automatic = None
if args.automatic or args.adjacent_inputs:
    command = json.loads((run / "launch-command.json").read_text())
    if any(value.startswith(("--halo3mp_advanced_forge=", "--halo3mp_advanced_forge_data=")) for value in command):
        raise ValueError("Automatic test supplied an enable/data-path override")
    automatic = dict(no_enable_or_path_override=True)
    if args.adjacent_inputs:
        loaded = re.findall(r"Advanced Forge inputs ready: (.+) \((\d+) bindings\)", log)
        expected_path = (Path(command[0]).parent / "advanced-forge").resolve(strict=True)
        if len(loaded) != 1 or Path(loaded[0][0]).resolve(strict=True) != expected_path or int(loaded[0][1]) != 79:
            raise ValueError(f"Adjacent private inputs not loaded: {loaded}")
        automatic["adjacent_inputs"] = str(expected_path)


def properties(path):
    data = path.read_bytes()
    if len(data) != 0xe090 or struct.unpack_from(">H", data, 0xf8)[0] != 12:
        raise ValueError("Not the ordinary H3 version-12 native layout")
    result = []
    for slot in range(640):
        offset = 0x130 + slot * 0x54
        if not struct.unpack_from(">H", data, offset)[0] & 1:
            continue
        # Quota identity and every serialized object property. Runtime handles,
        # transient slot flags and poses are allowed to differ between runs.
        quota = struct.unpack_from('>i', data, offset+12)[0]
        if quota < -1 or quota >= 256:
            raise ValueError("Invalid native object quota")
        tag = data[0xd34c+quota*12:0xd350+quota*12].hex() if quota >= 0 else None
        result.append((slot, data[offset+12:offset+16].hex(), tag,
                       data[offset+0x3c:offset+0x54].hex()))
    return result


actual = properties(run / "native-variant.bin")
expected = properties(reference / "native-variant.bin" if reference.is_dir() else reference)
if not actual or actual != expected:
    raise ValueError("Object properties differ from the native H3 reference run")
motion = None
coordinate = None
rotation = None
resume = None
if args.native_resume:
    commands = re.findall(
        r"Advanced Forge native coordinates selected: ([0-9A-F]+) row (\d+) choice (\d+) position ([^ ]+) angles ([^ ]+) locked (true|false)", log)
    if len(commands) != 2 or any(int(command[0], 16) != events[0]["datum"] for command in commands):
        raise ValueError(f"Expected a position lock followed by native Free selection: {commands}")
    locked, free = commands
    if locked[1] != '1' or locked[5] != 'true' or free[1:3] != ('7', '0') or free[5] != 'false':
        raise ValueError(f"Native lock/resume sequence did not complete: {commands}")
    position = tuple(map(float, locked[3].split(',')))
    released_position = tuple(map(float, free[3].split(',')))
    if max(abs(a-b) for a,b in zip(position, released_position)) > .0001:
        raise ValueError("Selecting Free unexpectedly changed the pose immediately")
    saved = (run / "native-variant.bin").read_bytes()
    matches = [offset for slot in range(640) for offset in [0x130+slot*0x54]
               if struct.unpack_from('>H', saved, offset)[0] & 1
               and struct.unpack_from('>I', saved, offset+4)[0] == events[0]['datum']]
    if len(matches) != 1:
        raise ValueError("Resumed object missing from native saved snapshot")
    final_position = struct.unpack_from('>3f', saved, matches[0]+16)
    if math.dist(position, final_position) < .02:
        raise ValueError("Object remained at the precise position after resumed dragging")
    rows = list(csv.reader((run / "forge-scene.bin.native.csv").read_text().splitlines()))
    positions = [tuple(map(float, row[3:6])) for row in rows if int(row[1]) == events[0]['datum']]
    if not any(math.dist(p, position) < .0001 for p in positions) or math.dist(positions[-1], final_position) > .0001:
        raise ValueError("Native pose history does not show the precise edit and resumed final pose")
    resume = dict(locked_position=position, free_selection_preserved_pose=True, final_position=final_position,
                  resumed_distance=math.dist(position, final_position))
if args.native_position or args.native_lifecycle:
    commands = re.findall(
        r"Advanced Forge native coordinates selected: ([0-9A-F]+) row ([1-3]) choice (\d+) position ([^ ]+) angles ([^ ]+) locked true", log)
    if len(commands) != 1 or int(commands[0][0], 16) != events[0]["datum"]:
        raise ValueError(f"Expected one native position edit on the selected object: {commands}")
    datum, row, choice, position, angles = commands[0]
    position = tuple(map(float, position.split(',')))
    angles = tuple(map(float, angles.split(',')))
    requested = -1000 + int(choice) * .1
    if len(position) != 3 or abs(position[int(row)-1] - requested) > .0001:
        raise ValueError("Position does not match the original H4 menu increment")
    saved = (run / "native-variant.bin").read_bytes()
    matches = [offset for slot in range(640) for offset in [0x130+slot*0x54]
               if struct.unpack_from('>H', saved, offset)[0] & 1
               and struct.unpack_from('>I', saved, offset+4)[0] == int(datum, 16)]
    if len(matches) != 1:
        raise ValueError("Edited object missing from saved snapshot")
    offset = matches[0]
    saved_position = struct.unpack_from('>3f', saved, offset+16)
    if max(abs(a-b) for a,b in zip(position, saved_position)) > .00005:
        raise ValueError(f"Native coordinate edit not retained: {position} -> {saved_position}")
    # This fixture changes position only and starts with identity orientation.
    axes = struct.unpack_from('>6f', saved, offset+28)
    if max(map(abs, angles)) > .001 or max(abs(a-b) for a,b in zip(axes, (1,0,0,0,0,1))) > .0001:
        raise ValueError("Position-only menu edit changed orientation")
    coordinate = dict(row=int(row), choice=int(choice), requested_value=requested,
                      position=saved_position, unchanged_orientation=True)
    if args.native_lifecycle:
        opens = re.findall(r"Advanced Forge native editor rows: screen ([0-9A-F]+) object ([0-9A-F]+) first row (\d+)", log)
        if len(opens) != 3 or any(int(item[1], 16) != events[0]['datum'] for item in opens):
            raise ValueError(f"Expected three opens of the same held object's properties: {opens}")
        coordinate['native_menu_opens'] = len(opens)
        coordinate['single_commit_retained_after_cancel'] = True
if args.native_yaw:
    commands = re.findall(
        r"Advanced Forge native coordinates selected: ([0-9A-F]+) row 4 choice (\d+) position ([^ ]+) angles ([^ ]+) locked true", log)
    if len(commands) != 1 or int(commands[0][0], 16) != events[0]["datum"]:
        raise ValueError(f"Expected one native yaw edit: {commands}")
    datum, choice, position, angles = commands[0]
    position, angles = tuple(map(float, position.split(','))), tuple(map(float, angles.split(',')))
    requested = int(choice)-180
    if not requested or abs(angles[0]-requested) > .001 or max(map(abs, angles[1:])) > .001:
        raise ValueError("Native yaw selection differs from its original one-degree step")
    saved = (run / "native-variant.bin").read_bytes()
    matches = [offset for slot in range(640) for offset in [0x130+slot*0x54]
               if struct.unpack_from('>H', saved, offset)[0] & 1
               and struct.unpack_from('>I', saved, offset+4)[0] == int(datum, 16)]
    if len(matches) != 1:
        raise ValueError("Rotated object missing from saved snapshot")
    saved_position = struct.unpack_from('>3f', saved, matches[0]+16)
    if max(abs(a-b) for a,b in zip(position, saved_position)) > .00005:
        raise ValueError("Yaw edit changed its requested saved position")
    axes = struct.unpack_from('>6f', saved, matches[0]+28)
    radians = math.radians(requested)
    expected_axes = (math.cos(radians), math.sin(radians), 0, 0, 0, 1)
    if max(abs(a-b) for a,b in zip(axes, expected_axes)) > .0001:
        raise ValueError(f"Native saved basis does not retain yaw {requested}: {axes}")
    rotation = dict(choice=int(choice), yaw_degrees=requested, forward=axes[:3], up=axes[3:])
if args.expect_motion:
    if expected_modes != [0]:
        raise ValueError("Motion check requires a Normal-only run")
    releases = re.findall(r"Advanced Forge physics released: ([0-9A-F]+) mode 00 flags ([0-9A-F]+) held false", log)
    if len(releases) != 1 or int(releases[0][0], 16) != events[0]["datum"] or int(releases[0][1], 16) & 0x1000c0 != 0x100080:
        raise ValueError("Normal release did not retain dynamic, collidable physics")
    rows = list(csv.reader((run / "forge-scene.bin.native.csv").read_text().splitlines()))
    positions = [tuple(float(value) for value in row[3:6]) for row in rows
                 if int(row[1]) == events[0]["datum"]]
    if len(positions) < 2:
        raise ValueError("No native pose motion after placement")
    fall = positions[0][2] - min(position[2] for position in positions[1:])
    if fall < .02:
        raise ValueError(f"No measured fall after placement: {fall}")
    motion = dict(native_pose_records=len(positions), vertical_drop=fall)
report = dict(result="PASS", run=run.name, reference=str(reference.relative_to(ROOT)),
              native_menu=args.native_menu, original_controller=args.original_controller,
              transitions=events, restoration=restored, unchanged_property_records=len(actual),
              motion=motion, native_position=coordinate, native_yaw=rotation, native_resume=resume, automatic=automatic,
              limitation="Native state and save-property evidence; inspect captures separately. Not a console or broad collision test.")
(run / "physics-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
