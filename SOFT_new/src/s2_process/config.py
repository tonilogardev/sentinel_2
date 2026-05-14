from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_dotenv(path: str | Path | None = None) -> dict[str, str]:
    """Load .env file into environment variables. Returns dict of loaded vars."""
    path = Path(path or ".env")
    if not path.exists():
        return {}
    loaded: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip("\"'")
            os.environ.setdefault(key, val)
            loaded[key] = val
    return loaded


def load_pipeline(path: str | Path) -> dict[str, Any]:
    """Load pipeline.json configuration."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {path}")
    with open(path) as f:
        return json.load(f)


def get_credentials() -> dict[str, str]:
    """Get credentials from environment variables."""
    return {
        "username": os.environ.get("CDSE_USERNAME", ""),
        "password": os.environ.get("CDSE_PASSWORD", ""),
    }


def load_config(pipeline_path: str | Path, dotenv_path: str | Path | None = None) -> dict[str, Any]:
    """Load pipeline.json + .env and return merged config."""
    load_dotenv(dotenv_path or Path(pipeline_path).parent / ".env")
    config = load_pipeline(pipeline_path)
    config["_credentials"] = get_credentials()
    return config
