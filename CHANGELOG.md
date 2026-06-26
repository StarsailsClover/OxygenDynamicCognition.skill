# Changelog

## v26.0 Alpha 8 — 2026-06-26

### New Features
- **Backend Abstraction Layer** (`llm_backend.py`): Abstract LLM backend interface with ABC base class
  - `LLMBackend`: Abstract base class defining unified interface
  - `OpenAIBackend`: OpenAI-compatible API backend with lazy loading and retry logic
  - `AgentNativeBackend`: Agent-native mode for skill integration (no API key required)
  - `MockBackend`: Intelligent mock backend with keyword-based response templates
  - `BackendFactory`: Factory pattern for automatic backend detection and creation
- **Agent-native Mode**: Support for skill loading without API key
  - `set_llm_callable()` method to inject LLM inference function
  - `create_skill_engine()` factory function as recommended entry point
- **Context Isolation**: Two context modes for flexible reasoning
  - `shared` mode: ODC reasoning can access agent's context (default)
  - `isolated` mode: ODC reasoning in fresh context, unaffected by agent history
  - `set_context_mode()` and `set_agent_context()` methods
- **L5 Parallel Reasoning**: True parallel execution using thread pool
  - `collaborative_reasoning(question, parallel=True)` method
  - Three independent paths: forward deduction, backward verification, boundary analysis
  - Automatic fallback to serial mode on failure
- **Backend Info**: `backend_info` field in result dictionary
- **Version Field**: `version` field in result dictionary

### Bug Fixes
- **Token Budget Bug**: Fixed `run()` method resetting budget with default value instead of configured `max_tokens_budget`
  - Now stores `_max_tokens_budget_config` and uses it for reset
- **Mock Mode Quality**: Improved from simple templates to intelligent keyword-based responses
  - Supports 11+ operation types with proper detection order

### Changes
- **Console Output**: Changed from emoji to `[TAG]` format for cross-platform compatibility
- **Comments Standardization**: All modified code uses English comments
- **Code Signatures**: All modifications signed with `Modified by StarsailsClover - v26.0-alpha.8: ...`
- **odc_agent.py**: Updated to use v26 engine by default with agent-native mode support
- **__init__.py**: Updated exports to include v26 engine and backend classes

### Backward Compatibility
- All v1/v2/v21 engines remain unchanged
- `mock_mode` parameter still works (mapped to `use_mock` internally)
- `AdvancedCognitionEngine` alias preserved
- Original `MockLLM` class preserved for backward compatibility

---

## v26.0 Alpha 7 — 2026-06-26

### New Features
- **Heuristic Quick Channel**: 简单问题（事实/数学/代码）使用本地启发式评估置信度，跳过LLM调用，节省token
- **Tool Decision in Return Value**: run() 结果包含 tool_decision 字段，返回是否需要工具及工具类型
- **Content Hash Recovery Fix**: _load_all_pages 使用 content_hash（而非 vector_hash）恢复去重映射

### Bug Fixes
- _load_all_pages 使用错误的字段（vector_hash）恢复哈希映射，现已修正为 content_hash
- 版本字符串全局更新（Alpha 4 → Alpha 7）

## v26.0 Alpha 6 — 2026-06-25
### Critical Bug Fixes
- 修复 verification + self_consistency 死循环
- 高级增强改为循环执行（最多3轮）+ 熔断机制
- 自一致性结果必须经过二次验证
- 内容去重后正确更新 TLB 和持久化
