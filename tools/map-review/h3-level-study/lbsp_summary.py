"""Summarise a scenario_lightmap_bsp_data XML from the kit's export-tag-to-xml: per mesh, part and subpart counts,
index counts, instance buckets; plus the block outline (names/counts to depth 3). Read-only."""
import sys, json, collections, xml.etree.ElementTree as ET
class Clean:
    def __init__(s, f): s.f = f
    def read(s, n=-1): return s.f.read(n).replace(b'"<unavailable>"', b'"unavailable"')
outline = collections.OrderedDict(); stack = []; meshes = []; cur = None
for ev, el in ET.iterparse(Clean(open(sys.argv[1], "rb")), events=("start", "end")):
    if ev == "start":
        stack.append((el.tag, el.get("name")))
        if el.tag == "block":
            path = "/".join(n for t, n in stack if t == "block")
            if path.count("/") < 3 and path not in outline: outline[path] = el.get("value")
        continue
    tag, name = stack.pop()
    bpath = [n for t, n in stack if t == "block"]
    if el.tag == "element" and bpath and bpath[-1] == "meshes" and bpath.count("meshes") == 1:
        rec = {}
        for c in el:
            if c.tag == "block":
                rec["#" + c.get("name")] = int(c.get("value").split(",")[-1])
                if c.get("name") == "parts":
                    rec["part_idx"] = [int(f.get("value")) for e in c for f in e if f.tag == "field" and f.get("name") == "index count"]
                    rec["part_subparts"] = [int(f.get("value")) for e in c for f in e if f.tag == "field" and f.get("name") == "subpart count"]
            elif c.tag == "field" and c.get("name") in ("mesh flags", "index buffer type", "vertex type", "prt vertex type"):
                rec[c.get("name")] = c.get("value")
        meshes.append(rec); el.clear()
    elif el.tag == "element" and "meshes" not in bpath:
        el.clear()
json.dump({"outline": outline, "meshes": meshes}, open(sys.argv[2], "w"))
print(len(meshes), "meshes"); [print(k, v) for k, v in outline.items()]
