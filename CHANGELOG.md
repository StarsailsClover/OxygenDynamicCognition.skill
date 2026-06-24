# Changelog

## v26.0 Alpha 4 — 2026-06-24
### 🚀 前沿技术集成
- **思维树（Tree of Thoughts, ToT）**：ThoughtNode思维节点、ThoughtGraph思维图，tree_of_thoughts() 方法，分支因子和最大深度可配置，剪枝机制
- **思维图（Graph of Thoughts, GoT）**：ThoughtGraph图结构，支持多种边类型，路径回溯和叶子节点聚合
- **自一致性（Self-Consistency）**：self_consistency() 方法，生成多个答案投票选出最一致的，_think_with_style() 不同风格思考，_cluster_answers() 基于文本相似度聚类
- **反射机制（Reflection）**：ReflectionResult反射结果类，reflect() 方法支持多轮反射，检查逻辑漏洞、遗漏因素、结论绝对性、论证方式
- **验证链（Chain of Verification, CoVe）**：VerificationResult验证结果类，chain_of_verification() 方法，_extract_claims() 提取声明，_verify_claim() 验证单个声明
- **渐进式深化（Progressive Deepening）**：progressive_deepening() 方法，从浅到深逐步深入思考，类似迭代加深搜索
- **元认知监控（Metacognitive Monitoring）**：get_metacognition_report() 方法，追踪思维节点数、反射次数、验证次数、偏差检查数、认知步骤数
- **认知偏差检测（Cognitive Bias Detection）**：BiasDetector偏差检测器类，检测4种偏差（确认偏差、锚定偏差、可得性启发、过度自信）

### 🔧 功能增强
- 完整向后兼容v2.1所有功能（Mock模式、重试、缓存、本地分类等）
- 功能开关：enable_tot, enable_reflection, enable_verification, enable_self_consistency, enable_bias_detection
- CLI接口增强：--no-tot, --no-reflection, --no-verification, --no-consistency, --consistency-samples, --reflection-depth, --tot-branches, --tot-depth, --version
- VERSION = "26.0.0-alpha.4"
- 向后兼容别名：AdvancedCognitionEngine = OxygenDynamicCognitionV26

### ✅ 测试验证
- 47项完整测试套件（test_v26.py）
- 47/47 测试全部通过
- 0失败，0错误

### 🐛 Bug修复
- 修复_verify_claim返回int而不是dict的问题（MockLLM判断顺序）
- 修复_extract_claims提取声明为空的问题（长度阈值）
- 修复思维树只有根节点的问题（_generate_thoughts被误判为难度评估）
- 修复_verify_claim返回格式不对的问题（添加单声明验证独特标识）

### GitHub
- Author: GitHub@StarsailsClover

## v2.1.0 — 2026-06-24
### Added
- 🧪 **Mock Mode**: Offline testing support without API Key, with intelligent mock responses
- 🔄 **Error Retry**: Automatic retry with exponential backoff on API failures
- 💾 **Result Cache**: LRU cache for faster repeated queries
- ⚡ **Local Classifier**: Heuristic-based problem type classification without API
- 📊 **Detailed Confidence**: Multi-dimensional confidence assessment support
- 💰 **Cost Analysis**: Detailed token breakdown by stage
- 📝 **Structured Logging**: Enhanced cognition log with more metadata
- `dynamic_cognition_v21.py`: v2.1 enhanced engine with all new features
- `test_v21.py`: Comprehensive unit test suite (20 tests, all passing)

### Fixed
- BudgetExceeded exception definition moved to file top for proper import order
- Mock LLM difficulty assessment now uses actual problem classification
- Mock LLM difficulty level based on question complexity heuristics

### Improved
- Better error handling and graceful degradation
- More accurate adaptive threshold behavior
- Enhanced CLI with --mock, --no-cache, --retries parameters
- GitHub@StarsailsClover

## v2.0.0-alpha (RC1) — 2026-06-23

### Added
- 🌐 L5 Collaborative Reasoning: three-path parallel exploration with cross-validation
- 🔧 Tool Awareness Layer: auto-detect calculator/search/code execution needs
- 🎯 Adaptive Thresholds: per-problem-type confidence thresholds
- 💰 Token Budget Control: configurable budget with consumption tracking
- 🧠 Memory Integration: context injection for reasoning reference
- 📊 Cost Analysis: per-round token tracking and budget usage ratio
- `dynamic_cognition_v2.py`: enhanced engine with all v2 features
- `prompt_library_v2.py`: expanded prompt library with L5/tool/adaptive prompts
- `odc_agent.py`: Agent integration interface

### Changed
- SKILL.md rewritten in English as primary documentation
- `SKILL_zh.md` added as Chinese translation copy

### Planned (v3.0)
- Native Agent integration via tool_call / thinking events
- Plugin registry support for OpenClaw skill marketplace
