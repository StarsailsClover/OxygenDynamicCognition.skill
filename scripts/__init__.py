#!/usr/bin/env python3
"""Oxygen Dynamic Cognition - Package init

Modified by StarsailsClover - v26.0-alpha.8: Added v26 engine and backend exports
"""
from .prompt_library_v2 import (
    COGNITIVE_LEVELS_V2,
    DEFAULT_CONFIG_V2,
    ADAPTIVE_THRESHOLDS,
    get_prompt_v2,
    get_level_config_v2,
    next_level_v2,
    classify_problem_type,
)

# Modified by StarsailsClover - v26.0-alpha.8: Import v26 engine
from .dynamic_cognition_v26 import (
    OxygenDynamicCognitionV26,
    AdvancedCognitionEngine,
    CognitiveLevel,
    ThoughtNode,
    ThoughtGraph,
    ToolDecision,
    CognitiveBudget,
    ReflectionResult,
    VerificationResult,
    BiasDetectionResult,
)

# Modified by StarsailsClover - v26.0-alpha.8: Import backend abstraction
from .llm_backend import (
    LLMBackend,
    OpenAIBackend,
    AgentNativeBackend,
    MockBackend,
    BackendFactory,
)

__version__ = "26.0.0-alpha.8"
__all__ = [
    # v2 prompt library
    "COGNITIVE_LEVELS_V2",
    "DEFAULT_CONFIG_V2",
    "ADAPTIVE_THRESHOLDS",
    "get_prompt_v2",
    "get_level_config_v2",
    "next_level_v2",
    "classify_problem_type",
    # v26 engine
    "OxygenDynamicCognitionV26",
    "AdvancedCognitionEngine",
    "CognitiveLevel",
    "ThoughtNode",
    "ThoughtGraph",
    "ToolDecision",
    "CognitiveBudget",
    "ReflectionResult",
    "VerificationResult",
    "BiasDetectionResult",
    # Backend abstraction
    "LLMBackend",
    "OpenAIBackend",
    "AgentNativeBackend",
    "MockBackend",
    "BackendFactory",
]
