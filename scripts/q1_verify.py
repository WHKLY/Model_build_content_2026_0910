"""Question 1 numerical and physical verification helpers."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from q1_data import DELTA_HOUR, INTERVAL_COUNT
from q1_model import (
    CHARGE_EFFICIENCY,
    DISCHARGE_EFFICIENCY,
    POWER_LIMIT_KW,
    SOC_INITIAL_KWH,
    SOC_MAX_KWH,
    SOC_MIN_KWH,
    SOC_TERMINAL_KWH,
    IntervalData,
    LinearProgram,
    ScheduleSolution,
)

VERIFY_TOL = 1.0e-6


@dataclass(frozen=True)
class SolutionCheck:
    name: str
    cost: float
    max_balance_residual: float
    min_soc: float
    max_soc: float
    terminal_soc: float
    max_charge_kwh: float
    max_discharge_kwh: float
    min_curtail_kwh: float
    max_soc_recurrence_residual: float
    max_charge_recovery_residual: float
    max_discharge_recovery_residual: float
    max_simultaneous_charge_discharge_kwh: float
    max_lp_ub_violation: float
    max_lp_eq_residual: float
    max_bound_violation: float


def _require_finite(name: str, values: np.ndarray) -> None:
    if not np.all(np.isfinite(values)):
        raise AssertionError(f"{name} contains NaN or infinite values")


def validate_interval_data(interval_data: IntervalData) -> None:
    fields = {
        "price": interval_data.price,
        "load_kw": interval_data.load_kw,
        "pv_kw": interval_data.pv_kw,
        "load_kwh": interval_data.load_kwh,
        "pv_kwh": interval_data.pv_kwh,
        "net_kwh": interval_data.net_kwh,
    }
    for name, values in fields.items():
        if len(values) != INTERVAL_COUNT:
            raise AssertionError(f"{name} length must be {INTERVAL_COUNT}")
        _require_finite(name, values)
    if float(np.min(interval_data.price)) < -VERIFY_TOL:
        raise AssertionError("negative price detected")
    if float(np.min(interval_data.load_kw)) < -VERIFY_TOL:
        raise AssertionError("negative load detected")
    if float(np.min(interval_data.pv_kw)) < -VERIFY_TOL:
        raise AssertionError("negative PV forecast detected")


def purchase_cost(price: np.ndarray, grid_kwh: np.ndarray) -> float:
    return float(np.dot(price, grid_kwh))


def balance_residual(interval_data: IntervalData, solution: ScheduleSolution) -> np.ndarray:
    return (
        solution.grid_kwh
        + interval_data.pv_kwh
        - solution.curtail_kwh
        + solution.discharge_kwh
        - interval_data.load_kwh
        - solution.charge_kwh
    )


def _max_lp_ub_violation(lp: LinearProgram, z: np.ndarray) -> float:
    return float(np.max(np.maximum(lp.a_ub @ z - lp.b_ub, 0.0)))


def _max_lp_eq_residual(lp: LinearProgram, z: np.ndarray) -> float:
    return float(np.max(np.abs(lp.a_eq @ z - lp.b_eq)))


def _max_bound_violation(lp: LinearProgram, z: np.ndarray) -> float:
    violations: list[float] = []
    for value, (lower, upper) in zip(z, lp.bounds):
        if lower is not None:
            violations.append(max(lower - value, 0.0))
        if upper is not None:
            violations.append(max(value - upper, 0.0))
    return float(max(violations) if violations else 0.0)


def verify_solution(interval_data: IntervalData, solution: ScheduleSolution, lp: LinearProgram | None = None) -> SolutionCheck:
    validate_interval_data(interval_data)

    arrays = {
        "z": solution.z,
        "grid_kwh": solution.grid_kwh,
        "soc_kwh": solution.soc_kwh,
        "internal_delta_kwh": solution.internal_delta_kwh,
        "charge_kwh": solution.charge_kwh,
        "discharge_kwh": solution.discharge_kwh,
        "curtail_kwh": solution.curtail_kwh,
    }
    for name, values in arrays.items():
        if len(values) not in (INTERVAL_COUNT, 2 * INTERVAL_COUNT):
            raise AssertionError(f"{solution.name} {name} has unexpected length")
        _require_finite(f"{solution.name} {name}", values)

    previous_soc = np.concatenate(([SOC_INITIAL_KWH], solution.soc_kwh[:-1]))
    recovered_delta = solution.soc_kwh - previous_soc
    recovered_charge = np.maximum(recovered_delta, 0.0) / CHARGE_EFFICIENCY
    recovered_discharge = DISCHARGE_EFFICIENCY * np.maximum(-recovered_delta, 0.0)

    soc_recurrence_residual = float(np.max(np.abs(solution.internal_delta_kwh - recovered_delta)))
    charge_recovery_residual = float(np.max(np.abs(solution.charge_kwh - recovered_charge)))
    discharge_recovery_residual = float(np.max(np.abs(solution.discharge_kwh - recovered_discharge)))
    simultaneous = float(np.max(np.minimum(solution.charge_kwh, solution.discharge_kwh)))

    if soc_recurrence_residual > VERIFY_TOL:
        raise AssertionError("SOC recurrence and internal delta disagree")
    if charge_recovery_residual > VERIFY_TOL:
        raise AssertionError("charge recovery from SOC delta failed")
    if discharge_recovery_residual > VERIFY_TOL:
        raise AssertionError("discharge recovery from SOC delta failed")
    if simultaneous > VERIFY_TOL:
        raise AssertionError("simultaneous charge and discharge detected")

    if float(np.min(solution.grid_kwh)) < -VERIFY_TOL:
        raise AssertionError("negative grid purchase detected")
    if float(np.min(solution.charge_kwh)) < -VERIFY_TOL:
        raise AssertionError("negative charge detected")
    if float(np.min(solution.discharge_kwh)) < -VERIFY_TOL:
        raise AssertionError("negative discharge detected")
    if float(np.min(solution.soc_kwh)) < SOC_MIN_KWH - VERIFY_TOL:
        raise AssertionError("SOC lower bound violated")
    if float(np.max(solution.soc_kwh)) > SOC_MAX_KWH + VERIFY_TOL:
        raise AssertionError("SOC upper bound violated")
    if abs(float(solution.soc_kwh[-1]) - SOC_TERMINAL_KWH) > VERIFY_TOL:
        raise AssertionError("terminal SOC violated")

    power_limit_kwh = POWER_LIMIT_KW * DELTA_HOUR
    if float(np.max(solution.charge_kwh)) > power_limit_kwh + VERIFY_TOL:
        raise AssertionError("charge power limit violated")
    if float(np.max(solution.discharge_kwh)) > power_limit_kwh + VERIFY_TOL:
        raise AssertionError("discharge power limit violated")
    if float(np.max(solution.discharge_kwh - interval_data.load_kwh)) > VERIFY_TOL:
        raise AssertionError("discharge exceeds same-interval load")
    if float(np.min(solution.curtail_kwh)) < -VERIFY_TOL:
        raise AssertionError("negative PV curtailment detected")
    if float(np.max(solution.curtail_kwh - interval_data.pv_kwh)) > VERIFY_TOL:
        raise AssertionError("PV curtailment exceeds available PV")

    residual = float(np.max(np.abs(balance_residual(interval_data, solution))))
    if residual > 1.0e-5:
        raise AssertionError(f"energy balance residual too large: {residual}")

    recomputed_cost = purchase_cost(interval_data.price, solution.grid_kwh)
    if abs(recomputed_cost - solution.cost) > 1.0e-5:
        raise AssertionError("reported cost does not match recomputed purchase cost")

    lp_ub = _max_lp_ub_violation(lp, solution.z) if lp is not None else 0.0
    lp_eq = _max_lp_eq_residual(lp, solution.z) if lp is not None else 0.0
    bound = _max_bound_violation(lp, solution.z) if lp is not None else 0.0
    if lp_ub > 1.0e-5:
        raise AssertionError(f"LP inequality violation too large: {lp_ub}")
    if lp_eq > 1.0e-5:
        raise AssertionError(f"LP equality residual too large: {lp_eq}")
    if bound > 1.0e-5:
        raise AssertionError(f"LP bound violation too large: {bound}")

    return SolutionCheck(
        name=solution.name,
        cost=recomputed_cost,
        max_balance_residual=residual,
        min_soc=float(np.min(solution.soc_kwh)),
        max_soc=float(np.max(solution.soc_kwh)),
        terminal_soc=float(solution.soc_kwh[-1]),
        max_charge_kwh=float(np.max(solution.charge_kwh)),
        max_discharge_kwh=float(np.max(solution.discharge_kwh)),
        min_curtail_kwh=float(np.min(solution.curtail_kwh)),
        max_soc_recurrence_residual=soc_recurrence_residual,
        max_charge_recovery_residual=charge_recovery_residual,
        max_discharge_recovery_residual=discharge_recovery_residual,
        max_simultaneous_charge_discharge_kwh=simultaneous,
        max_lp_ub_violation=lp_ub,
        max_lp_eq_residual=lp_eq,
        max_bound_violation=bound,
    )


def verify_pair(
    interval_data: IntervalData,
    plan_a: ScheduleSolution,
    plan_b: ScheduleSolution,
    lp: LinearProgram | None = None,
) -> dict[str, SolutionCheck]:
    check_a = verify_solution(interval_data, plan_a, lp)
    check_b = verify_solution(interval_data, plan_b, lp)
    if abs(plan_a.cost - plan_b.cost) > VERIFY_TOL:
        raise AssertionError("two schedules do not have equal optimal cost")
    if float(np.max(np.abs(plan_a.grid_kwh - plan_b.grid_kwh))) <= VERIFY_TOL:
        raise AssertionError("purchase schedules are not meaningfully different")
    return {"plan_a": check_a, "plan_b": check_b}
