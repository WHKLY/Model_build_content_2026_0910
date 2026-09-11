"""Question 1 numerical and physical verification helpers."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from q1_data import DELTA_HOUR
from q1_model import (
    POWER_LIMIT_KW,
    SOC_MAX_KWH,
    SOC_MIN_KWH,
    SOC_TERMINAL_KWH,
    IntervalData,
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


def purchase_cost(price: np.ndarray, grid_kwh: np.ndarray) -> float:
    return float(np.dot(price, grid_kwh))


def max_balance_residual(interval_data: IntervalData, solution: ScheduleSolution) -> float:
    residual = (
        solution.grid_kwh
        + interval_data.pv_kwh
        - solution.curtail_kwh
        + solution.discharge_kwh
        - interval_data.load_kwh
        - solution.charge_kwh
    )
    return float(np.max(np.abs(residual)))


def verify_solution(interval_data: IntervalData, solution: ScheduleSolution) -> SolutionCheck:
    if float(np.min(solution.grid_kwh)) < -VERIFY_TOL:
        raise AssertionError("negative grid purchase detected")
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
    if float(np.min(solution.curtail_kwh)) < -VERIFY_TOL:
        raise AssertionError("negative PV curtailment detected")
    if float(np.max(solution.curtail_kwh - interval_data.pv_kwh)) > VERIFY_TOL:
        raise AssertionError("PV curtailment exceeds available PV")

    residual = max_balance_residual(interval_data, solution)
    if residual > 1.0e-5:
        raise AssertionError(f"energy balance residual too large: {residual}")

    return SolutionCheck(
        name=solution.name,
        cost=purchase_cost(interval_data.price, solution.grid_kwh),
        max_balance_residual=residual,
        min_soc=float(np.min(solution.soc_kwh)),
        max_soc=float(np.max(solution.soc_kwh)),
        terminal_soc=float(solution.soc_kwh[-1]),
        max_charge_kwh=float(np.max(solution.charge_kwh)),
        max_discharge_kwh=float(np.max(solution.discharge_kwh)),
        min_curtail_kwh=float(np.min(solution.curtail_kwh)),
    )


def verify_pair(interval_data: IntervalData, plan_a: ScheduleSolution, plan_b: ScheduleSolution) -> dict[str, SolutionCheck]:
    check_a = verify_solution(interval_data, plan_a)
    check_b = verify_solution(interval_data, plan_b)
    if abs(plan_a.cost - plan_b.cost) > VERIFY_TOL:
        raise AssertionError("two schedules do not have equal optimal cost")
    if float(np.max(np.abs(plan_a.grid_kwh - plan_b.grid_kwh))) <= VERIFY_TOL:
        raise AssertionError("purchase schedules are not meaningfully different")
    return {"plan_a": check_a, "plan_b": check_b}
