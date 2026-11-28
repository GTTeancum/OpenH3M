"""Summarise a structure-bsp XML written by the kit's own `tool export-tag-to-xml`.
Only reads the official tool's output; collects the fields that matter for draw cost."""
import sys, json, collections
import xml.etree.ElementTree as ET

TARGETS = {"clusters", "cluster portals", "meshes", "instanced geometry instances",
           "instanced geometries definitions", "materials", "errors", "per mesh mopp",
           "per mesh subpart visibility", "decorator sets", "transparent planes"}

def scan(path):
    out = collections.defaultdict(list)
    top_counts = {}
    stack = []  # (tag, name)
    class Clean:
        def __init__(self, f): self.f = f
        def read(self, n=-1):
            d = self.f.read(n)
            return d.replace(b'"<unavailable>"', b'"unavailable"')
    # the kit's XML export writes value="<unavailable>" for pageable resources; make it parseable
    for ev, el in ET.iterparse(Clean(open(path, "rb")), events=("start", "end")):
        if ev == "start":
            stack.append((el.tag, el.get("name")))
            if el.tag == "block" and el.get("name") in TARGETS and el.get("name") not in top_counts:
                top_counts[el.get("name")] = el.get("value")
            continue
        stack.pop()
        if el.tag == "element" and stack and stack[-1][0] == "block" and stack[-1][1] in TARGETS:
            # only the outermost occurrence of each target block (avoid nested same-name blocks)
            depth_names = [n for t, n in stack if t == "block"]
            if depth_names.count(stack[-1][1]) == 1:
                rec = {"_name": el.get("name")}
                for c in el:
                    if c.tag == "field":
                        v = c.get("value")
                        if c.text and c.text.strip():
                            v = (v or "") + "|" + " ".join(c.text.split())
                        rec[c.get("name")] = v
                    elif c.tag == "block":
                        rec["#" + c.get("name")] = int(c.get("value").split(",")[-1])
                        if c.get("name") in ("parts", "subparts", "instance buckets", "portals"):
                            rec["@" + c.get("name")] = [
                                dict([(f.get("name"), f.get("value")) for f in e if f.tag == "field"] +
                                     [("#" + b.get("name"), b.get("value")) for b in e if b.tag == "block"]) for e in c]
                out[stack[-1][1]].append(rec)
            el.clear()
        elif el.tag in ("element", "block") and not any(t == "block" and n in TARGETS for t, n in stack):
            el.clear()
    return out, top_counts

if __name__ == "__main__":
    out, tc = scan(sys.argv[1])
    json.dump({"counts": tc, "data": out}, open(sys.argv[2], "w"))
    print(tc)
