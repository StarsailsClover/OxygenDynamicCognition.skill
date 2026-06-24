#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Oxygen Dynamic Cognition v2.1 - 单元测试
GitHub@StarsailsClover

使用 Mock 模式进行离线测试，无需 API Key
"""
import sys
import json
from pathlib import Path

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from dynamic_cognition_v21 import (
    EnhancedCognitionEngineV21,
    MockLLM,
    SimpleCache,
    CognitiveBudget,
    ToolDecision,
    BudgetExceeded,
    classify_problem_type,
)


def run_test(name, test_func):
    """运行单个测试"""
    try:
        test_func()
        print(f"  ✅ {name}")
        return True
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 基础组件测试
# ============================================================

def test_simple_cache():
    """测试 LRU 缓存"""
    cache = SimpleCache(max_size=3)
    
    # 基本 put/get
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.size() == 3
    
    # 超出容量，淘汰最旧的
    cache.put("d", 4)
    assert cache.size() == 3
    assert cache.get("a") is None  # a 被淘汰
    assert cache.get("d") == 4
    
    # 访问后移到末尾（不被淘汰）
    cache.get("b")  # 访问 b，移到最新
    cache.put("e", 5)
    assert cache.get("b") is not None  # b 还在
    assert cache.get("c") is None  # c 被淘汰
    
    # 清空
    cache.clear()
    assert cache.size() == 0


def test_cognitive_budget():
    """测试认知预算管理"""
    budget = CognitiveBudget(max_tokens=1000)
    
    assert budget.remaining() == 1000
    assert budget.usage_ratio() == 0.0
    
    budget.consume(300, "test_stage")
    assert budget.used_tokens == 300
    assert budget.remaining() == 700
    assert budget.usage_ratio() == 0.3
    assert budget.should_stop() is False  # 剩余700 > 500，不停止
    
    budget.consume(500, "another_stage")
    assert budget.remaining() == 200
    assert budget.should_stop() is True  # 剩余200 < 500，应该停止
    
    # 测试明细
    breakdown = budget.get_breakdown()
    assert breakdown["test_stage"] == 300
    assert breakdown["another_stage"] == 500


def test_mock_llm():
    """测试 Mock LLM"""
    mock = MockLLM(delay=0)
    
    # 测试难度评估
    response = mock.chat_completions_create(
        messages=[
            {"role": "system", "content": "你是难度评估器"},
            {"role": "user", "content": "请评估以下问题的难度：什么是AI？"},
        ],
        max_tokens=300,
    )
    content = response.choices[0].message.content
    result = json.loads(content)
    assert "level" in result
    assert "type" in result
    
    # 测试置信度评估
    response = mock.chat_completions_create(
        messages=[{"role": "user", "content": "请评估置信度..."}],
        max_tokens=20,
    )
    content = response.choices[0].message.content
    assert content.isdigit() or any(c.isdigit() for c in content)
    
    # 测试 usage
    assert hasattr(response, 'usage')
    assert response.usage.total_tokens == 100


def test_problem_classifier():
    """测试问题分类器"""
    assert classify_problem_type("计算 1+1 等于多少") == "数学计算类"
    assert classify_problem_type("什么是量子计算") == "数学计算类"  # 包含"计算"
    assert classify_problem_type("写一个快速排序算法") == "代码编程类"
    assert classify_problem_type("分析一下这个架构设计") == "专业分析类"
    assert classify_problem_type("你好，今天天气怎么样") == "综合类"


# ============================================================
# 引擎功能测试
# ============================================================

def test_engine_initialization():
    """测试引擎初始化"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        confidence_threshold=80,
        max_rounds=3,
        verbose=False,
    )
    
    assert engine.mock_mode is True
    assert engine.confidence_threshold == 80
    assert engine.max_rounds == 3
    assert engine.enable_cache is True
    assert isinstance(engine.client, MockLLM)


def test_quick_classify():
    """测试本地快速分类"""
    engine = EnhancedCognitionEngineV21(mock_mode=True, verbose=False)
    
    # 简单问题
    result = engine.quick_classify("你好")
    assert "type" in result
    assert "suggested_level" in result
    assert "adaptive_threshold" in result
    
    # 复杂问题
    result = engine.quick_classify("请分析设计一个高可用的分布式系统架构")
    assert result["suggested_level"] in ["L2", "L3"]


def test_basic_reasoning():
    """测试基本推理流程"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        confidence_threshold=50,  # 低阈值，确保early exit
        max_rounds=4,
        verbose=False,
    )
    
    result = engine.run("什么是机器学习？")
    
    assert "final_answer" in result
    assert "final_confidence" in result
    assert "total_rounds" in result
    assert "thinking_history" in result
    assert len(result["thinking_history"]) >= 1
    assert result["final_confidence"] > 0
    assert result["engine_version"] == "v2.1"
    assert result["mock_mode"] is True


def test_early_exit():
    """测试 Early Exit 机制"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        confidence_threshold=50,  # 很低的阈值
        max_rounds=5,
        verbose=False,
    )
    
    result = engine.run("简单问题")
    
    # 因为置信度是85，阈值50，应该第一轮就退出
    assert result["total_rounds"] == 1


def test_multi_round_upgrade():
    """测试多轮认知升级"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        confidence_threshold=95,  # 很高的阈值，强制多轮
        max_rounds=3,
        start_level="L2",
        enable_cache=False,  # 禁用缓存避免干扰
        verbose=False,
    )
    
    # 使用数学计算类问题，阈值90 > 置信度85，不会early exit
    result = engine.run("计算复杂的数学方程和积分证明")
    
    # 应该跑满3轮（置信度85 < 阈值90）
    assert result["total_rounds"] == 3
    assert len(result["thinking_history"]) == 3
    assert result["total_rounds"] <= engine.max_rounds


def test_l5_collaborative():
    """测试 L5 协同推理"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        confidence_threshold=95,
        max_rounds=5,  # 设为5才能到L5
        start_level="L3",
        enable_cache=False,  # 禁用缓存避免干扰
        verbose=False,
    )
    
    # 使用数学计算类问题，阈值90 > 置信度85，不会early exit
    # 等级路径：L3 -> L4 -> L5 -> 触发协同
    result = engine.run("计算复杂的数学积分方程和证明")
    
    assert result["used_l5"] is True
    assert result["total_rounds"] >= 3
    
    # 检查认知日志中是否有 L5 记录
    has_l5 = any(
        log.get("stage") == "L5_collaborative" 
        for log in result["cognition_log"]
    )
    assert has_l5


def test_adaptive_threshold():
    """测试自适应阈值"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        confidence_threshold=80,
        verbose=False,
    )
    
    result = engine.run("计算 1234 * 5678 等于多少")
    
    # 数学计算类阈值应该是90
    assert result["adaptive_threshold"] == 90
    assert result["problem_type"] == "数学计算类"


def test_context_support():
    """测试上下文支持"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        context="之前我们讨论了机器学习的基本概念",
        verbose=False,
    )
    
    result = engine.run("继续深入讲解")
    
    assert "final_answer" in result
    assert engine.context != ""


def test_cost_analysis():
    """测试成本分析"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        verbose=False,
    )
    
    result = engine.run("测试问题")
    
    assert "cost_analysis" in result
    cost = result["cost_analysis"]
    assert "total_tokens" in cost
    assert "total_time_seconds" in cost
    assert "budget_used_ratio" in cost
    assert "token_breakdown_by_stage" in cost


def test_cognition_log():
    """测试认知日志"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        max_rounds=3,
        confidence_threshold=95,
        verbose=False,
    )
    
    result = engine.run("测试问题")
    
    assert len(result["cognition_log"]) > 0
    
    # 检查日志结构
    for log in result["cognition_log"]:
        assert "stage" in log
        if log["stage"] == "thinking":
            assert "round" in log
            assert "level" in log
            assert "confidence" in log


def test_tool_decision():
    """测试工具决策"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        enable_tools=True,
        verbose=False,
    )
    
    decision = engine.decide_tools("计算圆周率", "圆周率约等于3.14159")
    
    assert isinstance(decision, ToolDecision)
    assert hasattr(decision, 'need_tool')
    assert hasattr(decision, 'tool_types')
    assert hasattr(decision, 'reason')


def test_cache_functionality():
    """测试缓存功能"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        enable_cache=True,
        verbose=False,
    )
    
    # 第一次调用
    result1 = engine.run("相同的问题")
    
    # 清空缓存
    engine.clear_cache()
    
    # 第二次调用（缓存应该已清空，但结果应该相同因为是mock）
    result2 = engine.run("相同的问题")
    
    assert result1["final_answer"] == result2["final_answer"]


def test_json_output():
    """测试 JSON 输出格式"""
    engine = EnhancedCognitionEngineV21(
        mock_mode=True,
        verbose=False,
    )
    
    result = engine.run("测试JSON输出")
    
    # 确保可以序列化为JSON
    json_str = json.dumps(result, ensure_ascii=False, default=str)
    assert len(json_str) > 0
    
    # 确保可以反序列化
    parsed = json.loads(json_str)
    assert "question" in parsed
    assert "final_answer" in parsed


# ============================================================
# 边界条件测试
# ============================================================

def test_empty_question():
    """测试空问题"""
    engine = EnhancedCognitionEngineV21(mock_mode=True, verbose=False)
    result = engine.run("")
    assert "final_answer" in result
    assert result["final_confidence"] > 0


def test_very_long_question():
    """测试超长问题"""
    engine = EnhancedCognitionEngineV21(mock_mode=True, verbose=False)
    long_question = "这是一个非常长的问题。" * 100
    result = engine.run(long_question)
    assert "final_answer" in result


def test_special_characters():
    """测试特殊字符"""
    engine = EnhancedCognitionEngineV21(mock_mode=True, verbose=False)
    result = engine.run("测试特殊字符：!@#$%^&*()_+-=[]{}|;':\",./<>?")
    assert "final_answer" in result


# ============================================================
# 主测试入口
# ============================================================

def main():
    print("=" * 60)
    print("Oxygen Dynamic Cognition v2.1 - 单元测试")
    print("GitHub@StarsailsClover")
    print("=" * 60)
    print()
    
    tests = [
        # 基础组件
        ("LRU 缓存", test_simple_cache),
        ("认知预算管理", test_cognitive_budget),
        ("Mock LLM", test_mock_llm),
        ("问题分类器", test_problem_classifier),
        
        # 引擎功能
        ("引擎初始化", test_engine_initialization),
        ("本地快速分类", test_quick_classify),
        ("基本推理流程", test_basic_reasoning),
        ("Early Exit 机制", test_early_exit),
        ("多轮认知升级", test_multi_round_upgrade),
        ("L5 协同推理", test_l5_collaborative),
        ("自适应阈值", test_adaptive_threshold),
        ("上下文支持", test_context_support),
        ("成本分析", test_cost_analysis),
        ("认知日志", test_cognition_log),
        ("工具决策", test_tool_decision),
        ("缓存功能", test_cache_functionality),
        ("JSON 输出", test_json_output),
        
        # 边界条件
        ("空问题", test_empty_question),
        ("超长问题", test_very_long_question),
        ("特殊字符", test_special_characters),
    ]
    
    passed = 0
    failed = 0
    
    print("📦 基础组件测试")
    print("-" * 40)
    for name, func in tests[:4]:
        if run_test(name, func):
            passed += 1
        else:
            failed += 1
    
    print()
    print("🧠 引擎功能测试")
    print("-" * 40)
    for name, func in tests[4:17]:
        if run_test(name, func):
            passed += 1
        else:
            failed += 1
    
    print()
    print("🔍 边界条件测试")
    print("-" * 40)
    for name, func in tests[17:]:
        if run_test(name, func):
            passed += 1
        else:
            failed += 1
    
    print()
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
