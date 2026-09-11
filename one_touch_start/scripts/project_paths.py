"""Paths owned by the self-contained contest submission bundle."""
from __future__ import annotations

from pathlib import Path


BUNDLE_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = BUNDLE_ROOT / "assets"
OUTPUT_ROOT = BUNDLE_ROOT / "output"

ATTACHMENT_1 = ASSET_ROOT / "附件1.xlsx"
TEMPLATE_RESULT_1 = ASSET_ROOT / "附件5" / "result1.xlsx"


def output_dir() -> Path:
    return OUTPUT_ROOT


def ensure_output_dir() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
