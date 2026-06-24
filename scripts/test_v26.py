#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OxygenDynamicCognition v26.0 Alpha 4 完整测试套件
GitHub@StarsailsClover

测试内容：
1. 基础组件（向后兼容）
2. 思维树 Tree of Thoughts
3. 思维图 Graph of Thoughts
4. 自一致性 Self-Consistency
5. 反射机制 Reflection
6. 验证链 Chain of Verification
7. 渐进式深化 Progressive Deepening
8. 元认知监控 Metacognitive Monitoring
9. 认知偏差检测 Cognitive Bias Detection
10. 主推理流程
"""

import os
import sys
import json
import unittest

# 添加脚本路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dynamic_cognition_v26 import (
    OxygenDynamicCognitionV26,
    ThoughtNode,
    ThoughtGraph,
    SimpleCache,
    CognitiveBudget,
    QuestionClassifier,
    BiasDetector,
    MockLLM,
)


class TestBasicComponents(unittest.TestCase):
    """测试基础组件"""
    
    def test_simple_cache(self):
        """测试LRU缓存"""
        cache = SimpleCache(capacity=3)
        
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("c"), 3)
        
        # 超出容量，应该淘汰最久未使用的
        cache.put("d", 4)
        self.assertIsNone(cache.get("a"))  # a被淘汰
        self.assertEqual(cache.get("d"), 4)
    
    def test_cognitive_budget(self):
        """测试认知预算"""
        budget = CognitiveBudget(
            max_tokens=1000,
            max_rounds=5,
            max_time_seconds=60,
        )
        
        self.assertTrue(budget.check())
        
        budget.use_tokens(500)
        self.assertEqual(budget.tokens_used, 500)
        self.assertEqual(budget.rounds_completed, 1)
        self.assertTrue(budget.check())
        
        budget.use_tokens(600)
        self.assertFalse(budget.check())  # 超出token预算
    
    def test_question_classifier(self):
        """测试问题分类器"""
        self.assertEqual(QuestionClassifier.classify("什么是Python？"), "factual")
        self.assertEqual(QuestionClassifier.classify("如何学习编程？"), "reasoning")
        self.assertEqual(QuestionClassifier.classify("设计一个新系统"), "creative")
        self.assertEqual(QuestionClassifier.classify("比较Java和Python"), "evaluation")
        self.assertEqual(QuestionClassifier.classify("计算1+1等于多少"), "math")
        self.assertEqual(QuestionClassifier.classify("写一个排序函数"), "coding")
    
    def test_bias_detector(self):
        """测试偏差检测器"""
        # 无偏差文本
        result = BiasDetector.detect("这是一个客观的分析，考虑了多个角度")
        self.assertEqual(len(result.biases_detected), 0)
        
        # 过度自信
        result = BiasDetector.detect("我100%确定这是正确的，不需要验证")
        self.assertIn("overconfidence", result.biases_detected)
    
    def test_mock_llm(self):
        """测试Mock LLM"""
        mock = MockLLM()
        
        response = mock.chat_completion([
            {"role": "user", "content": "评估这个问题的难度"}
        ])
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        self.assertEqual(mock.call_count, 1)


class TestThoughtGraph(unittest.TestCase):
    """测试思维图/思维树"""
    
    def test_thought_node(self):
        """测试思维节点"""
        node = ThoughtNode(
            node_id="n1",
            content="测试思维",
            depth=1,
            score=0.8,
        )
        
        self.assertEqual(node.node_id, "n1")
        self.assertEqual(node.depth, 1)
        self.assertEqual(node.score, 0.8)
        self.assertTrue(node.is_leaf)
    
    def test_thought_graph_basic(self):
        """测试思维图基本操作"""
        graph = ThoughtGraph()
        
        root = ThoughtNode(node_id="root", content="根节点", depth=0)
        child1 = ThoughtNode(node_id="c1", content="子节点1", depth=1)
        child2 = ThoughtNode(node_id="c2", content="子节点2", depth=1)
        
        graph.add_node(root)
        graph.add_node(child1)
        graph.add_node(child2)
        
        graph.add_edge("root", "c1", "follows")
        graph.add_edge("root", "c2", "follows")
        
        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(len(graph.edges), 2)
        self.assertEqual(graph.root_id, "root")
    
    def test_get_path(self):
        """测试获取路径"""
        graph = ThoughtGraph()
        
        root = ThoughtNode(node_id="root", content="根", depth=0)
        mid = ThoughtNode(node_id="mid", content="中间", depth=1)
        leaf = ThoughtNode(node_id="leaf", content="叶子", depth=2)
        
        graph.add_node(root)
        graph.add_node(mid)
        graph.add_node(leaf)
        
        graph.add_edge("root", "mid")
        graph.add_edge("mid", "leaf")
        
        path = graph.get_path("leaf")
        self.assertEqual(len(path), 3)
        self.assertEqual(path[0].node_id, "root")
        self.assertEqual(path[-1].node_id, "leaf")
    
    def test_get_leaves(self):
        """测试获取叶子节点"""
        graph = ThoughtGraph()
        
        root = ThoughtNode(node_id="root", content="根", depth=0)
        c1 = ThoughtNode(node_id="c1", content="子1", depth=1)
        c2 = ThoughtNode(node_id="c2", content="子2", depth=1)
        gc = ThoughtNode(node_id="gc", content="孙", depth=2)
        
        graph.add_node(root)
        graph.add_node(c1)
        graph.add_node(c2)
        graph.add_node(gc)
        
        graph.add_edge("root", "c1")
        graph.add_edge("root", "c2")
        graph.add_edge("c1", "gc")
        
        leaves = graph.get_leaves()
        leaf_ids = [l.node_id for l in leaves]
        
        self.assertIn("gc", leaf_ids)
        self.assertIn("c2", leaf_ids)
        self.assertNotIn("root", leaf_ids)
    
    def test_get_best_leaf(self):
        """测试获取最佳叶子"""
        graph = ThoughtGraph()
        
        root = ThoughtNode(node_id="root", content="根", depth=0, score=0.5)
        c1 = ThoughtNode(node_id="c1", content="子1", depth=1, score=0.8)
        c2 = ThoughtNode(node_id="c2", content="子2", depth=1, score=0.6)
        
        graph.add_node(root)
        graph.add_node(c1)
        graph.add_node(c2)
        
        graph.add_edge("root", "c1")
        graph.add_edge("root", "c2")
        
        best = graph.get_best_leaf()
        self.assertEqual(best.node_id, "c1")
        self.assertEqual(best.score, 0.8)


class TestTreeOfThoughts(unittest.TestCase):
    """测试思维树"""
    
    def setUp(self):
        self.engine = OxygenDynamicCognitionV26(
            mock_mode=True,
            enable_tot=True,
        )
    
    def test_tree_of_thoughts_basic(self):
        """测试基本思维树"""
        graph = self.engine.tree_of_thoughts(
            "如何学习编程？",
            branching_factor=2,
            max_depth=2,
        )
        
        self.assertIsInstance(graph, ThoughtGraph)
        self.assertIsNotNone(graph.root_id)
        
        # 应该有多个节点
        self.assertGreater(len(graph.nodes), 1)
    
    def test_tree_of_thoughts_branching(self):
        """测试思维树分支因子"""
        branching = 3
        graph = self.engine.tree_of_thoughts(
            "测试问题",
            branching_factor=branching,
            max_depth=1,
        )
        
        # 根节点 + 第一层分支
        self.assertEqual(len(graph.nodes), 1 + branching)
    
    def test_tree_of_thoughts_depth(self):
        """测试思维树深度"""
        max_depth = 2
        graph = self.engine.tree_of_thoughts(
            "测试问题",
            branching_factor=2,
            max_depth=max_depth,
        )
        
        # 检查最深的节点
        max_node_depth = max(n.depth for n in graph.nodes.values())
        self.assertEqual(max_node_depth, max_depth)
    
    def test_get_best_tot_answer(self):
        """测试获取最佳思维树答案"""
        graph = self.engine.tree_of_thoughts(
            "测试问题",
            branching_factor=2,
            max_depth=2,
        )
        
        answer = self.engine.get_best_tot_answer(graph)
        self.assertIsNotNone(answer)
        self.assertIsInstance(answer, str)


class TestSelfConsistency(unittest.TestCase):
    """测试自一致性"""
    
    def setUp(self):
        self.engine = OxygenDynamicCognitionV26(
            mock_mode=True,
            enable_self_consistency=True,
        )
    
    def test_self_consistency_basic(self):
        """测试基本自一致性"""
        result = self.engine.self_consistency(
            "什么是人工智能？",
            num_samples=3,
        )
        
        self.assertIn("final_answer", result)
        self.assertIn("consensus_score", result)
        self.assertIn("all_answers", result)
        self.assertEqual(len(result["all_answers"]), 3)
    
    def test_consensus_score_range(self):
        """测试一致性分数范围"""
        result = self.engine.self_consistency(
            "测试问题",
            num_samples=5,
        )
        
        self.assertGreaterEqual(result["consensus_score"], 0.0)
        self.assertLessEqual(result["consensus_score"], 1.0)
    
    def test_think_with_style(self):
        """测试不同风格思考"""
        answer1 = self.engine._think_with_style("测试问题", style_num=0)
        answer2 = self.engine._think_with_style("测试问题", style_num=1)
        answer3 = self.engine._think_with_style("测试问题", style_num=2)
        
        # 都应该返回字符串
        self.assertIsInstance(answer1, str)
        self.assertIsInstance(answer2, str)
        self.assertIsInstance(answer3, str)


class TestReflection(unittest.TestCase):
    """测试反射机制"""
    
    def setUp(self):
        self.engine = OxygenDynamicCognitionV26(
            mock_mode=True,
            enable_reflection=True,
        )
    
    def test_reflection_basic(self):
        """测试基本反射"""
        answer = "这是一个初步的答案。"
        question = "测试问题"
        
        result = self.engine.reflect(answer, question, depth=1)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.original_answer, answer)
        self.assertIsInstance(result.issues_found, list)
        self.assertIsInstance(result.improvements, list)
    
    def test_reflection_depth(self):
        """测试反射深度"""
        result = self.engine.reflect("答案", "问题", depth=2)
        
        self.assertEqual(result.reflection_depth, 2)
    
    def test_reflection_metacognition_update(self):
        """测试反射更新元认知"""
        initial = self.engine.metacognition["reflections_done"]
        
        self.engine.reflect("答案", "问题", depth=1)
        
        self.assertEqual(self.engine.metacognition["reflections_done"], initial + 1)


class TestChainOfVerification(unittest.TestCase):
    """测试验证链"""
    
    def setUp(self):
        self.engine = OxygenDynamicCognitionV26(
            mock_mode=True,
            enable_verification=True,
        )
    
    def test_verification_basic(self):
        """测试基本验证链"""
        answer = """这是第一个声明。这是第二个声明。这是第三个声明。"""
        question = "测试问题"
        
        result = self.engine.chain_of_verification(answer, question)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result.verification_steps, list)
        self.assertGreater(len(result.verification_steps), 0)
    
    def test_extract_claims(self):
        """测试提取声明"""
        answer = """声明一的内容。声明二的内容。声明三的内容。"""
        
        claims = self.engine._extract_claims(answer)
        
        self.assertIsInstance(claims, list)
        self.assertGreater(len(claims), 0)
    
    def test_verify_claim(self):
        """测试验证单个声明"""
        result = self.engine._verify_claim("这是一个测试声明", "测试问题")
        
        self.assertIn("verified", result)
        self.assertIn("confidence", result)
        self.assertIsInstance(result["verified"], bool)
    
    def test_verification_metacognition_update(self):
        """测试验证更新元认知"""
        initial = self.engine.metacognition["verifications_done"]
        
        self.engine.chain_of_verification("答案", "问题")
        
        self.assertEqual(self.engine.metacognition["verifications_done"], initial + 1)


class TestProgressiveDeepening(unittest.TestCase):
    """测试渐进式深化"""
    
    def setUp(self):
        self.engine = OxygenDynamicCognitionV26(
            mock_mode=True,
        )
    
    def test_progressive_deepening_basic(self):
        """测试基本渐进式深化"""
        result = self.engine.progressive_deepening(
            "什么是机器学习？",
            max_levels=3,
        )
        
        self.assertIn("final_answer", result)
        self.assertIn("final_confidence", result)
        self.assertIn("levels_explored", result)
        self.assertIn("progression", result)
    
    def test_progression_levels(self):
        """测试深化层级"""
        result = self.engine.progressive_deepening(
            "测试问题",
            max_levels=4,
        )
        
        self.assertGreaterEqual(result["levels_explored"], 1)
        self.assertLessEqual(result["levels_explored"], 4)
        self.assertEqual(len(result["progression"]), result["levels_explored"])
    
    def test_think_at_depth(self):
        """测试指定深度思考"""
        answer = self.engine._think_at_depth("测试问题", depth=2)
        
        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 0)


class TestMetacognitiveMonitoring(unittest.TestCase):
    """测试元认知监控"""
    
    def setUp(self):
        self.engine = OxygenDynamicCognitionV26(
            mock_mode=True,
        )
    
    def test_metacognition_report(self):
        """测试元认知报告"""
        # 先做一些操作
        self.engine.tree_of_thoughts("测试", branching_factor=2, max_depth=1)
        self.engine.reflect("答案", "问题", depth=1)
        
        report = self.engine.get_metacognition_report()
        
        self.assertIn("cognitive_effort", report)
        self.assertIn("thoughts_generated", report)
        self.assertIn("reflections", report)
        self.assertIn("verifications", report)
        self.assertIn("bias_checks", report)
    
    def test_cognitive_effort_score(self):
        """测试认知努力分数"""
        report = self.engine.get_metacognition_report()
        
        self.assertGreaterEqual(report["cognitive_effort"], 0.0)
        self.assertLessEqual(report["cognitive_effort"], 1.0)


class TestBiasDetection(unittest.TestCase):
    """测试认知偏差检测"""
    
    def setUp(self):
        self.engine = OxygenDynamicCognitionV26(
            mock_mode=True,
            enable_bias_detection=True,
        )
    
    def test_bias_detection_in_confidence(self):
        """测试置信度评估中的偏差检测"""
        answer = "我100%确定这是正确的答案。"
        
        result = self.engine.assess_confidence(answer, "问题", detailed=True)
        
        self.assertIn("bias_detection", result)
        self.assertIsNotNone(result["bias_detection"])
    
    def test_bias_checks_count(self):
        """测试偏差检查计数"""
        initial = self.engine.metacognition["bias_checks_done"]
        
        self.engine.assess_confidence("答案", "问题", detailed=True)
        
        self.assertEqual(self.engine.metacognition["bias_checks_done"], initial + 1)


class TestMainEngine(unittest.TestCase):
    """测试主引擎"""
    
    def setUp(self):
        self.engine = OxygenDynamicCognitionV26(
            mock_mode=True,
            enable_tot=True,
            enable_reflection=True,
            enable_verification=True,
            enable_self_consistency=True,
            enable_bias_detection=True,
        )
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        self.assertEqual(self.engine.VERSION, "26.0.0-alpha.4")
        self.assertTrue(self.engine.enable_tot)
        self.assertTrue(self.engine.enable_reflection)
    
    def test_assess_difficulty(self):
        """测试难度评估"""
        result = self.engine.assess_difficulty("什么是Python？")
        
        self.assertIn("level", result)
        self.assertIn("category", result)
        self.assertIn("threshold", result)
        self.assertGreaterEqual(result["level"], 1)
        self.assertLessEqual(result["level"], 5)
    
    def test_assess_confidence(self):
        """测试置信度评估"""
        result = self.engine.assess_confidence("这是一个答案", "问题")
        
        self.assertIn("confidence", result)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
    
    def test_assess_confidence_detailed(self):
        """测试详细置信度评估"""
        result = self.engine.assess_confidence("答案", "问题", detailed=True)
        
        self.assertIn("confidence", result)
        self.assertIn("dimensions", result)
        self.assertIn("bias_detection", result)
    
    def test_think_with_level(self):
        """测试分级思考"""
        for level in range(1, 6):
            answer = self.engine.think_with_level("测试问题", level)
            self.assertIsInstance(answer, str)
            self.assertGreater(len(answer), 0)
    
    def test_upgrade_cognition(self):
        """测试认知升级"""
        initial_answer = "初步答案"
        upgraded, new_level = self.engine.upgrade_cognition(
            "问题", initial_answer, 2
        )
        
        self.assertEqual(new_level, 3)
        self.assertIsInstance(upgraded, str)
    
    def test_decide_tools(self):
        """测试工具决策"""
        decision = self.engine.decide_tools("什么是Python？")
        
        self.assertIsInstance(decision.needs_tool, bool)
        self.assertIsInstance(decision.reason, str)
    
    def test_run_basic(self):
        """测试基本运行"""
        result = self.engine.run("什么是人工智能？")
        
        self.assertIn("answer", result)
        self.assertIn("confidence", result)
        self.assertIn("cognitive_level", result)
        self.assertIn("rounds", result)
        self.assertIn("cognition_log", result)
        self.assertIn("metacognition", result)
        self.assertIn("version", result)
    
    def test_run_version(self):
        """测试版本号"""
        result = self.engine.run("测试问题")
        
        self.assertEqual(result["version"], "26.0.0-alpha.4")
    
    def test_run_cognition_log(self):
        """测试认知日志"""
        result = self.engine.run("测试问题")
        
        self.assertGreater(len(result["cognition_log"]), 0)
        
        # 应该包含基本步骤
        steps = [s["step"] for s in result["cognition_log"]]
        self.assertIn("difficulty_assessment", steps)
        self.assertIn("initial_thinking", steps)
        self.assertIn("confidence_assessment", steps)
    
    def test_run_metacognition(self):
        """测试运行后的元认知"""
        result = self.engine.run("测试问题")
        
        meta = result["metacognition"]
        self.assertIn("cognitive_effort", meta)
        self.assertGreaterEqual(meta["cognitive_effort"], 0.0)


class TestBackwardCompatibility(unittest.TestCase):
    """测试向后兼容性"""
    
    def test_v21_style_usage(self):
        """测试v2.1风格的使用"""
        engine = OxygenDynamicCognitionV26(
            mock_mode=True,
        )
        
        # v2.1的基本方法应该都可用
        result = engine.run("测试问题")
        self.assertIn("answer", result)
        self.assertIn("confidence", result)
    
    def test_advanced_alias(self):
        """测试向后兼容别名"""
        from dynamic_cognition_v26 import AdvancedCognitionEngine
        
        engine = AdvancedCognitionEngine(mock_mode=True)
        result = engine.run("测试")
        
        self.assertIn("answer", result)
    
    def test_feature_toggles(self):
        """测试功能开关"""
        engine = OxygenDynamicCognitionV26(
            mock_mode=True,
            enable_tot=False,
            enable_reflection=False,
            enable_verification=False,
            enable_self_consistency=False,
            enable_bias_detection=False,
        )
        
        # 即使关闭所有高级功能，基本推理应该正常工作
        result = engine.run("测试问题", use_advanced=False)
        self.assertIn("answer", result)
    
    def test_mock_mode(self):
        """测试Mock模式"""
        engine = OxygenDynamicCognitionV26(mock_mode=True)
        
        # 应该能正常运行
        result = engine.run("测试问题")
        self.assertIsNotNone(result["answer"])


class TestCostAnalysis(unittest.TestCase):
    """测试成本分析"""
    
    def setUp(self):
        self.engine = OxygenDynamicCognitionV26(
            mock_mode=True,
        )
    
    def test_get_cost_analysis(self):
        """测试获取成本分析"""
        # 先运行一次
        self.engine.run("测试问题")
        
        analysis = self.engine.get_cost_analysis()
        
        self.assertIn("estimated_tokens", analysis)
        self.assertIn("stage_breakdown", analysis)
        self.assertIn("cognitive_effort", analysis)


def run_tests():
    """运行所有测试"""
    print("=" * 70)
    print("OxygenDynamicCognition v26.0 Alpha 4 测试套件")
    print("GitHub@StarsailsClover")
    print("=" * 70)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestBasicComponents,
        TestThoughtGraph,
        TestTreeOfThoughts,
        TestSelfConsistency,
        TestReflection,
        TestChainOfVerification,
        TestProgressiveDeepening,
        TestMetacognitiveMonitoring,
        TestBiasDetection,
        TestMainEngine,
        TestBackwardCompatibility,
        TestCostAnalysis,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 总结
    print("\n" + "=" * 70)
    print(f"测试完成: 运行 {result.testsRun} 个测试")
    print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 70)
    
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
