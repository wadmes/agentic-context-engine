"""Example workflow for the logic diagnosis environment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ace import (
    DummyLLMClient,
    FaultSpec,
    LogicDiagnosisEnvironment,
    LogicDiagnosisGenerator,
    OfflineAdapter,
    Playbook,
    Sample,
    Curator,
    Reflector,
)

TEST_RESPONSES = [
    {
        "input_patterns": [{"PI1": 0, "PI2": 1}],
        "good_outputs": [{"PO1": 0, "PO3": 1}],
        "faulty_outputs": [{"PO1": 1, "PO3": 0}],
        "differences": ["PO1", "PO3"],
    },
    {
        "input_patterns": [{"PI1": 1, "PI2": 0}],
        "good_outputs": [{"PO1": 1, "PO3": 0}],
        "faulty_outputs": [{"PO1": 0, "PO3": 0}],
        "differences": ["PO1"],
    },
]


def build_dummy_client() -> DummyLLMClient:
    client = DummyLLMClient()
    # Decision stage chooses the matching specialist.
    client.queue(
        json.dumps(
            {
                "reasoning": "Mismatch analysis will prioritise the failing outputs.",
                "action": "matching",
                "objective": "Summarise the mismatched outputs and propose the leading fault.",
            }
        )
    )
    # Action stage emits a final answer.
    client.queue(
        json.dumps(
            {
                "reasoning": "The PO1/PO3 discrepancies implicate gate N12 stuck-at-0.",
                "bullet_ids": [],
                "final_answer": {
                    "location": "N12",
                    "behavior": "stuck-at-0",
                },
            }
        )
    )
    # Reflection
    client.queue(
        json.dumps(
            {
                "reasoning": "Cross-checks confirmed the diagnosis.",
                "error_identification": "",
                "root_cause_analysis": "",
                "correct_approach": "Continue combining matcher evidence with structural reasoning.",
                "key_insight": "Inverted cones often manifest in paired PO errors.",
                "bullet_tags": [],
            }
        )
    )
    # Curation
    client.queue(
        json.dumps(
            {
                "reasoning": "Store the cone-analysis heuristic.",
                "operations": [
                    {
                        "type": "ADD",
                        "section": "cone_analysis",
                        "content": "When PO pairs fail together, inspect the shared fan-in cone using backconer.",
                        "metadata": {"helpful": 1},
                    }
                ],
            }
        )
    )
    return client


def run_demo() -> None:
    client = build_dummy_client()
    generator = LogicDiagnosisGenerator(client, graph_mode="networkx")
    reflector = Reflector(client)
    curator = Curator(client)
    playbook = Playbook()

    ground_truth = {"F1": FaultSpec(location="N12", behavior="stuck-at-0")}
    environment = LogicDiagnosisEnvironment(ground_truth)

    sample = Sample(
        question="Identify the stuck-at fault given the tester responses.",
        context="Use the provided tools to narrow down the defect.",
        metadata={"fault_id": "F1", "tester_responses": TEST_RESPONSES},
    )

    adapter = OfflineAdapter(
        playbook=playbook,
        generator=generator,
        reflector=reflector,
        curator=curator,
    )

    tester_context = json.dumps(TEST_RESPONSES)
    results = adapter.run(
        [sample],
        environment,
        epochs=1,
        generator_kwargs={"tester_responses": tester_context},
    )

    for result in results:
        print("Final answer:", result.generator_output.final_answer)
        print("Environment feedback:", result.environment_result.feedback)
        print("Metrics:", result.environment_result.metrics)


if __name__ == "__main__":
    run_demo()
