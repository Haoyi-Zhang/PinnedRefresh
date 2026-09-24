"""Independent bounded oracles for the public-budget theorem and scheduler.

This module deliberately does not import the certificate producer, checker, or
pinned-trace encoder.  It uses a separate modular-rank implementation for all
small concrete pin/exposure set systems, brute-force interval partitions for
the capacity duality, and brute-force cut subsets for the offline scheduler.
The checks are finite regression evidence, not a proof of the general theorem.
"""
from __future__ import annotations

from itertools import product
from typing import Iterable

from .budgets import (
    capacities,
    constant_capacity,
    fixed_pin_capacity,
    largest_safe_constant_horizon,
    minimum_cost_schedule,
)


def _rank_mod(rows: Iterable[Iterable[int]], q: int) -> int:
    """Return row rank over the prime field F_q using local elimination code."""
    matrix = [[value % q for value in row] for row in rows]
    if not matrix:
        return 0
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError("ragged rank matrix")
    top = 0
    for col in range(width):
        pivot = next((i for i in range(top, len(matrix)) if matrix[i][col]), None)
        if pivot is None:
            continue
        matrix[top], matrix[pivot] = matrix[pivot], matrix[top]
        inverse = pow(matrix[top][col], -1, q)
        matrix[top] = [(value * inverse) % q for value in matrix[top]]
        for i in range(top + 1, len(matrix)):
            factor = matrix[i][col]
            if factor:
                matrix[i] = [
                    (left - factor * right) % q
                    for left, right in zip(matrix[i], matrix[top])
                ]
        top += 1
        if top == len(matrix):
            break
    return top


def _pinned_reveals(
    q: int,
    k: int,
    exposed: list[list[int]],
    pins: list[list[int]],
) -> bool:
    """Independent rank test for whether the supplied shares determine S."""
    epochs = len(exposed)
    width = 1 + epochs * (k - 1)
    rows: list[list[int]] = []

    for epoch, coordinates in enumerate(pins):
        for x in coordinates:
            row = [0] * width
            for degree in range(1, k):
                power = pow(x, degree, q)
                row[1 + epoch * (k - 1) + degree - 1] = (-power) % q
                row[1 + (epoch + 1) * (k - 1) + degree - 1] = power
            rows.append(row)

    for epoch, coordinates in enumerate(exposed):
        for x in coordinates:
            row = [0] * width
            row[0] = 1
            for degree in range(1, k):
                row[1 + epoch * (k - 1) + degree - 1] = pow(x, degree, q)
            rows.append(row)

    secret = [1] + [0] * (width - 1)
    return _rank_mod(rows, q) == _rank_mod(rows + [secret], q)


def _all_subsets(n: int) -> list[list[int]]:
    return [
        [coordinate + 1 for coordinate in range(n) if mask >> coordinate & 1]
        for mask in range(1 << n)
    ]


def _flatten_index(values: tuple[int, ...], base: int) -> int:
    result = 0
    for value in values:
        result = result * base + value
    return result


def _exhaustive_universal_case(n: int, k: int, epochs: int, q: int) -> dict:
    """Exhaust every concrete set system and every dominating budget vector."""
    subsets = _all_subsets(n)
    dimensions = 2 * epochs - 1
    base = n + 1
    table_size = base**dimensions
    revealing_exact = bytearray(table_size)
    concrete_count = 0
    revealing_count = 0

    for parts in product(subsets, repeat=dimensions):
        exposed = [list(parts[i]) for i in range(epochs)]
        pins = [list(parts[epochs + i]) for i in range(epochs - 1)]
        concrete_count += 1
        if _pinned_reveals(q, k, exposed, pins):
            revealing_count += 1
            sizes = tuple(map(len, exposed + pins))
            revealing_exact[_flatten_index(sizes, base)] = 1

    # Multidimensional prefix OR: after this pass, entry v records whether a
    # revealing concrete trace exists with component-wise sizes at most v.
    stride = 1
    for _dimension in range(dimensions - 1, -1, -1):
        block = stride * base
        for start in range(0, table_size, block):
            for offset in range(stride):
                for value in range(1, base):
                    index = start + value * stride + offset
                    revealing_exact[index] |= revealing_exact[index - stride]
        stride *= base

    budget_count = 0
    for values in product(range(base), repeat=dimensions):
        exposures = list(values[:epochs])
        pin_budgets = list(values[epochs:])
        predicted = capacities(exposures, pin_budgets)["capacity"] >= k
        observed = bool(revealing_exact[_flatten_index(values, base)])
        if observed != predicted:
            raise AssertionError(
                "universal frontier mismatch: "
                f"n={n}, k={k}, T={epochs}, b={exposures}, u={pin_budgets}"
            )
        budget_count += 1

    return {
        "parties": n,
        "threshold": k,
        "epochs": epochs,
        "field": q,
        "concrete_set_systems": concrete_count,
        "revealing_set_systems": revealing_count,
        "budget_vectors": budget_count,
    }


def _interval_weight(exposures: list[int], pins: list[int], start: int, stop: int) -> int:
    value = sum(exposures[start:stop])
    if start:
        value += pins[start - 1]
    if stop < len(exposures):
        value += pins[stop - 1]
    return value


def _brute_partition_width(exposures: list[int], pins: list[int]) -> int:
    epochs = len(exposures)
    best: int | None = None
    for mask in range(1 << (epochs - 1)):
        cuts = [0] + [e + 1 for e in range(epochs - 1) if mask >> e & 1] + [epochs]
        width = max(
            _interval_weight(exposures, pins, start, stop)
            for start, stop in zip(cuts, cuts[1:])
        )
        if best is None or width < best:
            best = width
    assert best is not None
    return best


def _check_duality(max_epochs: int = 4, maximum_budget: int = 2) -> int:
    checked = 0
    for epochs in range(1, max_epochs + 1):
        for values in product(range(maximum_budget + 1), repeat=2 * epochs - 1):
            exposures = list(values[:epochs])
            pins = list(values[epochs:])
            recurrence = capacities(exposures, pins)["capacity"]
            brute = _brute_partition_width(exposures, pins)
            if recurrence != brute:
                raise AssertionError(
                    f"capacity/partition mismatch: b={exposures}, u={pins}, "
                    f"recurrence={recurrence}, brute={brute}"
                )
            checked += 1
    return checked


def _brute_schedule(
    exposures: list[int],
    pins: list[int],
    threshold: int,
    charges: list[int],
    allowed: list[bool],
) -> tuple[int, list[int]] | None:
    epochs = len(exposures)
    best: tuple[int, list[int]] | None = None
    for mask in range(1 << (epochs - 1)):
        cuts = [0] + [e + 1 for e in range(epochs - 1) if mask >> e & 1] + [epochs]
        if any(not allowed[cut - 1] for cut in cuts[1:-1]):
            continue
        if any(
            _interval_weight(exposures, pins, start, stop) >= threshold
            for start, stop in zip(cuts, cuts[1:])
        ):
            continue
        candidate = (sum(charges[cut - 1] for cut in cuts[1:-1]), cuts)
        if best is None or candidate < best:
            best = candidate
    return best


def _check_scheduler() -> int:
    checked = 0
    for epochs in range(1, 7):
        dimensions = 2 * epochs - 1
        tuple_count = 3**dimensions
        stride = max(1, tuple_count // 150)
        for index, values in enumerate(product(range(3), repeat=dimensions)):
            if index % stride:
                continue
            exposures = list(values[:epochs])
            pins = list(values[epochs:])
            if not any(exposures):
                continue
            charges = [(3 * i + sum(values)) % 5 for i in range(epochs - 1)]
            allowed = [((i + sum(values)) % 3) != 0 for i in range(epochs - 1)]
            for threshold in range(2, 5):
                expected = _brute_schedule(exposures, pins, threshold, charges, allowed)
                actual = minimum_cost_schedule(exposures, pins, threshold, charges, allowed)
                if expected is None:
                    if actual["kind"] != "impossible":
                        raise AssertionError("scheduler accepted a brute-force impossible case")
                elif actual["kind"] != "schedule" or (actual["cost"], actual["cuts"]) != expected:
                    raise AssertionError(
                        "scheduler optimum mismatch: "
                        f"b={exposures}, u={pins}, k={threshold}, charges={charges}, "
                        f"allowed={allowed}, actual={actual}, expected={expected}"
                    )
                checked += 1
    return checked


def run_exhaustive_validation() -> dict:
    universal = [
        _exhaustive_universal_case(2, 2, 4, 5),
        _exhaustive_universal_case(3, 2, 2, 5),
        _exhaustive_universal_case(3, 3, 2, 5),
        _exhaustive_universal_case(4, 3, 2, 5),
        _exhaustive_universal_case(4, 4, 2, 5),
    ]

    closed_form_checks = 0
    for epochs in range(1, 13):
        for exposure in range(5):
            for pin in range(5):
                expected = capacities([exposure] * epochs, [pin] * (epochs - 1))[
                    "capacity"
                ]
                if constant_capacity(epochs, exposure, pin) != expected:
                    raise AssertionError("constant-capacity closed form mismatch")
                closed_form_checks += 1

    fixed_pin_checks = 0
    for epochs in range(1, 6):
        for exposures in product(range(4), repeat=epochs):
            for pin in range(5):
                expected = min(sum(exposures), pin + max(exposures))
                if fixed_pin_capacity(list(exposures), pin) != expected:
                    raise AssertionError("fixed-pin closed form mismatch")
                fixed_pin_checks += 1

    horizon_checks = 0
    for exposure in range(1, 5):
        for pin in range(5):
            for threshold in range(2, 13):
                claimed = largest_safe_constant_horizon(exposure, pin, threshold)
                safe = [
                    epochs
                    for epochs in range(1, 13)
                    if constant_capacity(epochs, exposure, pin) < threshold
                ]
                if claimed is None:
                    if len(safe) != 12:
                        raise AssertionError("unbounded-horizon formula mismatch")
                else:
                    observed = max(safe, default=0)
                    # The bounded scan is decisive whenever the formula is at most 11;
                    # at 12 it also checks the terminal supported horizon directly.
                    if min(claimed, 12) != observed:
                        raise AssertionError("largest-safe-horizon formula mismatch")
                horizon_checks += 1

    return {
        "method": (
            "separate modular-rank implementation over every concrete small set system; "
            "brute-force interval partitions; brute-force permitted refresh subsets"
        ),
        "capacity_partition_vectors": _check_duality(),
        "universal_frontier_families": universal,
        "concrete_set_systems": sum(row["concrete_set_systems"] for row in universal),
        "revealing_set_systems": sum(row["revealing_set_systems"] for row in universal),
        "dominating_budget_vectors": sum(row["budget_vectors"] for row in universal),
        "scheduler_instances": _check_scheduler(),
        "constant_closed_form_checks": closed_form_checks,
        "fixed_pin_closed_form_checks": fixed_pin_checks,
        "horizon_inversion_checks": horizon_checks,
    }
