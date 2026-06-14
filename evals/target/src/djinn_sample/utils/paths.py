from pathlib import Path

CACHE_DIR = Path(".cache/djinn-sample")


def artifact_path(artifact_id: str) -> Path:
    return CACHE_DIR / f"{artifact_id}.json"
