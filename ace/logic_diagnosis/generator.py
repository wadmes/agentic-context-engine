"""Logic-diagnosis specific generator orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, MutableMapping, Optional

from ..llm import LLMClient
from ..playbook import Playbook
from ..roles import Generator, GeneratorOutput, _format_optional, _safe_json_loads
from .prompts import DECISION_MAKER_PROMPT, DEFAULT_ACTION_PROMPTS


DEFAULT_ACTION_DESCRIPTIONS = {
    "graph": "Inspect the netlist graph and fan-in/fan-out cones using the graph database and backconer.",
    "simulate": "Run ganga and hope simulations to gather response traces for candidate faults.",
    "generate_tests": "Leverage Atalanta to craft distinguishing test patterns.",
    "match_outputs": "Compare simulated and expected outputs with matcher to narrow the fault site.",
    "submit_suite": "Assemble the final diagnosis package and submit supporting tests.",
}


def _format_available_actions(actions: Mapping[str, str]) -> str:
    if not actions:
        return "(no actions configured)"
    lines = [f"- {name}: {description}" for name, description in actions.items()]
    return "\n".join(lines)


@dataclass
class DecisionMakerOutput:
    """Structured response from the decision maker."""

    reasoning: str
    action: str
    objective: str
    raw: Dict[str, Any]


class DecisionMaker:
    """Chooses which specialised generator should run next."""

    def __init__(
        self,
        llm: LLMClient,
        prompt_template: str = DECISION_MAKER_PROMPT,
        *,
        max_retries: int = 3,
    ) -> None:
        self.llm = llm
        self.prompt_template = prompt_template
        self.max_retries = max_retries

    def decide(
        self,
        *,
        question: str,
        context: Optional[str],
        playbook: Playbook,
        reflection: Optional[str],
        available_actions: Mapping[str, str],
        **kwargs: Any,
    ) -> DecisionMakerOutput:
        base_prompt = self.prompt_template.format(
            playbook=playbook.as_prompt() or "(empty playbook)",
            reflection=_format_optional(reflection),
            question=question,
            context=_format_optional(context),
            available_actions=_format_available_actions(available_actions),
        )
        prompt = base_prompt
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            response = self.llm.complete(prompt, **kwargs)
            try:
                data = _safe_json_loads(response.text)
                reasoning = str(data.get("reasoning", ""))
                action = str(data.get("action", ""))
                objective = str(data.get("objective", ""))
                if not action:
                    raise ValueError("Decision maker must provide an action identifier.")
                if not objective:
                    raise ValueError("Decision maker must provide an objective.")
                return DecisionMakerOutput(
                    reasoning=reasoning,
                    action=action,
                    objective=objective,
                    raw=data,
                )
            except ValueError as err:
                last_error = err
                if attempt + 1 >= self.max_retries:
                    break
                prompt = (
                    base_prompt
                    + "\n\nReturn a single valid JSON object with keys reasoning, action, objective."
                )
        raise RuntimeError("Decision maker failed to produce valid JSON.") from last_error


@dataclass
class ActionDefinition:
    """Metadata describing a specialised action generator."""

    generator: Generator
    description: str


def build_default_action_definitions(llm: LLMClient) -> Dict[str, ActionDefinition]:
    """Construct the default action definitions for the logic diagnosis workflow."""

    actions: Dict[str, ActionDefinition] = {}
    for action_name, prompt in DEFAULT_ACTION_PROMPTS.items():
        description = DEFAULT_ACTION_DESCRIPTIONS.get(
            action_name, f"Custom action generated from template '{action_name}'"
        )
        actions[action_name] = ActionDefinition(
            generator=Generator(llm, prompt_template=prompt),
            description=description,
        )
    return actions


class LogicDiagnosisGenerator:
    """Two-stage generator that routes through a decision maker and specialised prompts."""

    def __init__(
        self,
        *,
        decision_maker: DecisionMaker,
        action_definitions: MutableMapping[str, ActionDefinition],
    ) -> None:
        if not action_definitions:
            raise ValueError("At least one action definition must be provided.")
        self.decision_maker = decision_maker
        self.action_definitions = action_definitions

    def generate(
        self,
        *,
        question: str,
        context: Optional[str],
        playbook: Playbook,
        reflection: Optional[str] = None,
        **kwargs: Any,
    ) -> GeneratorOutput:
        decision_kwargs = kwargs.pop("decision_kwargs", {})
        action_kwargs = kwargs

        available_actions = {
            name: definition.description for name, definition in self.action_definitions.items()
        }
        decision = self.decision_maker.decide(
            question=question,
            context=context,
            playbook=playbook,
            reflection=reflection,
            available_actions=available_actions,
            **decision_kwargs,
        )

        try:
            action_definition = self.action_definitions[decision.action]
        except KeyError as exc:
            raise ValueError(f"Unknown action selected by decision maker: {decision.action}") from exc

        augmented_context_parts = [context or "", f"Objective: {decision.objective}"]
        if decision.reasoning:
            augmented_context_parts.append(f"Decision rationale: {decision.reasoning}")
        augmented_context = "\n".join(part for part in augmented_context_parts if part)

        action_output = action_definition.generator.generate(
            question=question,
            context=augmented_context,
            playbook=playbook,
            reflection=reflection,
            **action_kwargs,
        )
        metadata = dict(action_output.metadata)
        if isinstance(action_output.raw, dict):
            prediction = action_output.raw.get("fault_prediction")
            if isinstance(prediction, dict):
                metadata.setdefault("fault_prediction", prediction)
        metadata.update(
            {
                "decision": decision.raw,
                "selected_action": decision.action,
                "objective": decision.objective,
            }
        )
        return GeneratorOutput(
            reasoning=action_output.reasoning,
            final_answer=action_output.final_answer,
            bullet_ids=action_output.bullet_ids,
            raw=action_output.raw,
            metadata=metadata,
        )


__all__ = [
    "DecisionMaker",
    "DecisionMakerOutput",
    "ActionDefinition",
    "LogicDiagnosisGenerator",
    "build_default_action_definitions",
]
