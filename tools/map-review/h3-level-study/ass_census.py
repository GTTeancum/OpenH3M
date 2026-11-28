"""Census of a Halo 3 .ass level source (the editing kit's input format): materials, objects,
instances; splits structure from instanced (%-named) geometry. Read-only."""
import sys, collections, json

def lines(p):
    with open(p, encoding="latin-1") as f:
        for l in f:
            l = l.strip()
            if l and not l.startswith(";"):
                yield l

def parse(p):
    it = lines(p)
    nxt = lambda: next(it)
    assert nxt() == "7"
    for _ in range(4): nxt()
    nm = int(nxt()); mats = []
    for _ in range(nm):
        name = nxt().strip('"'); nxt(); nflags = int(nxt())
        for _ in range(nflags): nxt()
        mats.append(name)
    no = int(nxt()); objs = []
    for _ in range(no):
        typ = nxt().strip('"'); nxt(); nxt()
        if typ == "GENERIC_LIGHT":
            for _ in range(13): nxt()
            objs.append({"verts": 0, "tris": 0, "mats": collections.Counter(), "light": True}); continue
        if typ != "MESH":
            # SPHERE/BOX/etc primitives: material + params; consume until next known pattern is hard,
            # so record and bail if encountered
            raise SystemExit("non-mesh object " + typ)
        nv = int(nxt())
        for _ in range(nv):
            nxt(); nxt(); nxt()
            k = int(nxt())
            for _ in range(k): nxt()
            u = int(nxt())
            for _ in range(u): nxt()
        nt = int(nxt()); mc = collections.Counter()
        for _ in range(nt):
            mc[int(nxt().split()[0])] += 1
        objs.append({"verts": nv, "tris": nt, "mats": mc})
    ni = int(nxt()); insts = []
    for _ in range(ni):
        oi = int(nxt()); name = nxt().strip('"'); uid = nxt(); parent = nxt(); inh = nxt()
        for _ in range(6): nxt()
        insts.append({"obj": oi, "name": name})
    return mats, objs, insts

if __name__ == "__main__":
    mats, objs, insts = parse(sys.argv[1])
    special = collections.Counter(m.split()[0] for m in mats if m.startswith(("+", "@", "!")))
    st_tris = 0; st_mc = collections.Counter(); st_objs = 0
    in_tris = 0; defs = collections.Counter(); in_parts = 0
    for i in insts:
        if i["obj"] < 0: continue
        o = objs[i["obj"]]
        if i["name"].startswith("%"):
            in_tris += o["tris"]; defs[i["obj"]] += 1; in_parts += len(o["mats"])
        else:
            st_tris += o["tris"]; st_mc.update(o["mats"]); st_objs += 1
    portal_tris = sum(n for mi, n in st_mc.items() if mats[mi].startswith("+portal"))
    res = {"materials": len(mats), "objects": len(objs), "instances": len(insts),
           "structure_objects": st_objs, "structure_tris": st_tris,
           "structure_materials_used": len(st_mc), "portal_tris": portal_tris,
           "instance_placements": sum(defs.values()), "instance_defs": len(defs),
           "instance_tris_placed": in_tris, "instance_parts_placed": in_parts,
           "defs_placed_once": sum(1 for v in defs.values() if v == 1),
           "special_materials": dict(special),
           "top_defs_by_tris": sorted(((objs[k]["tris"] * v, objs[k]["tris"], v) for k, v in defs.items()), reverse=True)[:10],
           "instance_name_prefix2": dict(collections.Counter(i["name"][:2] for i in insts if i["name"].startswith("%")))}
    print(json.dumps(res, indent=1))
