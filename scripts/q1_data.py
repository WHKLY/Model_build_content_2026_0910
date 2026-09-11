"""Question 1 source-data loading and interval labeling."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

INTERVAL_COUNT = 144
DELTA_HOUR = 1.0 / 6.0


@dataclass(frozen=True)
class Q1SourceData:
    source_time: list[str]
    interval: list[str]
    price_yuan_per_kwh: np.ndarray
    load_kw: np.ndarray
    pv_forecast_kw: np.ndarray


def _compact(value: object) -> str:
    return str(value).strip().lower().replace(" ", "").replace("_", "")


def _find_column(columns: Iterable[object], keywords: tuple[str, ...], fallback_index: int) -> object:
    cols = list(columns)
    for col in cols:
        label = _compact(col)
        if any(key in label for key in keywords):
            return col
    if fallback_index >= len(cols):
        raise ValueError("Attachment 1 does not contain enough columns for question 1 data")
    return cols[fallback_index]


def _load_raw_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Attachment 1 not found: {path}")

    last_error: Exception | None = None
    for header_row in range(0, 8):
        try:
            frame = pd.read_excel(path, header=header_row)
            frame = frame.dropna(how="all").dropna(axis=1, how="all")
            if frame.shape[0] >= INTERVAL_COUNT and frame.shape[1] >= 4:
                return frame.iloc[:INTERVAL_COUNT].reset_index(drop=True)
        except Exception as exc:  # keep trying nearby header rows
            last_error = exc
    if last_error is not None:
        raise RuntimeError(f"Failed to read Attachment 1: {last_error}") from last_error
    raise ValueError("Could not find a 144-row table in Attachment 1")


def _format_time_label(value: object, index: int) -> str:
    if pd.isna(value):
        return _endpoint_label(index)
    if isinstance(value, pd.Timestamp):
        return _time_to_label(value.time(), index)
    if isinstance(value, datetime):
        return _time_to_label(value.time(), index)
    if isinstance(value, time):
        return _time_to_label(value, index)
    if isinstance(value, (int, float, np.integer, np.floating)):
        # Excel may store times as fractions of a day.
        seconds = int(round(float(value) * 24 * 3600)) % (24 * 3600)
        return _time_to_label((datetime(2000, 1, 1) + timedelta(seconds=seconds)).time(), index)
    text = str(value).strip()
    return text if text else _endpoint_label(index)


def _time_to_label(value: time, index: int) -> str:
    if index == INTERVAL_COUNT - 1 and value.hour == 0 and value.minute == 0:
        return "0:00+1"
    return f"{value.hour:02d}:{value.minute:02d}"


def _endpoint_label(index: int) -> str:
    minute = (index + 1) * 10
    if minute == 24 * 60:
        return "0:00+1"
    return f"{minute // 60:02d}:{minute % 60:02d}"


def _interval_label(index: int) -> str:
    start = index * 10
    end = (index + 1) * 10
    return f"{start // 60:02d}:{start % 60:02d}-{end // 60:02d}:{end % 60:02d}" if end < 24 * 60 else f"{start // 60:02d}:{start % 60:02d}-24:00"


def load_q1_source_data(path: Path) -> Q1SourceData:
    frame = _load_raw_table(path)
    time_col = _find_column(frame.columns, ("时间", "time"), 0)
    price_col = _find_column(frame.columns, ("电价", "price", "元/kwh", "元/千瓦时"), 1)
    load_col = _find_column(frame.columns, ("负荷", "load"), 2)
    pv_col = _find_column(frame.columns, ("光伏", "pv", "预测"), 3)

    source_time = [_format_time_label(value, i) for i, value in enumerate(frame[time_col].tolist())]
    interval = [_interval_label(i) for i in range(INTERVAL_COUNT)]
    price = pd.to_numeric(frame[price_col], errors="raise").to_numpy(dtype=float)
    load = pd.to_numeric(frame[load_col], errors="raise").to_numpy(dtype=float)
    pv = pd.to_numeric(frame[pv_col], errors="raise").to_numpy(dtype=float)

    if not (len(price) == len(load) == len(pv) == INTERVAL_COUNT):
        raise ValueError("Question 1 input arrays must all contain 144 intervals")

    return Q1SourceData(
        source_time=source_time,
        interval=interval,
        price_yuan_per_kwh=price,
        load_kw=load,
        pv_forecast_kw=pv,
    )
