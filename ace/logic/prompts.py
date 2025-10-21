"""Prompt templates for the logic diagnosis workflow."""

LOGIC_GRAPH_MODES = ("none", "dataframe", "networkx")

_DECISION_PROMPT_TEMPLATE = """
You are the logic diagnosis decision maker coordinating specialized tools:
{tooling_overview}

Playbook of current strategies:
{playbook}

Recent reflections:
{reflection}

Task: {question}
Context: {context}

Return JSON with keys `reasoning`, `action`, and `objective`.
The `action` must be one of [{actions_list}].
Describe the `objective` that the chosen specialist must accomplish.
""".strip()

_BASE_TOOLING_LINES = [
    "- simulation: call ganga or hope to obtain faulty responses for suspected stuck-at faults.",
    "- generation: leverage atalanta to synthesize distinguishing test patterns.",
    "- matching: analyse tester responses with matcher to compare outputs.",
    "- submission: bundle the best hypotheses and send them with submit_tests.",
]

_GRAPH_TOOLING_LINE = {
    "dataframe": (
        "- graph: use the netlist DataFrame (edge_id, net_name, corresponding_gate_type, "
        "corresponding_node_id, parent_edge_id, child_edge_id) and backconer to understand structural cones."
    ),
    "networkx": (
        "- graph: traverse the netlist NetworkX graph with backconer to understand structural cones."
    ),
}

_GRAPH_ACTION_PROMPTS = {
    "dataframe": """
You are the graph specialist using the netlist DataFrame and backconer.
You may write concise Python snippets to query the DataFrame columns
(`edge_id`, `net_name`, `corresponding_gate_type`, `corresponding_node_id`, `parent_edge_id`, `child_edge_id`) and summarise the findings.

Playbook:
{playbook}

Decision reasoning: {decision_reasoning}
Objective: {objective}
Task: {question}
Context: {context}
Recent reflections:
{reflection}

Return JSON with `reasoning`, `bullet_ids`, and `final_answer` describing the suspected stuck-at fault.
The `final_answer` must be valid JSON with fields `location` and `behavior`.
""".strip(),
    "networkx": """
You are the graph specialist using the netlist NetworkX graph and backconer.
Use NetworkX API calls to explore cones, predecessors, and successors that are relevant to the suspected fault.

Playbook:
{playbook}

Decision reasoning: {decision_reasoning}
Objective: {objective}
Task: {question}
Context: {context}
Recent reflections:
{reflection}

Return JSON with `reasoning`, `bullet_ids`, and `final_answer` describing the suspected stuck-at fault.
The `final_answer` must be valid JSON with fields `location` and `behavior`.
""".strip(),
}

_COMMON_ACTION_PROMPTS = {
    "simulation": """
You are the simulation specialist coordinating ganga and hope.
Use their responses to validate or invalidate candidate faults.

Playbook:
{playbook}

Decision reasoning: {decision_reasoning}
Objective: {objective}
Task: {question}
Context: {context}
Recent reflections:
{reflection}
Tester responses:
{tester_responses}

Return JSON with `reasoning`, `bullet_ids`, and `final_answer` describing the suspected stuck-at fault.
The `final_answer` must be valid JSON with fields `location` and `behavior`.
""".strip(),
    "generation": """
You are the test generation specialist using atalanta.
Design new distinguishing patterns that help isolate the stuck-at fault.

Playbook:
{playbook}

Decision reasoning: {decision_reasoning}
Objective: {objective}
Task: {question}
Context: {context}
Recent reflections:
{reflection}
Tester responses:
{tester_responses}

Return JSON with `reasoning`, `bullet_ids`, and `final_answer` describing the suspected stuck-at fault.
The `final_answer` must be valid JSON with fields `location` and `behavior`.
""".strip(),
    "matching": """
You are the mismatch analyst using matcher to compare observed and expected outputs.
Summarise which outputs disagree and what fault hypotheses they support.

Playbook:
{playbook}

Decision reasoning: {decision_reasoning}
Objective: {objective}
Task: {question}
Context: {context}
Recent reflections:
{reflection}
Tester responses:
{tester_responses}

Return JSON with `reasoning`, `bullet_ids`, and `final_answer` describing the suspected stuck-at fault.
The `final_answer` must be valid JSON with fields `location` and `behavior`.
""".strip(),
    "submission": """
You are the closer responsible for packaging the leading hypothesis and calling submit_tests.
Ensure the final answer reflects the best available evidence from previous steps.

Playbook:
{playbook}

Decision reasoning: {decision_reasoning}
Objective: {objective}
Task: {question}
Context: {context}
Recent reflections:
{reflection}
Tester responses:
{tester_responses}

Return JSON with `reasoning`, `bullet_ids`, and `final_answer` describing the suspected stuck-at fault.
The `final_answer` must be valid JSON with fields `location` and `behavior`.
""".strip(),
}


def build_logic_prompts(graph_mode: str) -> tuple[str, dict[str, str]]:
    """Return the decision and action prompts for the requested graph mode."""

    if graph_mode not in LOGIC_GRAPH_MODES:
        valid = ", ".join(LOGIC_GRAPH_MODES)
        raise ValueError(f"Unsupported graph_mode '{graph_mode}'. Valid options: {valid}")

    tooling_lines = list(_BASE_TOOLING_LINES)
    action_prompts = dict(_COMMON_ACTION_PROMPTS)

    if graph_mode != "none":
        tooling_lines.insert(0, _GRAPH_TOOLING_LINE[graph_mode])
        action_prompts["graph"] = _GRAPH_ACTION_PROMPTS[graph_mode]

    actions_order = ["simulation", "generation", "matching", "submission"]
    if graph_mode != "none":
        actions_order.insert(0, "graph")

    decision_prompt = _DECISION_PROMPT_TEMPLATE.format(
        tooling_overview="\n".join(tooling_lines),
        playbook="{playbook}",
        reflection="{reflection}",
        question="{question}",
        context="{context}",
        actions_list=", ".join(actions_order),
    )

    return decision_prompt, action_prompts


# Default prompts preserve the previous behaviour (DataFrame-backed graph tooling).
LOGIC_DECISION_PROMPT, LOGIC_ACTION_PROMPTS = build_logic_prompts("dataframe")
