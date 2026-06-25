# Changelog

## v26.0 Alpha 5 — 2026-06-25

### Bug Fixes & Performance
- **修复真实 API 调用**：`_call_llm()` 非 mock 模式不再 fallback 到 MockLLM，真实 OpenAI 调用现在正常工作
- **添加 `_init_client()`**：初始化 OpenAI 兼容客户端，支持环境变量和参数传入
- **添加 `_real_api_call()`**：实际 API 调用方法，带 token 追踪

### Default Configuration Optimization
- model: gpt-4 → gpt-3.5-turbo（性价比优化）
- max_rounds: 10 → 4（减少冗余）
- max_level: 5 → 4（L5 协同默认关闭）
- start_level: 2 → 1（不预判难度）
- confidence_threshold: 0.75 → 0.80
- max_tokens: 4096 → 2048
- ToT/Reflection/Verification/SelfConsistency/BiasDetection: 全默认关闭（按需启用）

### Tests
- 47项测试套件 + 新增 mock 模式端到端测试

## v26.0 Alpha 4 — 2026-06-24
### 🚀 前沿技术集成
- **思维树（Tree of Thoughts, ToT）**：ThoughtNode思维节点、ThoughtGraph思维图，tree_of_thoughts() 方法，分支因子和最大深度可配置，剪枝机制
- **思维图（Graph of Thoughts, GoT）**：支持复杂推理链的图结构表示
- **自一致性（Self-Consistency）**：多路径采样投票，提高答案可靠性
- **反射链（Reflection Chain）**：多轮自我反思，逐步修正答案
- **验证链（Verification Chain）**：事实核查 + 逻辑验证 + 反事实检验
- **认知偏差检测**：识别确认偏差、锚定效应、可得性偏差等
- **元认知监控**：实时监控思考质量、认知负载、推理效率
- **Token 预算控制**：CognitiveBudget 类，防止 token 超支
- **L5 协同认知**：多智能体协作推理模式

## v2.1.0 — 2026-06-24
- EnhancedCognitionEngine 集成到 odc_agent.py
- prompt_library_v2.py 新增
- dynamic_cognition_v2.py Agent 集成版本

## v2.0.0-alpha (RC1) — 2026-06-23
- 全仓库去 Emoji 化
- 英文主文档 SKILL.md + 中文副本 SKILL_zh.md
