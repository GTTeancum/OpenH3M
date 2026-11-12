"""Record original H3 held-update evidence; not a runtime parity test."""
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
FILES = {"820F2AE0":88, "820F2EC8":106, "8232EA98":11, "821F0688":94, "8227E5A0":98, "821F04C0":40, "82282378": 8, "82281A98": 109, "8227FA50": 25,
         "8227F768": 31, "8227F578": 70, "820F29C8": 107,
         "820B37D0": 67, "820D3E40": 42, "82219898": 66,
         "820B6EA0": 91, "8227E460":1, "822836D8":42, "8226E590":5, "8226E6C8":83, "820AE5C0":86, "820AEC70":7, "820AEA78":1, "820AD3E0":104, "82281268":43}
records = {}
bodies = {}
for address, number in FILES.items():
    path = ROOT / f"halo3mp/generated/default/halo3mp_recomp.{number}.cpp"
    body = path.read_text().split(f"DEFINE_REX_FUNC(sub_{address}) {{", 1)[1]
    body = body.split("DEFINE_REX_FUNC(", 1)[0]
    bodies[address] = body
    records[address] = {
        "source": str(path.relative_to(ROOT)),
        "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "calls": re.findall(r"\b(sub_\w+)\(ctx, base\)", body),
    }
assert "sub_82281A98" in records["82282378"]["calls"]
assert "sub_8227FA50" in records["82281A98"]["calls"]
assert "sub_8227F768" in records["82281A98"]["calls"]
for address in ("8227FA50", "8227F768"):
    assert "sub_820F29C8" in records[address]["calls"]
    assert "sub_822837C8" in records[address]["calls"]
image = (ROOT / "work/advanced-forge/guest-image.bin").read_bytes()
slot = 0x82040D68 + 104
assert struct.unpack_from(">I", image, slot - 0x82000000)[0] == 0x82282378
engine_table = 0x827E6980
engine_object = struct.unpack_from(">I", image, engine_table - 0x82000000 + 5 * 4)[0]
assert engine_object == 0x827A33B8
assert struct.unpack_from(">I", image, engine_object - 0x82000000)[0] == 0x82040D68
tick_calls = records["820B37D0"]["calls"]
assert tick_calls.index("sub_820B6EA0") < tick_calls.index("sub_820D3E40")
assert "sub_821EC0E0" in records["820B6EA0"]["calls"]
assert "sub_82219898" in records["820D3E40"]["calls"]
# Verify the register/data-flow sequence rather than any occurrence of offset104.
asm = [line.strip()[3:] for line in bodies["82219898"].splitlines()
       if line.strip().startswith("// ")]
dispatch = ["lwz r11,0(r3)", "mr r4,r26", "lwz r11,104(r11)",
            "mtctr r11", "bctrl"]
assert any(asm[i:i + len(dispatch)] == dispatch for i in range(len(asm)))
for instruction in ("li r11,100", "ori r10,r10,15692",
                    "lis r10,-32130", "addi r10,r10,27008",
                    "lwzx r3,r11,r10"):
    assert instruction in asm
assert records["822836D8"]["calls"] == ["sub_822835E0", "sub_8226E590", "sub_821DFC78"]
assert "sub_822836D8" in records["82281A98"]["calls"]
assert "// li r6,4" in bodies["822836D8"]
assert "sub_8226E6C8" in records["8226E590"]["calls"]
assert "// fmuls f31,f31,f29" in bodies["8226E590"]
assert records["8226E6C8"]["calls"].count("sub_820AE5C0") == 2
assert "sub_820AD3E0" in records["82281268"]["calls"]
assert "sub_820AEA78" in records["820AD3E0"]["calls"]
assert "sub_820AED80" in records["820AEC70"]["calls"]
assert struct.unpack_from(">I",image,0xD2C)[0] == 0x820AEC70
assert "// addi r11,r11,3368" in bodies["820AEA78"]
input_body=bodies["821F04C0"]
for instruction in ["li r9,96", "mulli r11,r11,880", "lfs f13,44(r31)", "addi r10,r30,776", "addi r9,r30,768", "stb r8,764(r30)", "stw r11,20(r31)", "stw r11,24(r31)"]:
    assert "// "+instruction in input_body
held=bodies["82281A98"]
for instruction in ["lbz r11,764(r21)", "lfs f13,768(r21)", "fmadds f0,f13,f0,f12", "addi r10,r24,14454"]:
    assert "// "+instruction in held
assert struct.unpack_from(">f",image,0x22e18)[0] > .099
assert abs(struct.unpack_from(">f",image,0x22574)[0]-.3)<1e-6
assert struct.unpack_from(">f",image,0x228ac)[0] == 10
# Both engines consume a local action copy before the ordinary unit writer.
h4_path=ROOT/"work/h4-forge-research/generated/halo4_recomp.259.cpp"
h4=h4_path.read_text().split("DEFINE_REX_FUNC(sub_8225CE30) {",1)[1].split("DEFINE_REX_FUNC(",1)[0]
h4_calls=re.findall(r"\b(sub_\w+)\(ctx, base\)",h4)
assert h4_calls.index("sub_82368CE0") < h4_calls.index("sub_823619F8")
h3_calls=records["820B6EA0"]["calls"]
assert h3_calls.index("sub_821F04C0") < h3_calls.index("sub_821EC0E0")
for body, instructions in [(bodies["820B6EA0"],["addi r4,r1,160", "li r5,116", "addi r5,r1,160"]),
                           (h4,["addi r4,r1,144", "li r5,256", "addi r5,r1,144"])]:
    for instruction in instructions:
        assert "// "+instruction in body
h4_input_evidence={"function":"8225CE30", "source":str(h4_path.relative_to(ROOT)),
    "body_sha256":hashlib.sha256(h4.encode()).hexdigest(),
    "local_packet":144,"copy_bytes":256,"forge_consumer":"82368CE0","unit_producer":"823619F8",
    "h3_correspondence":"820B6EA0 local packet160,116-byte copy;821F04C0 precedes821EC0E0",
    "limits":"Ordered reachable calls and shared stack packet, not unconditional execution: context/action-type/control-mode gates and intervening packet filters still apply. Device-axis correspondence remains open."}
output = ROOT / "work/h4-forge-research/isolated/h3-held-update.json"
for instruction in ['li r11,124','lbz r6,108(r11)','addi r11,r11,109','li r9,6',
                    'li r11,96','mulli r9,r9,880','addi r11,r11,20']:
    assert '// '+instruction in bodies['821F0688']
for instruction in ['ori r8,r8,57748','lhzx r9,r9,r8','lwz r5,40(r11)','bl 0x82261480']:
    assert '// '+instruction in bodies['8227E5A0']
for instruction in ['addi r11,r24,14438','mulli r11,r11,84','lwz r31,428(r11)',
                    'bl 0x821f0688','lwz r11,16(r25)']:
    assert '// '+instruction in bodies['82281A98']
# Preserve the stock object notification and per-body routing boundary.
assert records['820F29C8']['calls'][:2] == ['sub_8232EA98','sub_820F2AE0']
assert 'sub_820F2EC8' in records['820F29C8']['calls']
for instruction in ['addi r8,r10,120','addi r10,r10,132','li r4,16','ori r4,r4,32','b 0x820b8768']:
    assert '// '+instruction in bodies['8232EA98']
for instruction in ['lwz r11,160(r10)','lwz r10,172(r10)','lwz r11,36(r31)',
                    'addi r29,r29,72','cmplwi cr6,r11,7','cmplwi cr6,r11,6']:
    assert '// '+instruction in bodies['820F2AE0']
assert records['820F2AE0']['calls'].count('sub_820F8DC0') == 2
assert records['820F2AE0']['calls'].count('sub_820FAED0') == 2
assert 'sub_82333308' in records['820F2EC8']['calls']
output.write_text(json.dumps({
    "scope": "Static original-code audit; input stage precedes engine player update. Runtime field lifetime and drag parity unverified.",
    "input_stage_evidence":h4_input_evidence,
    "player_adapter": {
        "h3_ownership":"821F0688: TLS124 enabled108, identity109..114; TLS96 player stride880 identity20..25",
        "h4_ownership":"822ED938: TLS140 enabled104, identity105..110; validated player stride4144 identity20..25",
        "ownership_validation":"224 paired original-code comparisons in controller fixture; H4 player lookup controlled, network session untested",
        "h3_editor_eligibility":"8227E5A0: TLS100 bitmask57748, player40 controlled unit, tag equality with82261480",
        "h3_held_resolution":"TLS100 engine+57752+4*player selects variant slot; datum=engine+428+84*slot",
        "h3_update_entry":"82282378 called via engine vtable104; requires controlled player40 before82281A98; retains other per-player work",
        "integration_constraint":"Preserve surrounding H3 eligibility/session/UI work; do not replace full vtable callback with a magnet-only call. H3 parent condition is session-dependent, unlike the H4 local coupled path.",
        "open":"Complete session/parent mapping, dispatcher execution and native adapter validation"
    },
    "edit_input_mapping": {
        "h3_producer":"821F04C0: TLS96 player stride880; packet20/24 to player768/772; optional packet32/36 to776/780; active764; threshold packet44>0.1; consumes20/24",
        "h4_producer":"82368CE0: packet28/32 to player1892/1896 with dominant-axis selection; optional44/48 to1900/1904; active1888; threshold56>0.1; consumes28/32",
        "distance_difference":"H3 adds player768*0.3 with native upper10; H4 subtracts player1892*0.3 with radius/config bounds. Upstream physical-axis sign equivalence remains unverified.",
        "adapter_requirement":"Map pre-consumption packet semantics, retain H4 dominant-axis processing; do not blindly copy processed H3 fields or infer axis inversion from these consumers alone.",
        "status":"static original-code comparison; no production adapter or live behavior proof"
    },
    "engine_table": f"{engine_table:08X}", "forge_engine_index": 5,
    "engine_object": f"{engine_object:08X}",
    "tick_stages": ["820B6EA0: conditional unit input write", "820D3E40: engine player iteration"],
    "held_call_chain": ["820D3E40", "82219898", "vtable+104", "82282378", "82281A98"],
    "engine_vtable": "82040D68", "slot_offset": 104,
    "slot_function": "82282378", "functions": records,
    "placement_validation": {
        "chain": ["82281A98", "822836D8", "8226E590", "8226E6C8"],
        "wrapper": "822835E0 supplies tag-derived radius; up to4 attempts; successful result replaces requested point; variant-record gate follows (field semantics unresolved)",
        "search": "8226E590 clamps radius and multiplies it between attempts;8226E6C8 builds physics shapes and tests candidate points",
        "point_queries": "8226E6C8 calls820AE5C0 twice; candidate for H4 point-query boundary, not yet proven equivalent",
        "collision_candidate_chain": ["82281A98","82281268","820AD3E0","820AEA78","vtable82000D28+4","820AEC70"],
        "callback_evidence": "original image82000D2C=820AEC70;820AEA78 constructs table82000D28",
        "ray_arguments": {"r3":"64-bit mask", "r4":"mode byte (Forge passes0)", "r5":"start pointer", "r6":"displacement pointer, not endpoint", "r7_r8_r9":"three filter/identity inputs; detailed semantics pending", "r10":"result buffer, writes through offset92"},
        "ray_result_fields": {"fraction":4,"point":8,"forge_copies_normal":36,"forge_copies_optional_identity":60},
        "forge_ray_mask":"0x001000090000099D (caller literal); not assumed equivalent to H4 mask",
        "camera_mapping": "8227E460 is object32 vector minus820A9E58 root position, not a camera ray query",
        "status": "static evidence only; H4 ray service counterpart still unidentified"},
}, indent=2) + "\n")
print(f"PASS: {len(records)} original bodies recorded; Forge dispatch, tick-stage order, edit-input mapping and held-update calls verified statically")
