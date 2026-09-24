"""Bounded exact comparisons for the capacity/partition duality and scheduler."""
from __future__ import annotations
from itertools import product
import random
from .budgets import (capacities,bottleneck_partition,enumerate_schedules,minimum_cost_schedule,
                      lower_trace,verify_transport,root_certificate)
from .pinned_producer import produce_pinned
from .pinned_checker import verify_pinned


def check_budget_corpus(corpus: dict) -> dict:
    mathematical=[];partitions=0;certificates=0;transport_checks=0;case_records=[]
    for case in corpus['mathematical_cases']:
        b,u=case['exposures'],case['pins'];cap=capacities(b,u);dp=bottleneck_partition(b,u)
        enum=enumerate_schedules(b,u,2,[1]*len(u));partitions+=len(enum)
        exact=min(r['width'] for r in enum)
        if not cap['capacity']==dp['width']==exact:raise AssertionError('capacity/partition duality failed')
        mathematical.append({'exposures':b,'pins':u,'capacity':cap,'partition':dp,'exhaustive_partitions':enum})
    for case in corpus['variable_cases']:
        b,u=case['exposures'],case['pins'];cap=capacities(b,u);dp=bottleneck_partition(b,u)
        if cap['capacity']!=dp['width'] or dp!=case['partition']:raise AssertionError('variable partition mismatch')
        upper=case['upper_case'];cert=root_certificate(upper,dp['cuts'])
        other=produce_pinned(upper)
        if other['kind']!='hiding' or not verify_pinned(upper,cert) or not verify_pinned(upper,other):raise AssertionError('upper-bound certificate failed')
        certificates+=2
        lower=case['lower_witness'];tr=lower['case'];certificate=produce_pinned(tr)
        if not verify_transport(lower) or certificate['kind']!='revealing' or not verify_pinned(tr,certificate):raise AssertionError('matching lower bound failed')
        certificates+=1;transport_checks+=1
        case_records.append({'id':case['id'],'capacity':cap,'partition':dp,'upper_certificate':cert,'lower_certificate':certificate})
    sc=corpus['schedule_case'];b,u,k,w=sc['exposures'],sc['pins'],sc['threshold'],sc['charges']
    dp=minimum_cost_schedule(b,u,k,w);enum=enumerate_schedules(b,u,k,w);partitions+=len(enum)
    feasible=[r for r in enum if r['safe']]
    best=min((r['cost'],r['cuts']) for r in feasible)
    if dp['kind']!='schedule' or (dp['cost'],dp['cuts'])!=best:raise AssertionError('minimum-cost partition failed')
    schedules=[];rnd=random.Random(20260914)
    for index,row in enumerate(enum):
        cuts=set(row['cuts'][1:-1]);effective=[v if e+1 in cuts else 24 for e,v in enumerate(u)]
        cap=capacities(b,effective);safe=cap['capacity']<k
        if safe:
            case={'field':29,'threshold':k,'epochs':len(b),
                  'pins':[sorted(rnd.sample(range(1,25),v)) if e+1 in cuts else list(range(1,25)) for e,v in enumerate(u)],
                  'exposed':[[rnd.randrange(1,25)] for _ in b]}
            certificate=produce_pinned(case)
            if certificate['kind']!='hiding' or not verify_pinned(case,certificate):raise AssertionError('safe schedule failed')
        else:
            witness=lower_trace(b,effective,k);case=witness['case']
            for e in range(len(u)):
                if e+1 not in cuts:case['pins'][e]=list(range(1,25))
            if not verify_transport(witness):raise AssertionError('strengthened skipped-boundary witness failed')
            transport_checks+=1;certificate=produce_pinned(case)
            if certificate['kind']!='revealing' or not verify_pinned(case,certificate):raise AssertionError('unsafe schedule witness failed')
        certificates+=1
        schedules.append({'id':f'schedule-{index:02d}','refresh_boundaries':sorted(cuts),'cost':row['cost'],
                          'partition_certificate_safe':row['safe'],'universally_safe':safe,'capacity':cap,
                          'case':case,'certificate':certificate})
    safe_schedules=[r for r in schedules if r['universally_safe']]
    if min(r['cost'] for r in safe_schedules)!=dp['cost']:raise AssertionError('all-subset optimality failed')
    # Maximal refresh cannot help an all-zero-refresh-space trace.
    impossible=minimum_cost_schedule([1,1,1],[2,2],3,[1,1])
    if impossible['kind']!='impossible':raise AssertionError('impossible scheduling control failed')
    return {'mathematical_cases':mathematical,'variable_cases':case_records,
            'schedule_result':dp,'schedules':schedules,'impossible_control':impossible,
            'counts':{'mathematical_budget_cases':len(mathematical),'exhaustive_partitions':partitions,
                      'variable_budget_cases':len(case_records),'variable_concrete_traces':2*len(case_records),
                      'schedule_subsets':len(schedules),'safe_schedule_subsets':len(safe_schedules),
                      'feasible_exact_cut_partitions':len(feasible),'certificate_checks':certificates,
                      'transport_checks':transport_checks}}
