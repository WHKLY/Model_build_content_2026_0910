"""Question 1 deterministic battery scheduling model."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog

from q1_data import DELTA_HOUR, INTERVAL_COUNT, Q1SourceData

BATTERY_CAPACITY_KWH = 12000.0
SOC_MIN_KWH = 1200.0
SOC_MAX_KWH = 10800.0
SOC_INITIAL_KWH = 6000.0
SOC_TERMINAL_KWH = 6000.0
CHARGE_EFFICIENCY = 0.9
DISCHARGE_EFFICIENCY = 0.9
POWER_LIMIT_KW = 5000.0


@dataclass(frozen=True)
class IntervalData:
    price: np.ndarray
    load_kw: np.ndarray
    pv_kw: np.ndarray
    load_kwh: np.ndarray
    pv_kwh: np.ndarray
    net_kwh: np.ndarray


@dataclass(frozen=True)
class LinearProgram:
    objective: np.ndarray
    a_ub: np.ndarray
    b_ub: np.ndarray
    a_eq: np.ndarray
    b_eq: np.ndarray
    bounds: list[tuple[float | None, float | None]]


@dataclass(frozen=True)
class ScheduleSolution:
    name: str
    z: np.ndarray
    grid_kwh: np.ndarray
    soc_kwh: np.ndarray
    internal_delta_kwh: np.ndarray
    charge_kwh: np.ndarray
    discharge_kwh: np.ndarray
    curtail_kwh: np.ndarray
    cost: float
    total_grid_kwh: float
    total_charge_kwh: float
    total_discharge_kwh: float
    total_curtail_kwh: float
    target_index: int | None = None
    target_grid_kwh: float | None = None
    solver_status: int | None = None
    solver_message: str | None = None


@dataclass(frozen=True)
class BaselineSolution:
    name: str
    grid_kwh: np.ndarray
    curtail_kwh: np.ndarray
    cost: float
    total_grid_kwh: float
    total_curtail_kwh: float


def energy_from_power_kw(power_kw: np.ndarray) -> np.ndarray:
    return np.asarray(power_kw, dtype=float) * DELTA_HOUR


def prepare_interval_data(source: Q1SourceData) -> IntervalData:
    if len(source.price_yuan_per_kwh) != INTERVAL_COUNT:
        raise ValueError("price length must be 144")
    load_kwh = energy_from_power_kw(source.load_kw)
    pv_kwh = energy_from_power_kw(source.pv_forecast_kw)
    return IntervalData(
        price=np.asarray(source.price_yuan_per_kwh, dtype=float),
        load_kw=np.asarray(source.load_kw, dtype=float),
        pv_kw=np.asarray(source.pv_forecast_kw, dtype=float),
        load_kwh=load_kwh,
        pv_kwh=pv_kwh,
        net_kwh=load_kwh - pv_kwh,
    )


def grid_index(t: int) -> int:
    return t


def soc_index(t: int) -> int:
    return INTERVAL_COUNT + t


def variable_count() -> int:
    return 2 * INTERVAL_COUNT


def charge_internal_limit_kwh() -> float:
    return POWER_LIMIT_KW * DELTA_HOUR * CHARGE_EFFICIENCY


def build_lp(interval_data: IntervalData) -> LinearProgram:
    nvars = variable_count()
    objective = np.zeros(nvars)
    objective[:INTERVAL_COUNT] = interval_data.price

    a_ub = np.zeros((4 * INTERVAL_COUNT, nvars))
    b_ub = np.zeros(4 * INTERVAL_COUNT)
    charge_upper = charge_internal_limit_kwh()
    ac_discharge_limit = POWER_LIMIT_KW * DELTA_HOUR

    row = 0
    for t in range(INTERVAL_COUNT):
        g = grid_index(t)
        s = soc_index(t)
        previous_s = soc_index(t - 1) if t > 0 else None
        net = interval_data.net_kwh[t]

        # g_t >= n_t + x_t / eta_c
        a_ub[row, g] = -1.0
        a_ub[row, s] = 1.0 / CHARGE_EFFICIENCY
        if previous_s is None:
            b_ub[row] = -net + SOC_INITIAL_KWH / CHARGE_EFFICIENCY
        else:
            a_ub[row, previous_s] = -1.0 / CHARGE_EFFICIENCY
            b_ub[row] = -net
        row += 1

        # g_t >= n_t + eta_d * x_t
        a_ub[row, g] = -1.0
        a_ub[row, s] = DISCHARGE_EFFICIENCY
        if previous_s is None:
            b_ub[row] = -net + DISCHARGE_EFFICIENCY * SOC_INITIAL_KWH
        else:
            a_ub[row, previous_s] = -DISCHARGE_EFFICIENCY
            b_ub[row] = -net
        row += 1

        # x_t <= eta_c * Pmax * dt
        a_ub[row, s] = 1.0
        if previous_s is None:
            b_ub[row] = charge_upper + SOC_INITIAL_KWH
        else:
            a_ub[row, previous_s] = -1.0
            b_ub[row] = charge_upper
        row += 1

        # x_t >= -min(Pmax*dt, load_t) / eta_d
        discharge_lower = -min(ac_discharge_limit, interval_data.load_kwh[t]) / DISCHARGE_EFFICIENCY
        a_ub[row, s] = -1.0
        if previous_s is None:
            b_ub[row] = -discharge_lower - SOC_INITIAL_KWH
        else:
            a_ub[row, previous_s] = 1.0
            b_ub[row] = -discharge_lower
        row += 1

    a_eq = np.zeros((1, nvars))
    a_eq[0, soc_index(INTERVAL_COUNT - 1)] = 1.0
    b_eq = np.array([SOC_TERMINAL_KWH])

    bounds: list[tuple[float | None, float | None]] = [(0.0, None) for _ in range(nvars)]
    for t in range(INTERVAL_COUNT):
        bounds[soc_index(t)] = (SOC_MIN_KWH, SOC_MAX_KWH)

    return LinearProgram(objective, a_ub, b_ub, a_eq, b_eq, bounds)


def solve_lp(
    lp: LinearProgram,
    *,
    objective: np.ndarray | None = None,
    a_eq: np.ndarray | None = None,
    b_eq: np.ndarray | None = None,
    name: str,
):
    result = linprog(
        c=lp.objective if objective is None else objective,
        A_ub=lp.a_ub,
        b_ub=lp.b_ub,
        A_eq=lp.a_eq if a_eq is None else a_eq,
        b_eq=lp.b_eq if b_eq is None else b_eq,
        bounds=lp.bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"linprog failed for {name}: {result.message}")
    return result


def recover_solution(z: np.ndarray, interval_data: IntervalData, *, name: str) -> ScheduleSolution:
    grid_kwh = np.asarray(z[:INTERVAL_COUNT], dtype=float)
    soc_kwh = np.asarray(z[INTERVAL_COUNT:], dtype=float)
    previous_soc = np.concatenate(([SOC_INITIAL_KWH], soc_kwh[:-1]))
    internal_delta = soc_kwh - previous_soc
    charge_kwh = np.maximum(internal_delta, 0.0) / CHARGE_EFFICIENCY
    discharge_kwh = DISCHARGE_EFFICIENCY * np.maximum(-internal_delta, 0.0)
    curtail_kwh = grid_kwh + interval_data.pv_kwh + discharge_kwh - interval_data.load_kwh - charge_kwh
    return ScheduleSolution(
        name=name,
        z=np.asarray(z, dtype=float),
        grid_kwh=grid_kwh,
        soc_kwh=soc_kwh,
        internal_delta_kwh=internal_delta,
        charge_kwh=charge_kwh,
        discharge_kwh=discharge_kwh,
        curtail_kwh=curtail_kwh,
        cost=float(np.dot(interval_data.price, grid_kwh)),
        total_grid_kwh=float(np.sum(grid_kwh)),
        total_charge_kwh=float(np.sum(charge_kwh)),
        total_discharge_kwh=float(np.sum(discharge_kwh)),
        total_curtail_kwh=float(np.sum(curtail_kwh)),
    )


def solve_primary(interval_data: IntervalData) -> tuple[ScheduleSolution, LinearProgram]:
    lp = build_lp(interval_data)
    result = solve_lp(lp, name="primary-cost")
    solution = recover_solution(result.x, interval_data, name="primary-cost")
    return solution.__class__(**{**solution.__dict__, "solver_status": result.status, "solver_message": result.message}), lp


def solve_at_same_cost(
    interval_data: IntervalData,
    lp: LinearProgram,
    optimal_cost: float,
    *,
    target_index: int = 140,
    sense: str = "min",
) -> ScheduleSolution:
    if not 1 <= target_index <= INTERVAL_COUNT:
        raise ValueError("target_index is one-based and must be between 1 and 144")

    nvars = variable_count()
    objective = np.zeros(nvars)
    target_zero_based = target_index - 1
    objective[grid_index(target_zero_based)] = -1.0 if sense == "max" else 1.0

    cost_row = lp.objective.reshape(1, nvars)
    a_eq = np.vstack([lp.a_eq, cost_row])
    b_eq = np.concatenate([lp.b_eq, [optimal_cost]])
    result = solve_lp(lp, objective=objective, a_eq=a_eq, b_eq=b_eq, name=f"{sense}-g{target_index}")
    solname = f"plan_B_max_g{target_index}" if sense == "max" else f"plan_A_min_g{target_index}"
    solution = recover_solution(result.x, interval_data, name=solname)
    return solution.__class__(
        **{
            **solution.__dict__,
            "target_index": target_index,
            "target_grid_kwh": float(solution.grid_kwh[target_zero_based]),
            "solver_status": result.status,
            "solver_message": result.message,
        }
    )


def no_storage_baseline(interval_data: IntervalData) -> BaselineSolution:
    grid_kwh = np.maximum(interval_data.net_kwh, 0.0)
    curtail_kwh = np.maximum(-interval_data.net_kwh, 0.0)
    return BaselineSolution(
        name="no_storage",
        grid_kwh=grid_kwh,
        curtail_kwh=curtail_kwh,
        cost=float(np.dot(interval_data.price, grid_kwh)),
        total_grid_kwh=float(np.sum(grid_kwh)),
        total_curtail_kwh=float(np.sum(curtail_kwh)),
    )
