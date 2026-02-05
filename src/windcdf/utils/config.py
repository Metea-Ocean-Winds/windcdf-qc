"""Configuration loading and management."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_config(filepath: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from file.

    Args:
        filepath: Path to config file. If None, loads defaults.

    Returns:
        Configuration dictionary.
    """
    import yaml

    # Load defaults first
    defaults_path = Path(__file__).parent.parent / "qc" / "thresholds" / "defaults.yml"
    config = {}

    if defaults_path.exists():
        with open(defaults_path) as f:
            config = yaml.safe_load(f) or {}

    # Merge with user config if provided
    if filepath:
        user_path = Path(filepath)
        if user_path.exists():
            with open(user_path) as f:
                user_config = yaml.safe_load(f) or {}
            config = merge_configs(config, user_config)

    return config


def merge_configs(base: dict, override: dict) -> dict:
    """Recursively merge configuration dictionaries.

    Args:
        base: Base configuration.
        override: Override values.

    Returns:
        Merged configuration.
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


def save_config(config: dict, filepath: str | Path) -> None:
    """Save configuration to file.

    Args:
        config: Configuration dictionary.
        filepath: Output path.
    """
    import yaml

    with open(filepath, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)
