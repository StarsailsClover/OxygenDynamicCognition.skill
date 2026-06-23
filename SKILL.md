---
name: oxygen-dynamic-cognition
description: >
  ODC (Oxygen Dynamic Cognition) — Dynamic cognition reasoning engine for AI agents.
  Five cognitive levels (L1 Fast Response / L2 Step-by-Step / L3 Reflection / L4 Multi-Path / L5 Collaborative)
  + Confidence gated Early Exit + Tool awareness + Adaptive thresholds + Token budget control.
  Use when deep thinking, self-verification, multi-round iteration, mathematical proof, complex analysis,
  code review, or anything that benefits from structured reasoning.
  Triggers: dynamic cognition, deep thinking, OxygenTBM, L5 reasoning, think carefully.
---

# Oxygen Dynamic Cognition (ODC)

## Overview

Oxygen Dynamic Cognition is an AI reasoning framework based on dynamic cognitive theory. It implements dynamic computation ideas (Early Exit, Dynamic Depth, Dual System) through prompt engineering at the Agent layer — no model modifications, no retraining required.

**Core Philosophy:** *Let AI think like humans — fast answers for simple questions, deep thinking for complex ones, stop when confident, go deeper when not.*

## Key Features

- **Five Cognitive Levels**: From fast response to collaborative reasoning
- **Auto Difficulty Assessment**: Smart routing to the right cognitive depth
- **Confidence-Gated Early Exit**: Self-evaluate each round, stop when threshold met
- **Cognitive Upgrade**: Automatically deepen thinking when confidence is insufficient
- **L5 Collaborative Reasoning**: Three-path parallel exploration with cross-validation
- **Tool Awareness**: Auto-detect when calculator, search, or code execution is needed
- **Adaptive Thresholds**: Per-problem-type confidence thresholds (math: 90, chat: 65)
- **Token Budget Control**: Configurable budget with consumption tracking
- **Full Process Logging**: Observable, traceable cognition process

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-org>/OxygenDynamicCognition.skill.git
cd OxygenDynamicCognition.skill

# Install dependencies
pip install openai
```

### Basic CLI Usage

```bash
# Auto-assess difficulty, dynamic reasoning
python scripts/odc_agent.py "Explain quantum entanglement"

# Enable L5 collaborative reasoning
python scripts/odc_agent.py "Design a distributed system architecture" --rounds 5

# Set token budget
python scripts/odc_agent.py "Complex math proof" --budget 20000

# JSON output with full metrics
python scripts/odc_agent.py "Analyze AI trends" --json
```

### Python API

```python
from dynamic_cognition_v2 import EnhancedCognitionEngine

engine = EnhancedCognitionEngine(
    model="gpt-4",
    confidence_threshold=80,
    max_rounds=5,
    max_tokens_budget=16000,
    context="Previous discussion context",
    verbose=True,
)

result = engine.run("Your question here")
print(result["final_answer"])
```

## Five Cognitive Levels

| Level | Name | Emoji | Core Mechanism | Token Budget | Use Case |
|-------|------|-------|---------------|-------------|----------|
| L1 | Fast Response | ⚡ | System 1 intuition | ~100 | Facts, simple calculations |
| L2 | Step-by-Step | 📋 | Structured reasoning | ~500 | Knowledge explanations |
| L3 | Reflection | 🔍 | Generate → Critique → Fix | ~1200 | Complex analysis, proofs |
| L4 | Multi-Path | 🔬 | Dual-path cross-validation | ~2000 | High-difficulty problems |
| L5 | Collaborative | 🌐 | Three-path parallel + integration | ~3000 | Extreme difficulty, open problems |

## Cognitive Flow

```
User Question
    ↓
[Difficulty Assessment v2] → Level + Type + Tool Need + Adaptive Threshold
    ↓
┌─────────────────────────────────────────────────┐
│              Dynamic Reasoning Loop              │
│  ┌─────────────┐  ┌───────────────────────────┐  │
│  │ Think       │→│ Confidence Assessment v2   │  │
│  │ (current)   │  │ (context-enhanced)        │  │
│  └──────┬──────┘  └──────────┬────────────────┘  │
│         │                    │                   │
│         ↓           Met?     │                   │
│   [Tool Decision] → Call tool │                   │
│         ↓                    │                   │
│    Upgrade Level ←───────────┤   Not Met         │
│         ↓                    │                   │
│   [L5 Collab?]              │                   │
│    Three-path parallel       │                   │
│         ↓                    │                   │
│   [Integrate] ←──────────────┘                   │
└─────────────────────────────────────────────────┘
    ↓
[Final Answer] + [Cost Report]
```

## Adaptive Thresholds

| Problem Type | Threshold | Rationale |
|-------------|-----------|-----------|
| Math/Calculation | 90 | Precision-first |
| Logic/Proof | 85 | Rigorous reasoning |
| Professional Analysis | 85 | High depth required |
| Code/Programming | 80 | Correctness-first |
| Knowledge Q&A | 75 | Balanced quality/speed |
| Creative Generation | 70 | Allow diversity |
| Daily Conversation | 65 | Speed-first |

## CLI Reference

```
odc_agent.py <question> [options]

Options:
  --model <name>        Model name (default: gpt-3.5-turbo)
  --threshold <0-100>   Confidence threshold (default: 80)
  --rounds <n>          Max reasoning rounds (default: 4, set 5 for L5)
  --budget <tokens>     Token budget (default: 8000)
  --level <L1-L5>       Start level (default: auto)
  --context <text>      Context information
  --no-tools            Disable tool awareness
  --no-memory           Disable memory integration
  --json                JSON output
  --quiet               Minimal output
```

## Project Structure

```
OxygenDynamicCognition.skill/
├── SKILL.md                        # English documentation (this file)
├── SKILL_zh.md                     # 中文文档副本
├── README.md                       # Repository README
├── CHANGELOG.md                    # Version history
├── LICENSE                         # MIT License
├── scripts/
│   ├── __init__.py
│   ├── prompt_library.py           # v1 prompt library
│   ├── prompt_library_v2.py        # v2 enhanced prompts
│   ├── dynamic_cognition.py        # v1 engine
│   ├── dynamic_cognition_v2.py     # v2 enhanced engine
│   └── odc_agent.py                # Agent integration interface
├── references/
│   ├── cognitive_levels.md         # Detailed level documentation
│   └── research_background.md      # Research background & theory
└── tests/                          # Unit tests (planned)
```

## Version History

| Version | Features | Status |
|---------|---------|--------|
| v1.0 (MVP) | 4 levels + confidence gating + Early Exit | ✅ Released |
| v2.0 (RC1) | + L5 collaborative + tool awareness + adaptive thresholds + budget | 🔄 RC |
| v3.0 (planned) | Native Agent integration (tool_call / thinking events) | 🔜 Planned |

## Research Background

ODC draws from multiple frontier research threads:

- **Dual System Theory** (Kahneman): L1 fast thinking vs L2-L4 slow thinking
- **Early Exit** (DEER, SpecExit): Confidence-gated early termination
- **Dynamic Depth** (ITT, MoD): Token-level dynamic computation
- **Mixture of Experts**: Cognitive mode routing
- **Self-Reflection** (Reflexion): Generate-evaluate-refine loop
- **Metacognition**: Self-monitoring and strategy adjustment

See `references/research_background.md` for detailed citations.

## License

MIT — feel free to use, modify, and distribute.
