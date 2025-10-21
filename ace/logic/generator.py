"""Two-step generator for the logic diagnosis workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from ..llm import LLMClient
from ..playbook import Playbook
from ..roles import GeneratorOutput
from ..roles import _format_optional  # reuse helper
from ..roles import _safe_json_loads
from .prompts import build_logic_prompts


@dataclass
class ActionDecision:
    """Outcome of the decision maker stage."""

    action: str
    objective: str
    reasoning: str
    raw: Dict[str, Any]


class LogicDiagnosisGenerator:
    """Generator that first chooses an action and then executes it.

    Parameters
    ----------
    graph_mode:
        Controls how the graph specialist behaves. Use ``"none"`` to disable
        graph actions, ``"dataframe"`` (default) to query a pandas DataFrame,
        or ``"networkx"`` to traverse a NetworkX graph representation.
    """

    def __init__(
        self,
        llm: LLMClient,
        *,
        graph_mode: str = "dataframe",
        decision_prompt: Optional[str] = None,
        action_prompts: Optional[Mapping[str, str]] = None,
        max_retries: int = 3,
    ) -> None:
        self.llm = llm
        default_decision, default_actions = build_logic_prompts(graph_mode)
        self.decision_prompt = decision_prompt or default_decision
        self.action_prompts = dict(action_prompts or default_actions)
        self.graph_mode = graph_mode
        self.max_retries = max_retries

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
