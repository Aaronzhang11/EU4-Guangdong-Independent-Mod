#!/usr/bin/env python3
"""Shared support for country definitions created by map pipelines."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from apply_culture_country_name_pools import generated_country_data  # noqa: E402


def country_definition_bytes(definition: str, culture: str) -> bytes:
    """Attach the deterministic Chinese monarch and dynasty pools."""
    return generated_country_data(definition.encode("ascii"), culture)
