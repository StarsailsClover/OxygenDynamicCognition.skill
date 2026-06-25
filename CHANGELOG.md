# Changelog

## v26.0 Alpha 6 — 2026-06-25

### Bug Fixes (Critical)
- **修复 verification + self_consistency 死循环**：自一致性结果现在必须经过二次验证
- **修复 verification 通过但置信度仍低时跳过自一致性的逻辑遗漏**
- **高级增强功能改为循环执行**（最多3轮），带熔断机制防止无限循环
- **无变化即跳出**：每轮高级增强后检查是否有实质改进，无改进则提前退出
- **结果反馈回主循环**：高级功能改进的答案会重新评估置信度，达标则提前终止

### Performance
- 内容去重后正确更新 TLB 和持久化
- 删除时完整清理哈希映射

## v26.0 Alpha 5 — 2026-06-25
### Bug Fixes & Performance
- 修复真实 API 调用：_call_llm 非 mock 模式不再 fallback 到 MockLLM
- 添加 _init_client() 初始化 OpenAI 兼容客户端
- 添加 _real_api_call() 实际 API 调用方法，带 token 追踪
- 默认参数优化：gpt-3.5-turbo, 4 rounds, L1-L4 only
- ToT/Reflection/Verification/SelfConsistency/BiasDetection 默认关闭

## v26.0 Alpha 4 — 2026-06-24
### 前沿技术集成
- 思维树（ToT）、思维图（GoT）、自一致性、反射链、验证链
- 认知偏差检测、元认知监控、Token 预算控制、L5 协同认知
