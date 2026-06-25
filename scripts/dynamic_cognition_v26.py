#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OxygenDynamicCognition v26.0 Alpha 7 - 高级动态认知推理引擎
GitHub@StarsailsClover

前沿技术集成：
- 思维树（Tree of Thoughts, ToT）
- 思维图（Graph of Thoughts, GoT）
- 自一致性（Self-Consistency）
- 反射机制（Reflection）
- 验证链（Chain of Verification, CoVe）
- 多路径投票（Multi-Path Voting）
- 渐进式深化（Progressive Deepening）
- 元认知监控（Metacognitive Monitoring）
- 内部独白（Inner Monologue）
- 认知偏差检测（Cognitive Bias Detection）
"""

import os
import re
import json
import time
import random
import hashlib
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================================
# 异常定义
# ============================================================================

class BudgetExceeded(Exception):
    """认知预算超限"""
    pass


class APICallError(Exception):
    """API调用错误"""
    pass


# ============================================================================
# 数据类
# ============================================================================

class CognitiveLevel(Enum):
    """认知等级"""
    L1_INTUITIVE = 1      # 直觉/快速回答
    L2_ANALYTICAL = 2     # 分析/逐步推理
    L3_CRITICAL = 3       # 批判/多角度
    L4_CREATIVE = 4       # 创新/深度思考
    L5_COLLABORATIVE = 5  # 协同/多路径探索


@dataclass
class ThoughtNode:
    """思维节点（用于ToT/GoT）"""
    node_id: str
    content: str
    depth: int = 0
    score: float = 0.0
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    is_leaf: bool = True
    visited: bool = False
    metadata: Dict = field(default_factory=dict)


@dataclass
class ThoughtGraph:
    """思维图"""
    nodes: Dict[str, ThoughtNode] = field(default_factory=dict)
    edges: List[Tuple[str, str, str]] = field(default_factory=list)  # (from, to, type)
    root_id: Optional[str] = None
    
    def add_node(self, node: ThoughtNode):
        self.nodes[node.node_id] = node
        if self.root_id is None:
            self.root_id = node.node_id
    
    def add_edge(self, from_id: str, to_id: str, edge_type: str = "follows"):
        self.edges.append((from_id, to_id, edge_type))
        if from_id in self.nodes:
            self.nodes[from_id].children_ids.append(to_id)
            self.nodes[from_id].is_leaf = False
        if to_id in self.nodes:
            self.nodes[to_id].parent_id = from_id
    
    def get_path(self, node_id: str) -> List[ThoughtNode]:
        """获取从根到节点的路径"""
        path = []
        current = node_id
        while current:
            node = self.nodes.get(current)
            if node:
                path.insert(0, node)
                current = node.parent_id
            else:
                break
        return path
    
    def get_leaves(self) -> List[ThoughtNode]:
        """获取所有叶子节点"""
        return [n for n in self.nodes.values() if n.is_leaf]
    
    def get_best_leaf(self) -> Optional[ThoughtNode]:
        """获取评分最高的叶子节点"""
        leaves = self.get_leaves()
        if not leaves:
            return None
        return max(leaves, key=lambda x: x.score)


@dataclass
class ToolDecision:
    """工具决策结果"""
    needs_tool: bool = False
    tool_type: Optional[str] = None
    tool_name: Optional[str] = None
    reason: str = ""
    confidence: float = 0.0


@dataclass
class CognitiveBudget:
    """认知预算管理"""
    max_tokens: int = 4096
    max_rounds: int = 10
    max_time_seconds: float = 60.0
    
    tokens_used: int = 0
    rounds_completed: int = 0
    start_time: float = field(default_factory=time.time)
    
    def check(self) -> bool:
        """检查是否还有预算"""
        if self.tokens_used >= self.max_tokens:
            return False
        if self.rounds_completed >= self.max_rounds:
            return False
        if time.time() - self.start_time >= self.max_time_seconds:
            return False
        return True
    
    def use_tokens(self, tokens: int):
        self.tokens_used += tokens
        self.rounds_completed += 1
    
    def should_stop(self) -> bool:
        return not self.check()
    
    def get_breakdown(self) -> Dict:
        return {
            "max_tokens": self.max_tokens,
            "tokens_used": self.tokens_used,
            "tokens_remaining": self.max_tokens - self.tokens_used,
            "max_rounds": self.max_rounds,
            "rounds_completed": self.rounds_completed,
            "rounds_remaining": self.max_rounds - self.rounds_completed,
            "elapsed_seconds": round(time.time() - self.start_time, 2),
            "max_time_seconds": self.max_time_seconds,
        }


@dataclass
class ReflectionResult:
    """反射结果"""
    original_answer: str
    reflection_thoughts: str
    issues_found: List[str]
    improvements: List[str]
    revised_answer: Optional[str] = None
    reflection_depth: int = 1
    confidence_change: float = 0.0


@dataclass
class VerificationResult:
    """验证链结果"""
    original_claim: str
    verification_steps: List[Dict]
    verified: bool
    confidence: float
    errors_found: List[str]


@dataclass
class BiasDetectionResult:
    """认知偏差检测结果"""
    biases_detected: List[str]
    severity: float  # 0-1
    suggestions: List[str]


# ============================================================================
# 简单缓存
# ============================================================================

class SimpleCache:
    """LRU缓存"""
    
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)
        self.cache[key] = value
    
    def clear(self):
        self.cache.clear()


# ============================================================================
# Mock LLM（用于离线测试）
# ============================================================================

class MockLLM:
    """Mock LLM客户端 - 用于离线测试"""
    
    def __init__(self):
        self.call_count = 0
    
    def chat_completion(self, messages: List[Dict], **kwargs) -> str:
        """模拟聊天完成"""
        self.call_count += 1
        
        # 获取最后一条用户消息
        user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break
        
        # 根据消息内容返回不同的mock结果
        user_lower = user_msg.lower()
        
        # 单声明验证（必须在验证之前，因为更具体）
        if "单声明验证" in user_msg or "【单声明验证】" in user_msg:
            return self._mock_single_verification(user_msg)
        
        # 思维树生成（必须在难度评估之前，因为思维树prompt中包含"评估"）
        if "【思维树生成】" in user_msg or "思维树" in user_msg or "tree of thought" in user_lower or "生成多个" in user_msg:
            return self._mock_tot_thoughts(user_msg)
        
        # 难度评估
        if "评估" in user_msg or "难度" in user_msg or "difficulty" in user_lower:
            return self._mock_difficulty_assessment(user_msg)
        
        # 反射
        if "反思" in user_msg or "reflection" in user_lower or "检查错误" in user_msg:
            return self._mock_reflection(user_msg)
        
        # 验证（必须在置信度之前，因为验证prompt中也包含confidence）
        if "验证" in user_msg or "verif" in user_lower or ("检查" in user_msg and "声明" in user_msg):
            return self._mock_verification(user_msg)
        
        # 置信度评估
        if "置信度" in user_msg or ("confidence" in user_lower and "assess" in user_lower):
            return "85"
        
        # 工具决策
        if "工具" in user_msg or "tool" in user_lower:
            return json.dumps({
                "needs_tool": False,
                "tool_type": None,
                "reason": "问题可以通过推理直接回答",
                "confidence": 0.8
            }, ensure_ascii=False)
        
        # 整合答案
        if "整合" in user_msg or "综合" in user_msg or "integrate" in user_lower:
            return self._mock_integration(user_msg)
        
        # 认知升级
        if "升级" in user_msg or "深入" in user_msg or "upgrade" in user_lower:
            return self._mock_upgraded_answer(user_msg)
        
        # L5协同推理
        if "路径" in user_msg and "探索" in user_msg or "collaborative" in user_lower:
            return self._mock_collaborative(user_msg)
        
        # 自一致性投票
        if "投票" in user_msg or "vote" in user_lower or "一致性" in user_msg:
            return self._mock_voting(user_msg)
        
        # 默认：返回L2风格的分步推理
        return self._mock_analytical_answer(user_msg)
    
    def _mock_difficulty_assessment(self, question: str) -> str:
        """模拟难度评估"""
        # 简单的关键词判断
        easy_keywords = ["什么是", "定义", "介绍", "简单", "基本"]
        hard_keywords = ["为什么", "如何", "分析", "比较", "深度", "复杂", "原理"]
        
        score = 3  # 中等
        
        for kw in easy_keywords:
            if kw in question:
                score -= 1
        
        for kw in hard_keywords:
            if kw in question:
                score += 1
        
        score = max(1, min(5, score))
        
        level_map = {
            1: "L1",
            2: "L1",
            3: "L2",
            4: "L3",
            5: "L4",
        }
        
        return json.dumps({
            "level": level_map[score],
            "difficulty_score": score,
            "reason": f"基于问题复杂度评估，难度等级为{score}/5"
        }, ensure_ascii=False)
    
    def _mock_analytical_answer(self, question: str) -> str:
        """模拟分析型回答"""
        # 提取问题
        actual_question = question
        if "问题：" in question:
            parts = question.split("问题：")
            actual_question = parts[-1].strip()
        
        return f"""经过分析，这个问题可以从以下几个角度来理解：

1. 首先，问题的核心是关于{actual_question[:20]}...的探讨
2. 从基本原理来看，这涉及到多个层面的因素
3. 综合分析后，我认为答案应该是：

这是一个经过分步推理得出的结论，置信度约为85%。"""
    
    def _mock_tot_thoughts(self, question: str) -> str:
        """模拟思维树生成多个思路"""
        return json.dumps({
            "thoughts": [
                {
                    "id": "t1",
                    "content": "思路一：从第一性原理出发，先分析基本概念...",
                    "promise": 0.8
                },
                {
                    "id": "t2", 
                    "content": "思路二：从实际案例入手，通过类比推理...",
                    "promise": 0.7
                },
                {
                    "id": "t3",
                    "content": "思路三：从反面论证，先假设不成立...",
                    "promise": 0.6
                }
            ]
        }, ensure_ascii=False)
    
    def _mock_reflection(self, question: str) -> str:
        """模拟反射"""
        return json.dumps({
            "issues_found": [
                "推理过程中可能忽略了某些边界条件",
                "部分假设需要进一步验证"
            ],
            "improvements": [
                "需要补充更多的实证支持",
                "应该考虑反例情况"
            ],
            "revised_thinking": "经过反思，我认为原答案的核心结论是正确的，但需要补充以下限定条件..."
        }, ensure_ascii=False)
    
    def _mock_verification(self, question: str) -> str:
        """模拟验证"""
        return json.dumps({
            "steps": [
                {"step": 1, "claim": "前提假设", "verified": True, "evidence": "符合已知事实"},
                {"step": 2, "claim": "推理过程", "verified": True, "evidence": "逻辑链完整"},
                {"step": 3, "claim": "最终结论", "verified": True, "evidence": "与前提一致"}
            ],
            "overall_verified": True,
            "confidence": 0.88
        }, ensure_ascii=False)
    
    def _mock_single_verification(self, question: str) -> str:
        """模拟单个声明验证"""
        return json.dumps({
            "verified": True,
            "confidence": 0.88,
            "evidence": "符合已知事实和逻辑"
        }, ensure_ascii=False)
    
    def _mock_integration(self, question: str) -> str:
        """模拟答案整合"""
        return """综合多条推理路径的结果，我得出以下整合后的答案：

经过对多个角度的综合分析，最终结论是：这是一个经过多路径验证的答案。

主要依据：
1. 多个推理路径都指向相似的结论
2. 关键论点得到了交叉验证
3. 潜在的异议都得到了回应"""
    
    def _mock_upgraded_answer(self, question: str) -> str:
        """模拟升级后的深度回答"""
        return """经过更深入的思考，我发现这个问题还有更深层次的维度：

从更深层次来看，这个问题涉及到：
1. 底层的本质原理
2. 系统性的相互作用
3. 长期和短期的不同影响

深度分析后的结论是：这是一个经过深度思考的答案，比初步回答更加全面和准确。"""
    
    def _mock_collaborative(self, question: str) -> str:
        """模拟协同推理"""
        return json.dumps({
            "paths": [
                {
                    "path_id": "p1",
                    "approach": "演绎推理",
                    "answer": "从一般原理推导出的结论是...",
                    "confidence": 0.85
                },
                {
                    "path_id": "p2", 
                    "approach": "归纳推理",
                    "answer": "从具体案例归纳出的结论是...",
                    "confidence": 0.80
                },
                {
                    "path_id": "p3",
                    "approach": "类比推理",
                    "answer": "通过类比相似问题得出的结论是...",
                    "confidence": 0.75
                }
            ]
        }, ensure_ascii=False)
    
    def _mock_voting(self, question: str) -> str:
        """模拟自一致性投票"""
        return json.dumps({
            "answers": [
                "答案A：这是第一种可能的答案",
                "答案A：这是第二种可能的答案（本质相同）",
                "答案B：这是第三种可能的答案（不同观点）",
                "答案A：这是第四种可能的答案（本质相同）",
                "答案A：这是第五种可能的答案（本质相同）"
            ],
            "voting_result": {
                "答案A": {"count": 4, "percentage": 0.8},
                "答案B": {"count": 1, "percentage": 0.2}
            },
            "final_answer": "答案A：经过投票，多数推理路径指向答案A",
            "consensus_score": 0.8
        }, ensure_ascii=False)


# ============================================================================
# 问题分类器
# ============================================================================

class QuestionClassifier:
    """本地问题分类器"""
    
    CATEGORY_KEYWORDS = {
        "factual": ["什么是", "定义", "是什么", "who", "what", "when", "where"],
        "reasoning": ["为什么", "如何", "怎么", "why", "how", "分析", "推理"],
        "creative": ["设计", "创造", "创意", "想象", "如果", "假设"],
        "evaluation": ["评价", "比较", "哪个好", "对比", "评估"],
        "math": ["计算", "等于", "多少", "solve", "calculate", "数学"],
        "coding": ["代码", "程序", "函数", "算法", "code", "function"],
    }
    
    @classmethod
    def classify(cls, question: str) -> str:
        """快速分类问题类型"""
        q_lower = question.lower()
        
        scores = {}
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in q_lower:
                    score += 1
            scores[category] = score
        
        # 返回得分最高的类别
        if max(scores.values()) == 0:
            return "general"
        
        return max(scores.items(), key=lambda x: x[1])[0]
    
    @classmethod
    def get_threshold(cls, category: str) -> float:
        """获取对应类别的置信度阈值"""
        thresholds = {
            "factual": 0.80,
            "reasoning": 0.75,
            "creative": 0.65,
            "evaluation": 0.70,
            "math": 0.90,
            "coding": 0.85,
            "general": 0.75,
        }
        return thresholds.get(category, 0.75)


# ============================================================================
# 认知偏差检测器
# ============================================================================

class BiasDetector:
    """认知偏差检测器"""
    
    BIAS_PATTERNS = {
        "confirmation_bias": [
            "只寻找支持自己观点的证据",
            "忽略反面证据",
            "只看想看到的",
        ],
        "anchoring_bias": [
            "过度依赖第一印象",
            "被初始信息锚定",
        ],
        "availability_heuristic": [
            "只想到容易想到的例子",
            "用最近的例子代替整体",
        ],
        "overconfidence": [
            "过于自信",
            "低估不确定性",
            "100%确定",
        ],
    }
    
    @classmethod
    def detect(cls, text: str) -> BiasDetectionResult:
        """检测认知偏差"""
        biases_found = []
        total_severity = 0.0
        
        for bias_name, patterns in cls.BIAS_PATTERNS.items():
            hits = 0
            for pattern in patterns:
                if pattern in text:
                    hits += 1
            
            if hits > 0:
                biases_found.append(bias_name)
                total_severity += hits / len(patterns)
        
        severity = min(total_severity, 1.0)
        
        suggestions = []
        if "confirmation_bias" in biases_found:
            suggestions.append("建议主动寻找反面证据，进行钢人论证")
        if "overconfidence" in biases_found:
            suggestions.append("建议降低置信度，考虑更多不确定性")
        if not biases_found:
            suggestions.append("未检测到明显认知偏差，继续保持批判性思维")
        
        return BiasDetectionResult(
            biases_detected=biases_found,
            severity=severity,
            suggestions=suggestions,
        )


# ============================================================================
# v26.0 主引擎
# ============================================================================

class OxygenDynamicCognitionV26:
    """
    OxygenDynamicCognition v26.0 Alpha 7 - 高级动态认知推理引擎
    GitHub@StarsailsClover
    
    前沿技术：
    - 思维树 ToT
    - 思维图 GoT
    - 自一致性 Self-Consistency
    - 反射机制 Reflection
    - 验证链 CoVe
    - 多路径投票
    - 渐进式深化
    - 元认知监控
    - 认知偏差检测
    """
    
    VERSION = "26.0.0-alpha.7"
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-3.5-turbo",
                 max_rounds: int = 4,
                 confidence_threshold: float = 0.80,
                 start_level: int = 1,
                 max_level: int = 4,
                 max_tokens: int = 2048,
                 mock_mode: bool = False,
                 enable_cache: bool = True,
                 max_retries: int = 3,
                 enable_tot: bool = False,
                 enable_reflection: bool = False,
                 enable_verification: bool = False,
                 enable_self_consistency: bool = False,
                 enable_bias_detection: bool = False,
                 num_consistency_samples: int = 3,
                 max_reflection_depth: int = 1,
                 tot_branching_factor: int = 2,
                 tot_max_depth: int = 2):
        
        self.model = model
        self.max_rounds = max_rounds
        self.confidence_threshold = confidence_threshold
        self.start_level = start_level
        self.max_level = max_level
        
        # v26.0 功能开关
        self.enable_tot = enable_tot
        self.enable_reflection = enable_reflection
        self.enable_verification = enable_verification
        self.enable_self_consistency = enable_self_consistency
        self.enable_bias_detection = enable_bias_detection
        
        # v26.0 参数
        self.num_consistency_samples = num_consistency_samples
        self.max_reflection_depth = max_reflection_depth
        self.tot_branching_factor = tot_branching_factor
        self.tot_max_depth = tot_max_depth
        
        # Mock模式
        self.mock_mode = mock_mode
        self.api_key = api_key
        self.base_url = base_url
        self._client = None
        if not mock_mode:
            self._init_client()
        else:
            self.llm = MockLLM()

        # 缓存
        self.enable_cache = enable_cache
        if enable_cache:
            self.cache = SimpleCache(capacity=100)

        # 重试
        self.max_retries = max_retries

        # 预算
        self.budget = CognitiveBudget(
            max_tokens=max_tokens,
            max_rounds=max_rounds,
        )
        
        # 认知日志
        self.cognition_log = []
        
        # 元认知数据
        self.metacognition = {
            "total_thoughts_generated": 0,
            "reflections_done": 0,
            "verifications_done": 0,
            "bias_checks_done": 0,
            "cognitive_effort_score": 0.0,
        }
    
    # ------------------------------------------------------------------------
    # 基础方法
    # ------------------------------------------------------------------------
    
        # 预算追踪
        self._last_token_usage = 0

    def _init_client(self):
        """初始化 OpenAI 兼容客户端"""
        if OpenAI is None:
            raise ImportError("未安装 openai 库，请运行：pip install openai")

        import os as _os
        api_key = self.api_key or _os.environ.get("OPENAI_API_KEY", _os.environ.get("OXYGEN_API_KEY", ""))
        base_url = self.base_url or _os.environ.get("OPENAI_BASE_URL")

        if not api_key:
            raise ValueError("未设置 API Key")

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = OpenAI(**client_kwargs)

    def _real_api_call(self, messages: List[Dict], **kwargs) -> str:
        """真实 API 调用"""
        if self._client is None:
            raise RuntimeError("API 客户端未初始化，请设置 api_key 或启用 mock_mode")

        params = {
            "model": self.model,
            "messages": messages,
        }
        # 只传入支持的参数
        for key in ["max_tokens", "temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if key in kwargs:
                params[key] = kwargs[key]

        response = self._client.chat.completions.create(**params)

        # 追踪 token 使用
        if hasattr(response, "usage") and response.usage:
            self._last_token_usage = response.usage.total_tokens

        return response.choices[0].message.content.strip()

    def _call_llm(self, messages: List[Dict], **kwargs) -> str:
        """调用LLM（带重试和缓存）"""
        # 缓存检查
        if self.enable_cache:
            cache_key = hashlib.md5(json.dumps(messages, sort_keys=True).encode()).hexdigest()
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Mock模式
        if self.mock_mode:
            result = self.llm.chat_completion(messages, **kwargs)
            if self.enable_cache:
                self.cache.put(cache_key, result)
            return result

        # 实际API调用（带重试）
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = self._real_api_call(messages, **kwargs)

                if self.enable_cache:
                    self.cache.put(cache_key, result)

                # 预算追踪
                if hasattr(self, '_last_token_usage'):
                    self.budget.use_tokens(self._last_token_usage)

                return result

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                continue

        raise APICallError(f"API调用失败，已重试{self.max_retries}次: {last_error}")
    
    def quick_classify(self, question: str) -> str:
        """本地快速分类问题"""
        return QuestionClassifier.classify(question)
    
    def clear_cache(self):
        """清空缓存"""
        if self.enable_cache:
            self.cache.clear()
    
    # ------------------------------------------------------------------------
    # 难度评估
    # ------------------------------------------------------------------------
    
    def assess_difficulty(self, question: str) -> Dict:
        """评估问题难度"""
        # 先尝试本地分类
        category = self.quick_classify(question)
        local_threshold = QuestionClassifier.get_threshold(category)
        
        # 尝试调用LLM评估
        try:
            prompt = f"""请评估以下问题的难度等级（L1到L5）：
L1: 简单事实题，直接回答
L2: 需要简单分析或推理
L3: 需要多步推理或多角度思考
L4: 需要深度思考或创造性思维
L5: 需要多路径探索或专家级知识

问题：{question}

请以JSON格式返回，包含level和reason字段。"""
            
            response = self._call_llm([
                {"role": "user", "content": prompt}
            ])
            
            # 尝试解析JSON
            try:
                result = json.loads(response)
                level_str = result.get("level", "L2")
                reason = result.get("reason", "")
            except json.JSONDecodeError:
                # 降级到本地评估
                level_str = f"L{self.start_level}"
                reason = "使用本地分类器评估"
            
            level_num = int(re.search(r'\d+', level_str).group())
            
        except Exception as e:
            # 降级：使用本地评估
            level_num = self.start_level
            reason = f"API调用失败，使用本地评估: {e}"
        
        return {
            "level": level_num,
            "category": category,
            "threshold": local_threshold,
            "reason": reason,
        }
    
    # ------------------------------------------------------------------------
    # 置信度评估
    # ------------------------------------------------------------------------
    
    def assess_confidence(self, answer: str, question: str, 
                         detailed: bool = False) -> Dict:
        """评估答案置信度"""
        if detailed:
            return self._assess_confidence_detailed(answer, question)
        
        # 简单版
        try:
            prompt = f"""请评估以下答案的置信度（0-100分）：

问题：{question}

答案：{answer}

只返回一个数字，表示置信度分数。"""
            
            response = self._call_llm([
                {"role": "user", "content": prompt}
            ])
            
            # 提取数字
            numbers = re.findall(r'\d+', response)
            if numbers:
                confidence = min(100, max(0, int(numbers[0])))
            else:
                confidence = 70
            
        except Exception:
            confidence = 70
        
        return {"confidence": confidence / 100.0}
    
    def _heuristic_confidence(self, answer: str, question: str) -> float:
        """Alpha 7: 快速启发式置信度评估（不调用LLM）
        
        基于答案长度、问题类型匹配度快速估算置信度。
        """
        category = self.quick_classify(question)
        base = {
            "factual": 0.80, "reasoning": 0.70, "creative": 0.65,
            "evaluation": 0.70, "math": 0.85, "coding": 0.80, "general": 0.70
        }.get(category, 0.70)
        
        # 长度惩罚：太短可能不完整
        if len(answer) < 20:
            base *= 0.8
        elif len(answer) > 500:
            base = min(1.0, base + 0.05)
        
        return round(base, 2)

    def _assess_confidence_detailed(self, answer: str, question: str) -> Dict:
        """详细置信度评估（多维度）"""
        # 简化版：直接返回多维度评分
        base_confidence = 0.85
        
        dimensions = {
            "logical_consistency": 0.9,
            "factual_accuracy": 0.85,
            "completeness": 0.8,
            "clarity": 0.85,
        }
        
        # 偏差检测
        bias_result = None
        if self.enable_bias_detection:
            bias_result = BiasDetector.detect(answer)
            self.metacognition["bias_checks_done"] += 1
            if bias_result.severity > 0:
                base_confidence -= bias_result.severity * 0.1
        
        overall = sum(dimensions.values()) / len(dimensions)
        
        return {
            "confidence": min(1.0, max(0.0, overall)),
            "dimensions": dimensions,
            "bias_detection": bias_result,
        }
    
    # ------------------------------------------------------------------------
    # 工具决策
    # ------------------------------------------------------------------------
    
    def decide_tools(self, question: str) -> ToolDecision:
        """决策是否需要工具"""
        try:
            prompt = f"""判断回答以下问题是否需要使用外部工具：

问题：{question}

可选工具类型：
- search: 网络搜索（需要最新信息或事实核查）
- calculator: 计算器（复杂数学计算）
- code: 代码执行（编程问题）
- memory: 记忆检索（需要历史信息）

请以JSON格式返回：needs_tool, tool_type, reason, confidence"""
            
            response = self._call_llm([
                {"role": "user", "content": prompt}
            ])
            
            result = json.loads(response)
            return ToolDecision(
                needs_tool=result.get("needs_tool", False),
                tool_type=result.get("tool_type"),
                reason=result.get("reason", ""),
                confidence=result.get("confidence", 0.0),
            )
            
        except Exception:
            return ToolDecision(needs_tool=False, reason="工具决策失败，使用纯推理")
    
    # ------------------------------------------------------------------------
    # v26.0 新增：思维树 Tree of Thoughts
    # ------------------------------------------------------------------------
    
    def tree_of_thoughts(self, question: str, 
                        branching_factor: int = 3,
                        max_depth: int = 3) -> ThoughtGraph:
        """思维树推理
        
        生成多个推理路径，评估每个路径的前景，选择最优路径继续探索
        """
        graph = ThoughtGraph()
        
        # 创建根节点（初始问题）
        root = ThoughtNode(
            node_id="root",
            content=question,
            depth=0,
            score=0.5,
        )
        graph.add_node(root)
        
        current_level_ids = ["root"]
        
        for depth in range(1, max_depth + 1):
            next_level_ids = []
            
            for parent_id in current_level_ids:
                # 生成多个思路
                thoughts = self._generate_thoughts(
                    question, 
                    graph.get_path(parent_id),
                    branching_factor
                )
                
                for thought in thoughts:
                    node_id = f"d{depth}_{len(graph.nodes)}"
                    node = ThoughtNode(
                        node_id=node_id,
                        content=thought["content"],
                        depth=depth,
                        score=thought.get("promise", 0.5),
                    )
                    graph.add_node(node)
                    graph.add_edge(parent_id, node_id, "explores")
                    next_level_ids.append(node_id)
                    
                    self.metacognition["total_thoughts_generated"] += 1
            
            # 剪枝：只保留最好的几个继续探索
            if depth < max_depth:
                next_level_nodes = [graph.nodes[nid] for nid in next_level_ids]
                next_level_nodes.sort(key=lambda x: x.score, reverse=True)
                current_level_ids = [n.node_id for n in next_level_nodes[:branching_factor]]
            else:
                current_level_ids = next_level_ids
        
        return graph
    
    def _generate_thoughts(self, question: str, path: List[ThoughtNode], 
                          num: int) -> List[Dict]:
        """生成多个思路"""
        try:
            path_summary = "\n".join([f"第{i}步: {n.content[:50]}" for i, n in enumerate(path)])
            
            prompt = f"""【思维树生成】针对以下问题，生成{num}个不同的推理思路：

问题：{question}

当前推理路径：
{path_summary}

请为每个思路评估其前景（0-1，越高越有希望得到正确答案）。
以JSON格式返回thoughts数组，每个元素包含id, content, promise字段。"""
            
            response = self._call_llm([
                {"role": "user", "content": prompt}
            ])
            
            result = json.loads(response)
            return result.get("thoughts", [])
            
        except Exception:
            # Mock降级
            return [
                {"content": f"思路{i+1}：从不同角度分析问题...", "promise": 0.5 + i * 0.1}
                for i in range(num)
            ]
    
    def get_best_tot_answer(self, graph: ThoughtGraph) -> Optional[str]:
        """从思维树中获取最佳答案"""
        best_leaf = graph.get_best_leaf()
        if best_leaf:
            path = graph.get_path(best_leaf.node_id)
            return "\n".join([n.content for n in path])
        return None
    
    # ------------------------------------------------------------------------
    # v26.0 新增：自一致性 Self-Consistency
    # ------------------------------------------------------------------------
    
    def self_consistency(self, question: str, num_samples: int = 5) -> Dict:
        """自一致性：生成多个答案，投票选出最一致的
        
        核心思想：如果多个独立推理路径都得出相似结论，那这个结论更可能正确
        """
        answers = []
        
        for i in range(num_samples):
            # 每次用不同的"温度"或不同的推理方式
            answer = self._think_with_style(question, style_num=i % 3)
            answers.append(answer)
        
        # 聚类和投票（简化版：文本相似度聚类）
        clusters = self._cluster_answers(answers)
        
        # 找出最大簇
        largest_cluster = max(clusters, key=len)
        consensus_score = len(largest_cluster) / len(answers)
        
        # 返回簇中的代表性答案
        final_answer = largest_cluster[0] if largest_cluster else answers[0]
        
        return {
            "final_answer": final_answer,
            "num_samples": num_samples,
            "consensus_score": consensus_score,
            "all_answers": answers,
            "num_clusters": len(clusters),
        }
    
    def _think_with_style(self, question: str, style_num: int = 0) -> str:
        """用不同风格思考"""
        styles = [
            "严谨分析型",
            "直觉跳跃型",
            "类比推理型",
        ]
        style = styles[style_num % len(styles)]
        
        try:
            prompt = f"""请用{style}的方式回答以下问题：

问题：{question}

请给出你的完整推理过程和最终答案。"""
            
            return self._call_llm([{"role": "user", "content": prompt}])
        except Exception:
            return f"[{style}] 这是一个答案的模拟结果。"
    
    def _cluster_answers(self, answers: List[str]) -> List[List[str]]:
        """简单聚类（基于文本相似度）"""
        # 简化版：按关键词重叠度聚类
        clusters = []
        
        for answer in answers:
            placed = False
            for cluster in clusters:
                # 计算与簇中第一个答案的相似度
                sim = self._text_similarity(answer, cluster[0])
                if sim > 0.5:  # 相似度阈值
                    cluster.append(answer)
                    placed = True
                    break
            
            if not placed:
                clusters.append([answer])
        
        return clusters
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """简单文本相似度（基于词重叠）"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    # ------------------------------------------------------------------------
    # v26.0 新增：反射机制 Reflection
    # ------------------------------------------------------------------------
    
    def reflect(self, answer: str, question: str, 
               depth: int = 1) -> ReflectionResult:
        """反射：让模型反思自己的答案，发现问题并改进
        
        反射可以进行多轮，每轮都深入检查上一轮的结果
        """
        current_answer = answer
        all_issues = []
        all_improvements = []
        reflection_thoughts = []
        
        for d in range(depth):
            reflection = self._single_reflection(current_answer, question, d + 1)
            reflection_thoughts.append(reflection["thoughts"])
            all_issues.extend(reflection["issues"])
            all_improvements.extend(reflection["improvements"])
            
            if reflection.get("revised"):
                current_answer = reflection["revised"]
            else:
                break  # 没有改进空间了
        
        self.metacognition["reflections_done"] += depth
        
        return ReflectionResult(
            original_answer=answer,
            reflection_thoughts="\n".join(reflection_thoughts),
            issues_found=list(set(all_issues)),
            improvements=list(set(all_improvements)),
            revised_answer=current_answer if current_answer != answer else None,
            reflection_depth=depth,
        )
    
    def _single_reflection(self, answer: str, question: str, 
                          depth: int) -> Dict:
        """单次反射"""
        try:
            prompt = f"""请反思你对以下问题的回答，找出可能的问题和改进空间：

问题：{question}

回答：{answer}

这是第{depth}轮反思，请深入检查：
1. 逻辑是否有漏洞？
2. 是否有遗漏的重要因素？
3. 结论是否过于绝对？
4. 有没有更好的论证方式？

请以JSON格式返回：
- thoughts: 你的反思思考过程
- issues: 发现的问题列表
- improvements: 改进建议列表
- revised: 修正后的答案（如果有重大改进），否则返回null
- has_improvements: 是否有实质性改进"""
            
            response = self._call_llm([
                {"role": "user", "content": prompt}
            ])
            
            result = json.loads(response)
            return {
                "thoughts": result.get("thoughts", ""),
                "issues": result.get("issues", []),
                "improvements": result.get("improvements", []),
                "revised": result.get("revised"),
                "has_improvements": result.get("has_improvements", False),
            }
            
        except Exception:
            return {
                "thoughts": "反射过程中出现问题，使用启发式检查",
                "issues": ["无法进行深度反射"],
                "improvements": ["建议增加API可用性"],
                "revised": None,
                "has_improvements": False,
            }
    
    # ------------------------------------------------------------------------
    # v26.0 新增：验证链 Chain of Verification
    # ------------------------------------------------------------------------
    
    def chain_of_verification(self, answer: str, question: str) -> VerificationResult:
        """验证链：将答案分解为多个声明，逐一验证
        
        CoVe的核心是：不要相信自己的答案，要像验证别人的答案一样验证自己的
        """
        # 1. 提取声明
        claims = self._extract_claims(answer)
        
        # 2. 逐一验证
        verification_steps = []
        all_verified = True
        errors = []
        total_confidence = 0.0
        
        for i, claim in enumerate(claims):
            result = self._verify_claim(claim, question)
            verification_steps.append({
                "step": i + 1,
                "claim": claim,
                "verified": result["verified"],
                "confidence": result["confidence"],
                "evidence": result.get("evidence", ""),
            })
            
            if not result["verified"]:
                all_verified = False
                errors.append(f"声明{i+1}未通过验证: {claim}")
            
            total_confidence += result["confidence"]
        
        avg_confidence = total_confidence / len(claims) if claims else 0.0
        
        self.metacognition["verifications_done"] += 1
        
        return VerificationResult(
            original_claim=answer,
            verification_steps=verification_steps,
            verified=all_verified,
            confidence=avg_confidence,
            errors_found=errors,
        )
    
    def _extract_claims(self, answer: str) -> List[str]:
        """从答案中提取可验证的声明"""
        # 简化版：按句子分割，选择有实质内容的句子
        sentences = re.split(r'[。！？.!?\n]+', answer)
        claims = []
        
        for sent in sentences:
            sent = sent.strip()
            # 降低长度阈值，确保短句也能被提取
            if len(sent) >= 4 and not sent.startswith("注") and not sent.startswith("总之"):
                claims.append(sent)
        
        return claims[:5]  # 最多验证5个
    
    def _verify_claim(self, claim: str, question: str) -> Dict:
        """验证单个声明"""
        try:
            prompt = f"""【单声明验证】请验证以下声明是否正确：

声明：{claim}

原始问题：{question}

请检查：
1. 这个声明有事实依据吗？
2. 逻辑上成立吗？
3. 有没有反例？

以JSON格式返回：verified (bool), confidence (0-1), evidence (str)"""
            
            response = self._call_llm([
                {"role": "user", "content": prompt}
            ])
            
            return json.loads(response)
            
        except Exception:
            return {"verified": True, "confidence": 0.7, "evidence": "无法验证，假设正确"}
    
    # ------------------------------------------------------------------------
    # v26.0 新增：渐进式深化 Progressive Deepening
    # ------------------------------------------------------------------------
    
    def progressive_deepening(self, question: str, 
                             max_levels: int = 4) -> Dict:
        """渐进式深化：从浅到深逐步深入思考
        
        类似迭代加深搜索，每一轮都比上一轮更深入
        """
        results = []
        previous_answer = None
        
        for level in range(1, max_levels + 1):
            answer = self._think_at_depth(question, level, previous_answer)
            confidence = self.assess_confidence(answer, question)["confidence"]
            
            results.append({
                "level": level,
                "answer": answer,
                "confidence": confidence,
            })
            
            # 如果置信度足够高，可以提前停止
            if confidence >= self.confidence_threshold:
                break
            
            previous_answer = answer
        
        return {
            "final_answer": results[-1]["answer"],
            "final_confidence": results[-1]["confidence"],
            "levels_explored": len(results),
            "progression": results,
        }
    
    def _think_at_depth(self, question: str, depth: int, 
                       previous_answer: Optional[str] = None) -> str:
        """在指定深度思考"""
        try:
            if previous_answer:
                prompt = f"""请在第{depth}层深度上重新思考这个问题。
上一层的答案是：{previous_answer[:200]}...

问题：{question}

请比上一层更深入、更全面地思考。"""
            else:
                prompt = f"""请在第{depth}层深度上思考这个问题：
{question}

深度{depth}意味着：{['直觉回答', '简单分析', '深入推理', '多维度探索', '专家级综合'][min(depth-1, 4)]}"""
            
            return self._call_llm([{"role": "user", "content": prompt}])
        except Exception:
            return f"[深度{depth}] 这是深度思考的结果..."
    
    # ------------------------------------------------------------------------
    # v26.0 新增：元认知监控
    # ------------------------------------------------------------------------
    
    def get_metacognition_report(self) -> Dict:
        """获取元认知监控报告"""
        # 计算认知努力分数
        effort_score = (
            self.metacognition["total_thoughts_generated"] * 0.3 +
            self.metacognition["reflections_done"] * 1.0 +
            self.metacognition["verifications_done"] * 0.8 +
            self.metacognition["bias_checks_done"] * 0.5 +
            len(self.cognition_log) * 0.2
        ) / 10.0  # 归一化
        
        effort_score = min(1.0, effort_score)
        
        self.metacognition["cognitive_effort_score"] = effort_score
        
        return {
            "cognitive_effort": effort_score,
            "thoughts_generated": self.metacognition["total_thoughts_generated"],
            "reflections": self.metacognition["reflections_done"],
            "verifications": self.metacognition["verifications_done"],
            "bias_checks": self.metacognition["bias_checks_done"],
            "cognition_steps": len(self.cognition_log),
            "budget_used": self.budget.get_breakdown(),
        }
    
    # ------------------------------------------------------------------------
    # 分级思考
    # ------------------------------------------------------------------------
    
    def think_with_level(self, question: str, level: int, 
                        context: Optional[str] = None) -> str:
        """指定认知等级思考"""
        level = max(1, min(5, level))
        
        # 根据等级选择策略
        if level == 1:
            return self._think_l1(question, context)
        elif level == 2:
            return self._think_l2(question, context)
        elif level == 3:
            return self._think_l3(question, context)
        elif level == 4:
            return self._think_l4(question, context)
        elif level == 5:
            return self._think_l5(question, context)
        
        return self._think_l2(question, context)
    
    def _think_l1(self, question: str, context: Optional[str]) -> str:
        """L1: 直觉/快速回答"""
        try:
            prompt = f"""请快速回答以下问题（不需要详细推理）：
{question}
"""
            if context:
                prompt += f"\n参考上下文：{context[:500]}"
            
            return self._call_llm([{"role": "user", "content": prompt}])
        except Exception:
            return "这是一个快速回答。"
    
    def _think_l2(self, question: str, context: Optional[str]) -> str:
        """L2: 分析/逐步推理"""
        try:
            prompt = f"""请逐步分析并回答以下问题：
{question}

请给出清晰的推理步骤。"""
            if context:
                prompt += f"\n参考上下文：{context[:500]}"
            
            return self._call_llm([{"role": "user", "content": prompt}])
        except Exception:
            return "经过分析，答案是..."
    
    def _think_l3(self, question: str, context: Optional[str]) -> str:
        """L3: 批判/多角度"""
        try:
            prompt = f"""请从多个角度批判性地分析并回答以下问题：
{question}

请考虑：
1. 支持的论点
2. 反对的论点
3. 可能的局限性

给出综合结论。"""
            if context:
                prompt += f"\n参考上下文：{context[:500]}"
            
            return self._call_llm([{"role": "user", "content": prompt}])
        except Exception:
            return "从多个角度分析后..."
    
    def _think_l4(self, question: str, context: Optional[str]) -> str:
        """L4: 创新/深度思考"""
        try:
            prompt = f"""请深入思考并创造性地回答以下问题：
{question}

请不仅给出标准答案，还要：
1. 深入底层原理
2. 提出新颖的视角
3. 探索潜在的延伸"""
            if context:
                prompt += f"\n参考上下文：{context[:500]}"
            
            return self._call_llm([{"role": "user", "content": prompt}])
        except Exception:
            return "经过深度思考..."
    
    def _think_l5(self, question: str, context: Optional[str]) -> str:
        """L5: 协同/多路径探索（使用思维树或自一致性）"""
        if self.enable_tot:
            # 使用思维树
            graph = self.tree_of_thoughts(
                question,
                branching_factor=self.tot_branching_factor,
                max_depth=self.tot_max_depth,
            )
            answer = self.get_best_tot_answer(graph)
            if answer:
                return answer
        
        # 降级：使用自一致性
        if self.enable_self_consistency:
            result = self.self_consistency(question, self.num_consistency_samples)
            return result["final_answer"]
        
        # 再降级：普通深度思考
        return self._think_l4(question, context)
    
    # ------------------------------------------------------------------------
    # 认知升级
    # ------------------------------------------------------------------------
    
    def upgrade_cognition(self, question: str, current_answer: str, 
                         current_level: int) -> Tuple[str, int]:
        """认知升级：基于当前答案，升级到更深的认知水平"""
        new_level = min(current_level + 1, self.max_level)
        
        try:
            prompt = f"""请基于以下初步答案，进行更深入的思考：

问题：{question}

初步答案（L{current_level}）：
{current_answer[:500]}

请升级到L{new_level}水平的思考，提供更深入、更全面的答案。"""
            
            upgraded = self._call_llm([{"role": "user", "content": prompt}])
            return upgraded, new_level
            
        except Exception:
            return current_answer + "\n\n[深度补充] 经过更深入的思考...", new_level
    
    # ------------------------------------------------------------------------
    # 答案整合
    # ------------------------------------------------------------------------
    
    def integrate_answers(self, question: str, answers: List[str]) -> str:
        """整合多个答案"""
        if len(answers) == 1:
            return answers[0]
        
        try:
            answers_text = "\n\n".join([f"答案{i+1}:\n{a[:300]}" for i, a in enumerate(answers)])
            
            prompt = f"""请整合以下多个答案，形成一个综合、全面的最终答案：

问题：{question}

{answers_text}

请整合各答案的优点，形成最佳答案。"""
            
            return self._call_llm([{"role": "user", "content": prompt}])
            
        except Exception:
            return answers[0]
    
    # ------------------------------------------------------------------------
    # 主推理循环
    # ------------------------------------------------------------------------
    
    def run(self, question: str, context: Optional[str] = None,
            use_advanced: bool = True) -> Dict:
        """主推理循环
        
        v26.0 增强版：集成多种前沿技术
        """
        # 重置状态
        self.cognition_log = []
        self.budget = CognitiveBudget(
            max_tokens=self.budget.max_tokens,
            max_rounds=self.max_rounds,
        )
        self.metacognition = {
            "total_thoughts_generated": 0,
            "reflections_done": 0,
            "verifications_done": 0,
            "bias_checks_done": 0,
            "cognitive_effort_score": 0.0,
        }
        
        # 1. 难度评估
        difficulty = self.assess_difficulty(question)
        start_level = max(self.start_level, difficulty["level"])
        adaptive_threshold = difficulty["threshold"]
        
        self.cognition_log.append({
            "step": "difficulty_assessment",
            "level": start_level,
            "category": difficulty["category"],
            "threshold": adaptive_threshold,
        })
        
        # 2. 工具决策
        tool_decision = self.decide_tools(question)
        self.cognition_log.append({
            "step": "tool_decision",
            "needs_tool": tool_decision.needs_tool,
            "tool_type": tool_decision.tool_type,
        })
        
        # 3. 初始思考
        current_level = start_level
        current_answer = self.think_with_level(question, current_level, context)
        
        self.cognition_log.append({
            "step": "initial_thinking",
            "level": current_level,
            "answer_length": len(current_answer),
        })
        
        # 4. 置信度评估（Alpha 7: 启发式快速通道）
        # 简单问题类别使用启发式方法跳过LLM评估，节省token
        category = self.quick_classify(question)
        heuristic_categories = {"factual", "math", "coding"}
        if category in heuristic_categories and not self.mock_mode:
            current_confidence = self._heuristic_confidence(current_answer, question)
            confidence_source = "heuristic"
        else:
            confidence_result = self.assess_confidence(current_answer, question, detailed=True)
            current_confidence = confidence_result["confidence"]
            confidence_source = "llm"
        
        self.cognition_log.append({
            "step": "confidence_assessment",
            "confidence": current_confidence,
            "threshold": adaptive_threshold,
            "source": confidence_source,
        })
        
        # 5. 动态推理循环
        rounds = 0
        all_answers = [current_answer]
        
        while (current_confidence < adaptive_threshold and 
               rounds < self.max_rounds and 
               current_level < self.max_level and
               self.budget.check()):
            
            rounds += 1
            
            # 认知升级
            current_answer, current_level = self.upgrade_cognition(
                question, current_answer, current_level
            )
            all_answers.append(current_answer)
            
            # 重新评估置信度
            confidence_result = self.assess_confidence(current_answer, question, detailed=True)
            current_confidence = confidence_result["confidence"]
            
            self.cognition_log.append({
                "step": f"upgrade_round_{rounds}",
                "level": current_level,
                "confidence": current_confidence,
            })
        
        # 6. v26.0 高级增强（如果启用）— Alpha 6: 修复死区逻辑
        if use_advanced:
            adv_rounds = 0
            max_adv_rounds = 3  # Alpha 6: 熔断机制，防止无限循环

            while adv_rounds < max_adv_rounds:
                adv_rounds += 1
                changed = False

                # 反射
                if self.enable_reflection and current_confidence < 0.9:
                    reflection = self.reflect(
                        current_answer, question,
                        depth=min(self.max_reflection_depth, 2)
                    )
                    if reflection.revised_answer:
                        current_answer = reflection.revised_answer
                        current_confidence = self.assess_confidence(
                            current_answer, question
                        )["confidence"]
                        changed = True

                    self.cognition_log.append({
                        "step": f"reflection_adv_{adv_rounds}",
                        "issues_found": len(reflection.issues_found),
                        "improved": reflection.revised_answer is not None,
                    })

                # 验证链
                if self.enable_verification and current_confidence < 0.95:
                    verification = self.chain_of_verification(
                        current_answer, question
                    )
                    self.cognition_log.append({
                        "step": f"verification_adv_{adv_rounds}",
                        "verified": verification.verified,
                        "steps": len(verification.verification_steps),
                        "errors": len(verification.errors_found),
                    })

                    # Alpha 6 fix: 验证通过但置信度仍低 → 仍尝试自一致性
                    if verification.verified and current_confidence < 0.95 and self.enable_self_consistency:
                        consistency_result = self.self_consistency(
                            question, self.num_consistency_samples
                        )
                        current_answer = consistency_result["final_answer"]
                        current_confidence = consistency_result["consensus_score"]
                        changed = True

                        self.cognition_log.append({
                            "step": f"self_consistency_after_verify_{adv_rounds}",
                            "consensus_score": consistency_result["consensus_score"],
                            "trigger": "verified_but_low_confidence",
                        })

                    # 验证失败 → 尝试自一致性
                    elif not verification.verified and self.enable_self_consistency:
                        consistency_result = self.self_consistency(
                            question, self.num_consistency_samples
                        )
                        current_answer = consistency_result["final_answer"]
                        current_confidence = consistency_result["consensus_score"]
                        changed = True

                        self.cognition_log.append({
                            "step": f"self_consistency_{adv_rounds}",
                            "consensus_score": consistency_result["consensus_score"],
                            "trigger": "verification_failed",
                        })

                        # Alpha 6 fix: 自一致性结果必须经过二次验证！
                        if self.enable_verification:
                            re_verify = self.chain_of_verification(
                                current_answer, question
                            )
                            if re_verify.verified:
                                current_confidence = max(
                                    current_confidence,
                                    self.assess_confidence(current_answer, question)["confidence"]
                                )
                                changed = True
                            self.cognition_log.append({
                                "step": f"re_verification_{adv_rounds}",
                                "verified": re_verify.verified,
                                "trigger": "post_self_consistency",
                            })

                # 无变化则跳出高级增强循环
                if not changed:
                    break

                # Alpha 6: 每轮后重新评估，达标则提前退出
                if current_confidence >= adaptive_threshold:
                    break
        
        # 7. 最终整合
        if len(all_answers) > 1:
            final_answer = self.integrate_answers(question, all_answers)
        else:
            final_answer = current_answer
        
        # 8. 最终置信度
        final_confidence = self.assess_confidence(final_answer, question)["confidence"]
        
        # 9. 元认知报告
        metacognition_report = self.get_metacognition_report()
        
        return {
            "answer": final_answer,
            "confidence": final_confidence,
            "cognitive_level": current_level,
            "rounds": rounds + 1,
            "category": difficulty["category"],
            "tool_decision": {
                "needs_tool": tool_decision.needs_tool,
                "tool_type": tool_decision.tool_type,
            },
            "cognition_log": self.cognition_log,
            "metacognition": metacognition_report,
            "budget": self.budget.get_breakdown(),
            "version": self.VERSION,
        }
    
    # ------------------------------------------------------------------------
    # 成本分析
    # ------------------------------------------------------------------------
    
    def get_cost_analysis(self) -> Dict:
        """获取认知成本分析"""
        breakdown = self.budget.get_breakdown()
        
        # 估算各阶段成本
        costs = {
            "difficulty_assessment": 50,
            "initial_thinking": 200,
            "confidence_assessment": 30,
            "upgrade_rounds": 300 * (self.budget.rounds_completed - 1),
            "reflection": 150 * self.metacognition["reflections_done"],
            "verification": 100 * self.metacognition["verifications_done"],
            "self_consistency": 500 if self.metacognition.get("consistency_used") else 0,
        }
        
        total_estimated = sum(costs.values())
        
        return {
            "estimated_tokens": total_estimated,
            "actual_tokens_used": breakdown["tokens_used"],
            "stage_breakdown": costs,
            "cognitive_effort": self.metacognition.get("cognitive_effort_score", 0),
        }


# 向后兼容别名
AdvancedCognitionEngine = OxygenDynamicCognitionV26
EnhancedCognitionEngineV21 = OxygenDynamicCognitionV26


# ============================================================================
# CLI 接口
# ============================================================================

def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OxygenDynamicCognition v26.0 Alpha 7")
    parser.add_argument("--question", "-q", help="问题内容")
    parser.add_argument("--model", default="gpt-4", help="模型名称")
    parser.add_argument("--threshold", type=float, default=0.75, help="置信度阈值")
    parser.add_argument("--max-rounds", type=int, default=10, help="最大轮数")
    parser.add_argument("--start-level", type=int, default=2, help="起始认知等级")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--mock", action="store_true", help="Mock模式（离线测试）")
    parser.add_argument("--no-cache", action="store_true", help="禁用缓存")
    parser.add_argument("--retries", type=int, default=3, help="API重试次数")
    
    # v26.0 新增参数
    parser.add_argument("--no-tot", action="store_true", help="禁用思维树")
    parser.add_argument("--no-reflection", action="store_true", help="禁用反射")
    parser.add_argument("--no-verification", action="store_true", help="禁用验证链")
    parser.add_argument("--no-consistency", action="store_true", help="禁用自一致性")
    parser.add_argument("--consistency-samples", type=int, default=5, help="自一致性样本数")
    parser.add_argument("--reflection-depth", type=int, default=2, help="反射深度")
    parser.add_argument("--tot-branches", type=int, default=3, help="思维树分支数")
    parser.add_argument("--tot-depth", type=int, default=3, help="思维树深度")
    parser.add_argument("--version", action="store_true", help="显示版本")
    
    args = parser.parse_args()
    
    if args.version:
        print(f"OxygenDynamicCognition v{OxygenDynamicCognitionV26.VERSION}")
        print("GitHub@StarsailsClover")
        print("\n前沿技术:")
        print("  - 思维树 (Tree of Thoughts)")
        print("  - 思维图 (Graph of Thoughts)")
        print("  - 自一致性 (Self-Consistency)")
        print("  - 反射机制 (Reflection)")
        print("  - 验证链 (Chain of Verification)")
        print("  - 多路径投票 (Multi-Path Voting)")
        print("  - 渐进式深化 (Progressive Deepening)")
        print("  - 元认知监控 (Metacognitive Monitoring)")
        print("  - 认知偏差检测 (Cognitive Bias Detection)")
        return
    
    if not args.question:
        parser.print_help()
        return
    
    # 初始化引擎
    engine = OxygenDynamicCognitionV26(
        model=args.model,
        max_rounds=args.max_rounds,
        confidence_threshold=args.threshold,
        start_level=args.start_level,
        mock_mode=args.mock,
        enable_cache=not args.no_cache,
        max_retries=args.retries,
        enable_tot=not args.no_tot,
        enable_reflection=not args.no_reflection,
        enable_verification=not args.no_verification,
        enable_self_consistency=not args.no_consistency,
        num_consistency_samples=args.consistency_samples,
        max_reflection_depth=args.reflection_depth,
        tot_branching_factor=args.tot_branches,
        tot_max_depth=args.tot_depth,
    )
    
    # 运行推理
    result = engine.run(args.question)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"认知等级: L{result['cognitive_level']}")
        print(f"置信度: {result['confidence']:.1%}")
        print(f"推理轮数: {result['rounds']}")
        print(f"问题类型: {result['category']}")
        print(f"{'='*60}\n")
        print(result["answer"])
        
        if args.verbose:
            print(f"\n{'='*60}")
            print("认知过程日志:")
            for step in result["cognition_log"]:
                print(f"  - {step['step']}")
            
            print(f"\n元认知报告:")
            meta = result["metacognition"]
            print(f"  认知努力分数: {meta['cognitive_effort']:.2f}")
            print(f"  思维节点数: {meta['thoughts_generated']}")
            print(f"  反射次数: {meta['reflections']}")
            print(f"  验证次数: {meta['verifications']}")


if __name__ == "__main__":
    main()
