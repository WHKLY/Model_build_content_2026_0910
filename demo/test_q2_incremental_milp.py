"""Synthetic regression tests for the incremental-MILP experiment."""

from __future__ import annotations

import unittest
from dataclasses import replace

import numpy as np

from demo.q2_incremental_milp import (
    Config,
    numerical_objective_agreement,
    solve_full_milp,
    solve_incremental_milp,
)


class IncrementalMilpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = replace(
            Config(),
            soc_min_kwh=1200.0,
            soc_max_kwh=10800.0,
            initial_soc_kwh=1200.0,
            reference_soc_kwh=1290.0,
            terminal_penalty=100.0,
            mip_time_limit_seconds=30.0,
            mip_relative_gap=1e-9,
            energy_tolerance_kwh=1e-7,
        ).validate()

    def test_no_conflict_relaxation_is_already_certified(self) -> None:
        load = np.asarray([[100.0]])
        pv = np.zeros_like(load)
        weights = np.asarray([1.0])
        price = np.asarray([1.0])
        incremental = solve_incremental_milp(
            load,
            pv,
            weights,
            price,
            self.config.initial_soc_kwh,
            self.config,
        )
        full = solve_full_milp(
            load,
            pv,
            weights,
            price,
            self.config.initial_soc_kwh,
            self.config,
        )
        self.assertEqual(incremental.iterations, 0)
        self.assertEqual(incremental.solution.active_binary_count, 0)
        self.assertFalse(incremental.solution.conflicts)
        self.assertTrue(numerical_objective_agreement(incremental.solution, full))
        self.assertAlmostEqual(
            incremental.solution.objective,
            full.objective,
            places=7,
        )

    def test_conflict_activates_only_required_binary(self) -> None:
        load = np.zeros((10, 1))
        load[0, 0] = 100.0
        pv = np.zeros_like(load)
        weights = np.full(10, 0.1)
        price = np.asarray([1.0])
        incremental = solve_incremental_milp(
            load,
            pv,
            weights,
            price,
            self.config.initial_soc_kwh,
            self.config,
        )
        full = solve_full_milp(
            load,
            pv,
            weights,
            price,
            self.config.initial_soc_kwh,
            self.config,
        )
        self.assertEqual(len(incremental.relaxation.conflicts), 1)
        self.assertEqual(incremental.iterations, 1)
        self.assertEqual(incremental.solution.active_binary_count, 1)
        self.assertFalse(incremental.solution.conflicts)
        self.assertTrue(numerical_objective_agreement(incremental.solution, full))
        self.assertAlmostEqual(
            incremental.solution.objective,
            full.objective,
            places=7,
        )
        self.assertAlmostEqual(incremental.relaxation.objective, 150.0, places=7)
        self.assertAlmostEqual(incremental.solution.objective, 200.0, places=7)


if __name__ == "__main__":
    unittest.main()
