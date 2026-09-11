"""Question 1 matplotlib visualizations."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from q1_data import INTERVAL_COUNT, Q1SourceData
from q1_model import BaselineSolution, IntervalData, ScheduleSolution

COLOR_BLUE = "#2563EB"
COLOR_GREEN = "#059669"
COLOR_RED = "#DC2626"
COLOR_AMBER = "#D97706"
COLOR_PURPLE = "#7C3AED"
COLOR_GRAY = "#4B5563"


def _save(fig: plt.Figure, basepath: Path) -> dict[str, Path]:
    basepath.parent.mkdir(parents=True, exist_ok=True)
    png = basepath.with_suffix(".png")
    svg = basepath.with_suffix(".svg")
    fig.savefig(png, dpi=180, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    plt.close(fig)
    return {"png": png, "svg": svg}


def plot_dispatch(source: Q1SourceData, interval_data: IntervalData, plan_a: ScheduleSolution, plan_b: ScheduleSolution, figdir: Path) -> dict[str, Path]:
    x = np.arange(1, INTERVAL_COUNT + 1)
    fig, axes = plt.subplots(4, 1, figsize=(12, 12), sharex=True)

    axes[0].plot(x, interval_data.load_kw / 1000.0, color=COLOR_BLUE, linewidth=1.4, label="Load")
    axes[0].plot(x, interval_data.pv_kw / 1000.0, color=COLOR_GREEN, linewidth=1.4, label="PV forecast")
    axes[0].set_ylabel("MW")
    axes[0].set_title("Question 1 Load and PV Forecast")
    axes[0].legend(loc="upper right")

    axes[1].plot(x, interval_data.price, color=COLOR_AMBER, linewidth=1.4)
    axes[1].set_ylabel("yuan/kWh")
    axes[1].set_title("Electricity Price")

    axes[2].plot(x, plan_a.charge_kwh / 1000.0, color=COLOR_GREEN, linewidth=1.2, label="Charge")
    axes[2].plot(x, -plan_a.discharge_kwh / 1000.0, color=COLOR_RED, linewidth=1.2, label="Discharge")
    axes[2].set_ylabel("MWh")
    axes[2].set_title("Plan A Charge (+) and Discharge (-)")
    axes[2].legend(loc="upper right")

    axes[3].plot(x, plan_a.soc_kwh / 1000.0, color=COLOR_PURPLE, linewidth=1.4, label="SOC")
    axes[3].plot(x, plan_a.grid_kwh / 1000.0, color=COLOR_GRAY, linewidth=1.1, label="Grid purchase")
    axes[3].set_xlabel("10-minute interval index")
    axes[3].set_ylabel("MWh")
    axes[3].set_title("Plan A SOC and Grid Purchase")
    axes[3].legend(loc="upper right")

    for ax in axes:
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return _save(fig, figdir / "q1_dispatch_overview")


def plot_plan_difference(plan_a: ScheduleSolution, plan_b: ScheduleSolution, figdir: Path) -> dict[str, Path]:
    x = np.arange(1, INTERVAL_COUNT + 1)
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(x, plan_b.grid_kwh - plan_a.grid_kwh, color=COLOR_BLUE, linewidth=1.3, label="Grid purchase difference")
    ax.plot(x, plan_b.soc_kwh - plan_a.soc_kwh, color=COLOR_PURPLE, linewidth=1.3, label="SOC difference")
    ax.set_xlabel("10-minute interval index")
    ax.set_ylabel("kWh")
    ax.set_title("Question 1 Plan B minus Plan A")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    return _save(fig, figdir / "q1_plan_difference")


def plot_costs(baseline: BaselineSolution, plan_a: ScheduleSolution, plan_b: ScheduleSolution, figdir: Path) -> dict[str, Path]:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    labels = ["No storage", "Plan A", "Plan B"]
    costs = [baseline.cost, plan_a.cost, plan_b.cost]
    ax.bar(labels, costs, color=[COLOR_GRAY, COLOR_BLUE, COLOR_PURPLE])
    ax.set_ylabel("yuan")
    ax.set_title("Question 1 Purchase Cost Comparison")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    return _save(fig, figdir / "q1_cost_comparison")


def plot_all(source: Q1SourceData, interval_data: IntervalData, baseline: BaselineSolution, plan_a: ScheduleSolution, plan_b: ScheduleSolution, figdir: Path) -> dict[str, dict[str, Path]]:
    return {
        "dispatch": plot_dispatch(source, interval_data, plan_a, plan_b, figdir),
        "difference": plot_plan_difference(plan_a, plan_b, figdir),
        "costs": plot_costs(baseline, plan_a, plan_b, figdir),
    }
