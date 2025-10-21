"""Minimal example showing the logic diagnosis workflow pieces."""

from pathlib import Path

from ace import DummyLLMClient, Playbook, Sample
from ace.logic_diagnosis import (
    DecisionMaker,
    LogicDiagnosisEnvironment,
    LogicDiagnosisGenerator,
    build_default_action_definitions,
)


def main() -> None:
    responses_path = Path(__file__).resolve().parent / "data" / "logic_tester_responses.csv"

    llm = DummyLLMClient()
    llm.queue(
        '{"reasoning": "Graph evidence narrows to PO_7 cone", "action": "graph", "objective": "Inspect the PO_7 fan-in cone"}'
    )
    llm.queue(
        '{"reasoning": "Cone inspection shows SA0 at net N1", "bullet_ids": [], "final_answer": "Fault at PO_7 cone", "fault_prediction": {"fault_location": "PO_7", "fault_behavior": "stuck-at-0"}}'
    )

    decision_maker = DecisionMaker(llm)
    action_definitions = build_default_action_definitions(llm)
    generator = LogicDiagnosisGenerator(
        decision_maker=decision_maker,
        action_definitions=action_definitions,
    )

    playbook = Playbook()
    generator_output = generator.generate(
        question="Identify the stuck-at fault location and behaviour.",
        context="Case reference: example_case",
        playbook=playbook,
    )

    environment = LogicDiagnosisEnvironment(
        responses_csv=responses_path,
        truth_table={
            "example_case": {
                "fault_location": "PO_7",
                "fault_behavior": "stuck-at-0",
            }
        },
    )
    sample = Sample(
        question="Identify the stuck-at fault location and behaviour.",
        context="Case reference: example_case",
        metadata={"case_id": "example_case"},
    )
    env_result = environment.evaluate(sample, generator_output)

    print("Selected action:", generator_output.metadata.get("selected_action"))
    print("Objective:", generator_output.metadata.get("objective"))
    print("Final answer:", generator_output.final_answer)
    print("Environment feedback:\n", env_result.feedback)


if __name__ == "__main__":
    main()
