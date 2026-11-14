"""Keep applied compatibility decisions visible even when a later stage fails."""
def snapshot(importer, limit=2000):
    if limit < 1:
        raise ValueError('Compatibility report limit must be positive')
    names = ('approx', 'omit', 'omiss', 'unrepresent', 'difference', 'drop', 'adapter',
             'frozen', 'compat', 'candidate', 'notes', 'correction',
             'stock_equivalent', 'converted_source_animations')
    records = []
    for category, rows in (('tag', getattr(importer, 'added', [])),
                           ('scenario', getattr(importer, 'scenario_compatibility_notes', [])),
                           ('material', getattr(getattr(importer, 'materials', None), 'report', []))):
        for row in rows:
            notes = {key: value for key, value in row.items()
                     if value not in (None, False, [], {}, '', 0)
                     and any(word in key.lower() for word in names)}
            if notes:
                records.append(dict(kind=category, source=row.get('source', row.get('name')),
                                    group=row.get('group'), **notes))
    return dict(scope='Applied decisions in an incomplete assembly; not a serialized or accepted map',
                records=records[:limit], total_records=len(records), truncated=len(records) > limit)
