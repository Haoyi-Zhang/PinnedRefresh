#!/usr/bin/env python3
"""Compute a minimum-cost offline robust refresh schedule from public integer budgets."""
import argparse,json,sys
from pathlib import Path
from src.budgets import minimum_cost_schedule,lower_trace,verify_transport
p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
try:
    x=json.loads(a.input.read_text())
    if set(x)!={'exposures','pins','threshold','charges'}:raise ValueError('input requires exposures, pins, threshold, charges')
    r=minimum_cost_schedule(x['exposures'],x['pins'],x['threshold'],x['charges'])
    if r['kind']=='impossible':
        r['interpolation_witness']=lower_trace(x['exposures'],r['effective_pin_budgets'],x['threshold'])
        if not verify_transport(r['interpolation_witness']):raise AssertionError('transport witness rejected')
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(r['kind'])
except (OSError,ValueError,AssertionError) as e:print('FAILED: '+str(e),file=sys.stderr);raise SystemExit(1)
