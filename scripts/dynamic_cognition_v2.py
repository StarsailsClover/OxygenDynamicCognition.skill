#!/usr/bin/env python3
"""
Oxygen Dynamic Cognition v2 - Enhanced Engine
扩展特性：
- L5 协同推理（多路径并行探索）
- 工具感知层（决策是否需要外部工具）
- 记忆集成（上下文感知）
- 自适应阈值（按问题类型动态调整）
- Token 预算控制
- 认知成本分析
"""

import json
import sys
import time
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from prompt_library_v2 import (
    DIFFICULTY_ASSESSMENT_SYSTEM_V2,
    DIFFICULTY_ASSESSMENT_USER_TEMPLATE_V2,
    CONFIDENCE_ASSESSMENT_SYSTEM_V2,
    CONFIDENCE_ASSESSMENT_USER_TEMPLATE_V2,
    COGNITIVE_UPGRADE_SYSTEM_V2,
    COGNITIVE_UPGRADE_USER_TEMPLATE_V2,
    FINAL_ANSWER_INTEGRATION_SYSTEM_V2,
    FINAL_ANSWER_INTEGRATION_USER_TEMPLATE_V2,
    L5_COLLABORATIVE_SYSTEM,
    L5_COLLABORATIVE_USER_TEMPLATE,
    TOOL_DECISION_SYSTEM,
    TOOL_DECISION_USER_TEMPLATE,
    COGNITIVE_LEVELS_V2,
    DEFAULT_CONFIG_V2,
    get_prompt_v2,
    get_level_config_v2,
    next_level_v2,
    ADAPTIVE_THRESHOLDS,
    PROBLEM_TYPE_CLASSIFIER,
)

# 五级认知模式（新增 L5）
LEVELS = ["L1", "L2", "L3", "L4", "L5"]


class ToolDecision:
    """工具决策结果"""
    NEED_TOOL = "need_tool"
    NO_TOOL = "no_tool"
    TOOLS = {
        "calculator": "数学计算",
        "web_search": "网络搜索",
        "code_execution": "代码执行",
        "database_query": "数据库查询",
        "file_operation": "文件操作",
        "api_call": "API调用",
    }

    def __init__(self, need_tool: bool, tool_types: List[str], reason: str):
        self.need_tool = need_tool
        self.tool_types = tool_types
        self.reason = reason


class CognitiveBudget:
    """认知预算管理"""

    def __init__(self, max_tokens: int = 8000, warn_ratio: float = 0.7):
        self.max_tokens = max_tokens
        self.warn_ratio = warn_ratio
        self.used_tokens = 0
        self.token_history: List[Dict[str, int]] = []

    def consume(self, tokens: int, stage: str = ""):
        self.used_tokens += tokens
        self.token_history.append({"stage": stage, "tokens": tokens})

    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    def usage_ratio(self) -> float:
        return self.used_tokens / self.max_tokens if self.max_tokens > 0 else 0.0

    def should_stop(self) -> bool:
        return self.remaining() < 500  # 保留最少500 token

    def should_warn(self) -> bool:
        return self.usage_ratio() >= self.warn_ratio


class EnhancedCognitionEngine:
    """
    增强版动态认知引擎 v2

    新增特性：
    - L5 协同推理：多路径并行探索，交叉验证
    - 工具感知：自动判断是否需要调用外部工具
    - 记忆集成：利用上下文信息优化推理
    - 自适应阈值：根据问题类型动态调整置信度阈值
    - 预算管理：控制 Token 消耗
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        confidence_threshold: int = 80,
        max_rounds: int = 4,
        start_level: str = "auto",
        verbose: bool = False,
        max_tokens_budget: int = 8000,
        enable_tools: bool = True,
        enable_memory: bool = True,
        context: Optional[str] = None,
    ):
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.max_rounds = max_rounds
        self.start_level = start_level
        self.verbose = verbose
        self.enable_tools = enable_tools
        self.enable_memory = enable_memory
        self.context = context or ""

        self._init_client(api_key, base_url)

        self.budget = CognitiveBudget(max_tokens=max_tokens_budget)
        self.cognition_log: List[Dict[str, Any]] = []
        self.total_tokens = 0
        self.total_time = 0.0
        self.tool_calls: List[Dict[str, Any]] = []

    # ──────────────────────── 初始化 ────────────────────────

    def _init_client(self, api_key: Optional[str], base_url: Optional[str]):
        try:
            from openai import OpenAI
        except ImportError:
            print("❌ 错误：未安装 openai 库，请运行：pip install openai")
            sys.exit(1)

        import os

        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY", os.environ.get("OXYGEN_API_KEY", ""))
        if base_url is None:
            base_url = os.environ.get("OPENAI_BASE_URL", None)

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = OpenAI(**client_kwargs)

    # ──────────────────────── LLM 调用 ────────────────────────

    def _llm_call(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.5,
        stage: str = "",
    ) -> str:
        start_time = time.time()

        # 预算检查
        if self.budget.should_stop():
            raise BudgetExceeded("Token 预算不足，终止推理")

        effective_max = min(max_tokens, self.budget.remaining())
        if effective_max < 100:
            effective_max = 100

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=effective_max,
                temperature=temperature,
            )

            result = response.choices[0].message.content.strip()

            if hasattr(response, "usage") and response.usage:
                tokens = response.usage.total_tokens
                self.total_tokens += tokens
                self.budget.consume(tokens, stage)

            elapsed = time.time() - start_time
            self.total_time += elapsed

            # 预算警告
            if self.budget.should_warn() and self.verbose:
                print(f"  ⚠️  Token 预算警告：已用 {self.budget.usage_ratio():.0%}")

            return result

        except Exception as e:
            print(f"❌ API 调用失败：{e}")
            raise

    # ──────────────────────── 难度评估 V2 ────────────────────────

    def assess_difficulty(self, question: str) -> Dict[str, Any]:
        """评估问题难度，同时识别问题类型和工具需求"""

        # 上下文注入
        context_block = ""
        if self.context:
            context_block = f"\n\n【上下文信息】\n{self.context}\n"

        user_prompt = DIFFICULTY_ASSESSMENT_USER_TEMPLATE_V2.format(
            question=question,
            context_block=context_block,
        )

        result_text = self._llm_call(
            system_prompt=DIFFICULTY_ASSESSMENT_SYSTEM_V2,
            user_prompt=user_prompt,
            max_tokens=300,
            temperature=0.1,
            stage="difficulty_assessment",
        )

        try:
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result = json.loads(result_text.strip())
        except json.JSONDecodeError:
            result = {
                "level": "L2",
                "type": "综合类",
                "reason": "解析失败，使用默认等级",
                "estimated_tokens": 500,
                "needs_tools": False,
                "tool_types": [],
            }

        # 自适应阈值调整
        problem_type = result.get("type", "综合类")
        if problem_type in ADAPTIVE_THRESHOLDS:
            adaptive_threshold = ADAPTIVE_THRESHOLDS[problem_type]
            if self.verbose:
                print(f"  🎯 自适应阈值：{self.confidence_threshold} → {adaptive_threshold}（{problem_type}）")
            self._adaptive_threshold = adaptive_threshold
        else:
            self._adaptive_threshold = self.confidence_threshold

        self.cognition_log.append({
            "stage": "difficulty_assessment",
            "level": result.get("level", "L2"),
            "type": problem_type,
            "reason": result.get("reason", ""),
            "needs_tools": result.get("needs_tools", False),
            "tool_types": result.get("tool_types", []),
            "raw_output": result_text,
        })

        if self.verbose:
            level = result.get("level", "L2")
            level_name = COGNITIVE_LEVELS_V2.get(level, {}).get("name", level)
            print(f"  📊 难度：{level} ({level_name})")
            print(f"  📋 类型：{problem_type}")
            print(f"  💭 理由：{result.get('reason', '')}")
            if result.get("needs_tools"):
                print(f"  🔧 需要工具：{result.get('tool_types', [])}")

        return result

    # ──────────────────────── 工具决策 ────────────────────────

    def decide_tools(self, question: str, current_answer: str) -> ToolDecision:
        """判断是否需要调用外部工具"""

        if not self.enable_tools:
            return ToolDecision(False, [], "工具已禁用")

        user_prompt = TOOL_DECISION_USER_TEMPLATE.format(
            question=question,
            answer=current_answer,
        )

        result_text = self._llm_call(
            system_prompt=TOOL_DECISION_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=150,
            temperature=0.1,
            stage="tool_decision",
        )

        try:
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result = json.loads(result_text.strip())
        except json.JSONDecodeError:
            result = {"need_tool": False, "tool_types": [], "reason": "解析失败"}

        decision = ToolDecision(
            need_tool=result.get("need_tool", False),
            tool_types=result.get("tool_types", []),
            reason=result.get("reason", ""),
        )

        if decision.need_tool and self.verbose:
            print(f"  🔧 工具决策：需要 {decision.tool_types} — {decision.reason}")

        return decision

    # ──────────────────────── 置信度评估 V2 ────────────────────────

    def assess_confidence(self, question: str, answer: str, extra_criteria: str = "") -> int:
        """评估答案置信度（增强版，支持额外评估维度）"""

        context_hint = ""
        if self.context:
            context_hint = f"\n【上下文参考】\n{self.context[:500]}\n"

        extra = f"\n【额外评估维度】\n{extra_criteria}\n" if extra_criteria else ""

        user_prompt = CONFIDENCE_ASSESSMENT_USER_TEMPLATE_V2.format(
            question=question,
            answer=answer,
            context_hint=context_hint,
            extra=extra,
        )

        result_text = self._llm_call(
            system_prompt=CONFIDENCE_ASSESSMENT_SYSTEM_V2,
            user_prompt=user_prompt,
            max_tokens=20,
            temperature=0.0,
            stage="confidence_assessment",
        )

        try:
            # 提取所有数字，取第一个有效整数
            digits = ''.join(c for c in result_text if c.isdigit())
            if digits:
                confidence = int(digits[:3])  # 取前3位数字
                confidence = max(0, min(100, confidence))
            else:
                confidence = 70
        except (ValueError, IndexError):
            confidence = 70

        return confidence

    # ──────────────────────── 认知思考 ────────────────────────

    def think_with_level(self, question: str, level: str) -> str:
        """使用指定认知等级进行思考"""
        level_config = get_level_config_v2(level)
        system_prompt, user_prompt = get_prompt_v2(level, question)

        if self.verbose:
            print(f"  🧠 认知等级：{level} ({level_config['name']})")

        context_block = ""
        if self.context and level in ["L3", "L4", "L5"]:
            context_block = f"\n\n【上下文信息（仅供参考）】\n{self.context}\n"
            user_prompt += context_block

        result = self._llm_call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=level_config["max_tokens"],
            temperature=level_config["temperature"],
            stage=f"think_{level}",
        )

        return result

    def upgrade_cognition(self, question: str, previous_answer: str,
                          critique: str = "") -> str:
        """认知升级：基于之前答案和批判进行更深入思考"""

        user_prompt = COGNITIVE_UPGRADE_USER_TEMPLATE_V2.format(
            question=question,
            previous_answer=previous_answer,
            critique=critique,
        )

        result = self._llm_call(
            system_prompt=COGNITIVE_UPGRADE_SYSTEM_V2,
            user_prompt=user_prompt,
            max_tokens=1500,
            temperature=0.4,
            stage="cognitive_upgrade",
        )

        return result

    def collaborative_reasoning(self, question: str) -> Dict[str, str]:
        """L5 协同推理：多路径并行探索"""

        if self.verbose:
            print(f"  🌐 L5 协同推理：启动多路径并行探索...")

        paths = [
            {
                "name": "路径一：正向推导",
                "system": L5_COLLABORATIVE_SYSTEM,
                "template": L5_COLLABORATIVE_USER_TEMPLATE,
                "focus": "从已知条件出发，正向逻辑推导",
            },
            {
                "name": "路径二：逆向验证",
                "system": L5_COLLABORATIVE_SYSTEM,
                "template": L5_COLLABORATIVE_USER_TEMPLATE,
                "focus": "从目标结论出发，逆向验证条件",
            },
            {
                "name": "路径三：边界分析",
                "system": L5_COLLABORATIVE_SYSTEM,
                "template": L5_COLLABORATIVE_USER_TEMPLATE,
                "focus": "分析极端情况和边界条件",
            },
        ]

        results = {}
        for path in paths:
            user_prompt = path["template"].format(
                question=question,
                path_name=path["name"],
                focus=path["focus"],
            )

            if self.verbose:
                print(f"    🔀 {path['name']}...")

            result = self._llm_call(
                system_prompt=path["system"],
                user_prompt=user_prompt,
                max_tokens=800,
                temperature=0.5,
                stage=f"collab_{path['name'][:4]}",
            )
            results[path["name"]] = result

        return results

    def integrate_answers(self, question: str, thinking_history: List[str],
                          collaborative_results: Optional[Dict[str, str]] = None) -> str:
        """整合多轮思考结果"""

        history_text = ""
        for i, thought in enumerate(thinking_history, 1):
            history_text += f"第 {i} 轮思考：\n{thought}\n\n"

        if collaborative_results:
            history_text += "\n【L5 协同推理结果】\n"
            for name, result in collaborative_results.items():
                history_text += f"\n{name}：\n{result}\n"

        user_prompt = FINAL_ANSWER_INTEGRATION_USER_TEMPLATE_V2.format(
            question=question,
            thinking_history=history_text,
        )

        result = self._llm_call(
            system_prompt=FINAL_ANSWER_INTEGRATION_SYSTEM_V2,
            user_prompt=user_prompt,
            max_tokens=2000,
            temperature=0.3,
            stage="final_integration",
        )

        return result

    # ──────────────────────── 主推理循环 ────────────────────────

    def run(self, question: str) -> Dict[str, Any]:
        """执行动态认知推理（增强版）"""
        start_time = time.time()
        self.cognition_log = []
        self.total_tokens = 0
        self.budget = CognitiveBudget()
        self.tool_calls = []
        self._adaptive_threshold = self.confidence_threshold

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🚀 Oxygen Dynamic Cognition Engine v2")
            print(f"{'='*60}")
            print(f"📝 问题：{question}")
            print(f"⚙️  阈值={self.confidence_threshold}, 最大轮次={self.max_rounds}")
            print(f"💰 Token 预算：{self.budget.max_tokens}")
            print(f"{'='*60}\n")

        # ── 阶段1：难度评估 ──
        difficulty_result = self.assess_difficulty(question)
        current_level = difficulty_result.get("level", "L2")
        needs_tools = difficulty_result.get("needs_tools", False)
        tool_types = difficulty_result.get("tool_types", [])

        # ── 阶段2：动态推理循环 ──
        thinking_history = []
        best_answer = ""
        best_confidence = 0
        current_answer = ""
        used_l5 = False

        for round_num in range(1, self.max_rounds + 1):
            if self.verbose:
                print(f"\n🔄 第 {round_num} 轮思考")
                print(f"  {'─'*40}")

            # 执行思考
            if round_num == 1:
                current_answer = self.think_with_level(question, current_level)
            else:
                # 工具决策（仅在升级轮次）
                if needs_tools and self.enable_tools:
                    tool_decision = self.decide_tools(question, current_answer)
                    if tool_decision.need_tool:
                        self.tool_calls.append({
                            "round": round_num,
                            "tools": tool_decision.tool_types,
                            "reason": tool_decision.reason,
                        })

                current_answer = self.upgrade_cognition(question, current_answer)
                current_level = next_level_v2(current_level)

            thinking_history.append(current_answer)

            # 评估置信度
            threshold = getattr(self, '_adaptive_threshold', self.confidence_threshold)
            confidence = self.assess_confidence(question, current_answer)

            self.cognition_log.append({
                "stage": "thinking",
                "round": round_num,
                "level": current_level,
                "confidence": confidence,
                "answer_preview": current_answer[:200],
            })

            if confidence > best_confidence:
                best_confidence = confidence
                best_answer = current_answer

            if self.verbose:
                print(f"  📈 置信度：{confidence}/100（阈值：{threshold}）")

            # Early Exit
            if confidence >= threshold:
                if self.verbose:
                    print(f"  ✅ 达标，Early Exit")
                break

            # L5 特殊处理
            if current_level == "L5" and not used_l5:
                if self.verbose:
                    print(f"  🌐 触发 L5 协同推理...")
                collab_results = self.collaborative_reasoning(question)
                used_l5 = True

                # 整合协同结果
                integrated = self.integrate_answers(question, thinking_history, collab_results)
                integrated_conf = self.assess_confidence(question, integrated)
                thinking_history.append(integrated)

                if integrated_conf > best_confidence:
                    best_confidence = integrated_conf
                    best_answer = integrated

                self.cognition_log.append({
                    "stage": "L5_collaborative",
                    "paths": list(collab_results.keys()),
                    "integrated_confidence": integrated_conf,
                })

                if integrated_conf >= threshold:
                    break

            if current_level == "L5":
                if self.verbose:
                    print(f"  ⚠️  L5 已完成，继续深度迭代...")

        # ── 阶段3：答案整合 ──
        if len(thinking_history) > 1:
            final_answer = self.integrate_answers(question, thinking_history)
            final_confidence = self.assess_confidence(question, final_answer)

            if final_confidence > best_confidence:
                best_confidence = final_confidence
                best_answer = final_answer
        else:
            final_answer = best_answer
            final_confidence = best_confidence

        total_elapsed = time.time() - start_time

        result = {
            "question": question,
            "final_answer": best_answer,
            "final_confidence": best_confidence,
            "total_rounds": len(thinking_history),
            "initial_level": self.start_level if self.start_level != "auto" else difficulty_result.get("level", "L2"),
            "used_l5": used_l5,
            "tool_calls": self.tool_calls,
            "total_tokens": self.total_tokens,
            "token_budget_used": f"{self.budget.usage_ratio():.0%}",
            "total_time": round(total_elapsed, 2),
            "adaptive_threshold": getattr(self, '_adaptive_threshold', self.confidence_threshold),
            "cognition_log": self.cognition_log,
            "thinking_history": thinking_history,
        }

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🏁 推理完成")
            print(f"{'='*60}")
            print(f"📊 置信度：{best_confidence}/100")
            print(f"🔄 轮次：{len(thinking_history)}")
            print(f"🧠 L5协同：{'是' if used_l5 else '否'}")
            print(f"🎯 Token：{self.total_tokens}（预算{self.budget.usage_ratio():.0%}）")
            print(f"⏱️  耗时：{total_elapsed:.2f}s")
            print(f"{'='*60}\n")

        return result


class BudgetExceeded(Exception):
    """Token 预算耗尽"""
    pass


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Oxygen Dynamic Cognition v2 - 增强版动态认知推理引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 基本用法
  python dynamic_cognition_v2.py "解释什么是量子计算"

  # 启用 L5 协同推理
  python dynamic_cognition_v2.py "设计一个推荐系统" --max-rounds 5

  # 设置 Token 预算
  python dynamic_cognition_v2.py "复杂分析题" --budget 16000

  # 提供上下文
  python dynamic_cognition_v2.py "继续之前的问题" --context "之前讨论了量子计算的基础..."

  # JSON 输出
  python dynamic_cognition_v2.py "分析AI趋势" --json --log-file result.json
        """,
    )

    parser.add_argument("question", help="要回答的问题")
    parser.add_argument("--api-key", help="API 密钥")
    parser.add_argument("--base-url", help="API 基础 URL")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="模型（默认：gpt-3.5-turbo）")
    parser.add_argument("--threshold", type=int, default=80, help="置信度阈值（默认：80）")
    parser.add_argument("--max-rounds", type=int, default=4, help="最大轮次（默认：4，设5启用L5）")
    parser.add_argument("--budget", type=int, default=8000, help="Token 预算（默认：8000）")
    parser.add_argument(
        "--start-level", default="auto",
        choices=["auto", "L1", "L2", "L3", "L4", "L5"],
        help="起始认知等级（默认：auto）",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--log-file", help="保存认知日志")
    parser.add_argument("--context", help="上下文信息")
    parser.add_argument("--no-tools", action="store_true", help="禁用工具感知")
    parser.add_argument("--no-memory", action="store_true", help="禁用记忆集成")

    args = parser.parse_args()

    engine = EnhancedCognitionEngine(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        confidence_threshold=args.threshold,
        max_rounds=args.max_rounds,
        start_level=args.start_level,
        verbose=args.verbose,
        max_tokens_budget=args.budget,
        enable_tools=not args.no_tools,
        enable_memory=not args.no_memory,
        context=args.context,
    )

    try:
        result = engine.run(args.question)

        if args.log_file:
            with open(args.log_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        if args.json:
            output = {
                "question": result["question"],
                "answer": result["final_answer"],
                "confidence": result["final_confidence"],
                "rounds": result["total_rounds"],
                "level": result["initial_level"],
                "l5_used": result["used_l5"],
                "tokens": result["total_tokens"],
                "budget": result["token_budget_used"],
                "time": result["total_time"],
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(result["final_answer"])

    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断")
        sys.exit(1)
    except BudgetExceeded:
        print("\n⚠️  Token 预算耗尽，输出当前最佳答案：")
        if engine.budget.usage_ratio() > 0:
            print(engine.cognition_log[-1].get("answer_preview", "N/A"))
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
