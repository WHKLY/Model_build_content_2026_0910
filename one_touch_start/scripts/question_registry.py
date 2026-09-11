"""Registry for contest questions that have complete, verified runners."""
from __future__ import annotations

from collections.abc import Callable, Iterable

from q1_runner import run_question_1


QuestionRunner = Callable[[], None]

# Add a question only after its model, exporter, and verification are complete.
QUESTION_RUNNERS: dict[int, QuestionRunner] = {
    1: run_question_1,
}


def available_questions() -> tuple[int, ...]:
    return tuple(sorted(QUESTION_RUNNERS))


def run_questions(question_numbers: Iterable[int]) -> None:
    selected = tuple(question_numbers)
    if not selected:
        raise ValueError("no implemented questions are registered")
    for number in selected:
        try:
            runner = QUESTION_RUNNERS[number]
        except KeyError as exc:
            raise ValueError(f"question {number} is not implemented") from exc
        print(f"Running Question {number}...")
        runner()
