# Architecture Optimization Plan
## Oxygen Dynamic Cognition v26.0-alpha.7 → v26.0-alpha.8

**Author**: StarsailsClover
**Date**: 2026-06-26
**Version**: v26.0-alpha.8

---

## 1. Overview

This document outlines the architecture improvements made in v26.0-alpha.8, addressing 14 design issues identified in the code audit. The primary focus is on backend abstraction, agent-native integration, and improved extensibility.

---

## 2. Architecture Before (v26.0-alpha.7)

```
┌─────────────────────────────────────────────────┐
│          OxygenDynamicCognitionV26              │
├─────────────────────────────────────────────────┤
│  - Direct OpenAI client initialization          │
│  - Hardcoded API calls                          │
│  - Internal MockLLM class (tightly coupled)     │
│  - No agent-native support                      │
│  - Serial L5 reasoning                          │
│  - Token budget reset bug                       │
└─────────────────────────────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │   OpenAI API     │
              │  (Direct Call)   │
              └──────────────────┘
```

### Problems
1. **Tight coupling**: Engine directly depends on OpenAI SDK
2. **No extensibility**: Cannot add new backends without modifying core code
3. **No agent-native mode**: Skill cannot reuse host agent's LLM
4. **No context isolation**: Every inference carries full context
5. **Serial L5**: "Collaborative" reasoning is actually sequential

---

## 3. Architecture After (v26.0-alpha.8)

```
┌─────────────────────────────────────────────────────────────┐
│               OxygenDynamicCognitionV26                     │
├─────────────────────────────────────────────────────────────┤
│  - Uses LLMBackend interface                                │
│  - BackendFactory for automatic detection                   │
│  - Agent-native mode support                                │
│  - Context isolation (shared/isolated)                      │
│  - Parallel L5 reasoning (ThreadPoolExecutor)               │
│  - Fixed token budget reset                                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   LLMBackend (ABC)  │
                    │  - chat_completion  │
                    │  - get_backend_info │
                    │  - is_available     │
                    │  - estimate_tokens  │
                    └──────────┬──────────┘
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  OpenAIBackend   │ │ AgentNativeBack- │ │   MockBackend    │
│  - Lazy loading  │ │    end           │ │  - Keyword-based │
│  - Retry logic   │ │  - llm_callable  │ │    smart replies │
│  - Token tracking│ │  - Context modes │ │  - 11+ op types  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
           │                   │
           ▼                   ▼
    ┌──────────┐        ┌──────────┐
    │ OpenAI   │        │  Host    │
    │   API    │        │  Agent   │
    └──────────┘        └──────────┘
```

---

## 4. Key Improvements

### 4.1 Backend Abstraction Layer

**Pattern**: Abstract Base Class + Factory Pattern

**Interface** (`LLMBackend`):
```python
class LLMBackend(ABC):
    def chat_completion(self, messages: List[Dict], **kwargs) -> str: ...
    def get_backend_info(self) -> Dict[str, str]: ...
    def is_available(self) -> bool: ...
    def estimate_tokens(self, text: str) -> int: ...
```

**Implementations**:
- `OpenAIBackend`: Original API-based backend, now with lazy loading and retry logic
- `AgentNativeBackend`: Skill/agent integration mode, injects `llm_callable`
- `MockBackend`: Intelligent testing backend with keyword-matched responses

**Factory** (`BackendFactory`):
- `create_backend()`: Creates backend based on explicit parameters
- `auto_detect()`: Intelligently detects and creates appropriate backend
  - Priority: `use_mock=True` → `llm_callable` present → OpenAI (with API key) → fallback to Mock

### 4.2 Agent-native Mode

**Design Rationale**:
- Skills are typically loaded by agents, which already have LLM access
- Requiring a separate API key for each skill is redundant and wasteful
- Agent-native mode allows ODC to reuse the host agent's LLM capability

**Implementation**:
```python
# Recommended entry point for skill loading
def create_skill_engine(llm_callable=None, context_mode="shared", **kwargs):
    return OxygenDynamicCognitionV26(
        llm_callable=llm_callable,
        context_mode=context_mode,
        **kwargs
    )

# Runtime injection (if LLM becomes available later)
engine.set_llm_callable(my_llm_function)
```

**llm_callable Signature**:
```python
def llm_callable(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Args:
        messages: List of message dicts with 'role' and 'content'
        **kwargs: Additional parameters (temperature, max_tokens, etc.)
    Returns:
        str: Model response text
    """
```

### 4.3 Context Isolation

**Two Modes**:

1. **`shared` (default)**:
   - ODC reasoning can access the agent's conversation context
   - Good for: Continuation of reasoning, building on previous context
   - Trade-off: Higher token usage, potential bias from history

2. **`isolated`**:
   - ODC reasoning runs in a fresh context, no history
   - Good for: Unbiased analysis, fresh perspective, verification
   - Trade-off: No context continuity, lower token usage

**API**:
```python
engine.set_context_mode("isolated")  # or "shared"
engine.set_agent_context(agent_messages)  # Update shared context
```

### 4.4 L5 Parallel Reasoning

**Before**: Sequential execution of 3 reasoning paths
- Total time = sum of all path times
- No actual parallelism despite "collaborative" name

**After**: True parallel execution using `ThreadPoolExecutor`
- Three independent paths: Forward deduction, Backward verification, Boundary analysis
- Total time ≈ max of path times (with thread overhead)
- Automatic fallback to serial mode on failure

**API**:
```python
result = engine.collaborative_reasoning(question, parallel=True)
# result contains: paths, final_answer, consensus_score, parallel flag
```

### 4.5 Token Budget Bug Fix

**Bug**: `run()` reset budget using `self.budget.max_tokens` (current value) instead of configured value

**Fix**: Store original configuration at initialization
```python
# __init__
self._max_tokens_budget_config = max_tokens

# run()
self.budget = CognitiveBudget(
    max_tokens=self._max_tokens_budget_config,  # Use stored config
    max_rounds=self.max_rounds,
)
```

---

## 5. Backward Compatibility

All changes maintain full backward compatibility:

| Feature | Alpha 7 | Alpha 8 |
|---------|---------|---------|
| `mock_mode` parameter | ✅ | ✅ (mapped to `use_mock`) |
| `AdvancedCognitionEngine` alias | ✅ | ✅ |
| `EnhancedCognitionEngineV21` alias | ✅ | ✅ |
| Original `MockLLM` class | ✅ | ✅ (preserved internally) |
| v1/v2/v21 engines | ✅ | ✅ (unchanged) |
| OpenAI API mode | ✅ | ✅ (now via `OpenAIBackend`) |

---

## 6. Extensibility

### Adding a New Backend

```python
from .llm_backend import LLMBackend

class CustomBackend(LLMBackend):
    def chat_completion(self, messages, **kwargs):
        # Custom implementation
        pass
    
    def get_backend_info(self):
        return {"type": "custom", "model": "..."}
    
    def is_available(self):
        return True
    
    def estimate_tokens(self, text):
        return len(text) // 3  # Conservative estimate
```

Then register with `BackendFactory` or use directly:
```python
engine = OxygenDynamicCognitionV26(use_mock=False)
engine._backend = CustomBackend()  # Or add to factory
```

---

## 7. Performance Considerations

### L5 Parallelism
- **Best case**: 3x speedup for L5 reasoning (CPU-bound paths)
- **Realistic**: 2-2.5x speedup (thread overhead, GIL for Python)
- **Note**: I/O-bound API calls benefit most from threading

### Token Estimation
- Character-count based estimation (`len(text) // 3`)
- Conservative overestimate to avoid budget overruns
- Actual token counting still used when available (OpenAI backend)

---

## 8. Future Roadmap

### v26.0-alpha.9 (Planned)
- Streaming output support
- More sophisticated token counting (tiktoken integration)
- Plugin system for custom reasoning strategies
- Additional backends (Anthropic, Google, etc.)

### v26.0-beta (Planned)
- Comprehensive test suite
- Performance benchmarks
- Full documentation site
- Type hints completion

---

## 9. Files Changed

| File | Type | Description |
|------|------|-------------|
| `scripts/llm_backend.py` | New | Backend abstraction layer |
| `scripts/dynamic_cognition_v26.py` | Modified | Backend integration, L5 parallelism, bug fixes |
| `scripts/odc_agent.py` | Modified | v26 engine, agent-native mode, [TAG] format |
| `scripts/__init__.py` | Modified | Updated exports, version |
| `CHANGELOG.md` | Modified | Alpha 8 changelog |
| `CODE_AUDIT_REPORT.md` | New | Audit findings |
| `ARCHITECTURE_OPTIMIZATION.md` | New | This document |
| `MULTI_PLATFORM_COMPATIBILITY.md` | New | Cross-platform guide |
| `SKILL.md` | Modified | Updated documentation |
| `SKILL_zh.md` | Modified | Updated documentation (Chinese) |
