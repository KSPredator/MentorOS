"""
MentorOS - Agents Module
Multi-agent system: Planner Agent (routing) and Evaluation Agent (hallucination gating).

Note: the Planner Agent only needs the stdlib + `llm.ollama_client`;
the Evaluation Agent additionally needs torch + sentence-transformers
(embeddings). Imports are lazy so the planner stays usable even before the
heavy pipeline deps are installed. Import directly from submodules for
concrete classes:
    from agents.planner_agent import PlannerAgent, PlannerAction, PlanDecision
    from agents.evaluation_agent import EvaluationAgent, EvaluationResult
"""


def __getattr__(name):
    if name in ("PlannerAgent", "PlannerAction", "PlanDecision"):
        from agents.planner_agent import PlannerAgent, PlannerAction, PlanDecision
        globals()["PlannerAgent"] = PlannerAgent
        globals()["PlannerAction"] = PlannerAction
        globals()["PlanDecision"] = PlanDecision
        return globals()[name]
    if name in ("EvaluationAgent", "EvaluationResult"):
        from agents.evaluation_agent import EvaluationAgent, EvaluationResult
        globals()["EvaluationAgent"] = EvaluationAgent
        globals()["EvaluationResult"] = EvaluationResult
        return globals()[name]
    raise AttributeError(f"module 'agents' has no attribute {name!r}")


__all__ = [
    "PlannerAgent",
    "PlannerAction",
    "PlanDecision",
    "EvaluationAgent",
    "EvaluationResult",
]