"""Summarize observed guest memory without treating host RSS as console usage."""
import argparse
import json
from pathlib import Path


def summarize(path):
    events = [json.loads(line) for line in path.read_text().splitlines()]
    inputs = next(e for e in events if e['event'] == 'input_map')
    stats = [e for e in events if 'heap_accounted_physical_bytes' in e]
    virtual = [e for e in events if e['event'] == 'guest_virtual_commit']
    if not stats or not virtual:
        raise ValueError('Both native statistics and unique guest backing samples are required')
    errors = [e for e in events if e['event'] in ('error', 'exception')]
    peak_physical = max(e['heap_accounted_physical_bytes'] for e in stats)
    peak_virtual = max(e['virtual_committed_bytes']+e['xex_committed_bytes'] for e in virtual)
    last_stats = stats[-1]
    later_allocations = [e for e in events if e.get('function') in ('physical_allocate','physical_free')
                         and e['seconds'] > last_stats['seconds'] and e['event'] == 'enter']
    # Event accounting is diagnostic only: software breakpoints may miss a call
    # on another thread while the original instruction is single-stepped.
    pending, live, unmatched, failed = {}, {}, [], 0
    for e in events:
        name = e.get('function')
        if e['event'] == 'enter' and name == 'physical_allocate':
            pending.setdefault(e['tid'], []).append([int(x,16) for x in e['guest_arguments']])
        elif e['event'] == 'return' and name == 'physical_allocate':
            args = pending[e['tid']].pop()
            address = int(e['result'],16)&0xffffffff
            if not address:
                failed += 1
                continue
            page = 65536 if args[2]&0x20000000 else 16777216 if args[2]&0x80000000 else 4096
            live[address] = (args[1]+page-1)//page*page
        elif e['event'] == 'enter' and name == 'physical_free':
            address = int(e['guest_arguments'][1],16)
            if address not in live:
                unmatched.append(hex(address))
            live.pop(address, None)
    return {'input': inputs, 'statistics_samples':len(stats),
            'last_statistics_seconds':last_stats['seconds'],
            'physical_heap_peak_bytes':peak_physical,
            'unique_virtual_xex_peak_bytes':peak_virtual,
            'combined_observed_components_bytes':peak_physical+peak_virtual,
            'host_runtime_physical_writeback_reservation_bytes':16777216,
            'virtual_samples':virtual,
            'observed_physical_calls_after_last_statistics':len(later_allocations),
            'observed_failed_physical_allocations':failed,
            'unmatched_free_events':unmatched, 'errors':errors,
            'watchdog_reached':any(e['event']=='watchdog' for e in events),
            'retail_console_budget_verified':False,
            'limitations':['Host physical reservation is not a retail console allocation.',
                           'Runtime kernel page count is a placeholder.',
                           'Virtual backing includes runtime support and debug allocations.',
                           'Event totals may miss concurrent calls; use native heap statistics.',
                           'Startup statistics do not measure occupancy within the game resource pool.']}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace', type=Path)
    p.add_argument('--report', type=Path, required=True)
    args=p.parse_args()
    report=summarize(args.trace)
    args.report.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('input','virtual_samples','limitations')}))
