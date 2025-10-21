"""Logic diagnosis task environment and dataset helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from ..adaptation import EnvironmentResult, Sample, TaskEnvironment
from ..roles import GeneratorOutput


@dataclass
class TesterResponse:
    """Single tester response entry for a test pattern."""

    input_patterns: list[dict[str, int]]
    good_outputs: list[dict[str, int]]
    faulty_outputs: list[dict[str, int]]
    differences: list[str]


@dataclass
class FaultSpec:
    """Ground-truth fault information."""

    location: str
    behavior: str


class LogicDiagnosisEnvironment(TaskEnvironment):
    """Environment that scores predicted stuck-at faults.

    The environment assumes each task corresponds to a single stuck-at fault and
    compares the model prediction against the provided ground truth specification.
    """

    def __init__(
        self,
        ground_truth: Mapping[str, FaultSpec],
        *,
        tolerance: Optional[float] = None,
    ) -> None:
        self._ground_truth = dict(ground_truth)
        self._tolerance = tolerance

    @staticmethod
    def load_tester_responses(path: str | Path) -> list[TesterResponse]:
        """Load tester responses for a single-fault task from a JSON array."""

        with Path(path).open("r", encoding="utf-8") as fh:
            payload = json.load(fh)

        if not isinstance(payload, list):
            raise ValueError("Tester responses JSON must be an array of pattern objects.")

        responses: list[TesterResponse] = []
        for index, entry in enumerate(payload):
            if not isinstance(entry, dict):
                raise ValueError(f"Tester response at index {index} is not an object: {entry!r}")

            responses.append(
                TesterResponse(
                    input_patterns=_coerce_io(entry.get("input_patterns"), index, "input_patterns"),
                    good_outputs=_coerce_io(entry.get("good_outputs"), index, "good_outputs"),
                    faulty_outputs=_coerce_io(entry.get("faulty_outputs"), index, "faulty_outputs"),
                    differences=_coerce_differences(entry.get("differences"), index),
                )
            )
        return responses

    def evaluate(
        self,
        sample: Sample,
        generator_output: GeneratorOutput,
    ) -> EnvironmentResult:
        prediction = _parse_prediction(generator_output.final_answer)
        fault_id = str(sample.metadata.get("fault_id", sample.metadata.get("id", "")))
        expected = self._ground_truth.get(fault_id)

        if expected is None:
            feedback = "No ground truth found for fault_id; unable to score prediction."
            metrics = {"matched_location": 0.0, "matched_behavior": 0.0}
            return EnvironmentResult(
                feedback=feedback,
                ground_truth=None,
                metrics=metrics,
            )

        location_match = _matches(prediction.location, expected.location)
        behavior_match = _matches(prediction.behavior, expected.behavior)
        score = 1.0 if location_match and behavior_match else 0.0
        feedback_parts = [
            f"predicted location={prediction.location or 'unknown'}",
            f"expected location={expected.location}",
            f"predicted behavior={prediction.behavior or 'unknown'}",
            f"expected behavior={expected.behavior}",
        ]
        feedback = "; ".join(feedback_parts)
        metrics = {
            "matched_location": 1.0 if location_match else 0.0,
            "matched_behavior": 1.0 if behavior_match else 0.0,
            "accuracy": score,
        }
        return EnvironmentResult(
            feedback=feedback,
            ground_truth=f"{expected.location} {expected.behavior}",
            metrics=metrics,
        )


def _matches(candidate: Optional[str], expected: str) -> bool:
    if candidate is None:
        return False
    return candidate.strip().lower() == expected.strip().lower()


@dataclass
class _Prediction:
    location: Optional[str] = None
    behavior: Optional[str] = None


def _parse_prediction(final_answer: str) -> _Prediction:
    """Interpret the generator's final answer as a structured prediction."""

    final_answer = final_answer.strip()
    if not final_answer:
        return _Prediction()

    # Prefer JSON payloads if available
    if final_answer.startswith("{") and final_answer.endswith("}"):
        try:
            import json

            data = json.loads(final_answer)
            location = str(data.get("location") or data.get("suspect") or "")
            behavior = str(
                data.get("behavior")
                or data.get("fault")
                or data.get("stuck_at")
                or ""
            )
            return _Prediction(location=location or None, behavior=behavior or None)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # Fallback: look for "stuck-at" like text
    tokens = final_answer.split()
    location = tokens[0] if tokens else None
    behavior = None
    for token in tokens:
        if "stuck-at" in token.lower():
            behavior = token.strip(",.;")
            break
    return _Prediction(location=location, behavior=behavior)


def _coerce_io(value: object, index: int, field: str) -> list[dict[str, int]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(
            f"Tester response at index {index} has non-list '{field}': {value!r}"
        )

    normalised: list[dict[str, int]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(
                f"Tester response at index {index} has non-object in '{field}': {item!r}"
            )
        converted: dict[str, int] = {}
        for name, raw in item.items():
            if not isinstance(name, str):
                raise ValueError(
                    f"Tester response at index {index} has non-string key in '{field}': {name!r}"
                )
            try:
                converted[name] = int(raw)
            except (TypeError, ValueError):
                raise ValueError(
                    f"Tester response at index {index} has non-integer value for '{name}' in '{field}': {raw!r}"
                ) from None
        normalised.append(converted)
    return normalised


def _coerce_differences(value: object, index: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(
            f"Tester response at index {index} has non-list 'differences': {value!r}"
        )
    differences: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            raise ValueError(
                f"Tester response at index {index} has non-string difference entry: {entry!r}"
            )
        differences.append(entry)
    return differences
