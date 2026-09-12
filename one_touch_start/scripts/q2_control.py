"""Causal real-time replay for a frozen Question 2 day-ahead plan."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, diags, hstack, vstack

from q2_model import Q2Config


def _mpc_first_action(
    net_forecast_kwh: np.ndarray,
    price_yuan_per_kwh: np.ndarray,
    frozen_plan_kwh: np.ndarray,
    initial_soc_kwh: float,
    config: Q2Config,
    terminal_free: bool = False,
) -> tuple[float, float]:
    """Solve the remaining horizon and return only the first charge/discharge."""

    net = np.asarray(net_forecast_kwh, dtype=float)
    price = np.asarray(price_yuan_per_kwh, dtype=float)
    plan = np.asarray(frozen_plan_kwh, dtype=float)
    horizon = len(net)
    if not (len(price) == len(plan) == horizon and horizon > 0):
        raise ValueError("Real-time horizon arrays have inconsistent lengths")
    surplus = np.maximum(plan - net, 0.0)
    deficit = np.maximum(net - plan, 0.0)
    upper_delta = config.eta_c * np.minimum(config.interval_limit_kwh, surplus)
    lower_delta = -np.minimum(config.interval_limit_kwh, deficit) / config.eta_d

    difference = diags(
        [np.ones(horizon), -np.ones(max(horizon - 1, 0))],
        [0, -1],
        shape=(horizon, horizon),
        format="csr",
    )
    initial = np.zeros(horizon)
    initial[0] = initial_soc_kwh
    emergency_saving = (
        config.emergency_multiplier
        * price
        * config.eta_d
        * (deficit > 0)
    )
    state_cost = np.asarray(difference.T @ emergency_saving).ravel()
    objective = np.r_[
        state_cost,
        0.0 if terminal_free else config.terminal_penalty_yuan_per_kwh,
    ]
    zero_column = csr_matrix((horizon, 1))
    terminal = csr_matrix(
        ([-1.0, -1.0], ([0, 0], [horizon - 1, horizon])),
        shape=(1, horizon + 1),
    )
    constraints = vstack(
        [
            hstack([difference, zero_column]),
            hstack([-difference, zero_column]),
            terminal,
        ],
        format="csr",
    )
    upper_bounds = np.r_[
        upper_delta + initial,
        -lower_delta - initial,
        -config.reference_soc_kwh,
    ]
    result = linprog(
        objective,
        A_ub=constraints,
        b_ub=upper_bounds,
        bounds=[(config.soc_min_kwh, config.soc_max_kwh)] * horizon
        + [(0.0, None)],
        method="highs",
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"Real-time LP failed: {result.message}")
    state_change = float(result.x[0] - initial_soc_kwh)
    charge = max(state_change, 0.0) / config.eta_c
    discharge = config.eta_d * max(-state_change, 0.0)
    return charge, discharge


def simulate_frozen_plan_day(
    actual_load_kwh: np.ndarray,
    actual_pv_kwh: np.ndarray,
    forecast_load_kwh: np.ndarray,
    forecast_pv_kwh: np.ndarray,
    price_yuan_per_kwh: np.ndarray,
    plan_kwh: np.ndarray,
    initial_soc_kwh: float,
    physical_intervals: tuple[str, ...],
    config: Q2Config,
    terminal_free: bool = False,
) -> pd.DataFrame:
    """Replay one day without changing its day-ahead purchase schedule."""

    actual_load = np.asarray(actual_load_kwh, dtype=float)
    actual_pv = np.asarray(actual_pv_kwh, dtype=float)
    forecast_load = np.asarray(forecast_load_kwh, dtype=float)
    forecast_pv = np.asarray(forecast_pv_kwh, dtype=float)
    price = np.asarray(price_yuan_per_kwh, dtype=float)
    plan = np.asarray(plan_kwh, dtype=float).copy()
    arrays = (actual_load, actual_pv, forecast_load, forecast_pv, price, plan)
    if len({array.shape for array in arrays}) != 1 or actual_load.ndim != 1:
        raise ValueError("Replay arrays must be equal-length vectors")
    if len(physical_intervals) != len(actual_load):
        raise ValueError("Physical interval labels do not match the replay horizon")
    if not np.isfinite(np.concatenate(arrays)).all():
        raise ValueError("Replay arrays contain non-finite values")
    if np.any(actual_load < 0) or np.any(actual_pv < 0) or np.any(plan < 0):
        raise ValueError("Load, photovoltaic energy, and plan must be nonnegative")

    frozen_plan = plan.copy()
    state = float(initial_soc_kwh)
    records: list[dict[str, float | int | str]] = []
    for interval in range(len(actual_load)):
        future_net = (forecast_load[interval:] - forecast_pv[interval:]).copy()
        future_net[0] = actual_load[interval] - actual_pv[interval]
        charge, discharge = _mpc_first_action(
            future_net,
            price[interval:],
            plan[interval:],
            state,
            config,
            terminal_free,
        )
        surplus = max(plan[interval] + actual_pv[interval] - actual_load[interval], 0.0)
        deficit = max(actual_load[interval] - actual_pv[interval] - plan[interval], 0.0)
        charge = min(
            max(charge, 0.0),
            config.interval_limit_kwh,
            surplus,
            max((config.soc_max_kwh - state) / config.eta_c, 0.0),
        )
        discharge = min(
            max(discharge, 0.0),
            config.interval_limit_kwh,
            deficit,
            max((state - config.soc_min_kwh) * config.eta_d, 0.0),
        )
        emergency = max(deficit - discharge, 0.0)
        served_before_inputs = actual_load[interval] + charge - discharge - emergency
        pv_used = min(actual_pv[interval], max(served_before_inputs, 0.0))
        plan_used = max(served_before_inputs - pv_used, 0.0)
        next_state = state + config.eta_c * charge - discharge / config.eta_d
        plan_cost = price[interval] * plan[interval]
        emergency_cost = (
            config.emergency_multiplier * price[interval] * emergency
        )
        records.append(
            {
                "t": interval,
                "interval": physical_intervals[interval],
                "price_yuan_per_kwh": price[interval],
                "load_kwh": actual_load[interval],
                "pv_kwh": actual_pv[interval],
                "load_hat_kwh": forecast_load[interval],
                "pv_hat_kwh": forecast_pv[interval],
                "plan_kwh": plan[interval],
                "charge_kwh": charge,
                "discharge_kwh": discharge,
                "emergency_kwh": emergency,
                "pv_used_kwh": pv_used,
                "plan_used_kwh": plan_used,
                "curtailment_kwh": max(actual_pv[interval] - pv_used, 0.0),
                "unused_plan_kwh": max(plan[interval] - plan_used, 0.0),
                "soc_start_kwh": state,
                "soc_end_kwh": next_state,
                "plan_cost_yuan": plan_cost,
                "emergency_cost_yuan": emergency_cost,
                "total_cost_yuan": plan_cost + emergency_cost,
            }
        )
        state = next_state
    if not np.array_equal(plan, frozen_plan):
        raise AssertionError("The day-ahead purchase plan changed during replay")
    return pd.DataFrame.from_records(records)
