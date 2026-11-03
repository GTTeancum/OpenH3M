"""Audit/rebind native material animation registers after template relocation.

Animation routes carry their own GPU destination as well as a constant index.
Changing template routes alone leaves these destinations stale. Resolve by
stage and constant index, preserving the function index and authored data.
"""


def animation_register_updates(cache, template_ids, replacements=None):
    """Return unique two-byte register edits and a per-use audit.

    replacements maps template IDs to {pass_index: twelve usage lists}; this
    lets a shader patch validate animation against its not-yet-written routes.
    Missing entries use the current cache. Ambiguous/shared destinations fail.
    """
    replacements = replacements or {}
    edits, audit = {}, []

    def span(rows, packed):
        start, count = packed & 1023, packed >> 10
        if start + count > len(rows):
            raise ValueError('Animation/template route range exceeds table')
        return list(enumerate(rows))[start:start + count]

    for material, tag in cache.tags.items():
        if tag['group'] != 'rmsh':
            continue
        for post in cache.block(tag['offset'] + 40, 132):
            template = cache.u(post + 12) & 65535
            if template not in template_ids:
                continue
            target = cache.tags[template]['offset']
            ae, te = cache.block(post + 56, 2), cache.block(target + 36, 2)
            ap, tp = cache.block(post + 68, 6), cache.block(target + 48, 28)
            ar, tr = cache.block(post + 80, 4), cache.block(target + 60, 4)
            functions = cache.block(post + 92, 36)
            if not ae and not ar and not functions:
                continue
            if len(ae) != len(te):
                raise ValueError('Animation and template entry counts differ')
            seen = set()
            for entry, (a, t) in enumerate(zip(ae, te)):
                animation_passes = span(ap, cache.unpack('H', a)[0])
                template_passes = span(tp, cache.unpack('H', t)[0])
                if len(animation_passes) != len(template_passes):
                    raise ValueError('Animation and template pass counts differ')
                for (_, animation_pass), (pass_index, template_pass) in zip(animation_passes, template_passes):
                    for usage, target_usage in enumerate((0, 1, 4)):
                        planned = replacements.get(template, {}).get(pass_index)
                        routes = planned[target_usage] if planned is not None else [
                            cache.unpack('HBB', row) for _, row in
                            span(tr, cache.unpack('H', template_pass + target_usage * 2)[0])]
                        for _, row in span(ar, cache.unpack('H', animation_pass + usage * 2)[0]):
                            old, function, parameter = cache.unpack('HBB', row)
                            expected = [r[0] for r in routes if r[1] == parameter]
                            if len(expected) != 1 or function >= len(functions):
                                raise ValueError('Missing/ambiguous animation destination or function')
                            new = expected[0]
                            if row in edits and edits[row] != new:
                                raise ValueError('Shared animation route has conflicting destinations')
                            edits[row] = new
                            seen.add(row)
                            audit.append(dict(material=material, template=template, entry=entry,
                                              usage=usage, function=function, parameter=parameter,
                                              offset=row, old_register=old, new_register=new))
            if seen != set(ar):
                raise ValueError('Unreferenced material animation routes')
    return {offset: value for offset, value in edits.items()
            if cache.unpack('H', offset)[0] != value}, audit
