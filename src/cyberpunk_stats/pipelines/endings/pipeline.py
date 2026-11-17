from kedro.pipeline import Node, Pipeline

from .completion import completionists
from .first_endings import route_availability, unmarked_breakdown, world_cosync
from .groups import pl_vs_main, rusher_playtime
from .nodes import (assemble_summary, compute_sampling_bias, compute_tracks, compute_tracks_clean, run_metrics,
                    story_funnels)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        Node(run_metrics, ["run_state", "candidate_summary", "player_records"], "run_metrics", name="run_metrics"),
        Node(route_availability, "player_records", "route_availability", name="route_availability"),
        Node(compute_tracks, ["player_records", "route_availability"], "tracks", name="tracks"),
        Node(compute_tracks_clean, "clean_player_records", "tracks_clean", name="tracks_clean"),
        Node(world_cosync, "player_records", "world_cosync", name="world_cosync"),
        Node(unmarked_breakdown, "player_records", "unmarked_breakdown", name="unmarked_breakdown"),
        Node(pl_vs_main, "player_records", "pl_vs_main", name="pl_vs_main"),
        Node(rusher_playtime, "player_records", "rusher_playtime", name="rusher_playtime"),
        Node(completionists, "player_records", "completionists", name="completionists"),
        Node(compute_sampling_bias, ["candidate_summary", "player_records", "tracks"], "sampling_bias",
             name="sampling_bias"),
        Node(story_funnels, "player_records", "story_funnel", name="story_funnel"),
        Node(assemble_summary,
             ["achievement_mapping", "run_metrics", "params:flags", "tracks", "tracks_clean", "world_cosync",
              "unmarked_breakdown", "route_availability", "pl_vs_main", "rusher_playtime", "completionists",
              "sampling_bias", "story_funnel"],
             "endings_summary", name="assemble_summary"),
    ])
