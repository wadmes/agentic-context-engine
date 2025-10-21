"""Logic diagnosis extensions for ACE."""

from .environment import FaultSpec, LogicDiagnosisEnvironment, TesterResponse
from .generator import (
    ActionDecision,
    LogicDiagnosisGenerator,
)
from .prompts import (
    LOGIC_ACTION_PROMPTS,
    LOGIC_DECISION_PROMPT,
    LOGIC_GRAPH_MODES,
    build_logic_prompts,
)

__all__ = [
    "FaultSpec",
    "LogicDiagnosisEnvironment",
    "TesterResponse",
    "ActionDecision",
    "LogicDiagnosisGenerator",
    "LOGIC_DECISION_PROMPT",
    "LOGIC_ACTION_PROMPTS",
    "LOGIC_GRAPH_MODES",
    "build_logic_prompts",
]
