from pathlib import Path

import pytest
import yaml
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from kedro_datasets.pandas import SQLQueryDataset

from cyberpunk_stats.collect.checkpoint import Checkpoint
from cyberpunk_stats.domain.classify import classify
from cyberpunk_stats.domain.constants import TRACKED
from cyberpunk_stats.pipelines import classification, endings, ingest

H = 3600
ROOT = Path(__file__).resolve().parents[1]


def make_rec(ach, playtime=600, suspect=False):
    """A player record as built by the classification pipeline, without going through SQLite."""
    return {"raw_achievements": ach, "playtime_forever": playtime, "suspect": suspect,
            "unlock_timestamps": {k: ach.get(k) for k in TRACKED}, **classify(ach)}


def run_summary(db_path: Path) -> dict:
    """Run ingest -> classification -> endings on a checkpoint, using the SQL from conf/base/catalog.yml."""
    conf = ROOT / "conf" / "base"
    entries = yaml.safe_load((conf / "catalog.yml").read_text())
    params = yaml.safe_load((conf / "parameters.yml").read_text())
    datasets = {name: SQLQueryDataset(sql=entries[name]["sql"], credentials={"con": f"sqlite:///{db_path}"})
                for name in ("checkpoint_players", "checkpoint_candidates", "checkpoint_state")}
    datasets["params:flags"] = MemoryDataset(params["flags"])
    datasets["endings_summary"] = MemoryDataset()
    catalog = DataCatalog(datasets)
    pipe = ingest.create_pipeline() + classification.create_pipeline() + endings.create_pipeline()
    SequentialRunner().run(pipe, catalog)
    return catalog.load("endings_summary")


@pytest.fixture
def checkpoint(tmp_path):
    """A fresh checkpoint plus a function that runs the pipelines on it."""
    path = tmp_path / "checkpoint.sqlite"
    return Checkpoint(path), lambda: run_summary(path)
