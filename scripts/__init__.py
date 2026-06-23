#!/usr/bin/env python3
"""Oxygen Dynamic Cognition - Package init"""

from .prompt_library_v2 import (
    COGNITIVE_LEVELS_V2,
    DEFAULT_CONFIG_V2,
    ADAPTIVE_THRESHOLDS,
    get_prompt_v2,
    get_level_config_v2,
    next_level_v2,
    classify_problem_type,
)

__version__ = "2.0.0"
__all__ = [
    "COGNITIVE_LEVELS_V2",
    "DEFAULT_CONFIG_V2",
    "ADAPTIVE_THRESHOLDS",
    "get_prompt_v2",
    "get_level_config_v2",
    "next_level_v2",
    "classify_problem_type",
]
