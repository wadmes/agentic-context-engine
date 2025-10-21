"""Task environment tailored for the logic diagnosis workflow."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

from ..adaptation import EnvironmentResult, Sample, TaskEnvironment
from ..roles import GeneratorOutput


def _normalize_string(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _stringify_truth(truth: Mapping[str, object]) -> str:
    payload = {k: truth[k] for k in sorted(truth)}
    return json.dumps(payload, ensure_ascii=False)


class LogicDiagnosisEnvironment(TaskEnvironment):
    """Evaluates predictions for stuck-at fault diagnosis tasks."""

    def __init__(
        self,
        responses_csv: Path | str,
        *,
        sample_id_column: str = "case_id",
        truth_table: Optional[Mapping[str, Mapping[str, object]]] = None,
    ) -> None:
        self.responses_csv = Path(responses_csv)
        if not self.responses_csv.exists():
            raise FileNotFoundError(f"Tester response CSV not found: {self.responses_csv}")
        self.sample_id_column = sample_id_column
        self._rows = self._load_rows()
        self._responses_by_case = self._index_rows(self._rows)
        self.truth_table: Dict[str, Mapping[str, object]] = {
            str(key): value for key, value in (truth_table or {}).items()
        }

    # ------------------------------------------------------------------ #
    def _load_rows(self) -> List[Mapping[str, str]]:
        with self.responses_csv.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader]

    def _index_rows(self, rows: Iterable[Mapping[str, str]]) -> Dict[str, List[Mapping[str, str]]]:
        index: Dict[str, List[Mapping[str, str]]] = {}
        for row in rows:
            case_id = str(row.get(self.sample_id_column, ""))
            index.setdefault(case_id, []).append(row)
        return index

    def _extract_case_id(self, sample: Sample) -> str:
        metadata_value = sample.metadata.get(self.sample_id_column)
        if metadata_value is not None:
            return str(metadata_value)
        # Fall back to generic identifiers.
        for key in ("case_id", "id", "sample_id"):
            if key == self.sample_id_column:
                continue
            value = sample.metadata.get(key)
            if value is not None:
                return str(value)
        return ""

    def _lookup_ground_truth(self, case_id: str, sample: Sample) -> Optional[Mapping[str, object]]:
        if case_id and case_id in self.truth_table:
            return self.truth_table[case_id]
        if sample.ground_truth:
            try:
                parsed = json.loads(sample.ground_truth)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, Mapping):
                return parsed
        return None

    def _extract_prediction(self, output: GeneratorOutput) -> Optional[Mapping[str, object]]:
        # Metadata takes priority because it survives additional routing layers.
        if output.metadata:
            prediction = output.metadata.get("fault_prediction")
            if isinstance(prediction, Mapping):
                return prediction
        raw = output.raw
        if isinstance(raw, Mapping):
            prediction = raw.get("fault_prediction")
            if isinstance(prediction, Mapping):
                return prediction
        final_answer = output.final_answer.strip()
        if not final_answer:
            return None
        try:
            parsed = json.loads(final_answer)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, Mapping):
            return parsed
        return None

    def responses_for_case(self, case_id: str) -> List[Mapping[str, str]]:
        """Return the raw tester responses for a case."""

        return list(self._responses_by_case.get(case_id, []))

    # ------------------------------------------------------------------ #
    def evaluate(self, sample: Sample, generator_output: GeneratorOutput) -> EnvironmentResult:
        case_id = self._extract_case_id(sample)
        truth = self._lookup_ground_truth(case_id, sample)
        prediction = self._extract_prediction(generator_output)

        if truth is None:
            feedback_lines = [
                "Ground truth not available for this sample; unable to score diagnosis.",
            ]
            metrics: Dict[str, float] = {}
            ground_truth_payload = None
        else:
            truth_location = _normalize_string(truth.get("fault_location"))
            truth_behavior = _normalize_string(truth.get("fault_behavior"))
            if prediction is None:
                feedback_lines = [
                    "No structured fault prediction produced.",
                    f"Expected location: {truth.get('fault_location')}",
                    f"Expected behaviour: {truth.get('fault_behavior')}",
                ]
                metrics = {"location_accuracy": 0.0, "behavior_accuracy": 0.0}
            else:
                pred_location = _normalize_string(prediction.get("fault_location"))
                pred_behavior = _normalize_string(prediction.get("fault_behavior"))
                location_correct = pred_location == truth_location and bool(pred_location)
                behavior_correct = pred_behavior == truth_behavior and bool(pred_behavior)
                if location_correct and behavior_correct:
                    feedback_lines = [
                        "Diagnosis matches the ground truth fault.",
                        f"Location: {prediction.get('fault_location')}",
                        f"Behaviour: {prediction.get('fault_behavior')}",
                    ]
                else:
                    feedback_lines = [
                        "Diagnosis does not match ground truth.",
                        f"Predicted location: {prediction.get('fault_location')}",
                        f"Predicted behaviour: {prediction.get('fault_behavior')}",
                        f"Expected location: {truth.get('fault_location')}",
                        f"Expected behaviour: {truth.get('fault_behavior')}",
                    ]
                metrics = {
                    "location_accuracy": 1.0 if location_correct else 0.0,
                    "behavior_accuracy": 1.0 if behavior_correct else 0.0,
                }
            ground_truth_payload = _stringify_truth(truth)

        if case_id:
            feedback_lines.append(f"Case identifier: {case_id}")
            related = self._responses_by_case.get(case_id)
            if related:
                sample_count = len(related)
                feedback_lines.append(
                    f"Tester responses available for case: {sample_count} row(s) in {self.responses_csv.name}."
                )
        else:
            feedback_lines.append("Sample did not include a case identifier.")

        feedback = "\n".join(feedback_lines)
        return EnvironmentResult(
            feedback=feedback,
            ground_truth=ground_truth_payload,
            metrics=metrics,
        )


__all__ = ["LogicDiagnosisEnvironment"]
