"""Contest entry point: run all implemented questions or one selected question."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


BUNDLE_ROOT = Path(__file__).resolve().parent
SCRIPT_DIR = BUNDLE_ROOT / "scripts"

# Force imports to resolve inside this submission bundle, regardless of cwd.
sys.path.insert(0, str(SCRIPT_DIR))

from question_registry import available_questions, run_questions  # noqa: E402


def parse_args() -> argparse.Namespace:
    implemented = available_questions()
    parser = argparse.ArgumentParser(description="Run implemented contest questions and write non-image outputs.")
    parser.add_argument(
        "--question",
        type=int,
        choices=implemented,
        help="Run one implemented question. Omit to run all implemented questions.",
    )
    parser.add_argument(
        "--list-questions",
        action="store_true",
        help="List implemented question numbers and exit.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    implemented = available_questions()
    if args.list_questions:
        print("Implemented questions: " + ", ".join(str(number) for number in implemented))
        return
    selected = implemented if args.question is None else (args.question,)
    run_questions(selected)


if __name__ == "__main__":
    main()
