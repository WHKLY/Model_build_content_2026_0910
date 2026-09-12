"""Central project paths for the Python implementation."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "original_source"
ATTACHMENT_ROOT = SOURCE_ROOT / "附件"
OUTPUT_ROOT = PROJECT_ROOT / "output"

PROBLEM_PDF = SOURCE_ROOT / "C题.pdf"
ATTACHMENT_1 = ATTACHMENT_ROOT / "附件1.xlsx"
ATTACHMENT_2 = ATTACHMENT_ROOT / "附件2.xlsx"
ATTACHMENT_3 = ATTACHMENT_ROOT / "附件3.xlsx"
ATTACHMENT_4 = ATTACHMENT_ROOT / "附件4.xlsx"
TEMPLATE_ROOT = ATTACHMENT_ROOT / "附件5"
TEMPLATE_RESULT_1 = TEMPLATE_ROOT / "result1.xlsx"
TEMPLATE_RESULT_2 = TEMPLATE_ROOT / "result2.xlsx"
TEMPLATE_RESULT_3 = TEMPLATE_ROOT / "result3.xlsx"
TEMPLATE_RESULT_4_2 = TEMPLATE_ROOT / "result4-2.xlsx"
TEMPLATE_RESULT_4_3 = TEMPLATE_ROOT / "result4-3.xlsx"


def q1_output_dir() -> Path:
    return OUTPUT_ROOT / "question_1"


def q2_output_dir() -> Path:
    return OUTPUT_ROOT / "question_2"


def ensure_output_dirs() -> None:
    q1_output_dir().mkdir(parents=True, exist_ok=True)
    (q1_output_dir() / "figures").mkdir(parents=True, exist_ok=True)
