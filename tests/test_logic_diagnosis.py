import json
import unittest
from pathlib import Path

from ace import (
    DummyLLMClient,
    FaultSpec,
    GeneratorOutput,
    LogicDiagnosisEnvironment,
    LogicDiagnosisGenerator,
    Playbook,
    Sample,
)


class LogicDiagnosisGeneratorTest(unittest.TestCase):
    def test_two_stage_generation_routes_action(self) -> None:
        client = DummyLLMClient()
        client.queue(
            json.dumps(
                {
                    "reasoning": "Graph investigation will narrow the suspect cone.",
                    "action": "graph",
                    "objective": "Inspect the fan-in cone for PO1.",
                }
            )
        )
        client.queue(
            json.dumps(
                {
                    "reasoning": "Cone analysis implicates gate N12 stuck-at-1.",
                    "bullet_ids": ["b-001"],
                    "final_answer": {
                        "location": "N12",
                        "behavior": "stuck-at-1",
                    },
                }
            )
        )
        generator = LogicDiagnosisGenerator(client)
        output = generator.generate(
            question="Diagnose the fault",
            context="",
            playbook=Playbook(),
        )
        decision = output.raw["decision"]
        self.assertEqual(decision["action"], "graph")
        final_payload = json.loads(output.final_answer)
        self.assertEqual(final_payload["location"], "N12")
        self.assertEqual(final_payload["behavior"], "stuck-at-1")
        self.assertEqual(output.bullet_ids, ["b-001"])

    def test_graph_mode_disabled_blocks_graph_action(self) -> None:
        client = DummyLLMClient()
        client.queue(
            json.dumps(
                {
                    "reasoning": "Attempt graph even though disabled.",
                    "action": "graph",
                    "objective": "Inspect the cone",
                }
            )
        )
        generator = LogicDiagnosisGenerator(client, graph_mode="disabled")
        with self.assertRaises(ValueError):
            generator.generate(question="", context="", playbook=Playbook())


class LogicDiagnosisEnvironmentTest(unittest.TestCase):
    def test_environment_scores_prediction(self) -> None:
        env = LogicDiagnosisEnvironment({
            "F1": FaultSpec(location="N12", behavior="stuck-at-0")
        })
        sample = Sample(question="", metadata={"fault_id": "F1"})
        generator_output = GeneratorOutput(
            reasoning="",
            final_answer=json.dumps({"location": "N12", "behavior": "stuck-at-0"}),
            bullet_ids=[],
            raw={},
        )
        result = env.evaluate(sample, generator_output)
        self.assertEqual(result.metrics["accuracy"], 1.0)
        self.assertIn("predicted", result.feedback)

    def test_load_tester_responses_parses_json_schema(self) -> None:
        payload = [
            {
                "input_patterns": [{"PI1": 0}],
                "good_outputs": [{"PO1": 1}],
                "faulty_outputs": [{"PO1": 0}],
                "differences": ["PO1"],
            },
            {
                "input_patterns": [{"PI1": 1}],
                "good_outputs": [{"PO1": 0}],
                "faulty_outputs": [{"PO1": 1}],
                "differences": ["PO1"],
            },
        ]
        path = Path("tester_responses.json")
        try:
            path.write_text(json.dumps(payload), encoding="utf-8")
            responses = list(LogicDiagnosisEnvironment.load_tester_responses(path))
        finally:
            if path.exists():
                path.unlink()
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0].differences, ["PO1"])


if __name__ == "__main__":
    unittest.main()
