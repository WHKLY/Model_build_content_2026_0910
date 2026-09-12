"""Regression tests for the formal Question 2 workflow."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from project_paths import TEMPLATE_RESULT_2  # noqa: E402
from q2_control import simulate_frozen_plan_day  # noqa: E402
from q2_export import verify_template_result2, write_template_result2  # noqa: E402
from q2_model import (  # noqa: E402
    Q2Config,
    objective_intervals_overlap,
    solve_full_milp,
    solve_incremental_milp,
)
from q2_verify import verify_dispatch  # noqa: E402


class Q2ModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = replace(
            Q2Config(),
            initial_soc_kwh=1200.0,
            reference_soc_kwh=1290.0,
            terminal_penalty_yuan_per_kwh=100.0,
            mip_time_limit_seconds=30.0,
            mip_relative_gap=1.0e-9,
            energy_tolerance_kwh=1.0e-7,
        ).validate()

    def test_lp_without_conflict_is_full_milp_certified(self) -> None:
        load = np.asarray([[100.0]])
        pv = np.zeros_like(load)
        weight = np.ones(1)
        price = np.ones(1)
        incremental = solve_incremental_milp(
            load, pv, weight, price, self.config.initial_soc_kwh, self.config
        )
        full = solve_full_milp(
            load, pv, weight, price, self.config.initial_soc_kwh, self.config
        )
        self.assertEqual(incremental.rounds, 0)
        self.assertEqual(incremental.solution.active_binary_count, 0)
        self.assertTrue(objective_intervals_overlap(incremental.solution, full))
        self.assertAlmostEqual(
            incremental.solution.objective_yuan,
            full.objective_yuan,
            places=7,
        )

    def test_conflict_activates_only_conflicting_scenario(self) -> None:
        load = np.zeros((10, 1))
        load[0, 0] = 100.0
        pv = np.zeros_like(load)
        weight = np.full(10, 0.1)
        price = np.ones(1)
        incremental = solve_incremental_milp(
            load, pv, weight, price, self.config.initial_soc_kwh, self.config
        )
        full = solve_full_milp(
            load, pv, weight, price, self.config.initial_soc_kwh, self.config
        )
        self.assertEqual(len(incremental.relaxation.conflicts), 1)
        self.assertEqual(incremental.rounds, 1)
        self.assertEqual(incremental.solution.active_binary_count, 1)
        self.assertFalse(incremental.solution.conflicts)
        self.assertTrue(objective_intervals_overlap(incremental.solution, full))
        self.assertAlmostEqual(incremental.relaxation.objective_yuan, 150.0, places=7)
        self.assertAlmostEqual(incremental.solution.objective_yuan, 200.0, places=7)

    def test_frozen_plan_replay_passes_independent_physics(self) -> None:
        config = replace(
            Q2Config(),
            soc_min_kwh=0.0,
            soc_max_kwh=1000.0,
            initial_soc_kwh=500.0,
            reference_soc_kwh=500.0,
            power_max_kw=600.0,
            energy_tolerance_kwh=1.0e-7,
        ).validate()
        load = np.asarray([100.0, 180.0, 100.0])
        pv = np.asarray([180.0, 0.0, 100.0])
        plan = np.asarray([0.0, 100.0, 0.0])
        frame = simulate_frozen_plan_day(
            load,
            pv,
            load,
            pv,
            np.ones(3),
            plan,
            config.initial_soc_kwh,
            ("00:00-00:10", "00:10-00:20", "00:20-00:30"),
            config,
        )
        checks = verify_dispatch(frame, config)
        self.assertTrue(checks["passed"])
        self.assertLessEqual(checks["balance_max_abs_kwh"], 1.0e-7)
        self.assertTrue(np.array_equal(frame["plan_kwh"].to_numpy(), plan))


class Q2TemplateTests(unittest.TestCase):
    def test_template_export_retains_official_columns_and_sheets(self) -> None:
        dates = [datetime(2025, 2, 1) + timedelta(days=day) for day in range(334)]
        records = []
        for date in dates:
            for interval in range(144):
                records.append(
                    {
                        "date": date,
                        "t": interval,
                        "plan_kwh": float(interval % 7),
                        "charge_kwh": 0.0,
                        "discharge_kwh": 0.0,
                        "emergency_kwh": 0.0,
                        "soc_start_kwh": 6000.0,
                        "soc_end_kwh": 6000.0,
                        "total_cost_yuan": float(interval % 7),
                    }
                )
        detail = pd.DataFrame(records)
        with TemporaryDirectory() as directory:
            output = Path(directory) / "result2.xlsx"
            _, blocks, events = write_template_result2(
                output, detail, 2.0e-5, TEMPLATE_RESULT_2
            )
            result = verify_template_result2(
                output, detail, blocks, events, TEMPLATE_RESULT_2
            )
        self.assertTrue(result["passed"])
        self.assertEqual(result["sheet_names"], ["计划购电量", "充放电量", "紧急购电量"])
        self.assertEqual(result["storage_rows"], 334 * 6)
        self.assertEqual(result["emergency_rows"], 334)


if __name__ == "__main__":
    unittest.main()
