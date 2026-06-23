#!/usr/bin/env python3
"""
Oxygen Dynamic Cognition v2 - Agent Integration Module
为 OpenClaw Agent 提供动态认知能力的集成模块。

使用方式：
1. 作为 Python 模块导入
2. 通过 CLI 调用
3. 通过 JSON-RPC 与 Agent 通信
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from dynamic_cognition_v2 import EnhancedCognitionEngine


def run_cognition(
    question: str,
    model: str = "stepfun_api/step-3.7-flash",
    base_url: Optional[str] = None,
    threshold: int = 80,
    max_rounds: int = 4,
    start_level: str = "auto",
    verbose: bool = True,
    context: Optional[str] = None,
    budget: int = 16000,
) -> Dict[str, Any]:
    """
    运行动态认知推理（Agent 集成接口）

    Args:
        question: 要回答的问题
        model: 使用的模型
        base_url: API 基础 URL
        threshold: 置信度阈值
        max_rounds: 最大思考轮次
        start_level: 起始认知等级
        verbose: 详细输出
        context: 上下文信息
        budget: Token 预算

    Returns:
        推理结果字典
    """
    engine = EnhancedCognitionEngine(
        model=model,
        base_url=base_url,
        confidence_threshold=threshold,
        max_rounds=max_rounds,
        start_level=start_level,
        verbose=verbose,
        max_tokens_budget=budget,
        context=context,
    )

    return engine.run(question)


def format_result_for_agent(result: Dict[str, Any]) -> str:
    """将推理结果格式化为 Agent 友好的输出"""

    lines = []
    level_emoji = {
        "L1": "⚡", "L2": "📋", "L3": "🔍",
        "L4": "🔬", "L5": "🌐",
    }
    initial_level = result.get("initial_level", "L2")
    emoji = level_emoji.get(initial_level, "🧠")

    lines.append(f"{emoji} **动态认知 [{initial_level}]**")
    lines.append(f"📊 置信度：{result['final_confidence']}/100")
    lines.append(f"🔄 轮次：{result['total_rounds']}")

    if result.get("used_l5"):
        lines.append(f"🌐 L5 协同：已启用")

    if result.get("tool_calls"):
        tools = [t["tools"] for t in result["tool_calls"]]
        lines.append(f"🔧 工具调用：{tools}")

    lines.append(f"💰 Token：{result['total_tokens']}（{result.get('token_budget_used', '?')}）")
    lines.append(f"⏱️  耗时：{result.get('total_time', '?')}s")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(result["final_answer"])

    return "\n".join(lines)


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="ODC v2 Agent 集成接口")
    parser.add_argument("question", help="问题")
    parser.add_argument("--model", default=None, help="模型名称")
    parser.add_argument("--threshold", type=int, default=80)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--level", default="auto")
    parser.add_argument("--context", default=None)
    parser.add_argument("--budget", type=int, default=16000)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")

    args = parser.parse_args()

    result = run_cognition(
        question=args.question,
        model=args.model,
        threshold=args.threshold,
        max_rounds=args.rounds,
        start_level=args.level,
        verbose=not args.quiet,
        context=args.context,
        budget=args.budget,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_result_for_agent(result))


if __name__ == "__main__":
    main()
