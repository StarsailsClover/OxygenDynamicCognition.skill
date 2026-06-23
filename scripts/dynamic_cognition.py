#!/usr/bin/env python3
"""
Oxygen Dynamic Cognition - Main CLI Tool
基于动态认知理论的 AI 推理引擎

核心特性：
- 认知难度自动评估（借鉴 Early Exit 思想）
- 四级认知模式（L1~L4，对应 Dual System 理论）
- 动态置信度门控（达到阈值则提前终止）
- 认知升级机制（置信度不足时自动升级思考深度）
- 完整的认知过程日志（可观测、可分析）

设计理念：
将 Transformer 内部的固定计算图，映射为 Agent 层的动态思考轮次 + 可切换的认知模式，
实现"按需思考、自我评估、动态调整"的类人认知过程。
"""

import json
import sys
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

# 导入提示词库
try:
    from prompt_library import (
        DIFFICULTY_ASSESSMENT_SYSTEM,
        DIFFICULTY_ASSESSMENT_USER_TEMPLATE,
        CONFIDENCE_ASSESSMENT_SYSTEM,
        CONFIDENCE_ASSESSMENT_USER_TEMPLATE,
        COGNITIVE_UPGRADE_SYSTEM,
        COGNITIVE_UPGRADE_USER_TEMPLATE,
        FINAL_ANSWER_INTEGRATION_SYSTEM,
        FINAL_ANSWER_INTEGRATION_USER_TEMPLATE,
        COGNITIVE_LEVELS,
        DEFAULT_CONFIG,
        get_prompt,
        get_level_config,
        next_level,
    )
except ImportError:
    # 兼容直接运行的情况
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))
    from prompt_library import (
        DIFFICULTY_ASSESSMENT_SYSTEM,
        DIFFICULTY_ASSESSMENT_USER_TEMPLATE,
        CONFIDENCE_ASSESSMENT_SYSTEM,
        CONFIDENCE_ASSESSMENT_USER_TEMPLATE,
        COGNITIVE_UPGRADE_SYSTEM,
        COGNITIVE_UPGRADE_USER_TEMPLATE,
        FINAL_ANSWER_INTEGRATION_SYSTEM,
        FINAL_ANSWER_INTEGRATION_USER_TEMPLATE,
        COGNITIVE_LEVELS,
        DEFAULT_CONFIG,
        get_prompt,
        get_level_config,
        next_level,
    )


class DynamicCognitionEngine:
    """
    动态认知推理引擎
    
    核心流程：
    1. 难度初评 → 确定初始认知等级
    2. 动态推理循环 → 每轮思考后评估置信度
    3. 置信度达标 → 提前终止（Early Exit）
    4. 置信度不足 → 升级认知等级，继续思考
    5. 达到最大轮次 → 整合多轮结果，输出最终答案
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
    ):
        """
        初始化动态认知引擎
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 使用的模型名称
            confidence_threshold: 置信度阈值（0-100）
            max_rounds: 最大思考轮次
            start_level: 起始认知等级（auto/L1/L2/L3/L4）
            verbose: 是否输出详细过程
        """
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.max_rounds = max_rounds
        self.start_level = start_level
        self.verbose = verbose
        
        # 初始化 OpenAI 客户端
        self._init_client(api_key, base_url)
        
        # 认知过程记录
        self.cognition_log: List[Dict[str, Any]] = []
        self.total_tokens = 0
        self.total_time = 0.0
    
    def _init_client(self, api_key: Optional[str], base_url: Optional[str]):
        """初始化 OpenAI 兼容客户端"""
        try:
            from openai import OpenAI
        except ImportError:
            print("❌ 错误：未安装 openai 库")
            print("请运行：pip install openai")
            sys.exit(1)
        
        import os
        
        # 从环境变量获取默认值
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY", os.environ.get("OXYGEN_API_KEY", ""))
        if base_url is None:
            base_url = os.environ.get("OPENAI_BASE_URL", None)
        
        if not api_key:
            print("⚠️  警告：未设置 API Key")
            print("请设置环境变量 OPENAI_API_KEY 或通过 --api-key 参数传入")
        
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self.client = OpenAI(**client_kwargs)
    
    def _llm_call(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.5,
    ) -> str:
        """
        调用大模型 API
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            max_tokens: 最大生成 token 数
            temperature: 温度参数
            
        Returns:
            模型生成的文本
        """
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            result = response.choices[0].message.content.strip()
            
            # 统计 token 使用
            if hasattr(response, "usage") and response.usage:
                self.total_tokens += response.usage.total_tokens
            
            elapsed = time.time() - start_time
            self.total_time += elapsed
            
            return result
            
        except Exception as e:
            print(f"❌ API 调用失败：{e}")
            raise
    
    def assess_difficulty(self, question: str) -> Dict[str, Any]:
        """
        评估问题的认知难度
        
        Args:
            question: 用户问题
            
        Returns:
            难度评估结果字典
        """
        if self.verbose:
            print(f"🔍 正在评估问题难度...")
        
        user_prompt = DIFFICULTY_ASSESSMENT_USER_TEMPLATE.format(question=question)
        
        result_text = self._llm_call(
            system_prompt=DIFFICULTY_ASSESSMENT_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=200,
            temperature=0.1,
        )
        
        # 尝试解析 JSON
        try:
            # 清理可能的 markdown 代码块标记
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            result = json.loads(result_text.strip())
        except json.JSONDecodeError:
            # 解析失败，使用默认值
            if self.verbose:
                print(f"⚠️  难度评估 JSON 解析失败，使用默认等级 L2")
            result = {
                "level": "L2",
                "type": "综合类",
                "reason": "解析失败，使用默认等级",
                "estimated_tokens": 500,
            }
        
        # 记录日志
        self.cognition_log.append({
            "stage": "difficulty_assessment",
            "level": result.get("level", "L2"),
            "type": result.get("type", "综合类"),
            "reason": result.get("reason", ""),
            "raw_output": result_text,
        })
        
        if self.verbose:
            level = result.get("level", "L2")
            level_name = COGNITIVE_LEVELS.get(level, {}).get("name", level)
            print(f"  📊 难度等级：{level} ({level_name})")
            print(f"  📋 问题类型：{result.get('type', '未知')}")
            print(f"  💭 评估理由：{result.get('reason', '')}")
        
        return result
    
    def assess_confidence(self, question: str, answer: str) -> int:
        """
        评估答案的置信度
        
        Args:
            question: 问题
            answer: 答案
            
        Returns:
            置信度分数（0-100）
        """
        user_prompt = CONFIDENCE_ASSESSMENT_USER_TEMPLATE.format(
            question=question,
            answer=answer,
        )
        
        result_text = self._llm_call(
            system_prompt=CONFIDENCE_ASSESSMENT_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=10,
            temperature=0.0,
        )
        
        # 提取数字
        try:
            # 清理非数字字符
            digits = ''.join(c for c in result_text if c.isdigit())
            confidence = int(digits)
            confidence = max(0, min(100, confidence))  # 限制在 0-100
        except (ValueError, IndexError):
            confidence = 70  # 默认置信度
        
        return confidence
    
    def think_with_level(self, question: str, level: str) -> str:
        """
        使用指定认知等级进行思考
        
        Args:
            question: 用户问题
            level: 认知等级（L1/L2/L3/L4）
            
        Returns:
            思考结果
        """
        level_config = get_level_config(level)
        system_prompt, user_prompt = get_prompt(level, question)
        
        if self.verbose:
            print(f"  🧠 使用认知等级：{level} ({level_config['name']})")
        
        result = self._llm_call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=level_config["max_tokens"],
            temperature=level_config["temperature"],
        )
        
        return result
    
    def upgrade_cognition(self, question: str, previous_answer: str) -> str:
        """
        认知升级：基于之前的答案进行更深入的思考
        
        Args:
            question: 问题
            previous_answer: 之前的答案
            
        Returns:
            升级后的答案
        """
        user_prompt = COGNITIVE_UPGRADE_USER_TEMPLATE.format(
            question=question,
            previous_answer=previous_answer,
        )
        
        result = self._llm_call(
            system_prompt=COGNITIVE_UPGRADE_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=1500,
            temperature=0.4,
        )
        
        return result
    
    def integrate_answers(self, question: str, thinking_history: List[str]) -> str:
        """
        整合多轮思考结果，输出最终答案
        
        Args:
            question: 原始问题
            thinking_history: 思考历史列表
            
        Returns:
            整合后的最终答案
        """
        # 格式化思考历史
        history_text = ""
        for i, thought in enumerate(thinking_history, 1):
            history_text += f"第 {i} 轮思考：\n{thought}\n\n"
        
        user_prompt = FINAL_ANSWER_INTEGRATION_USER_TEMPLATE.format(
            question=question,
            thinking_history=history_text,
        )
        
        result = self._llm_call(
            system_prompt=FINAL_ANSWER_INTEGRATION_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=2000,
            temperature=0.3,
        )
        
        return result
    
    def run(self, question: str) -> Dict[str, Any]:
        """
        执行动态认知推理
        
        Args:
            question: 用户问题
            
        Returns:
            完整的推理结果字典
        """
        start_time = time.time()
        self.cognition_log = []
        self.total_tokens = 0
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🚀 Oxygen Dynamic Cognition Engine")
            print(f"{'='*60}")
            print(f"📝 问题：{question}")
            print(f"⚙️  配置：阈值={self.confidence_threshold}, 最大轮次={self.max_rounds}")
            print(f"{'='*60}\n")
        
        # 1. 确定初始认知等级
        if self.start_level == "auto":
            difficulty_result = self.assess_difficulty(question)
            current_level = difficulty_result.get("level", "L2")
        else:
            current_level = self.start_level
            if self.verbose:
                level_name = COGNITIVE_LEVELS.get(current_level, {}).get("name", current_level)
                print(f"📊 指定起始等级：{current_level} ({level_name})")
        
        # 2. 动态推理循环
        thinking_history = []
        best_answer = ""
        best_confidence = 0
        current_answer = ""
        
        for round_num in range(1, self.max_rounds + 1):
            if self.verbose:
                print(f"\n🔄 第 {round_num} 轮思考")
                print(f"  {'─'*40}")
            
            # 执行思考
            if round_num == 1:
                # 第一轮使用初始认知等级
                current_answer = self.think_with_level(question, current_level)
            else:
                # 后续轮次使用认知升级
                current_answer = self.upgrade_cognition(question, current_answer)
                # 同时升级认知等级
                current_level = next_level(current_level)
            
            thinking_history.append(current_answer)
            
            # 评估置信度
            confidence = self.assess_confidence(question, current_answer)
            
            # 记录日志
            round_log = {
                "stage": "thinking",
                "round": round_num,
                "level": current_level,
                "confidence": confidence,
                "answer": current_answer,
            }
            self.cognition_log.append(round_log)
            
            # 更新最佳答案
            if confidence > best_confidence:
                best_confidence = confidence
                best_answer = current_answer
            
            if self.verbose:
                level_name = COGNITIVE_LEVELS.get(current_level, {}).get("name", current_level)
                print(f"  📈 置信度：{confidence}/100")
                print(f"  🏆 当前最佳：{best_confidence}/100")
            
            # 检查是否达到阈值（Early Exit）
            if confidence >= self.confidence_threshold:
                if self.verbose:
                    print(f"\n✅ 置信度达标（{confidence} ≥ {self.confidence_threshold}），提前终止")
                break
            
            # 检查是否还有升级空间
            if current_level == "L4" and round_num >= 2:
                if self.verbose:
                    print(f"  ⚠️  已达最高认知等级，继续优化...")
        
        # 3. 整合最终答案（如果有多轮思考）
        if len(thinking_history) > 1:
            if self.verbose:
                print(f"\n🔗 整合多轮思考结果...")
            final_answer = self.integrate_answers(question, thinking_history)
            final_confidence = self.assess_confidence(question, final_answer)
            
            # 如果整合后的置信度更高，使用整合结果
            if final_confidence > best_confidence:
                best_confidence = final_confidence
                best_answer = final_answer
        else:
            final_answer = best_answer
            final_confidence = best_confidence
        
        # 4. 计算总耗时
        total_elapsed = time.time() - start_time
        
        # 5. 构建结果
        result = {
            "question": question,
            "final_answer": best_answer,
            "final_confidence": best_confidence,
            "total_rounds": len(thinking_history),
            "initial_level": self.start_level if self.start_level != "auto" else difficulty_result.get("level", "L2"),
            "total_tokens": self.total_tokens,
            "total_time": round(total_elapsed, 2),
            "cognition_log": self.cognition_log,
            "thinking_history": thinking_history,
        }
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🏁 推理完成")
            print(f"{'='*60}")
            print(f"📊 最终置信度：{best_confidence}/100")
            print(f"🔄 思考轮次：{len(thinking_history)}")
            print(f"🎯 消耗 Token：{self.total_tokens}")
            print(f"⏱️  总耗时：{total_elapsed:.2f}s")
            print(f"{'='*60}\n")
        
        return result


def main():
    """CLI 入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Oxygen Dynamic Cognition - 动态认知推理引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 基本用法
  python dynamic_cognition.py "解释什么是量子计算"
  
  # 指定模型和阈值
  python dynamic_cognition.py "证明勾股定理" --model gpt-4 --threshold 90
  
  # 指定起始认知等级
  python dynamic_cognition.py "1+1等于几" --start-level L1
  
  # 输出详细过程
  python dynamic_cognition.py "设计一个推荐系统架构" --verbose
  
  # 输出 JSON 格式
  python dynamic_cognition.py "分析AI的未来发展趋势" --json
        """,
    )
    
    parser.add_argument("question", help="要回答的问题")
    parser.add_argument("--api-key", help="API 密钥")
    parser.add_argument("--base-url", help="API 基础 URL")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="使用的模型（默认：gpt-3.5-turbo）")
    parser.add_argument("--threshold", type=int, default=80, help="置信度阈值 0-100（默认：80）")
    parser.add_argument("--max-rounds", type=int, default=4, help="最大思考轮次（默认：4）")
    parser.add_argument(
        "--start-level",
        default="auto",
        choices=["auto", "L1", "L2", "L3", "L4"],
        help="起始认知等级（默认：auto 自动评估）",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="输出详细推理过程")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    parser.add_argument("--log-file", help="将认知日志保存到指定文件")
    
    args = parser.parse_args()
    
    # 创建引擎
    engine = DynamicCognitionEngine(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        confidence_threshold=args.threshold,
        max_rounds=args.max_rounds,
        start_level=args.start_level,
        verbose=args.verbose,
    )
    
    try:
        # 运行推理
        result = engine.run(args.question)
        
        # 保存日志
        if args.log_file:
            with open(args.log_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            if args.verbose:
                print(f"📝 认知日志已保存到：{args.log_file}")
        
        # 输出结果
        if args.json:
            # JSON 模式
            output = {
                "question": result["question"],
                "answer": result["final_answer"],
                "confidence": result["final_confidence"],
                "rounds": result["total_rounds"],
                "tokens": result["total_tokens"],
                "time": result["total_time"],
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            # 普通模式
            if not args.verbose:
                # 如果没有 verbose，只输出最终答案
                print(result["final_answer"])
            # verbose 模式下已经在 run() 中输出了过程，这里输出最终答案
            elif args.verbose:
                print(f"\n📝 最终答案：")
                print(f"{'─'*60}")
                print(result["final_answer"])
                print(f"{'─'*60}")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
