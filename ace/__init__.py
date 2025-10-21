"""Agentic Context Engineering (ACE) reproduction framework."""

from .playbook import Bullet, Playbook
from .delta import DeltaOperation, DeltaBatch
from .llm import LLMClient, DummyLLMClient, TransformersLLMClient
from .roles import (
    Generator,
    Reflector,
    Curator,
    GeneratorOutput,
    ReflectorOutput,
    CuratorOutput,
)
from .adaptation import (
    OfflineAdapter,
    OnlineAdapter,
    Sample,
    TaskEnvironment,
    EnvironmentResult,
    AdapterStepResult,
)
from .logic import (
    FaultSpec,
    LogicDiagnosisEnvironment,
    TesterResponse,
    ActionDecision,
    LogicDiagnosisGenerator,
    LOGIC_DECISION_PROMPT,
    LOGIC_ACTION_PROMPTS,
    LOGIC_GRAPH_MODES,
    build_logic_prompts,
)

# Import production LLM clients if available
try:
    from .llm_providers import LiteLLMClient

    LITELLM_AVAILABLE = True
except ImportError:
    LiteLLMClient = None
    LITELLM_AVAILABLE = False

__all__ = [
    "Bullet",
    "Playbook",
    "DeltaOperation",
    "DeltaBatch",
    "LLMClient",
    "DummyLLMClient",
    "TransformersLLMClient",
    "LiteLLMClient",
    "Generator",
    "Reflector",
    "Curator",
    "GeneratorOutput",
    "ReflectorOutput",
    "CuratorOutput",
    "FaultSpec",
    "LogicDiagnosisEnvironment",
    "TesterResponse",
    "ActionDecision",
    "LogicDiagnosisGenerator",
    "LOGIC_DECISION_PROMPT",
    "LOGIC_ACTION_PROMPTS",
    "LOGIC_GRAPH_MODES",
    "build_logic_prompts",
    "OfflineAdapter",
    "OnlineAdapter",
    "Sample",
    "TaskEnvironment",
    "EnvironmentResult",
    "AdapterStepResult",
    "LITELLM_AVAILABLE",
]
