"""Run manifest helpers for reproducible experiment records."""

from __future__ import annotations

from datetime import datetime
import json
import platform
from pathlib import Path
import sys
from typing import Any


def package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("pytest", "yaml", "matplotlib"):
        try:
            module = __import__(name)
            versions[name] = str(getattr(module, "__version__", "unknown"))
        except Exception:
            versions[name] = "not_installed"
    return versions


def write_manifest(
    run_id: str,
    output_dir: str | Path,
    *,
    config_path: str | Path | None = None,
    config_snapshot_path: str | Path | None = None,
    adapter: str | None = None,
    model: str | None = None,
    config: dict[str, Any] | None = None,
    raw_generation_files: list[str] | None = None,
    input_csvs: list[str] | None = None,
    output_reports: dict[str, Any] | None = None,
    operation: str = "pipeline",
    extra: dict[str, Any] | None = None,
) -> Path:
    manifest_dir = Path(output_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / f"manifest_{run_id}.json"
    payload = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "operation": operation,
        "config_path": str(config_path) if config_path else "",
        "config_snapshot_path": str(config_snapshot_path) if config_snapshot_path else "",
        "adapter": adapter or "",
        "model": model or "",
        "prompt_strategies": _prompt_strategies(config or {}),
        "experiment_blocks": (config or {}).get("experiment_blocks", []),
        "experiment_grid": (config or {}).get("experiment_grid", {}),
        "generation": (config or {}).get("generation", {}),
        "raw_generation_files": raw_generation_files or [],
        "input_csvs": input_csvs or [],
        "output_reports": {key: str(value) for key, value in (output_reports or {}).items()},
        "python_version": sys.version,
        "platform": platform.platform(),
        "package_versions": package_versions(),
        "extra": extra or {},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _prompt_strategies(config: dict[str, Any]) -> list[str]:
    if config.get("experiment_blocks"):
        values: list[str] = []
        for block in config["experiment_blocks"]:
            for strategy in block.get("prompt_strategies", []):
                if strategy not in values:
                    values.append(strategy)
        return values
    return list(config.get("experiment_grid", {}).get("prompt_strategies", []))

