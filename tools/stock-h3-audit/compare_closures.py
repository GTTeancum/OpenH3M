"""Compare dependency names reported by upstream TagTool; no binary editing."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
KIT = ROOT / 'work/editing-kits/h3ek/tags'
a = json.loads((OUT / 'closure-360.json').read_text())['tags']
b = json.loads((OUT / 'closure-mcc.json').read_text())['tags']
lists = dict(
    mcc_only_relative_to_stock_closure=sorted(set(b) - set(a)),
    stock_only_relative_to_mcc_closure=sorted(set(a) - set(b)),
    stock_names_missing_from_kit=sorted(x for x in a if not (KIT / x).is_file()),
    mcc_names_missing_from_kit=sorted(x for x in b if not (KIT / x).is_file()),
)
report = dict(stock_count=len(a), mcc_count=len(b), shared_names=len(set(a) & set(b)),
              **lists, groups={k: dict(Counter(n.rsplit('.', 1)[-1] for n in v))
                              for k, v in lists.items()},
              limits='Tag-reference traversal only. Differences include platform representation; no runtime, resource payload, or content-equivalence proof.')
(OUT / 'closure-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in report.items()
                  if k != 'groups'}, indent=2))
