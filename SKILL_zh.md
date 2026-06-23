---
name: oxygen-dynamic-cognition
description: >
  ODC (Oxygen Dynamic Cognition) — 基于动态认知理论的 AI 推理引擎。
  五级认知模式（L1快速响应 / L2分步推理 / L3反思校验 / L4多路径验证 / L5协同推理）
  + 置信度门控 Early Exit + 工具感知 + 自适应阈值 + Token 预算控制。
  用于需要深度思考、自我校验、多轮迭代优化答案、数学证明、复杂分析、代码审查等场景。
  触发词：动态认知、深度思考、OxygenTBM、L5推理、认真想一下。
---

# Oxygen Dynamic Cognition (ODC) — 中文文档

## 概述

Oxygen Dynamic Cognition（氧动态认知）是一个基于动态认知理论的 AI 推理框架。它通过提示词工程在 Agent 层实现了动态计算思想（Early Exit、Dynamic Depth、Dual System），无需修改模型、无需重新训练。

**核心思想：** *让 AI 像人类一样思考——简单问题快速回答，复杂问题深入思考，想通了就停止，没想通就继续深入。*

## 核心特性

- **五级认知模式**：从快速响应到协同推理，覆盖不同推理深度
- **自动难度评估**：智能判断问题复杂度，选择合适的初始认知等级
- **置信度门控 Early Exit**：每轮思考后自我评估，达标则提前终止
- **认知升级机制**：置信度不足时自动提升思考深度
- **L5 协同推理**：三路径并行探索（正向推导 / 逆向验证 / 边界分析），交叉整合
- **工具感知层**：自动判断是否需要计算器、搜索、代码执行等外部工具
- **自适应阈值**：根据问题类型自动调整置信度阈值（数学 90 / 日常 65）
- **Token 预算控制**：预设预算上限 + 消耗追踪 + 耗尽保护
- **完整过程日志**：可观测、可追溯的认知过程记录

## 快速开始

### 安装

```bash
git clone https://github.com/<your-org>/OxygenDynamicCognition.skill.git
cd OxygenDynamicCognition.skill
pip install openai
```

### 基本使用

```bash
# 自动评估难度，动态推理
python scripts/odc_agent.py "解释量子纠缠"

# 启用 L5 协同推理
python scripts/odc_agent.py "设计分布式系统架构" --rounds 5

# 设置 Token 预算
python scripts/odc_agent.py "复杂数学证明" --budget 20000

# JSON 输出（含完整指标）
python scripts/odc_agent.py "分析 AI 发展趋势" --json
```

### Python API

```python
from dynamic_cognition_v2 import EnhancedCognitionEngine

engine = EnhancedCognitionEngine(
    model="gpt-4",
    confidence_threshold=80,
    max_rounds=5,
    max_tokens_budget=16000,
    verbose=True,
)

result = engine.run("你的问题")
print(result["final_answer"])
print(f"置信度: {result['final_confidence']}")
```

## 五级认知模式

| 等级 | 名称 | 核心机制 | 典型 Token | 适用场景 |
|------|------|---------|-----------|---------|
| L1 | 快速响应 ⚡ | 系统1直觉 | ~100 | 常识、简单计算 |
| L2 | 分步推理 📋 | 结构化推导 | ~500 | 常规知识解释 |
| L3 | 反思校验 🔍 | 生成→批判→修正 | ~1200 | 复杂分析、证明 |
| L4 | 多路径验证 🔬 | 双路径交叉验证 | ~2000 | 高难度专业问题 |
| L5 | 协同推理 🌐 | 三路径并行+整合 | ~3000 | 极高难度、开放问题 |

## 自适应阈值

| 问题类型 | 推荐阈值 | 说明 |
|---------|---------|------|
| 数学计算类 | 90 | 精确性优先 |
| 逻辑推理类 | 85 | 严谨推导 |
| 专业分析类 | 85 | 深度要求高 |
| 代码编程类 | 80 | 正确性优先 |
| 知识问答类 | 75 | 平衡质量与速度 |
| 创意生成类 | 70 | 允许多样性 |
| 日常对话类 | 65 | 速度优先 |

## 研究背景

ODC 的设计灵感来源于多条前沿研究路线：

- **双系统认知理论**：卡尼曼《思考，快与慢》，Dualformer 架构
- **提前退出机制**：Early Exit、DEER、SpecExit
- **动态深度 Transformer**：ITT、Mixture of Depths
- **混合专家架构**：MoE 路由思想
- **自我反思机制**：Reflexion、Self-Correction
- **元认知理论**：自我监控与调节能力

详见 `references/research_background.md`

## 许可证

MIT
