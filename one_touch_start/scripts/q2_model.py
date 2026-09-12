"""Question 2 day-ahead conflict-driven incremental MILP."""
from __future__ import annotations

from dataclasses import dataclass, replace
from time import perf_counter
from typing import Iterable

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix, csr_matrix


DELTA_HOUR = 1.0 / 6.0


@dataclass(frozen=True)
class Q2Config:
    eta_c: float = 0.9
    eta_d: float = 0.9
    soc_min_kwh: float = 1200.0
    soc_max_kwh: float = 10800.0
    power_max_kw: float = 5000.0
    initial_soc_kwh: float = 6000.0
    reference_soc_kwh: float = 6000.0
    terminal_penalty_yuan_per_kwh: float = 0.5
    emergency_multiplier: float = 5.0
    forecast_window_days: int = 7
    scenario_history_days: int = 28
    scenario_count: int = 20
    random_seed: int = 20260911
    residual_scale: float = 1.0
    mip_time_limit_seconds: float = 30.0
    mip_relative_gap: float = 1.0e-3
    energy_tolerance_kwh: float = 2.0e-5
    max_incremental_rounds: int = 8
    activation_scope: str = "scenario"

    @property
    def interval_limit_kwh(self) -> float:
        return self.power_max_kw * DELTA_HOUR

    def validate(self) -> "Q2Config":
        numeric = np.asarray(
            [
                self.eta_c,
                self.eta_d,
                self.soc_min_kwh,
                self.soc_max_kwh,
                self.power_max_kw,
                self.initial_soc_kwh,
                self.reference_soc_kwh,
                self.terminal_penalty_yuan_per_kwh,
                self.emergency_multiplier,
                self.forecast_window_days,
                self.scenario_history_days,
                self.scenario_count,
                self.random_seed,
                self.residual_scale,
                self.mip_time_limit_seconds,
                self.mip_relative_gap,
                self.energy_tolerance_kwh,
                self.max_incremental_rounds,
            ],
            dtype=float,
        )
        if not np.isfinite(numeric).all():
            raise ValueError("All Question 2 configuration values must be finite")
        if not (0 < self.eta_c <= 1 and 0 < self.eta_d <= 1):
            raise ValueError("Charge and discharge efficiencies must be in (0, 1]")
        if not (0 <= self.soc_min_kwh < self.soc_max_kwh):
            raise ValueError("Invalid SOC bounds")
        if not self.soc_min_kwh <= self.initial_soc_kwh <= self.soc_max_kwh:
            raise ValueError("Initial SOC is outside its bounds")
        if not self.soc_min_kwh <= self.reference_soc_kwh <= self.soc_max_kwh:
            raise ValueError("Reference SOC is outside its bounds")
        if self.power_max_kw <= 0 or self.emergency_multiplier <= 1:
            raise ValueError("Power limit or emergency multiplier is invalid")
        if min(
            self.forecast_window_days,
            self.scenario_history_days,
            self.scenario_count,
            self.max_incremental_rounds,
        ) < 1:
            raise ValueError("Forecast, scenario, and iteration counts must be positive")
        if self.mip_time_limit_seconds <= 0 or self.mip_relative_gap < 0:
            raise ValueError("MILP stopping settings are invalid")
        if self.activation_scope not in {"scenario", "pair", "interval"}:
            raise ValueError("Unknown conflict activation scope")
        return self


@dataclass(frozen=True)
class ModelLayout:
    scenario_count: int
    interval_count: int
    q: np.ndarray
    soc: np.ndarray
    emergency: np.ndarray
    terminal_shortfall: np.ndarray
    binary_by_pair: dict[tuple[int, int], int]
    variable_count: int


@dataclass(frozen=True)
class BuiltModel:
    objective: np.ndarray
    lower_bounds: np.ndarray
    upper_bounds: np.ndarray
    constraints: csr_matrix
    constraint_upper_bounds: np.ndarray
    integrality: np.ndarray
    layout: ModelLayout
    build_seconds: float


@dataclass(frozen=True)
class PlanSolution:
    method: str
    solver_success: bool
    status_code: int
    message: str
    objective_yuan: float
    dual_bound_yuan: float
    relative_gap: float
    build_seconds: float
    solve_seconds: float
    plan_kwh: np.ndarray
    scenario_soc_kwh: np.ndarray
    scenario_emergency_kwh: np.ndarray
    scenario_charge_kwh: np.ndarray
    scenario_discharge_kwh: np.ndarray
    conflicts: tuple[tuple[int, int], ...]
    active_binary_count: int
    node_count: int
    max_constraint_violation: float

    @property
    def has_feasible_solution(self) -> bool:
        return np.isfinite(self.objective_yuan) and not self.conflicts


@dataclass(frozen=True)
class IncrementalPlan:
    relaxation: PlanSolution
    solution: PlanSolution
    rounds: int
    binary_history: tuple[int, ...]
    total_build_seconds: float
    total_solve_seconds: float


def _validate_inputs(
    load_scenarios: np.ndarray,
    pv_scenarios: np.ndarray,
    weights: np.ndarray,
    price: np.ndarray,
    initial_soc_kwh: float,
    config: Q2Config,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    config.validate()
    load = np.atleast_2d(np.asarray(load_scenarios, dtype=float))
    pv = np.atleast_2d(np.asarray(pv_scenarios, dtype=float))
    probability = np.asarray(weights, dtype=float)
    price = np.asarray(price, dtype=float)
    if load.shape != pv.shape or load.ndim != 2 or load.shape[1] != len(price):
        raise ValueError("Scenario and price dimensions do not match")
    if len(probability) != load.shape[0] or np.any(probability < 0):
        raise ValueError("Scenario probabilities are invalid")
    if not np.isclose(probability.sum(), 1.0):
        raise ValueError("Scenario probabilities must sum to one")
    if not np.isfinite(load).all() or not np.isfinite(pv).all():
        raise ValueError("Scenario data must be finite")
    if np.any(load < 0) or np.any(pv < 0) or np.any(price <= 0):
        raise ValueError("Scenario energy must be nonnegative and price positive")
    if not config.soc_min_kwh <= initial_soc_kwh <= config.soc_max_kwh:
        raise ValueError("Initial SOC is outside its bounds")
    return load, pv, probability, price


def _sparse_matrix(
    rows: list[int],
    columns: list[int],
    values: list[float],
    right_hand_side: list[float],
    variable_count: int,
) -> csr_matrix:
    return coo_matrix(
        (values, (rows, columns)),
        shape=(len(right_hand_side), variable_count),
    ).tocsr()


def build_day_ahead_model(
    load_scenarios: np.ndarray,
    pv_scenarios: np.ndarray,
    weights: np.ndarray,
    price: np.ndarray,
    initial_soc_kwh: float,
    config: Q2Config,
    active_binary_pairs: Iterable[tuple[int, int]] = (),
    terminal_free: bool = False,
) -> BuiltModel:
    started = perf_counter()
    load, pv, probability, price = _validate_inputs(
        load_scenarios,
        pv_scenarios,
        weights,
        price,
        initial_soc_kwh,
        config,
    )
    scenario_count, interval_count = load.shape
    pair_count = scenario_count * interval_count
    q = np.arange(interval_count)
    soc = interval_count + np.arange(pair_count).reshape(scenario_count, interval_count)
    emergency = interval_count + pair_count + np.arange(pair_count).reshape(
        scenario_count, interval_count
    )
    terminal_shortfall = interval_count + 2 * pair_count + np.arange(scenario_count)
    continuous_count = interval_count + 2 * pair_count + scenario_count

    pairs = tuple(sorted(set(active_binary_pairs)))
    for scenario, interval in pairs:
        if not (0 <= scenario < scenario_count and 0 <= interval < interval_count):
            raise ValueError(f"Invalid binary pair {(scenario, interval)}")
    binary_by_pair = {
        pair: continuous_count + offset for offset, pair in enumerate(pairs)
    }
    variable_count = continuous_count + len(pairs)
    layout = ModelLayout(
        scenario_count,
        interval_count,
        q,
        soc,
        emergency,
        terminal_shortfall,
        binary_by_pair,
        variable_count,
    )

    objective = np.zeros(variable_count)
    objective[q] = price
    objective[emergency] = (
        probability[:, None] * config.emergency_multiplier * price[None, :]
    )
    if not terminal_free:
        objective[terminal_shortfall] = (
            probability * config.terminal_penalty_yuan_per_kwh
        )

    lower = np.zeros(variable_count)
    upper = np.full(variable_count, np.inf)
    lower[soc] = config.soc_min_kwh
    upper[soc] = config.soc_max_kwh
    upper[emergency] = load
    for binary in binary_by_pair.values():
        upper[binary] = 1.0

    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    right_hand_side: list[float] = []

    def add(terms: Iterable[tuple[int, float]], bound: float) -> None:
        row = len(right_hand_side)
        for column, coefficient in terms:
            rows.append(row)
            columns.append(int(column))
            values.append(float(coefficient))
        right_hand_side.append(float(bound))

    def delta_terms(scenario: int, interval: int, scale: float) -> list[tuple[int, float]]:
        terms = [(soc[scenario, interval], scale)]
        if interval:
            terms.append((soc[scenario, interval - 1], -scale))
        return terms

    charge_internal_limit = config.eta_c * config.interval_limit_kwh
    discharge_internal_limit = np.minimum(config.interval_limit_kwh, load) / config.eta_d
    for scenario in range(scenario_count):
        for interval in range(interval_count):
            initial_shift = initial_soc_kwh if interval == 0 else 0.0
            net_load = load[scenario, interval] - pv[scenario, interval]
            for slope in (1.0 / config.eta_c, config.eta_d):
                add(
                    [(q[interval], -1.0), (emergency[scenario, interval], -1.0)]
                    + delta_terms(scenario, interval, slope),
                    -net_load + slope * initial_shift,
                )
            add(
                delta_terms(scenario, interval, 1.0),
                charge_internal_limit + initial_shift,
            )
            add(
                delta_terms(scenario, interval, -1.0),
                discharge_internal_limit[scenario, interval] - initial_shift,
            )
        add(
            [
                (soc[scenario, -1], -1.0),
                (terminal_shortfall[scenario], -1.0),
            ],
            -config.reference_soc_kwh,
        )

    for (scenario, interval), binary in binary_by_pair.items():
        initial_shift = initial_soc_kwh if interval == 0 else 0.0
        discharge_limit = discharge_internal_limit[scenario, interval]
        add(
            delta_terms(scenario, interval, 1.0)
            + [(binary, -charge_internal_limit)],
            initial_shift,
        )
        add(
            delta_terms(scenario, interval, -1.0)
            + [(binary, discharge_limit)],
            discharge_limit - initial_shift,
        )
        add(
            [
                (emergency[scenario, interval], 1.0),
                (binary, load[scenario, interval]),
            ],
            load[scenario, interval],
        )

    constraints = _sparse_matrix(
        rows,
        columns,
        values,
        right_hand_side,
        variable_count,
    )
    integrality = np.zeros(variable_count, dtype=int)
    if pairs:
        integrality[continuous_count:] = 1
    return BuiltModel(
        objective=objective,
        lower_bounds=lower,
        upper_bounds=upper,
        constraints=constraints,
        constraint_upper_bounds=np.asarray(right_hand_side),
        integrality=integrality,
        layout=layout,
        build_seconds=perf_counter() - started,
    )


def _finite_attribute(result, name: str, fallback: float) -> float:
    value = getattr(result, name, fallback)
    if value is None:
        return float(fallback)
    value = float(value)
    return value if np.isfinite(value) else float(fallback)


def _decode_solution(
    method: str,
    result,
    model: BuiltModel,
    initial_soc_kwh: float,
    config: Q2Config,
    solve_seconds: float,
) -> PlanSolution:
    if result.x is None:
        raise RuntimeError(f"{method} returned no feasible solution: {result.message}")
    vector = np.asarray(result.x, dtype=float)
    if not np.isfinite(vector).all():
        raise AssertionError(f"{method} returned non-finite variables")
    layout = model.layout
    state = np.column_stack(
        [np.full(layout.scenario_count, initial_soc_kwh), vector[layout.soc]]
    )
    state_change = np.diff(state, axis=1)
    emergency = np.maximum(vector[layout.emergency], 0.0)
    charge = np.maximum(state_change, 0.0) / config.eta_c
    discharge = config.eta_d * np.maximum(-state_change, 0.0)
    conflicts_array = np.argwhere(
        (charge > config.energy_tolerance_kwh)
        & (emergency > config.energy_tolerance_kwh)
    )
    conflicts = tuple(map(tuple, conflicts_array.tolist()))
    violation = model.constraints @ vector - model.constraint_upper_bounds
    max_violation = max(0.0, float(np.max(violation)))
    if max_violation > config.energy_tolerance_kwh:
        raise AssertionError(
            f"{method} constraint violation {max_violation:.6g} exceeds tolerance"
        )
    if np.min(vector[layout.q]) < -config.energy_tolerance_kwh:
        raise AssertionError(f"{method} returned a negative plan")
    if state.min() < config.soc_min_kwh - config.energy_tolerance_kwh:
        raise AssertionError(f"{method} violated the lower SOC bound")
    if state.max() > config.soc_max_kwh + config.energy_tolerance_kwh:
        raise AssertionError(f"{method} violated the upper SOC bound")
    if charge.max() > config.interval_limit_kwh + config.energy_tolerance_kwh:
        raise AssertionError(f"{method} violated the charge limit")
    if discharge.max() > config.interval_limit_kwh + config.energy_tolerance_kwh:
        raise AssertionError(f"{method} violated the discharge limit")

    objective = float(model.objective @ vector)
    return PlanSolution(
        method=method,
        solver_success=bool(result.success),
        status_code=int(result.status),
        message=str(result.message),
        objective_yuan=objective,
        dual_bound_yuan=_finite_attribute(result, "mip_dual_bound", objective),
        relative_gap=_finite_attribute(result, "mip_gap", 0.0),
        build_seconds=model.build_seconds,
        solve_seconds=solve_seconds,
        plan_kwh=np.maximum(vector[layout.q], 0.0),
        scenario_soc_kwh=state,
        scenario_emergency_kwh=emergency,
        scenario_charge_kwh=charge,
        scenario_discharge_kwh=discharge,
        conflicts=conflicts,
        active_binary_count=len(layout.binary_by_pair),
        node_count=int(getattr(result, "mip_node_count", 0) or 0),
        max_constraint_violation=max_violation,
    )


def solve_with_binary_pairs(
    load_scenarios: np.ndarray,
    pv_scenarios: np.ndarray,
    weights: np.ndarray,
    price: np.ndarray,
    initial_soc_kwh: float,
    config: Q2Config,
    active_binary_pairs: Iterable[tuple[int, int]],
    method: str,
    terminal_free: bool = False,
) -> PlanSolution:
    pairs = tuple(active_binary_pairs)
    model = build_day_ahead_model(
        load_scenarios,
        pv_scenarios,
        weights,
        price,
        initial_soc_kwh,
        config,
        pairs,
        terminal_free,
    )
    started = perf_counter()
    if not pairs:
        result = linprog(
            model.objective,
            A_ub=model.constraints,
            b_ub=model.constraint_upper_bounds,
            bounds=list(zip(model.lower_bounds, model.upper_bounds)),
            method="highs",
        )
        if not result.success:
            raise RuntimeError(f"Day-ahead LP failed: {result.message}")
    else:
        result = milp(
            model.objective,
            integrality=model.integrality,
            bounds=Bounds(model.lower_bounds, model.upper_bounds),
            constraints=LinearConstraint(
                model.constraints,
                -np.inf,
                model.constraint_upper_bounds,
            ),
            options={
                "time_limit": config.mip_time_limit_seconds,
                "mip_rel_gap": config.mip_relative_gap,
            },
        )
    return _decode_solution(
        method,
        result,
        model,
        initial_soc_kwh,
        config,
        perf_counter() - started,
    )


def solve_relaxation(
    load_scenarios: np.ndarray,
    pv_scenarios: np.ndarray,
    weights: np.ndarray,
    price: np.ndarray,
    initial_soc_kwh: float,
    config: Q2Config,
    terminal_free: bool = False,
) -> PlanSolution:
    return solve_with_binary_pairs(
        load_scenarios,
        pv_scenarios,
        weights,
        price,
        initial_soc_kwh,
        config,
        (),
        "LP_RELAXATION",
        terminal_free,
    )


def solve_full_milp(
    load_scenarios: np.ndarray,
    pv_scenarios: np.ndarray,
    weights: np.ndarray,
    price: np.ndarray,
    initial_soc_kwh: float,
    config: Q2Config,
    terminal_free: bool = False,
) -> PlanSolution:
    load = np.atleast_2d(load_scenarios)
    pairs = (
        (scenario, interval)
        for scenario in range(load.shape[0])
        for interval in range(load.shape[1])
    )
    solution = solve_with_binary_pairs(
        load_scenarios,
        pv_scenarios,
        weights,
        price,
        initial_soc_kwh,
        config,
        pairs,
        "FULL_MILP",
        terminal_free,
    )
    if solution.conflicts:
        raise AssertionError("Full MILP returned a charge/emergency conflict")
    return solution


def _expand_conflicts(
    conflicts: Iterable[tuple[int, int]],
    scenario_count: int,
    interval_count: int,
    scope: str,
) -> set[tuple[int, int]]:
    conflicts = tuple(conflicts)
    if scope == "pair":
        return set(conflicts)
    if scope == "scenario":
        scenarios = {scenario for scenario, _ in conflicts}
        return {
            (scenario, interval)
            for scenario in scenarios
            for interval in range(interval_count)
        }
    intervals = {interval for _, interval in conflicts}
    return {
        (scenario, interval)
        for scenario in range(scenario_count)
        for interval in intervals
    }


def solve_incremental_milp(
    load_scenarios: np.ndarray,
    pv_scenarios: np.ndarray,
    weights: np.ndarray,
    price: np.ndarray,
    initial_soc_kwh: float,
    config: Q2Config,
    terminal_free: bool = False,
    trace: bool = False,
) -> IncrementalPlan:
    """Add mode binaries only where the LP relaxation exposes a conflict."""

    config.validate()
    relaxation = solve_relaxation(
        load_scenarios,
        pv_scenarios,
        weights,
        price,
        initial_soc_kwh,
        config,
        terminal_free,
    )
    total_build = relaxation.build_seconds
    total_solve = relaxation.solve_seconds
    scenario_count, interval_count = np.atleast_2d(load_scenarios).shape
    active = _expand_conflicts(
        relaxation.conflicts,
        scenario_count,
        interval_count,
        config.activation_scope,
    )
    binary_history = [0]
    if trace:
        print(
            "[q2 incremental] LP "
            f"objective={relaxation.objective_yuan:.6f} "
            f"conflicts={len(relaxation.conflicts)} active={len(active)}",
            flush=True,
        )
    if not active:
        certified = replace(relaxation, method="INCREMENTAL_LP_CERTIFIED")
        return IncrementalPlan(
            relaxation,
            certified,
            0,
            tuple(binary_history),
            total_build,
            total_solve,
        )

    for round_number in range(1, config.max_incremental_rounds + 1):
        binary_history.append(len(active))
        solution = solve_with_binary_pairs(
            load_scenarios,
            pv_scenarios,
            weights,
            price,
            initial_soc_kwh,
            config,
            active,
            f"INCREMENTAL_MILP_ROUND_{round_number}",
            terminal_free,
        )
        total_build += solution.build_seconds
        total_solve += solution.solve_seconds
        unresolved = set(solution.conflicts)
        if trace:
            print(
                f"[q2 incremental] round={round_number} active={len(active)} "
                f"unresolved={len(unresolved)} gap={solution.relative_gap:.6g} "
                f"success={solution.solver_success}",
                flush=True,
            )
        if not unresolved:
            method = (
                "INCREMENTAL_MILP_GAP_REACHED"
                if solution.solver_success
                else "INCREMENTAL_MILP_FEASIBLE_TIME_LIMIT"
            )
            return IncrementalPlan(
                relaxation,
                replace(solution, method=method),
                round_number,
                tuple(binary_history),
                total_build,
                total_solve,
            )
        new_pairs = _expand_conflicts(
            unresolved,
            scenario_count,
            interval_count,
            config.activation_scope,
        ) - active
        if not new_pairs:
            raise AssertionError(
                "An active binary scope still contains a charge/emergency conflict"
            )
        active.update(new_pairs)
    raise RuntimeError(
        "Incremental MILP did not remove every conflict; "
        f"binary history={binary_history}, unresolved={len(unresolved)}"
    )


def objective_interval(solution: PlanSolution) -> tuple[float, float]:
    return (
        min(solution.dual_bound_yuan, solution.objective_yuan),
        max(solution.dual_bound_yuan, solution.objective_yuan),
    )


def objective_intervals_overlap(
    first: PlanSolution,
    second: PlanSolution,
    absolute_tolerance_yuan: float = 1.0e-5,
) -> bool:
    first_lower, first_upper = objective_interval(first)
    second_lower, second_upper = objective_interval(second)
    return max(first_lower, second_lower) <= (
        min(first_upper, second_upper) + absolute_tolerance_yuan
    )
