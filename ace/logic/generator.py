"""Two-step generator for the logic diagnosis workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
from typing import Literal

from ..llm import LLMClient
from ..playbook import Playbook
from ..roles import GeneratorOutput
from ..roles import _format_optional  # reuse helper
from ..roles import _safe_json_loads
from .prompts import LOGIC_ACTION_PROMPTS, LOGIC_DECISION_PROMPT


@dataclass
class ActionDecision:
    """Outcome of the decision maker stage."""

    action: str
    objective: str
    reasoning: str
    raw: Dict[str, Any]


class LogicDiagnosisGenerator:
    """Generator that first chooses an action and then executes it."""

    BASE_ACTION_ORDER = ("graph", "simulation", "generation", "matching", "submission")

    def __init__(
        self,
        llm: LLMClient,
        *,
        decision_prompt: str = LOGIC_DECISION_PROMPT,
        action_prompts: Optional[Mapping[str, str]] = None,
        max_retries: int = 3,
        graph_mode: Literal["disabled", "dataframe", "networkx"] = "dataframe",
    ) -> None:
        self.llm = llm
        self.decision_prompt = decision_prompt
        self.action_prompts = dict(action_prompts or LOGIC_ACTION_PROMPTS)
        self.max_retries = max_retries
        self.graph_mode = graph_mode
        if self.graph_mode not in {"disabled", "dataframe", "networkx"}:
            raise ValueError(
                "graph_mode must be one of 'disabled', 'dataframe', or 'networkx'"
            )

        if self.graph_mode == "disabled":
            self.action_prompts.pop("graph", None)

        self.available_actions = [
            action
            for action in self.BASE_ACTION_ORDER
            if action in self.action_prompts
        ]
        extra_actions = [
            action
            for action in self.action_prompts
            if action not in self.available_actions
        ]
        self.available_actions.extend(extra_actions)
        if not self.available_actions:
            raise ValueError("LogicDiagnosisGenerator requires at least one action prompt.")

        self.graph_guidance = self._build_graph_guidance()

    def generate(
        self,
        *,
        question: str,
        context: Optional[str],
        playbook: Playbook,
        reflection: Optional[str] = None,
        tester_responses: Optional[str] = None,
        **kwargs: Any,
    ) -> GeneratorOutput:
        decision = self._decide_action(
            question=question,
            context=context,
            playbook=playbook,
            reflection=reflection,
        )
        action_prompt = self._render_action_prompt(
            decision=decision,
            question=question,
            context=context,
            playbook=playbook,
            reflection=reflection,
            tester_responses=tester_responses,
        )
        action_output = self._invoke_action(action_prompt, **kwargs)
        payload = dict(action_output.raw)
        payload["decision"] = decision.raw
        return GeneratorOutput(
            reasoning=action_output.reasoning,
            final_answer=action_output.final_answer,
            bullet_ids=action_output.bullet_ids,
            raw=payload,
        )

    # ------------------------------------------------------------------ #
    def _decide_action(
        self,
        *,
        question: str,
        context: Optional[str],
        playbook: Playbook,
        reflection: Optional[str],
    ) -> ActionDecision:
        prompt = self.decision_prompt.format(
            playbook=playbook.as_prompt() or "(empty playbook)",
            reflection=_format_optional(reflection),
            question=question,
            context=_format_optional(context),
            available_actions=", ".join(self.available_actions),
            graph_guidance=self.graph_guidance,
        )
        response = self.llm.complete(prompt)
        data = _safe_json_loads(response.text)
        action = str(data.get("action", "")).strip().lower()
        if action not in self.action_prompts:
            valid = ", ".join(sorted(self.action_prompts))
            raise ValueError(f"Unsupported action '{action}'. Valid options: {valid}")
        objective = str(data.get("objective", "")).strip()
        reasoning = str(data.get("reasoning", "")).strip()
        return ActionDecision(
            action=action,
            objective=objective,
            reasoning=reasoning,
            raw=data,
        )

    def _render_action_prompt(
        self,
        *,
        decision: ActionDecision,
        question: str,
        context: Optional[str],
        playbook: Playbook,
        reflection: Optional[str],
        tester_responses: Optional[str],
    ) -> str:
        template = self.action_prompts[decision.action]
        return template.format(
            playbook=playbook.as_prompt() or "(empty playbook)",
            reflection=_format_optional(reflection),
            question=question,
            context=_format_optional(context),
            decision_reasoning=decision.reasoning or "(no reasoning provided)",
            objective=decision.objective or "(unspecified)",
            tester_responses=_format_optional(tester_responses),
            graph_guidance=self.graph_guidance,
        )

    def _invoke_action(self, prompt: str, **kwargs: Any) -> GeneratorOutput:
        last_error: Optional[Exception] = None
        base_prompt = prompt
        for attempt in range(self.max_retries):
            response = self.llm.complete(prompt, **kwargs)
            try:
                data = _safe_json_loads(response.text)
            except ValueError as err:
                last_error = err
                if attempt + 1 >= self.max_retries:
                    break
                prompt = base_prompt + "\n\nReturn only valid JSON with reasoning, bullet_ids, final_answer."
                continue
            reasoning = str(data.get("reasoning", ""))
            final_answer_field = data.get("final_answer", "")
            if isinstance(final_answer_field, (dict, list)):
                final_answer = json.dumps(final_answer_field, ensure_ascii=False)
            else:
                final_answer = str(final_answer_field)
            bullet_ids = [
                str(item)
                for item in data.get("bullet_ids", [])
                if isinstance(item, (str, int))
            ]
            return GeneratorOutput(
                reasoning=reasoning,
                final_answer=final_answer,
                bullet_ids=bullet_ids,
                raw=data,
            )
        raise RuntimeError("LogicDiagnosisGenerator failed to obtain valid JSON.") from last_error

    def _build_graph_guidance(self) -> str:
        if self.graph_mode == "disabled":
            return "Graph actions are disabled for this task; select another action."
        if self.graph_mode == "dataframe":
            return (
                "Graph actions operate on a pandas DataFrame where each row describes a"
                " netlist edge with columns edge_id, net_name, corresponding_gate_type,"
                " corresponding_node_id, parent_edge_id (list[int]), and child_edge_id"
                " (list[int]). Provide Python snippets to query the DataFrame when"
                " needed."
            )
        return (
            "Graph actions operate on a NetworkX graph representation of the netlist."
            " Use the NetworkX API to traverse fan-in/fan-out cones and collect"
            " structural insights."
        )
