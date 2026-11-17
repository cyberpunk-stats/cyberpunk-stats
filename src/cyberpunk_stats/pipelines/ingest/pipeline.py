from kedro.pipeline import Node, Pipeline

from .nodes import achievement_mapping, decode_state, summarize_candidates


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        Node(decode_state, "checkpoint_state", "run_state", name="decode_state"),
        Node(achievement_mapping, "run_state", "achievement_mapping", name="achievement_mapping"),
        Node(summarize_candidates, "checkpoint_candidates", "candidate_summary", name="summarize_candidates"),
    ])
