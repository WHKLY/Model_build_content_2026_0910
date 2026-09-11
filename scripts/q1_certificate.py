"""Generate an exact rational optimality certificate for Question 1."""
from __future__ import annotations

from datetime import datetime, time
from fractions import Fraction
from hashlib import sha256
import json
from math import lcm
from pathlib import Path
from typing import Iterable

import numpy as np
from openpyxl import load_workbook

from q1_data import INTERVAL_COUNT
from q1_model import ScheduleSolution

F = Fraction
ETA_C = F(9, 10)
ETA_D = F(9, 10)
DELTA_HOUR = F(1, 6)
POWER_LIMIT_KW = F(5000)
INTERVAL_LIMIT_KWH = POWER_LIMIT_KW * DELTA_HOUR
SOC_MIN_KWH = F(1200)
SOC_MAX_KWH = F(10800)
SOC_INITIAL_KWH = F(6000)


def _fraction(value: object) -> F:
    if value is None or isinstance(value, bool):
        raise ValueError(f"invalid numeric source value: {value!r}")
    return F(str(value))


def _minute_of_day(value: object) -> int:
    if isinstance(value, (datetime, time)):
        minute = value.hour * 60 + value.minute
        return 1440 if minute == 0 else minute
    if isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0:
        minute = round(float(value) * 1440)
        return 1440 if minute == 0 else minute
    text = str(value).strip().replace(" ", "")
    offset = 1440 if "+1" in text else 0
    fields = text.replace("+1", "").split(":")
    if len(fields) < 2:
        raise ValueError(f"invalid source time label: {value!r}")
    minute = offset + int(fields[0]) * 60 + int(fields[1])
    return 1440 if minute == 0 else minute


def read_exact_source(path: Path) -> tuple[list[F], list[F], list[F]]:
    """Read Attachment 1 as exact decimal fractions."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = [row for row in list(workbook.active.values)[1:] if any(value is not None for value in row)]
    finally:
        workbook.close()

    if len(rows) != INTERVAL_COUNT:
        raise ValueError(f"Attachment 1 must contain {INTERVAL_COUNT} data rows")
    minutes = [_minute_of_day(row[0]) for row in rows]
    if minutes != list(range(10, 1441, 10)):
        raise ValueError("Attachment 1 time labels must be continuous right endpoints from 00:10 to 24:00")

    price = [_fraction(row[1]) for row in rows]
    load = [_fraction(row[2]) * DELTA_HOUR for row in rows]
    pv = [_fraction(row[3]) * DELTA_HOUR for row in rows]
    if not all(value > 0 for value in price):
        raise ValueError("certificate model requires strictly positive prices")
    if not all(value >= 0 for value in load + pv):
        raise ValueError("load and PV values must be nonnegative")
    return price, load, pv


def _constraint_rows(load: list[F], pv: list[F]) -> tuple[list[dict[int, F]], list[F]]:
    rows: list[dict[int, F]] = []
    rhs: list[F] = []
    net = [load_t - pv_t for load_t, pv_t in zip(load, pv)]

    for t in range(INTERVAL_COUNT):
        for slope in (1 / ETA_C, ETA_D):
            row = {t: F(-1), INTERVAL_COUNT + t: slope}
            if t > 0:
                row[INTERVAL_COUNT + t - 1] = -slope
            rows.append(row)
            rhs.append(-net[t] + (slope * SOC_INITIAL_KWH if t == 0 else F(0)))

        for sign, limit in (
            (F(1), ETA_C * INTERVAL_LIMIT_KWH),
            (F(-1), INTERVAL_LIMIT_KWH / ETA_D),
        ):
            row = {INTERVAL_COUNT + t: sign}
            if t > 0:
                row[INTERVAL_COUNT + t - 1] = -sign
            rows.append(row)
            rhs.append(limit + (sign * SOC_INITIAL_KWH if t == 0 else F(0)))
    return rows, rhs


def _variable_bounds(load: list[F]) -> tuple[list[F], list[F]]:
    lower = [F(0)] * INTERVAL_COUNT + [SOC_MIN_KWH] * INTERVAL_COUNT
    # With positive prices, g > load + Pmax*dt is dominated by reducing g.
    upper = [value + INTERVAL_LIMIT_KWH for value in load] + [SOC_MAX_KWH] * INTERVAL_COUNT
    lower[-1] = SOC_INITIAL_KWH
    upper[-1] = SOC_INITIAL_KWH
    return lower, upper


def _state_lattice(load: list[F], pv: list[F]) -> int:
    net = [load_t - pv_t for load_t, pv_t in zip(load, pv)]
    candidates = [
        SOC_MIN_KWH,
        SOC_MAX_KWH,
        SOC_INITIAL_KWH,
        ETA_C * INTERVAL_LIMIT_KWH,
        INTERVAL_LIMIT_KWH / ETA_D,
    ]
    candidates.extend(-ETA_C * value for value in net)
    candidates.extend(-value / ETA_D for value in net)
    denominator = 1
    for value in candidates:
        denominator = lcm(denominator, value.denominator)
    return denominator


def _recover_exact_plan(
    solution: ScheduleSolution,
    price: list[F],
    load: list[F],
    pv: list[F],
    tolerance: float = 1.0e-6,
) -> dict[str, list[F] | F]:
    lattice = _state_lattice(load, pv)
    state = [SOC_INITIAL_KWH]
    state.extend(F(round(float(value) * lattice), lattice) for value in solution.soc_kwh)

    delta = [state[t + 1] - state[t] for t in range(INTERVAL_COUNT)]
    charge = [max(value, F(0)) / ETA_C for value in delta]
    discharge = [ETA_D * max(-value, F(0)) for value in delta]
    grid = [
        max(
            F(0),
            load[t] - pv[t] + delta[t] / ETA_C,
            load[t] - pv[t] + ETA_D * delta[t],
        )
        for t in range(INTERVAL_COUNT)
    ]
    surplus = [
        grid[t] + pv[t] + discharge[t] - load[t] - charge[t]
        for t in range(INTERVAL_COUNT)
    ]

    max_grid_difference = max(abs(float(value) - observed) for value, observed in zip(grid, solution.grid_kwh))
    max_soc_difference = max(abs(float(value) - observed) for value, observed in zip(state[1:], solution.soc_kwh))
    if max_grid_difference > tolerance or max_soc_difference > tolerance:
        raise ValueError(
            "failed to recover the reported schedule as exact fractions: "
            f"grid={max_grid_difference}, soc={max_soc_difference}"
        )
    if state[0] != state[-1] or state[0] != SOC_INITIAL_KWH:
        raise ValueError("exact schedule violates the initial/terminal SOC condition")
    if not all(SOC_MIN_KWH <= value <= SOC_MAX_KWH for value in state):
        raise ValueError("exact schedule violates SOC bounds")
    if not all(-INTERVAL_LIMIT_KWH / ETA_D <= value <= ETA_C * INTERVAL_LIMIT_KWH for value in delta):
        raise ValueError("exact schedule violates charge/discharge power bounds")
    if not all(value >= 0 for value in surplus):
        raise ValueError("exact schedule does not meet load in every interval")

    objective = sum(p * g for p, g in zip(price, grid))
    return {
        "state": state,
        "grid": grid,
        "charge": charge,
        "discharge": discharge,
        "surplus": surplus,
        "objective": objective,
    }


def _dual_bound(
    dual: Iterable[F],
    objective: list[F],
    rows: list[dict[int, F]],
    rhs: list[F],
    lower: list[F],
    upper: list[F],
) -> F:
    residual = objective.copy()
    bound = F(0)
    for multiplier, row, row_rhs in zip(dual, rows, rhs):
        bound += row_rhs * multiplier
        for column, coefficient in row.items():
            residual[column] -= coefficient * multiplier
    bound += sum(min(value * lo, value * hi) for value, lo, hi in zip(residual, lower, upper))
    return bound


def _recover_dual(
    marginals: np.ndarray,
    objective: list[F],
    rows: list[dict[int, F]],
    rhs: list[F],
    lower: list[F],
    upper: list[F],
    primal_value: F,
) -> tuple[list[F], F]:
    values = np.asarray(marginals, dtype=float)
    if values.shape != (4 * INTERVAL_COUNT,) or not np.all(np.isfinite(values)):
        raise ValueError("HiGHS did not return 576 finite inequality marginals")

    candidates: list[tuple[F, list[F]]] = []
    for max_denominator in (10_000, 1_000_000, 100_000_000, 10_000_000_000):
        dual = [min(F(0), F(str(value)).limit_denominator(max_denominator)) for value in values]
        lower_bound = _dual_bound(dual, objective, rows, rhs, lower, upper)
        candidates.append((lower_bound, dual))

    lower_bound, dual = max(candidates, key=lambda item: item[0])
    if lower_bound > primal_value:
        raise ValueError("invalid certificate: dual lower bound exceeds primal value")
    return dual, lower_bound


def build_certificate(
    source_path: Path,
    plan_a: ScheduleSolution,
    inequality_marginals: np.ndarray,
) -> dict[str, object]:
    price, load, pv = read_exact_source(source_path)
    exact = _recover_exact_plan(plan_a, price, load, pv)
    rows, rhs = _constraint_rows(load, pv)
    lower, upper = _variable_bounds(load)
    objective = price + [F(0)] * INTERVAL_COUNT
    z = list(exact["grid"]) + list(exact["state"])[1:]

    if not all(lo <= value <= hi for value, lo, hi in zip(z, lower, upper)):
        raise ValueError("exact plan violates certificate variable bounds")
    for index, (row, row_rhs) in enumerate(zip(rows, rhs), start=1):
        if sum(coefficient * z[column] for column, coefficient in row.items()) > row_rhs:
            raise ValueError(f"exact plan violates LP inequality {index}")

    upper_bound = exact["objective"]
    dual, lower_bound = _recover_dual(
        inequality_marginals,
        objective,
        rows,
        rhs,
        lower,
        upper,
        upper_bound,
    )
    gap = upper_bound - lower_bound
    certificate = {
        "format": "microgrid-q1-rational-certificate-v1",
        "input_file": source_path.name,
        "input_sha256": sha256(source_path.read_bytes()).hexdigest(),
        "model": {
            "interval_count": INTERVAL_COUNT,
            "interval_hours": str(DELTA_HOUR),
            "charge_efficiency": str(ETA_C),
            "discharge_efficiency": str(ETA_D),
            "power_limit_kw": str(POWER_LIMIT_KW),
            "soc_min_kwh": str(SOC_MIN_KWH),
            "soc_max_kwh": str(SOC_MAX_KWH),
            "initial_terminal_soc_kwh": str(SOC_INITIAL_KWH),
            "time_interpretation": "10-minute right endpoints; physical intervals 00:00-00:10 through 23:50-24:00",
            "energy_balance": "supply must be at least load; unused surplus has no revenue",
            "certificate_grid_bound": "g_t <= load_t + Pmax*dt; redundant for positive prices",
        },
        "price": [str(value) for value in price],
        "load_energy": [str(value) for value in load],
        "pv_energy": [str(value) for value in pv],
        "state": [str(value) for value in exact["state"]],
        "grid": [str(value) for value in exact["grid"]],
        "dual_inequality_multipliers": [str(value) for value in dual],
        "upper_bound": str(upper_bound),
        "lower_bound": str(lower_bound),
        "gap": str(gap),
        "exact_optimal": gap == 0,
    }
    if not certificate["exact_optimal"]:
        raise ValueError(f"rational certificate gap is not zero: {gap}")
    return certificate


def write_certificate(path: Path, certificate: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(certificate, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
