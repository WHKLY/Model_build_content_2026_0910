"""Verify a Question 1 rational certificate without calling an optimizer."""
from __future__ import annotations

import argparse
from datetime import datetime, time
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from openpyxl import load_workbook

F = Fraction
N = 144
ETA_C = F(9, 10)
ETA_D = F(9, 10)
DT = F(1, 6)
POWER_LIMIT_KW = F(5000)
Q = POWER_LIMIT_KW * DT
SOC_MIN = F(1200)
SOC_MAX = F(10800)
SOC_INITIAL = F(6000)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _minute_of_day(value: object) -> int:
    if isinstance(value, (datetime, time)):
        minute = value.hour * 60 + value.minute
        return 1440 if minute == 0 else minute
    if isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0:
        minute = round(float(value) * 1440)
        return 1440 if minute == 0 else minute
    text = str(value).strip().replace(" ", "")
    offset = 1440 if "+1" in text else 0
    hour, minute = text.replace("+1", "").split(":")[:2]
    result = offset + int(hour) * 60 + int(minute)
    return 1440 if result == 0 else result


def _check_source(path: Path, certificate: dict[str, object], price: list[F], load: list[F], pv: list[F]) -> None:
    _require(path.is_file(), f"source file not found: {path}")
    _require(sha256(path.read_bytes()).hexdigest() == certificate["input_sha256"], "source SHA-256 mismatch")
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = [row for row in list(workbook.active.values)[1:] if any(value is not None for value in row)]
    finally:
        workbook.close()
    _require(len(rows) == N, "source row count is not 144")
    for t, row in enumerate(rows):
        _require(_minute_of_day(row[0]) == (t + 1) * 10, f"source time mismatch at interval {t + 1}")
        _require(F(str(row[1])) == price[t], f"source price mismatch at interval {t + 1}")
        _require(F(str(row[2])) * DT == load[t], f"source load mismatch at interval {t + 1}")
        _require(F(str(row[3])) * DT == pv[t], f"source PV mismatch at interval {t + 1}")


def verify_certificate(certificate: dict[str, object], source_path: Path | None = None) -> dict[str, object]:
    _require(certificate.get("format") == "microgrid-q1-rational-certificate-v1", "unsupported certificate format")
    price = [F(value) for value in certificate["price"]]
    load = [F(value) for value in certificate["load_energy"]]
    pv = [F(value) for value in certificate["pv_energy"]]
    state = [F(value) for value in certificate["state"]]
    grid = [F(value) for value in certificate["grid"]]
    dual = [F(value) for value in certificate["dual_inequality_multipliers"]]
    _require(all(len(values) == N for values in (price, load, pv, grid)), "certificate vector length mismatch")
    _require(len(state) == N + 1 and len(dual) == 4 * N, "certificate state or dual length mismatch")
    _require(all(value > 0 for value in price), "prices must be positive")
    _require(all(value >= 0 for value in load + pv), "load and PV must be nonnegative")
    _require(all(value <= 0 for value in dual), "dual multipliers must be nonpositive")
    if source_path is not None:
        _check_source(source_path, certificate, price, load, pv)

    _require(state[0] == state[-1] == SOC_INITIAL, "initial/terminal SOC mismatch")
    _require(all(SOC_MIN <= value <= SOC_MAX for value in state), "SOC bound violation")
    _require(all(F(0) <= value <= load[t] + Q for t, value in enumerate(grid)), "grid bound violation")

    rows: list[dict[int, F]] = []
    rhs: list[F] = []
    z = grid + state[1:]
    for t in range(N):
        for slope in (1 / ETA_C, ETA_D):
            row = {t: F(-1), N + t: slope}
            if t > 0:
                row[N + t - 1] = -slope
            rows.append(row)
            rhs.append(-(load[t] - pv[t]) + (slope * SOC_INITIAL if t == 0 else F(0)))
        for sign, limit in ((F(1), ETA_C * Q), (F(-1), Q / ETA_D)):
            row = {N + t: sign}
            if t > 0:
                row[N + t - 1] = -sign
            rows.append(row)
            rhs.append(limit + (sign * SOC_INITIAL if t == 0 else F(0)))

    for index, (row, row_rhs) in enumerate(zip(rows, rhs), start=1):
        _require(sum(coefficient * z[column] for column, coefficient in row.items()) <= row_rhs, f"LP inequality {index} failed")

    for t in range(N):
        delta = state[t + 1] - state[t]
        charge = max(delta, F(0)) / ETA_C
        discharge = ETA_D * max(-delta, F(0))
        _require(charge <= Q and discharge <= Q, f"power bound failed at interval {t + 1}")
        _require(grid[t] + pv[t] + discharge >= load[t] + charge, f"supply failed at interval {t + 1}")

    objective = price + [F(0)] * N
    lower = [F(0)] * N + [SOC_MIN] * N
    upper = [load_t + Q for load_t in load] + [SOC_MAX] * N
    lower[-1] = upper[-1] = SOC_INITIAL
    residual = objective.copy()
    lower_bound = F(0)
    for multiplier, row, row_rhs in zip(dual, rows, rhs):
        lower_bound += row_rhs * multiplier
        for column, coefficient in row.items():
            residual[column] -= coefficient * multiplier
    lower_bound += sum(min(value * lo, value * hi) for value, lo, hi in zip(residual, lower, upper))
    upper_bound = sum(p * g for p, g in zip(price, grid))
    gap = upper_bound - lower_bound

    _require(gap >= 0, "dual lower bound exceeds primal upper bound")
    _require(lower_bound == F(certificate["lower_bound"]), "stored lower bound mismatch")
    _require(upper_bound == F(certificate["upper_bound"]), "stored upper bound mismatch")
    _require(gap == F(certificate["gap"]), "stored gap mismatch")
    _require((gap == 0) == bool(certificate["exact_optimal"]), "stored optimality flag mismatch")
    return {
        "exact_optimal": gap == 0,
        "gap": str(gap),
        "verified_source": source_path is not None,
        "upper_bound": str(upper_bound),
        "lower_bound": str(lower_bound),
    }


def verify_certificate_file(certificate_path: Path, source_path: Path | None = None) -> dict[str, object]:
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    return verify_certificate(certificate, source_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--input", type=Path, default=None, help="Attachment 1 used to bind the certificate to source data")
    args = parser.parse_args()
    try:
        result = verify_certificate_file(args.certificate, args.input)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Certificate verification failed: {exc}\n")
    if result["exact_optimal"]:
        print("Certificate verified: exact primal and dual costs are equal; the schedule is globally optimal for the stated LP.")
    else:
        print(f"Certificate feasible but not exact; certified gap: {result['gap']}")
    print(f"Source workbook verified: {result['verified_source']}")


if __name__ == "__main__":
    main()
