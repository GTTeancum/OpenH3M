"""Extract original ReXGlue bodies; never translate Forge behavior by hand."""
import hashlib
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "work/h4-forge-research"
GENERATED = RESEARCH / "generated"
OUT = RESEARCH / "isolated"
# These world queries must be supplied by the H3 integration, not replaced
# with an approximation of the original selection/alignment algorithm.
BOUNDARIES = {
    "sub_82415970": "monitor-follow boolean native point containment",
    "sub_82400D48": "local monitor-view notification after original angle conversion",
    "sub_822B79A0": "native unit selection-ray origin",
    "sub_82268800": "ordered native seatless-biped selection exclusions",
    "sub_82417550": "explicit native selection collision query",
    "sub_823C5C28": "selection-only discarded variant-record read",
    "sub_82CD40A8": "native controlled-body relocation",
    "sub_82CD55F0": "native controlled-body activation",
    "sub_82486B78": "native scenery contact geometry collection",
    "sub_822D1158": "native contact-response velocity submission",
    "sub_82943B08": "unsupported non-scenery contact notification guard",

    "sub_82260CF0": "native held object motion-vector query",
    "sub_82243068": "local native object orientation for original camera prediction",
    "sub_8249B1F8": "first physics-body local center with original fixed/keyframed authored alternative",
    "sub_822410D0": "native object reference-point query for original held update",
    "sub_82451BA8": "native geometry containment query matching original H4 service",
    "sub_822AD348": "native selected physics body transform query",
    "sub_82235650": "native contact response with cached-point writeback, velocity and flags",
    "sub_82452930": "native target-controller submission boundary",

    "sub_82232AC8": "native edit-input eligibility and current held object",
    "sub_8225EA20": "native original object reference vector for held selection",
    "sub_82505DE8": "native focus-object lookup for original held selection",
    "sub_8312D878": "native sink for original Forge editor lifecycle events",
    "sub_82260B58": "native object point before/after scenery physics transition",
    "sub_822ED938": "native local holder ownership for scenery physics transition",
    "sub_82388C68": "native scenery physics instance creation adapter",
    "sub_82388A08": "native scenery physics rebuild adapter",
    "sub_82449B18": "owning editor player for supplied scenery physics query",
    "sub_82469630": "original keyframed-body predicate result from host physics",
    "sub_8244A5F0": "original session/engine/multiplayer-property predicate result",
    "sub_823C2020": "private variant property view supplied for scenery physics selection",
    "sub_821F2050": "nearby object query",
    "sub_82582610": "collect object marker transforms",
    "sub_82582A68": "configured marker group name",
    "sub_82937F50": "object marker eligibility",
    "sub_8293A3B0": "object world position",
    "sub_825827B0": "create host-only marker visuals for an object",
    "sub_82582950": "remove host-only marker visuals for an object",
    "sub_82271460": "validate selected object in supplied editor scene",
    "sub_822714E0": "validate local editor player",
    "sub_825812D0": "transport original coordinate-edit event to H3 placement",
}
ROOTS = ["sub_82C969B0", "sub_8249B418", "sub_824863F8", "sub_8244A8D8", "sub_8244B338", "sub_82451A38", "sub_8244EED8", "sub_8244A7D0", "sub_82368CE0", "sub_82282580", "sub_82449ED8", "sub_82449DD8", "sub_8244A2A0", "sub_8244A180", "sub_82452738", "sub_82582178", "sub_82582250", "sub_82582AD0", "sub_825826B0",
         "sub_8268AE80", "sub_8268B410", "sub_8268C340", "sub_8232F960",
         # Original tag-function scalar evaluation and color conversion.
         # Marker particle curves use these too; isolated checks supply the
         # original data reference and its input/range values.
         "sub_8226CD10", "sub_8228F2A0"]
# Original collision-layer predicate used by the selection ray's hcfd filter.
ROOTS.append("sub_82D813F8")
ROOTS.append("sub_8244C740")
ROOTS.append("sub_824BFE90")
ROOTS.append("sub_824F5CF0")
ROOTS.append("sub_823FC348")
ROOTS.append("sub_8257FB98")
ROOTS.append("sub_8244AF48")
# Preserve original region/permutation filtering, node transform composition,
# marker metadata and mirrored orientation when adapting native marker data.
ROOTS.append("sub_8259E9A8")
# Original controlled-root attachment compensation math,82939248.
ROOTS.extend(["sub_82300D40", "sub_821E0550", "sub_822864E0"])
ROOTS.extend(["sub_83292E30", "sub_83292E50"])
# Keep the contact implementation distinct from the held caller's world
# boundary so it can run with a separate mapped native-response context.
SCOPED_ROOTS = {"contact_response": ["sub_82235650"]}
functions = {}
for path in sorted(GENERATED.glob("halo4_recomp.*.cpp")):
    text = path.read_text()
    matches = list(re.finditer(r"^DEFINE_REX_FUNC\((\w+)\) \{", text, re.M))
    for i, match in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        body = text[match.start():end].strip()
        functions[match[1]] = (path.name, body)
selected = set()
pending = ROOTS.copy()
for names in SCOPED_ROOTS.values():
    for name in names:
        body = functions[name][1]
        if "REX_CALL_INDIRECT" in body:
            raise RuntimeError(f"Unresolved scoped dependency in {name}")
        pending.extend(re.findall(r"\b((?:sub_|__save|__rest)\w+)\(ctx, base\)", body))
while pending:
    name = pending.pop()
    if name in selected or name in BOUNDARIES:
        continue
    if name not in functions:
        raise RuntimeError(f"Missing original function: {name}")
    selected.add(name)
    body = functions[name][1]
    if "REX_CALL_INDIRECT" in body and name != "sub_82C01FB8":
        raise RuntimeError(f"Unresolved indirect dependency in {name}")
    pending.extend(re.findall(r"\b((?:sub_|__save|__rest)\w+)\(ctx, base\)", body))
OUT.mkdir(exist_ok=True)
header = ['#pragma once', '#include "../generated/halo4_pch.h"', '#include <cmath>',
          'namespace h4_forge_original {',
          'void controller_dispatch(PPCContext&, uint8_t*, uint32_t);']
for name in sorted(selected | set(BOUNDARIES)):
    header.append(f"void {name}(PPCContext& ctx, uint8_t* base);")
for scope, names in SCOPED_ROOTS.items():
    header.append(f"namespace {scope} {{")
    header.extend(f"void {name}(PPCContext& ctx, uint8_t* base);" for name in names)
    header.append('}')
header.append('}')
(OUT / 'forge_original.h').write_text('\n'.join(header)+'\n')
source = ['#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx, uint8_t* base)',
          '#include "forge_original.h"',
          '#undef REX_CALL_INDIRECT_FUNC',
          '#define REX_CALL_INDIRECT_FUNC(address) controller_dispatch(ctx,base,address)',
          'namespace h4_forge_original {']
report = dict(roots=ROOTS, scoped_roots=SCOPED_ROOTS, data_boundaries=BOUNDARIES, functions={}, scoped_functions={})
for name in sorted(selected):
    file, body = functions[name]
    source.append(body)
    report['functions'][name] = dict(source=file,
        sha256=hashlib.sha256(body.encode()).hexdigest(), bytes=len(body))
for scope, names in SCOPED_ROOTS.items():
    source.append(f"namespace {scope} {{")
    for name in names:
        file, body = functions[name]
        source.append(body)
        report['scoped_functions'][scope+'::'+name] = dict(source=file,
            sha256=hashlib.sha256(body.encode()).hexdigest(), bytes=len(body))
    source.append('}')
source.append('}')
(OUT / 'forge_original.cpp').write_text('\n\n'.join(source)+'\n')
(OUT / 'extraction.json').write_text(json.dumps(report, indent=2)+'\n')
print(f"Extracted {len(selected)+len(report['scoped_functions'])} unchanged original function bodies; {len(BOUNDARIES)} scene-data boundaries")
