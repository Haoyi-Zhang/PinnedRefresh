"""Exact public-budget frontier and offline robust refresh scheduling.

The dynamic program is standard shortest-path optimization. Its edge condition
and the matching central-share witness are the mathematical objects checked here.
No online prediction, deployed corruption rate, or malicious-party model is used.
"""
from __future__ import annotations
from itertools import combinations
from .model import integer
from .pinned import validate_pinned, multiply


def validate_budget(exposures: list[int], pins: list[int]) -> None:
    if not isinstance(exposures,list) or not 1<=len(exposures)<=12 or not isinstance(pins,list) or len(pins)!=len(exposures)-1:
        raise ValueError('one exposure budget per slot and one pin budget per boundary required')
    if any(not integer(v) or not 0<=v<=24 for v in exposures+pins):
        raise ValueError('budgets must be integers between 0 and 24')
    if sum(exposures)>64:
        raise ValueError('the sum of exposure budgets must not exceed 64')


def constant_capacity(epochs: int, exposure: int, pin: int) -> int:
    """Closed-form capacity for constant public budgets.

    This helper is intentionally separate from :func:`capacities` so tests can
    compare the theorem formula with the recurrence implementation.
    """
    if not integer(epochs) or not 1 <= epochs <= 12:
        raise ValueError("epochs must be an integer between 1 and 12")
    if not integer(exposure) or not 0 <= exposure <= 24:
        raise ValueError("exposure must be an integer between 0 and 24")
    if not integer(pin) or not 0 <= pin <= 24:
        raise ValueError("pin must be an integer between 0 and 24")
    return min(
        epochs * exposure,
        ((epochs + 1) // 2) * exposure + pin,
        exposure + 2 * pin,
    )


def fixed_pin_capacity(exposures: list[int], pin: int) -> int:
    """Worst-case capacity when one fixed identity set is pinned throughout."""
    if not isinstance(exposures, list) or not exposures:
        raise ValueError("at least one exposure budget is required")
    if any(not integer(value) or not 0 <= value <= 24 for value in exposures):
        raise ValueError("exposures must be integers between 0 and 24")
    if not integer(pin) or not 0 <= pin <= 24:
        raise ValueError("pin must be an integer between 0 and 24")
    return min(sum(exposures), pin + max(exposures))


def largest_safe_constant_horizon(exposure: int, pin: int, threshold: int) -> int | None:
    """Return the largest positive safe horizon, or ``None`` if unbounded.

    Zero means that no positive horizon is safe.  The function implements the
    closed-form inversion proved in the manuscript and is checked against the
    recurrence on every supported bounded input.
    """
    if not integer(exposure) or not 1 <= exposure <= 24:
        raise ValueError("positive exposure must be an integer at most 24")
    if not integer(pin) or not 0 <= pin <= 24:
        raise ValueError("pin must be an integer between 0 and 24")
    if not integer(threshold) or not 2 <= threshold <= 24:
        raise ValueError("threshold must be an integer between 2 and 24")
    if exposure + 2 * pin < threshold:
        return None
    horizon_one = (threshold - 1) // exposure
    horizon_two = 2 * max(0, (threshold - 1 - pin) // exposure)
    return max(horizon_one, horizon_two)


def capacities(exposures: list[int], pins: list[int]) -> dict:
    validate_budget(exposures,pins)
    t=len(exposures);left=[0]*t;right=[0]*t
    for e in range(t-1):left[e+1]=min(pins[e],left[e]+exposures[e])
    for e in range(t-2,-1,-1):right[e]=min(pins[e],right[e+1]+exposures[e+1])
    local=[a+b+c for a,b,c in zip(exposures,left,right)]
    maximum=max(local)
    return {'left':left,'right':right,'local':local,'capacity':maximum,'pivot':local.index(maximum)}


def interval_cost(exposures: list[int], pins: list[int], a: int, z: int) -> int:
    """Cost of half-open [a,z); boundary indices are cut positions 1,...,T-1."""
    t=len(exposures)
    if not 0<=a<z<=t:raise ValueError('empty or invalid interval')
    return sum(exposures[a:z])+(pins[a-1] if a else 0)+(pins[z-1] if z<t else 0)


def bottleneck_partition(exposures: list[int], pins: list[int]) -> dict:
    validate_budget(exposures,pins);t=len(exposures)
    value=[None]*(t+1);paths=[None]*(t+1);value[0]=0;paths[0]=[0]
    for z in range(1,t+1):
        candidates=[(max(value[a],interval_cost(exposures,pins,a,z)),paths[a]+[z]) for a in range(z)]
        value[z],paths[z]=min(candidates)
    return {'width':value[t],'cuts':paths[t],
            'interval_costs':[interval_cost(exposures,pins,a,z) for a,z in zip(paths[t],paths[t][1:])]}


def minimum_cost_schedule(exposures: list[int], pins: list[int], threshold: int, charges: list[int], allowed: list[bool]|None=None) -> dict:
    validate_budget(exposures,pins);t=len(exposures)
    if not integer(threshold) or not 2<=threshold<=12:raise ValueError('threshold must be between 2 and 12')
    if not isinstance(charges,list) or len(charges)!=t-1 or any(not integer(c) or c<0 for c in charges):raise ValueError('nonnegative integer charges required')
    if allowed is None:allowed=[True]*(t-1)
    if not isinstance(allowed,list) or len(allowed)!=t-1 or any(type(a) is not bool for a in allowed):raise ValueError('one boolean availability per boundary required')
    value=[None]*(t+1);paths=[None]*(t+1);value[0]=0;paths[0]=[0]
    for z in range(1,t+1):
        if z<t and not allowed[z-1]:continue
        choices=[]
        for a in range(z):
            if value[a] is None or interval_cost(exposures,pins,a,z)>=threshold:continue
            choices.append((value[a]+(charges[z-1] if z<t else 0),paths[a]+[z]))
        if choices:value[z],paths[z]=min(choices)
    if value[t] is None:
        # A skipped boundary preserves every coordinate. A pool of 24 is used
        # for this bounded artifact; k<=12, so such a boundary cannot be a safe cut.
        effective=[u if on else 24 for u,on in zip(pins,allowed)]
        witness=capacities(exposures,effective)
        if witness['capacity']<threshold:raise AssertionError('inconsistent scheduling alternative')
        return {'kind':'impossible','capacity_witness':witness,'effective_pin_budgets':effective}
    cuts=paths[t];return {'kind':'schedule','cost':value[t],'cuts':cuts,'refresh_boundaries':cuts[1:-1],
                        'interval_costs':[interval_cost(exposures,pins,a,z) for a,z in zip(cuts,cuts[1:])]}


def enumerate_schedules(exposures: list[int], pins: list[int], threshold: int, charges: list[int]) -> list[dict]:
    """Independent partition enumeration, limited to at most 64 schedules."""
    validate_budget(exposures,pins);t=len(exposures)
    if t>7:raise ValueError('exhaustive scheduler check is capped at six boundaries')
    result=[]
    for mask in range(1<<(t-1)):
        cuts=[0]+[e+1 for e in range(t-1) if mask>>e&1]+[t]
        costs=[interval_cost(exposures,pins,a,z) for a,z in zip(cuts,cuts[1:])]
        result.append({'cuts':cuts,'width':max(costs),'safe':max(costs)<threshold,
                       'cost':sum(charges[e-1] for e in cuts[1:-1])})
    return result


def lower_trace(exposures: list[int], pins: list[int], threshold: int, field: int=29) -> dict:
    """Concrete share-capture witness for any k <= the public-budget capacity."""
    witness=capacities(exposures,pins);t=len(exposures);pivot=witness['pivot'];k=threshold
    if not integer(k) or not 2<=k<=min(12,field-1) or k>witness['capacity']:raise ValueError('no supported lower-bound witness at this threshold')
    at=min(exposures[pivot],k);before=min(witness['left'][pivot],k-at);after=k-at-before
    if after>witness['right'][pivot]:raise AssertionError('capacity split failed')
    ls=list(range(1,before+1));cs=list(range(before+1,before+at+1));rs=list(range(before+at+1,k+1))
    actual_c=[[] for _ in range(t)];actual_o=[[] for _ in range(t-1)];actual_c[pivot]=cs
    needed=ls[:]
    for e in range(pivot-1,-1,-1):
        actual_o[e]=needed[:]
        take=min(exposures[e],len(needed));actual_c[e]=needed[:take];needed=needed[take:]
    if needed:raise AssertionError('left transport failed')
    needed=rs[:]
    for e in range(pivot+1,t):
        actual_o[e-1]=needed[:]
        take=min(exposures[e],len(needed));actual_c[e]=needed[:take];needed=needed[take:]
    if needed:raise AssertionError('right transport failed')
    case={'field':field,'threshold':k,'epochs':t,'pins':actual_o,'exposed':actual_c};validate_pinned(case)
    if any(len(c)>b for c,b in zip(actual_c,exposures)) or any(len(o)>u for o,u in zip(actual_o,pins)):raise AssertionError('budget violation')
    sources=[{'x':x,'epoch':e} for e,xs in enumerate(actual_c) for x in xs]
    weights=[]
    for row in sources:
        x=row['x'];w=1
        for other in sources:
            y=other['x']
            if y!=x:w=w*(-y)*pow(x-y,-1,field)%field
        weights.append(w)
    return {'case':case,'pivot':pivot,'sources':sources,'interpolation_weights':weights,'capacity':witness['capacity']}


def verify_transport(record: dict) -> bool:
    """Check equality paths and interpolation basis; no Gaussian elimination."""
    case=record['case'];validate_pinned(case);q=case['field'];k=case['threshold'];p=record['pivot']
    if not integer(p) or not 0<=p<case['epochs']:return False
    sources=record['sources'];weights=record['interpolation_weights']
    if len(sources)!=k or len(weights)!=k or len({s['x'] for s in sources})!=k:return False
    for source in sources:
        x,e=source['x'],source['epoch']
        if not integer(e) or not 0<=e<case['epochs'] or x not in case['exposed'][e]:return False
        if any(x not in case['pins'][j] for j in range(min(p,e),max(p,e))):return False
    if any(not integer(w) or not 0<=w<q for w in weights):return False
    return all(sum(w*pow(s['x'],j,q) for s,w in zip(sources,weights))%q==int(j==0) for j in range(k))


def root_certificate(case: dict, cuts: list[int]) -> dict:
    validate_pinned(case);q=case['field'];k=case['threshold'];t=case['epochs']
    if not isinstance(cuts,list) or len(cuts)<2 or cuts[0]!=0 or cuts[-1]!=t or any(not integer(c) for c in cuts) or any(a>=z for a,z in zip(cuts,cuts[1:])):raise ValueError('invalid partition')
    polys=[None]*t
    for a,z in zip(cuts,cuts[1:]):
        roots=set().union(*(set(c) for c in case['exposed'][a:z]))
        if a:roots.update(case['pins'][a-1])
        if z<t:roots.update(case['pins'][z-1])
        if len(roots)>=k:raise ValueError('root certificate would exceed degree bound')
        poly=[1]
        for x in sorted(roots):poly=multiply(poly,[1,-pow(x,-1,q)%q],q)
        poly += [0]*(k-len(poly))
        for e in range(a,z):polys[e]=poly[:]
    return {'kind':'hiding','polynomials':polys}
