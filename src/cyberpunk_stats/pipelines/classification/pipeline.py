from kedro.pipeline import Node, Pipeline

from .nodes import build_records, clean_records


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        Node(build_records, ["checkpoint_players", "achievement_mapping", "params:flags"], "player_records",
             name="build_records"),
        Node(clean_records, "player_records", "clean_player_records", name="clean_records"),
    ])
