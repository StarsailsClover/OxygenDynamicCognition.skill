# Changelog

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
