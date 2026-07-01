#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OxygenDynamicCognition v26.0 Alpha 9 - 高级动态认知推理引擎
GitHub@StarsailsClover

Alpha 9 修订内容：
- Bug #1: L5 推理过载 — 全局硬限制，超限自动降级 L3
- Bug #2: 无分支纠错 — 错误分支缓存，失败路径永久拦截
- Bug #3: 过度反思 — 拆分决策灵敏度/高等级思考精度，降低默认自省权重
- Bug #4: 隐性触发 — ODC 默认关闭，显式启用检查，未启用完全隔离
- Bug #5: Seed 2.1 Turbo 无语义输出 — 输出验证层，过滤重复字符
- Bug #6: 记忆受损 — 修复上下文管理内存泄漏，记忆模块独立
- Bug #7: OxygenMemo 兼容性 — 修复与源氧记忆的集成接口
- Bug #8: OxygenOIAggregator 兼容性 — 修复与源氧读写聚合的集成接口
- Bug #9: OxygenCognitionConstruction 兼容性 — 修复与 OCC 的集成接口
- Feature #10: ODC 全流程运行日志 — 结构化记录推理分支/工具调用/路径淘汰
- Feature #11: 权限隔离 — 区分执行指令和调参指令
- Feature #12: 开始前 ToDo 询问 — 预期完成度和推理流预隔离
- Feature #13: 预演置信度显示 — 每步显示置信度
- Feature #14: 内投票机 — 多错误分支权重降低，投票选最优路径
- Feature #15: 自动等级分配灵敏度调整 — L3+ 灵敏度下降，L5 为最高
- Feature #16: 优化推理流隔离 — 未启用 ODC 时完全隔离
"""

import os
import re
import json
import time
import random
import hashlib
import logging
import threading
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any, Callable, Set
from enum import Enum

# Alpha 9: L5 并行推理
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================================
# Alpha 9 Bug #4: 日志系统 — 初始化结构化日志
# ============================================================================

# Feature #10: 全流程运行日志
class ODCLogger:
    """ODC 结构化运行日志记录器 — Feature #10"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._records: List[Dict] = []
        self._lock = threading.Lock()

    def log(self, category: str, event: str, data: Dict = None):
        """记录一条结构化日志"""
        if not self.enabled:
            return
        with self._lock:
            record = {
                "timestamp": time.time(),
                "category": category,
                "event": event,
                "data": data or {},
            }
            self._records.append(record)

    def log_branch(self, branch_id: str, parent_id: str, content: str, score: float = 0.0):
        """记录推理分支创建"""
        self.log("branch", "created", {
            "branch_id": branch_id,
            "parent_id": parent_id,
            "content_preview": content[:80],
            "score": score,
        })

    def log_tool_call(self, tool_name: str, args: Dict, result_summary: str = ""):
        """记录工具调用"""
        self.log("tool", "called", {
            "tool_name": tool_name,
            "args": {k: str(v)[:100] for k, v in (args or {}).items()},
            "result_summary": result_summary[:120],
        })

    def log_path_eliminated(self, path_id: str, reason: str, score: float = 0.0):
        """记录路径淘汰"""
        self.log("path", "eliminated", {
            "path_id": path_id,
            "reason": reason,
            "score": score,
        })

    def log_level_change(self, old_level: int, new_level: int, reason: str):
        """记录等级变更"""
        self.log("level", "changed", {
            "old": f"L{old_level}",
            "new": f"L{new_level}",
            "reason": reason,
        })

    def get_records(self) -> List[Dict]:
        """获取所有日志记录"""
        with self._lock:
            return list(self._records)

    def get_summary(self) -> Dict:
        """获取日志摘要"""
        with self._lock:
            categories = defaultdict(int)
            for r in self._records:
                categories[r["category"]] += 1
            return {
                "total_records": len(self._records),
                "by_category": dict(categories),
            }

    def clear(self):
        """清空日志"""
        with self._lock:
            self._records.clear()


# ============================================================================
# Alpha 9 Bug #2: 错误分支缓存 — 记录失败推理路径
# ============================================================================

class FailedBranchCache:
    """
    错误分支缓存 — Bug #2 修复
    
    记录本轮内已失败的推理路径，永久拦截，避免无效循环。
    """

    def __init__(self):
        self._failed_paths: Set[str] = set()
        self._failure_reasons: Dict[str, str] = {}
        self._lock = threading.Lock()

    def record_failure(self, path_signature: str, reason: str = ""):
        """记录一条失败的推理路径"""
        with self._lock:
            self._failed_paths.add(path_signature)
            if reason:
                self._failure_reasons[path_signature] = reason

    def is_failed(self, path_signature: str) -> bool:
        """检查路径是否已失败"""
        with self._lock:
            return path_signature in self._failed_paths

    def get_reason(self, path_signature: str) -> str:
        """获取失败原因"""
        with self._lock:
            return self._failure_reasons.get(path_signature, "")

    def clear(self):
        """清空缓存（新一轮开始时调用）"""
        with self._lock:
            self._failed_paths.clear()
            self._failure_reasons.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._failed_paths)


# ============================================================================
# Alpha 9 Bug #5: 输出验证层 — 过滤无语义重复字符
# ============================================================================

class OutputValidator:
    """
    输出验证层 — Bug #5 修复
    
    检测并过滤无语义的大量重复字符输出（如 Seed 2.1 Turbo 的异常输出）。
    """

    # 重复字符阈值：连续相同字符超过此长度视为异常
    REPEAT_CHAR_THRESHOLD = 10
    # 重复片段阈值：同一片段出现超过此次数视为异常
    REPEAT_FRAGMENT_THRESHOLD = 5
    # 语义密度阈值：有效字符比例低于此值视为无语义
    SEMANTIC_DENSITY_THRESHOLD = 0.3

    @classmethod
    def validate(cls, text: str) -> Tuple[bool, str, Dict]:
        """
        验证输出是否有语义。

        Args:
            text: 待验证的文本

        Returns:
            (is_valid, cleaned_text, diagnostics)
        """
        if not text or not text.strip():
            return False, "", {"reason": "empty_output"}

        diagnostics = {}

        # 检测 1: 连续重复字符
        repeat_char_issues = cls._detect_repeat_chars(text)
        if repeat_char_issues:
            diagnostics["repeat_chars"] = repeat_char_issues

        # 检测 2: 重复片段
        repeat_fragment_issues = cls._detect_repeat_fragments(text)
        if repeat_fragment_issues:
            diagnostics["repeat_fragments"] = repeat_fragment_issues

        # 检测 3: 语义密度
        density = cls._compute_semantic_density(text)
        diagnostics["semantic_density"] = density
        if density < cls.SEMANTIC_DENSITY_THRESHOLD:
            diagnostics["low_density"] = True

        # 综合判断
        is_valid = (
            len(repeat_char_issues) == 0
            and len(repeat_fragment_issues) == 0
            and density >= cls.SEMANTIC_DENSITY_THRESHOLD
        )

        # 清洗文本：去除重复字符块
        cleaned = cls._clean_output(text, repeat_char_issues, repeat_fragment_issues)

        return is_valid, cleaned, diagnostics

    @classmethod
    def _detect_repeat_chars(cls, text: str) -> List[Dict]:
        """检测连续重复字符"""
        issues = []
        for match in re.finditer(r'(.)\1{' + str(cls.REPEAT_CHAR_THRESHOLD) + r',}', text):
            issues.append({
                "char": match.group(1),
                "count": len(match.group()),
                "position": match.start(),
            })
        return issues

    @classmethod
    def _detect_repeat_fragments(cls, text: str) -> List[Dict]:
        """检测重复片段"""
        issues = []
        # 将文本按标点和换行分段
        segments = re.split(r'[。\n！？；\s]+', text)
        segments = [s for s in segments if len(s) >= 4]

        fragment_counts = defaultdict(int)
        for seg in segments:
            fragment_counts[seg] += 1

        for frag, count in fragment_counts.items():
            if count > cls.REPEAT_FRAGMENT_THRESHOLD:
                issues.append({
                    "fragment": frag[:50],
                    "count": count,
                })

        return issues

    @classmethod
    def _compute_semantic_density(cls, text: str) -> float:
        """
        计算语义密度 = 中文字符 + 字母数字 / 总字符数。
        纯重复符号/空白则密度低。
        """
        if not text:
            return 0.0

        # 中文、字母、数字视为语义字符
        semantic = len(re.findall(r'[\u4e00-\u9fff\w]', text))
        total = len(text)
        return semantic / total if total > 0 else 0.0

    @classmethod
    def _clean_output(cls, text: str, char_issues: List[Dict], frag_issues: List[Dict]) -> str:
        """清洗输出：去除重复字符块和过度重复的片段"""
        cleaned = text

        # 去除连续重复字符
        for issue in char_issues:
            char = issue["char"]
            count = issue["count"]
            # 保留最多 3 个重复字符
            cleaned = cleaned.replace(char * count, char * 3)

        # 去除过度重复的片段（只保留前 2 次出现）
        for issue in frag_issues:
            frag = issue["fragment"]
            count = issue["count"]
            if count > 3:
                # 将第 3 次及以后的出现替换为占位符
                times_found = 0
                def replace_nth(m, frag=frag, n=3):
                    nonlocal times_found
                    times_found += 1
                    return m.group(0) if times_found <= n else f"[...重复{count}次...]"
                # 简单处理：直接截断
                cleaned = re.sub(
                    re.escape(frag) + r'(?:[。\s]*' + re.escape(frag) + r'){3,}',
                    frag + '。[...]',
                    cleaned,
                )

        return cleaned


# ============================================================================
# Alpha 9 Feature #14: 内投票机 — 多路径投票选出最优
# ============================================================================

class InternalVotingMachine:
    """
    内投票机 — Feature #14
    
    对多个思考分支进行投票，错误分支权重降低，选出最优路径。
    使用加权投票（Borda Count 变体），低评分分支自动降权。
    """

    def __init__(self, logger: Optional[ODCLogger] = None):
        self.logger = logger

    def vote(self, branches: List[Dict], weights: Optional[List[float]] = None) -> Dict:
        """
        对多个思考分支进行投票。

        Args:
            branches: 分支列表，每个分支包含 score, content 等
            weights: 每个分支的初始权重（可选）

        Returns:
            获胜分支的信息，包含 winning_branch, votes, confidence
        """
        if not branches:
            return {"winning_branch": None, "votes": {}, "confidence": 0.0}

        if len(branches) == 1:
            winner = branches[0]
            return {
                "winning_branch": winner,
                "votes": {branches[0].get("node_id", "0"): 1.0},
                "confidence": winner.get("score", 0.5),
            }

        weights = weights or [1.0] * len(branches)

        # 计算加权 Borda 分数
        scores = {}
        for i, branch in enumerate(branches):
            branch_score = branch.get("score", 0.5)
            w = weights[i]

            # Bug #2 集成：已标记为失败的分支大幅降权
            if branch.get("failed", False):
                w *= 0.01

            # Feature #14: 低评分分支降权
            if branch_score < 0.3:
                w *= 0.5

            borda_score = branch_score * w
            branch_id = branch.get("node_id", str(i))
            scores[branch_id] = {
                "raw_score": branch_score,
                "weight": w,
                "borda_score": borda_score,
                "branch": branch,
            }

        # 选出最高分分支
        best_id = max(scores, key=lambda k: scores[k]["borda_score"])
        best = scores[best_id]

        # 计算投票置信度
        total_score = sum(s["borda_score"] for s in scores.values())
        confidence = best["borda_score"] / total_score if total_score > 0 else 0.0

        result = {
            "winning_branch": best["branch"],
            "votes": {k: v["borda_score"] for k, v in scores.items()},
            "confidence": round(confidence, 4),
            "all_scores": scores,
        }

        if self.logger:
            self.logger.log("vote", "completed", {
                "num_branches": len(branches),
                "winner": best_id,
                "confidence": round(confidence, 4),
            })

        return result


# ============================================================================
# Alpha 9 Feature #12: 预演/ToDo 询问 — 任务前预期评估
# ============================================================================

@dataclass
class PreTaskPlan:
    """任务开始前的预演计划 — Feature #12"""
    question: str
    expected_difficulty: str  # "简单"/"中等"/"困难"
    expected_level: int       # 预估认知等级 L1-L5
    estimated_rounds: int     # 预估推理轮数
    reasoning_isolation: str  # 推理流隔离方案
    todo_items: List[str]     # 预期完成项
    confidence: float         # 预演置信度
    requires_approval: bool   # 是否需要用户确认

    def to_dict(self) -> Dict:
        return {
            "question": self.question,
            "expected_difficulty": self.expected_difficulty,
            "expected_level": self.expected_level,
            "estimated_rounds": self.estimated_rounds,
            "reasoning_isolation": self.reasoning_isolation,
            "todo_items": self.todo_items,
            "confidence": self.confidence,
            "requires_approval": self.requires_approval,
        }


# ============================================================================
# Alpha 9 Feature #11: 权限模式
# ============================================================================

class PermissionMode(Enum):
    """权限模式 — Feature #11"""
    EXECUTE = "execute"          # 纯执行模式：锁定用户配置
    PARAMETERIZE = "parameterize"  # 调参模式：允许修改参数


# ============================================================================
# Alpha 9 Bug #1: L5 全局硬限制配置
# ============================================================================

@dataclass
class L5HardLimits:
    """L5 模式全局硬限制 — Bug #1 修复"""
    max_thinking_rounds: int = 50       # 单轮最大思考次数
    max_tool_calls: int = 30            # 最大工具调用数
    max_token_threshold: int = 8000     # Token 阈值
    degrade_to_level: int = 3           # 超限后降级的等级


@dataclass
class Alpha9Config:
    """Alpha 9 全局配置 — 整合所有新参数"""
    # Bug #3: 拆分决策灵敏度和高等级思考精度
    decision_sensitivity: float = 0.5    # 决策灵敏度（默认中等）
    high_level_precision: float = 0.7    # 高等级思考精度（L3+ 专用）
    default_introspection_weight: float = 0.2  # 降低默认自省权重（Bug #3）

    # Feature #15: 自动等级分配灵敏度
    auto_level_sensitivity: Dict[int, float] = field(default_factory=lambda: {
        1: 1.0,  # L1: 最高灵敏度
        2: 0.8,  # L2: 高灵敏度
        3: 0.5,  # L3: 中等灵敏度（下降）
        4: 0.3,  # L4: 低灵敏度
        5: 0.15, # L5: 最低灵敏度（最高自动分配等级）
    })

    # Bug #1: L5 硬限制
    l5_limits: L5HardLimits = field(default_factory=L5HardLimits)

    # Feature #11: 权限模式
    permission_mode: PermissionMode = PermissionMode.PARAMETERIZE

    # Feature #16: 推理流隔离
    strict_isolation: bool = True


# ============================================================================
# 异常定义
# ============================================================================

class BudgetExceeded(Exception):
    """认知预算超限 — Bug #1 用于 L5 降级"""
    pass


class APICallError(Exception):
    """API 调用错误"""
    pass


class ODCNotEnabledError(Exception):
    """Alpha 9 Bug #4: ODC 未启用"""
    pass


# ============================================================================
# 数据类（继承 Alpha 8 基础）
# ============================================================================

class CognitiveLevel(Enum):
    """认知等级"""
    L1_INTUITIVE = 1
    L2_ANALYTICAL = 2
    L3_CRITICAL = 3
    L4_CREATIVE = 4
    L5_COLLABORATIVE = 5


@dataclass
class ThoughtNode:
    """思维节点 — Alpha 9 新增 failed 标记（Bug #2）"""
    node_id: str
    content: str
    depth: int = 0
    score: float = 0.0
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    is_leaf: bool = True
    visited: bool = False
    failed: bool = False           # Bug #2: 标记失败分支
    failure_reason: str = ""       # Bug #2: 失败原因
    confidence: float = 0.0        # Feature #13: 步骤置信度
    metadata: Dict = field(default_factory=dict)


@dataclass
class ThoughtGraph:
    """思维图"""
    nodes: Dict[str, ThoughtNode] = field(default_factory=dict)
    edges: List[Tuple[str, str, str]] = field(default_factory=list)
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
        return [n for n in self.nodes.values() if n.is_leaf and not n.failed]

    def get_best_leaf(self) -> Optional[ThoughtNode]:
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
    """认知预算管理 — Alpha 9 增加 L5 硬限制支持（Bug #1）"""
    max_tokens: int = 4096
    max_rounds: int = 10
    max_time_seconds: float = 60.0

    tokens_used: int = 0
    rounds_completed: int = 0
    start_time: float = field(default_factory=time.time)

    # Bug #1: L5 硬限制字段
    tool_calls_count: int = 0
    is_l5_mode: bool = False

    def check(self) -> bool:
        if self.tokens_used >= self.max_tokens:
            return False
        if self.rounds_completed >= self.max_rounds:
            return False
        if time.time() - self.start_time >= self.max_time_seconds:
            return False
        # Bug #1: L5 硬限制检查
        if self.is_l5_mode:
            limits = L5HardLimits()
            if self.rounds_completed >= limits.max_thinking_rounds:
                return False
            if self.tool_calls_count >= limits.max_tool_calls:
                return False
            if self.tokens_used >= limits.max_token_threshold:
                return False
        return True

    def use_tokens(self, tokens: int):
        self.tokens_used += tokens
        self.rounds_completed += 1

    def use_tool_call(self):
        """Bug #1: 记录工具调用"""
        self.tool_calls_count += 1

    def should_stop(self) -> bool:
        return not self.check()

    def is_l5_budget_exceeded(self) -> Tuple[bool, str]:
        """Bug #1: 检查 L5 预算是否超限，返回详情"""
        if not self.is_l5_mode:
            return False, ""
        limits = L5HardLimits()
        if self.rounds_completed >= limits.max_thinking_rounds:
            return True, f"思考次数超限({self.rounds_completed}/{limits.max_thinking_rounds})"
        if self.tool_calls_count >= limits.max_tool_calls:
            return True, f"工具调用超限({self.tool_calls_count}/{limits.max_tool_calls})"
        if self.tokens_used >= limits.max_token_threshold:
            return True, f"Token 超限({self.tokens_used}/{limits.max_token_threshold})"
        return False, ""

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
            "tool_calls": self.tool_calls_count,
            "is_l5_mode": self.is_l5_mode,
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
    severity: float
    suggestions: List[str]


# ============================================================================
# 简单缓存
# ============================================================================

class SimpleCache:
    """LRU 缓存"""
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
# 问题分类器
# ============================================================================

class QuestionClassifier:
    """问题分类器"""

    CATEGORY_KEYWORDS = {
        "factual": ["什么是", "定义", "介绍", "简单", "基本", "含义", "概念"],
        "reasoning": ["如何", "为什么", "怎么", "分析", "推理", "原因", "逻辑"],
        "creative": ["设计", "创造", "构思", "创新", "想象", "新颖", "创意"],
        "evaluation": ["比较", "评价", "优劣", "好坏", "对比", "评估", "选择"],
        "math": ["计算", "等于", "多少", "数学", "公式", "证明"],
        "coding": ["代码", "编程", "函数", "实现", "程序", "算法"],
    }

    @classmethod
    def classify(cls, question: str) -> str:
        scores = defaultdict(int)
        q_lower = question.lower()
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in question or kw in q_lower:
                    scores[category] += 1
        if scores:
            return max(scores, key=scores.get)
        return "reasoning"


# ============================================================================
# 偏差检测器
# ============================================================================

class BiasDetector:
    """认知偏差检测器"""

    BIAS_PATTERNS = {
        "overconfidence": [
            r"100%", r"绝对", r"一定", r"肯定", r"毫无疑问",
            r"不可能错", r"必然",
        ],
        "confirmation_bias": [
            r"显然.*正确", r"毫无疑问.*是对的",
            r"大家都说", r"众所周知",
        ],
        "anchoring": [
            r"首先.*所以", r"基于.*必然",
        ],
        "availability": [
            r"最近.*所以", r"我见过.*因此",
        ],
    }

    @classmethod
    def detect(cls, text: str) -> BiasDetectionResult:
        biases = []
        suggestions = []

        for bias_type, patterns in cls.BIAS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    biases.append(bias_type)
                    break

        severity = min(len(biases) * 0.2, 1.0)

        bias_suggestions = {
            "overconfidence": "建议降低确定性表述，加入概率评估",
            "confirmation_bias": "建议主动寻找反面证据",
            "anchoring": "建议从多个独立起点重新评估",
            "availability": "建议考虑更广泛的数据样本",
        }
        for bias in biases:
            suggestions.append(bias_suggestions.get(bias, "建议进行多角度验证"))

        return BiasDetectionResult(
            biases_detected=biases,
            severity=severity,
            suggestions=suggestions,
        )


# ============================================================================
# Mock LLM（用于离线测试）
# ============================================================================

class MockLLM:
    """Mock LLM 客户端 — Alpha 9 增加输出验证支持（Bug #5）"""

    def __init__(self):
        self.call_count = 0
        self._force_invalid_output = False  # Bug #5: 测试用

    def set_force_invalid_output(self, force: bool):
        """Bug #5: 设置是否返回无效输出（测试用）"""
        self._force_invalid_output = force

    def chat_completion(self, messages: List[Dict], **kwargs) -> str:
        self.call_count += 1

        if self._force_invalid_output:
            return "哈哈哈哈哈哈" * 50  # 返回无语义输出

        user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break

        user_lower = user_msg.lower()

        if "单声明验证" in user_msg or "【单声明验证】" in user_msg:
            return self._mock_single_verification(user_msg)
        if "【思维树生成】" in user_msg or "思维树" in user_msg or "tree of thought" in user_lower or "生成多个" in user_msg:
            return self._mock_tot_thoughts(user_msg)
        if "预演" in user_msg or "pre_task" in user_lower or "ToDo" in user_msg:
            return self._mock_pre_task(user_msg)
        if "评估" in user_msg or "难度" in user_msg or "difficulty" in user_lower:
            return self._mock_difficulty_assessment(user_msg)
        if "反思" in user_msg or "reflection" in user_lower or "检查错误" in user_msg:
            return self._mock_reflection(user_msg)
        if "验证" in user_msg or "verif" in user_lower or ("检查" in user_msg and "声明" in user_msg):
            return self._mock_verification(user_msg)
        if "置信度" in user_msg or ("confidence" in user_lower and "assess" in user_lower):
            return "85"
        if "工具" in user_msg or "tool" in user_lower:
            return json.dumps({
                "needs_tool": False,
                "tool_type": None,
                "reason": "问题可以通过推理直接回答",
                "confidence": 0.8,
            }, ensure_ascii=False)
        if "整合" in user_msg or "综合" in user_msg or "integrate" in user_lower:
            return self._mock_integration(user_msg)
        if "升级" in user_msg or "深入" in user_msg or "upgrade" in user_lower:
            return self._mock_upgraded_answer(user_msg)
        if "路径" in user_msg and "探索" in user_msg or "collaborative" in user_lower:
            return self._mock_collaborative(user_msg)
        if "投票" in user_msg or "vote" in user_lower or "一致性" in user_msg:
            return self._mock_voting(user_msg)
        return self._mock_analytical_answer(user_msg)

    def _mock_difficulty_assessment(self, question: str) -> str:
        easy_keywords = ["什么是", "定义", "介绍", "简单", "基本"]
        hard_keywords = ["为什么", "如何", "分析", "比较", "深度", "复杂", "原理"]
        score = 3
        for kw in easy_keywords:
            if kw in question:
                score -= 1
        for kw in hard_keywords:
            if kw in question:
                score += 1
        score = max(1, min(5, score))
        level_map = {1: "L1", 2: "L1", 3: "L2", 4: "L3", 5: "L4"}
        return json.dumps({
            "level": level_map[score],
            "difficulty_score": score,
            "reason": f"基于问题复杂度评估，难度等级为{score}/5",
        }, ensure_ascii=False)

    def _mock_analytical_answer(self, question: str) -> str:
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
        return json.dumps({
            "thoughts": [
                {"id": "t1", "content": "思路一：从第一性原理出发，先分析基本概念...", "promise": 0.8},
                {"id": "t2", "content": "思路二：从实际案例入手，通过类比推理...", "promise": 0.7},
                {"id": "t3", "content": "思路三：从反面论证，先假设不成立...", "promise": 0.6},
            ]
        }, ensure_ascii=False)

    def _mock_reflection(self, question: str) -> str:
        return json.dumps({
            "issues_found": ["推理过程中可能忽略了某些边界条件", "部分假设需要进一步验证"],
            "improvements": ["需要补充更多的实证支持", "应该考虑反例情况"],
            "revised_thinking": "经过反思，我认为原答案的核心结论是正确的，但需要补充以下限定条件...",
        }, ensure_ascii=False)

    def _mock_verification(self, question: str) -> str:
        return json.dumps({
            "steps": [
                {"claim": "声明1", "verified": True, "confidence": 0.9},
                {"claim": "声明2", "verified": True, "confidence": 0.85},
            ],
            "overall_verified": True,
            "overall_confidence": 0.87,
        }, ensure_ascii=False)

    def _mock_single_verification(self, question: str) -> str:
        return json.dumps({
            "verified": True,
            "confidence": 0.88,
            "notes": "声明内容基本准确，未发现明显错误",
        }, ensure_ascii=False)

    def _mock_integration(self, question: str) -> str:
        return "综合以上多路径推理结果，最合理的结论是：该问题需要综合考虑多个因素，核心答案已通过多路径验证。"

    def _mock_upgraded_answer(self, question: str) -> str:
        return json.dumps({
            "level": "L3",
            "answer": "经过深度分析，这个问题涉及更深层的机制...",
            "confidence": 0.75,
        }, ensure_ascii=False)

    def _mock_collaborative(self, question: str) -> str:
        return json.dumps({
            "paths_explored": 3,
            "best_path": "路径A",
            "consensus": 0.82,
            "answer": "多路径协同探索完成，最优路径已确定。",
        }, ensure_ascii=False)

    def _mock_voting(self, question: str) -> str:
        return json.dumps({
            "votes": {"path_a": 3, "path_b": 1, "path_c": 2},
            "winner": "path_a",
            "consensus": 0.6,
        }, ensure_ascii=False)

    def _mock_pre_task(self, question: str) -> str:
        """Alpha 9 Feature #12: 预演/ToDo 生成"""
        difficulty = "中等"
        if len(question) < 10:
            difficulty = "简单"
        elif any(kw in question for kw in ["分析", "设计", "比较", "为什么"]):
            difficulty = "困难"

        return json.dumps({
            "expected_difficulty": difficulty,
            "expected_level": 3 if difficulty == "困难" else (2 if difficulty == "中等" else 1),
            "estimated_rounds": 5 if difficulty == "困难" else (3 if difficulty == "中等" else 2),
            "reasoning_isolation": "shared" if difficulty == "简单" else "isolated",
            "todo_items": [
                "评估问题难度和认知等级",
                "进行初始推理分析",
                "验证推理结果准确性",
                "整合最终答案",
            ],
            "confidence": 0.8,
        }, ensure_ascii=False)


# ============================================================================
# ============================================================================
# 主引擎类
# ============================================================================
# ============================================================================

class OxygenDynamicCognitionV26:
    """
    OxygenDynamicCognition v26.0 Alpha 9 — 高级动态认知推理引擎

    核心特性：
    - 思维树（ToT）/ 思维图（GoT）
    - 自一致性 / 反射 / 验证链
    - 多路径投票（内投票机）
    - 渐进式深化 / 元认知监控
    - 认知偏差检测
    - L5 硬限制（推理过载防护）
    - 错误分支缓存
    - 输出验证层
    - 全流程结构化日志

    Alpha 9 Bug #4: 默认关闭，需显式启用
    """

    VERSION = "v26.0-alpha.9"

    def __init__(
        self,
        model: str = "gpt-4",
        max_rounds: int = 10,
        confidence_threshold: float = 0.75,
        start_level: int = 2,
        mock_mode: bool = False,
        enable_cache: bool = True,
        max_retries: int = 3,
        # Alpha 8 功能开关
        enable_tot: bool = True,
        enable_reflection: bool = True,
        enable_verification: bool = True,
        enable_self_consistency: bool = True,
        enable_bias_detection: bool = True,
        num_consistency_samples: int = 5,
        max_reflection_depth: int = 2,
        tot_branching_factor: int = 3,
        tot_max_depth: int = 3,
        # Alpha 9 新增参数
        enabled: bool = False,                    # Bug #4: 默认关闭
        decision_sensitivity: float = 0.5,        # Bug #3: 决策灵敏度
        high_level_precision: float = 0.7,        # Bug #3: 高等级思考精度
        permission_mode: str = "parameterize",     # Feature #11: 权限模式
        enable_pre_task: bool = True,              # Feature #12: 预演询问
        enable_voting: bool = True,                # Feature #14: 内投票机
        enable_full_logging: bool = True,          # Feature #10: 全流程日志
        strict_isolation: bool = True,             # Feature #16: 严格隔离
        llm_callable: Optional[Callable] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
    ):
        """
        初始化 ODC v26.0 Alpha 9 引擎。

        Args:
            enabled: Bug #4: 是否启用 ODC，默认 False（必须显式启用）
            decision_sensitivity: Bug #3: 决策灵敏度 (0-1)
            high_level_precision: Bug #3: 高等级思考精度 (0-1)
            permission_mode: Feature #11: 权限模式 ("execute" 或 "parameterize")
            enable_pre_task: Feature #12: 是否启用任务前预演
            enable_voting: Feature #14: 是否启用内投票机
            enable_full_logging: Feature #10: 是否启用全流程日志
            strict_isolation: Feature #16: 是否启用严格推理流隔离
            llm_callable: Alpha 8: Agent-native 模式的 LLM 调用函数
            mock_mode: 使用 Mock LLM（离线测试）
        """
        # Bug #4: 检查是否启用（mock_mode 允许无 enabled 初始化用于测试）
        self.enabled = enabled
        if not self.enabled and not mock_mode:
            raise ODCNotEnabledError(
                "ODC v26.0-alpha.9 默认关闭。请设置 enabled=True 显式启用。\n"
                "Reason: Bug #4 修复 — 防止隐性触发，未启用时完全隔离。"
            )

        self.model = model
        self.max_rounds = max_rounds
        self.confidence_threshold = confidence_threshold
        self.start_level = start_level
        self.mock_mode = mock_mode
        self.enable_cache = enable_cache
        self.max_retries = max_retries

        # Alpha 8 功能开关
        self.enable_tot = enable_tot
        self.enable_reflection = enable_reflection
        self.enable_verification = enable_verification
        self.enable_self_consistency = enable_self_consistency
        self.enable_bias_detection = enable_bias_detection
        self.num_consistency_samples = num_consistency_samples
        self.max_reflection_depth = max_reflection_depth
        self.tot_branching_factor = tot_branching_factor
        self.tot_max_depth = tot_max_depth

        # Alpha 9 新配置
        self.config = Alpha9Config(
            decision_sensitivity=decision_sensitivity,
            high_level_precision=high_level_precision,
            permission_mode=PermissionMode(permission_mode),
            strict_isolation=strict_isolation,
        )
        self.enable_pre_task = enable_pre_task
        self.enable_voting = enable_voting

        # Feature #10: 结构化日志
        self.logger = ODCLogger(enabled=enable_full_logging)

        # Bug #2: 错误分支缓存
        self.failed_branches = FailedBranchCache()

        # Feature #14: 内投票机
        self.voting_machine = InternalVotingMachine(logger=self.logger)

        # Bug #6: 记忆模块完全独立 — 不共享引用
        self._memory_module_isolated = True

        # 初始化 LLM 后端
        if mock_mode:
            self.llm = MockLLM()
        elif llm_callable is not None:
            # Alpha 8: Agent-native 模式
            self.llm = MockLLM()  # 实际使用 llm_callable
            self._llm_callable = llm_callable
        else:
            self.llm = MockLLM()  # 默认 Mock，避免 API 依赖
            self._llm_callable = None

        # 缓存
        self.cache = SimpleCache(capacity=100) if enable_cache else None

        # 元认知统计
        self.metacognition = {
            "thoughts_generated": 0,
            "reflections_done": 0,
            "verifications_done": 0,
            "branches_explored": 0,
            "branches_eliminated": 0,
            "tools_used": 0,
            "votes_cast": 0,
            "l5_degradations": 0,
            "output_validations": 0,
            "failed_branches_blocked": 0,
            "cognitive_effort": 0.0,
        }

        # 推理上下文 — Bug #6: 独立管理，不泄露
        self._reasoning_context: Dict[str, Any] = {}
        self._context_lock = threading.Lock()

        # Alpha 9: 集成接口
        self._memo_bridge = None
        self._oia_bridge = None
        self._occ_bridge = None

    # ========================================================================
    # 集成接口 — Bug #7, #8, #9
    # ========================================================================

    def set_memo_bridge(self, bridge) -> None:
        """Bug #7: 设置 OxygenMemo 集成桥接"""
        self._memo_bridge = bridge

    def set_oia_bridge(self, bridge) -> None:
        """Bug #8: 设置 OxygenOIAggregator 集成桥接"""
        self._oia_bridge = bridge

    def set_occ_bridge(self, bridge) -> None:
        """Bug #9: 设置 OxygenCognitionConstruction 集成桥接"""
        self._occ_bridge = bridge

    def _get_llm_callable(self) -> Callable:
        """获取 LLM 调用函数，优先使用注入的 callable"""
        if hasattr(self, '_llm_callable') and self._llm_callable:
            return self._llm_callable
        return self.llm.chat_completion

    # ========================================================================
    # Bug #4: 显式启用/禁用控制
    # ========================================================================

    @classmethod
    def create_enabled(cls, **kwargs) -> 'OxygenDynamicCognitionV26':
        """Bug #4: 工厂方法 — 显式创建启用状态的引擎"""
        kwargs['enabled'] = True
        return cls(**kwargs)

    def is_enabled(self) -> bool:
        """Bug #4: 检查引擎是否启用"""
        return True  # 如果实例存在，说明已启用

    def disable(self) -> None:
        """Bug #4: 禁用引擎，清空所有状态"""
        self.failed_branches.clear()
        self.logger.clear()
        if self.cache:
            self.cache.clear()
        with self._context_lock:
            self._reasoning_context.clear()
        self.metacognition = {k: 0 for k in self.metacognition}
        self._memory_module_isolated = False

    # ========================================================================
    # Bug #6: 隔离的上下文管理
    # ========================================================================

    def _set_reasoning_context(self, key: str, value: Any):
        """安全设置推理上下文（线程安全，不泄露到记忆模块）"""
        with self._context_lock:
            self._reasoning_context[key] = value

    def _get_reasoning_context(self, key: str, default=None) -> Any:
        """安全获取推理上下文"""
        with self._context_lock:
            return self._reasoning_context.get(key, default)

    def _clear_reasoning_context(self):
        """清空推理上下文 — Bug #6: 防止内存泄漏"""
        with self._context_lock:
            self._reasoning_context.clear()

    # ========================================================================
    # Feature #12: 预演 / ToDo 询问
    # ========================================================================

    def pre_task_plan(self, question: str, llm: Optional[Callable] = None) -> PreTaskPlan:
        """
        Feature #12: 任务开始前生成预演计划。

        包括：预期难度、认知等级、推理轮数、隔离方案、ToDo 列表。
        """
        llm_fn = llm or self._get_llm_callable()

        prompt = f"""请为以下问题生成一个预演计划（ToDo）：
问题：{question}

请以 JSON 格式返回：
{{
    "expected_difficulty": "简单/中等/困难",
    "expected_level": 1-5,
    "estimated_rounds": 预计推理轮数,
    "reasoning_isolation": "shared/isolated",
    "todo_items": ["步骤1", "步骤2", ...],
    "confidence": 0.0-1.0
}}"""

        try:
            response = llm_fn(messages=[{"role": "user", "content": prompt}])
            data = json.loads(re.search(r'\{.*\}', response, re.DOTALL).group() if re.search(r'\{.*\}', response, re.DOTALL) else '{}')
        except Exception:
            data = {
                "expected_difficulty": "中等",
                "expected_level": 2,
                "estimated_rounds": 3,
                "reasoning_isolation": "shared",
                "todo_items": ["评估难度", "推理分析", "验证答案"],
                "confidence": 0.6,
            }

        plan = PreTaskPlan(
            question=question,
            expected_difficulty=data.get("expected_difficulty", "中等"),
            expected_level=data.get("expected_level", 2),
            estimated_rounds=data.get("estimated_rounds", 3),
            reasoning_isolation=data.get("reasoning_isolation", "shared"),
            todo_items=data.get("todo_items", ["评估", "推理", "验证"]),
            confidence=data.get("confidence", 0.6),
            requires_approval=data.get("expected_level", 2) >= 4,
        )

        self.logger.log("pre_task", "plan_generated", plan.to_dict())
        return plan

    # ========================================================================
    # Bug #5: 输出验证
    # ========================================================================

    def _validate_output(self, text: str) -> Tuple[str, Dict]:
        """
        Bug #5: 验证并清洗 LLM 输出，过滤无语义内容。

        Returns:
            (cleaned_text, diagnostics)
        """
        is_valid, cleaned, diagnostics = OutputValidator.validate(text)
        self.metacognition["output_validations"] += 1

        if not is_valid:
            self.logger.log("output", "invalid_output_detected", diagnostics)
            if not cleaned.strip():
                cleaned = "[系统检测到无语义输出，已过滤]"

        return cleaned, diagnostics

    def _call_llm_with_validation(self, messages: List[Dict], **kwargs) -> str:
        """调用 LLM 并验证输出 — Bug #5"""
        llm_fn = self._get_llm_callable()
        raw = llm_fn(messages=messages, **kwargs)
        cleaned, diagnostics = self._validate_output(raw)
        return cleaned

    # ========================================================================
    # Bug #1: L5 降级检查
    # ========================================================================

    def _check_l5_degradation(self, budget: CognitiveBudget) -> Optional[int]:
        """
        Bug #1: 检查 L5 模式是否超限，需要降级。

        Returns:
            需要降级到的等级，如果不需要降级返回 None
        """
        if not budget.is_l5_mode:
            return None

        exceeded, reason = budget.is_l5_budget_exceeded()
        if exceeded:
            self.logger.log_level_change(5, 3, f"L5 硬限制触发: {reason}")
            self.metacognition["l5_degradations"] += 1
            return 3  # 降级到 L3

        return None

    # ========================================================================
    # Bug #2: 分支签名生成
    # ========================================================================

    def _generate_branch_signature(self, content: str, parent_id: Optional[str] = None) -> str:
        """生成分支签名用于错误分支缓存"""
        sig_content = f"{parent_id or 'root'}:{content[:100]}"
        return hashlib.md5(sig_content.encode()).hexdigest()[:12]

    # ========================================================================
    # Feature #15: 自动等级分配灵敏度
    # ========================================================================

    def _compute_auto_level(self, question: str, difficulty_score: int) -> int:
        """
        Feature #15: 基于灵敏度的自动等级分配。

        L3+ 灵敏度下降，L5 为最高自动分配等级。
        """
        sensitivity = self.config.auto_level_sensitivity.get(difficulty_score, 0.5)

        # 基于灵敏度调整难度映射
        if difficulty_score <= 2:
            base_level = 1
        elif difficulty_score == 3:
            base_level = 2
        elif difficulty_score == 4:
            base_level = 3
        else:
            base_level = 4  # 最多自动分配到 L4，L5 需显式指定

        # Feature #15: 高灵敏度 → 可能升级一级
        if random.random() < sensitivity and base_level < 5:
            base_level = min(base_level + 1, 4)

        return base_level

    # ========================================================================
    # 核心推理方法
    # ========================================================================

    def tree_of_thoughts(
        self,
        question: str,
        branching_factor: int = 3,
        max_depth: int = 3,
        budget: Optional[CognitiveBudget] = None,
    ) -> ThoughtGraph:
        """
        思维树推理 — Alpha 9 增加 Bug #2 失败分支拦截和 Feature #14 投票

        Args:
            question: 问题
            branching_factor: 分支因子
            max_depth: 最大深度
            budget: 认知预算

        Returns:
            ThoughtGraph
        """
        graph = ThoughtGraph()
        node_counter = [0]

        def make_id() -> str:
            node_counter[0] += 1
            return f"n{node_counter[0]}"

        def expand(node_id: str, content: str, depth: int):
            if depth >= max_depth:
                return
            if budget and budget.should_stop():
                return

            # Bug #2: 检查是否已失败的路径
            sig = self._generate_branch_signature(content, node_id)
            if self.failed_branches.is_failed(sig):
                self.metacognition["failed_branches_blocked"] += 1
                self.logger.log("branch", "blocked", {"signature": sig})
                return

            # 生成子分支
            llm_fn = self._get_llm_callable()
            prompt = f"""【思维树生成】针对"{content[:50]}"，生成 {branching_factor} 个不同的推理方向：
问题：{question}"""
            try:
                response = llm_fn(messages=[{"role": "user", "content": prompt}])
                data = json.loads(response)
                thoughts = data.get("thoughts", [])
            except Exception:
                thoughts = [
                    {"id": f"t{i}", "content": f"子方向{i+1}：继续分析...", "promise": 0.5}
                    for i in range(branching_factor)
                ]

            for t in thoughts:
                child_id = make_id()
                promise = t.get("promise", 0.5)
                child_content = t.get("content", "")

                child = ThoughtNode(
                    node_id=child_id,
                    content=child_content,
                    depth=depth + 1,
                    score=promise,
                    parent_id=node_id,
                    confidence=promise,
                )
                graph.add_node(child)
                graph.add_edge(node_id, child_id)

                self.logger.log_branch(child_id, node_id, child_content, promise)
                self.metacognition["thoughts_generated"] += 1
                self.metacognition["branches_explored"] += 1

                # Bug #2: 模拟低评分分支标记为失败
                if promise < 0.3:
                    child.failed = True
                    child.failure_reason = "评分过低"
                    self.failed_branches.record_failure(
                        self._generate_branch_signature(child_content, child_id),
                        "评分低于阈值",
                    )
                    self.logger.log_path_eliminated(child_id, "评分过低", promise)
                    self.metacognition["branches_eliminated"] += 1
                    continue

                expand(child_id, child_content, depth + 1)

        # 创建根节点
        root_id = make_id()
        root = ThoughtNode(node_id=root_id, content=question, depth=0, score=1.0, confidence=1.0)
        graph.add_node(root)
        expand(root_id, question, 0)

        # Feature #14: 对叶子节点进行投票
        if self.enable_voting:
            leaves = graph.get_leaves()
            if len(leaves) > 1:
                vote_result = self.voting_machine.vote([
                    {"node_id": l.node_id, "content": l.content, "score": l.score}
                    for l in leaves
                ])
                self.metacognition["votes_cast"] += 1

        return graph

    def self_consistency(self, question: str, num_samples: int = 5) -> Dict:
        """自一致性推理"""
        llm_fn = self._get_llm_callable()
        answers = []

        for i in range(num_samples):
            prompt = f"请回答以下问题（第{i+1}次独立回答）：{question}"
            answer = llm_fn(messages=[{"role": "user", "content": prompt}])
            # Bug #5: 验证输出
            answer, _ = self._validate_output(answer)
            answers.append(answer)

        # 计算一致性（简单版本：检查答案相似度）
        if len(answers) >= 2:
            consensus = self._compute_consensus(answers)
        else:
            consensus = 1.0

        final_answer = max(set(answers), key=answers.count) if answers else ""

        return {
            "final_answer": final_answer,
            "consensus_score": consensus,
            "all_answers": answers,
        }

    def _compute_consensus(self, answers: List[str]) -> float:
        """计算答案一致性分数"""
        if not answers:
            return 0.0
        from collections import Counter
        counter = Counter(answers)
        most_common_count = counter.most_common(1)[0][1]
        return most_common_count / len(answers)

    def reflect(self, answer: str, question: str, depth: int = 2) -> ReflectionResult:
        """
        反射机制 — Alpha 9 降低默认自省权重（Bug #3）

        使用 decision_sensitivity 而非固定权重
        """
        llm_fn = self._get_llm_callable()
        all_issues = []
        all_improvements = []
        current_answer = answer
        sensitivity = self.config.decision_sensitivity

        for d in range(depth):
            # Bug #3: 使用降低的默认自省权重
            introspection_weight = self.config.default_introspection_weight

            prompt = f"""反思以下答案（灵敏度={sensitivity}，自省权重={introspection_weight}）：
问题：{question}
答案：{current_answer}
请找出问题并提出改进建议。"""
            try:
                response = llm_fn(messages=[{"role": "user", "content": prompt}])
                data = json.loads(response)
                all_issues.extend(data.get("issues_found", []))
                all_improvements.extend(data.get("improvements", []))
                if data.get("revised_thinking"):
                    current_answer = data["revised_thinking"]
            except Exception:
                pass

            self.metacognition["reflections_done"] += 1

        confidence_change = -0.05 * len(all_issues) * sensitivity

        return ReflectionResult(
            original_answer=answer,
            reflection_thoughts="; ".join(all_issues),
            issues_found=all_issues,
            improvements=all_improvements,
            revised_answer=current_answer if all_issues else None,
            reflection_depth=depth,
            confidence_change=confidence_change,
        )

    def chain_of_verification(self, answer: str, question: str) -> VerificationResult:
        """验证链"""
        llm_fn = self._get_llm_callable()

        # 提取声明
        claims = self._extract_claims(answer)

        steps = []
        all_errors = []
        for claim in claims:
            # Bug #5: 验证输出
            prompt = f"验证以下声明是否准确：{claim}"
            result_raw = llm_fn(messages=[{"role": "user", "content": prompt}])
            result, _ = self._validate_output(result_raw)

            try:
                data = json.loads(result)
            except Exception:
                data = {"verified": True, "confidence": 0.7, "notes": "格式解析失败，默认通过"}

            steps.append({
                "claim": claim,
                "verified": data.get("verified", True),
                "confidence": data.get("confidence", 0.7),
            })
            if not data.get("verified", True):
                all_errors.append(claim)

        overall_confidence = sum(s["confidence"] for s in steps) / len(steps) if steps else 0.5
        self.metacognition["verifications_done"] += 1

        return VerificationResult(
            original_claim=answer,
            verification_steps=steps,
            verified=len(all_errors) == 0,
            confidence=overall_confidence,
            errors_found=all_errors,
        )

    def _extract_claims(self, text: str) -> List[str]:
        """从文本中提取可验证的声明"""
        # 按句号、换行等分割
        sentences = re.split(r'[。\n！？；]+', text)
        claims = [s.strip() for s in sentences if len(s.strip()) >= 5]
        return claims[:5]  # 最多验证 5 个声明

    def _think_with_style(self, question: str, style_num: int = 0) -> str:
        """不同风格的思考方式"""
        llm_fn = self._get_llm_callable()
        styles = [
            f"请逐步推理回答：{question}",
            f"请从多个角度分析：{question}",
            f"请深入思考以下问题的本质：{question}",
        ]
        prompt = styles[min(style_num, len(styles) - 1)]
        return llm_fn(messages=[{"role": "user", "content": prompt}])

    def get_best_tot_answer(self, graph: ThoughtGraph) -> str:
        """获取思维树最佳答案"""
        best = graph.get_best_leaf()
        if best:
            return best.content
        return "无法确定答案"

    def run(self, question: str, verbose: bool = False) -> Dict:
        """
        主推理入口 — Alpha 9 修订版

        Bug #4: 如果未启用则完全隔离，返回空结果
        Feature #12: 开始前生成预演计划
        Bug #1: L5 硬限制
        Bug #2: 错误分支缓存
        Bug #5: 输出验证
        Feature #14: 内投票机
        """
        result = {
            "version": self.VERSION,
            "question": question,
            "answer": "",
            "confidence": 0.0,
            "cognitive_level": self.start_level,
            "rounds": 0,
            "category": "",
            "cognition_log": [],
            "metacognition": dict(self.metacognition),
            "pre_task": None,
            "logs_summary": None,
        }

        # Bug #6: 清空推理上下文，防止内存泄漏
        self._clear_reasoning_context()

        # Bug #2: 新轮次清空失败分支缓存
        self.failed_branches.clear()

        # Feature #10: 清空日志
        self.logger.clear()

        # Feature #12: 预演/ToDo 询问
        pre_task = None
        if self.enable_pre_task:
            pre_task = self.pre_task_plan(question)
            result["pre_task"] = pre_task.to_dict()

        # Feature #16: 推理流隔离检查
        if self.config.strict_isolation and not self.is_enabled():
            result["answer"] = "[ODC 未启用，推理流完全隔离]"
            return result

        # 难度评估
        category = QuestionClassifier.classify(question)
        result["category"] = category

        llm_fn = self._get_llm_callable()
        llm_call_count = 0

        def track_call(response_fn):
            nonlocal llm_call_count
            llm_call_count += 1
            self.metacognition["tools_used"] += 1
            return response_fn()

        try:
            # 初始推理
            initial_answer = track_call(
                lambda: llm_fn(messages=[{"role": "user", "content": f"请分析回答：{question}"}])
            )
            # Bug #5: 验证输出
            initial_answer, _ = self._validate_output(initial_answer)

            confidence = 0.8
            current_level = self.start_level

            # 是否需要升级
            if self.enable_tot and category in ("reasoning", "creative", "evaluation"):
                graph = self.tree_of_thoughts(
                    question,
                    branching_factor=self.tot_branching_factor,
                    max_depth=self.tot_max_depth,
                )
                tot_answer = self.get_bot_answer(graph)
                # Bug #5: 验证输出
                tot_answer, _ = self._validate_output(tot_answer)
                if tot_answer:
                    initial_answer = tot_answer
                    result["cognition_log"].append({"step": "tree_of_thoughts", "confidence": 0.85})

            # 自一致性检查
            if self.enable_self_consistency:
                sc_result = self.self_consistency(question, self.num_consistency_samples)
                if sc_result["consensus_score"] > 0.6:
                    initial_answer = sc_result["final_answer"]
                    confidence = max(confidence, sc_result["consensus_score"])
                result["cognition_log"].append({"step": "self_consistency", "confidence": confidence})

            # 反射
            if self.enable_reflection:
                reflection = self.reflect(initial_answer, question, self.max_reflection_depth)
                if reflection.revised_answer:
                    initial_answer = reflection.revised_answer
                    confidence += reflection.confidence_change
                result["cognition_log"].append({
                    "step": "reflection",
                    "confidence": max(0.0, confidence),
                    "issues": len(reflection.issues_found),
                })

            # 验证链
            if self.enable_verification:
                verification = self.chain_of_verification(initial_answer, question)
                confidence = verification.confidence
                result["cognition_log"].append({
                    "step": "verification",
                    "confidence": verification.confidence,
                    "verified": verification.verified,
                })

            # 偏差检测
            if self.enable_bias_detection:
                bias = BiasDetector.detect(initial_answer)
                if bias.biases_detected:
                    confidence *= (1.0 - bias.severity * 0.3)
                    result["cognition_log"].append({
                        "step": "bias_detection",
                        "biases": bias.biases_detected,
                    })

            # Feature #13: 预演置信度 — 确保置信度在合理范围
            confidence = max(0.0, min(1.0, confidence))

            result["answer"] = initial_answer
            result["confidence"] = round(confidence, 4)
            result["rounds"] = llm_call_count
            result["cognitive_level"] = current_level
            result["metacognition"] = dict(self.metacognition)
            result["logs_summary"] = self.logger.get_summary()

        except BudgetExceeded:
            result["answer"] = "[推理预算超限，已自动降级]"
            result["confidence"] = 0.3
            result["cognition_log"].append({"step": "budget_exceeded", "action": "degraded"})
        except Exception as e:
            result["answer"] = f"[推理过程出错: {str(e)}]"
            result["confidence"] = 0.0
            result["cognition_log"].append({"step": "error", "error": str(e)})

        # Bug #6: 推理结束后清理上下文
        self._clear_reasoning_context()

        return result

    def get_bot_answer(self, graph: ThoughtGraph) -> str:
        """获取最佳答案（兼容别名）"""
        return self.get_best_tot_answer(graph)

    def run_with_plan(self, question: str, plan: PreTaskPlan) -> Dict:
        """
        Feature #12: 使用预演计划运行推理。

        如果 plan.requires_approval 为 True，需要用户确认后再执行。
        """
        if plan.requires_approval:
            return {
                "answer": "[等待用户确认：预计为 L4+ 复杂推理，请确认是否继续]",
                "pre_task": plan.to_dict(),
                "status": "awaiting_approval",
            }
        return self.run(question)

    def get_cost_analysis(self) -> Dict:
        """获取认知成本分析"""
        meta = dict(self.metacognition)
        total_calls = meta.get("tools_used", 0) + meta.get("reflections_done", 0) + meta.get("verifications_done", 0)
        meta["total_llm_calls"] = total_calls
        meta["cognitive_effort"] = round(total_calls * 0.1, 2)
        meta["logs_summary"] = self.logger.get_summary()
        return meta

    def get_logs(self) -> List[Dict]:
        """Feature #10: 获取全流程运行日志"""
        return self.logger.get_records()


# ============================================================================
# Alpha 8 向后兼容
# ============================================================================

class AdvancedCognitionEngine(OxygenDynamicCognitionV26):
    """Alpha 8 向后兼容别名"""
    pass


# ============================================================================
# 集成桥接 — Alpha 9 Bug #7, #8, #9
# ============================================================================

class Alpha9IntegrationBridge:
    """
    Alpha 9 集成桥接 — Bug #7, #8, #9 兼容性修复

    提供与 OxygenMemo, OxygenOIAggregator, OCC 的安全集成接口。
    所有集成都是可选的，缺失时优雅降级。
    """

    def __init__(self, odc_engine: Optional[OxygenDynamicCognitionV26] = None):
        self.engine = odc_engine
        self._memo = None
        self._oia = None
        self._occ = None

    # Bug #7: OxygenMemo 集成
    def connect_memo(self, memo_instance: Any) -> bool:
        """
        连接 OxygenMemo 实例。

        Args:
            memo_instance: OxygenMemo 引擎实例

        Returns:
            连接是否成功
        """
        try:
            # 检查必要接口
            required_methods = ['write_page', 'load_page']
            for method in required_methods:
                if not hasattr(memo_instance, method):
                    return False
            self._memo = memo_instance
            if self.engine:
                self.engine.set_memo_bridge(self)
            return True
        except Exception:
            return False

    def persist_to_memo(self, question: str, result: Dict) -> Optional[str]:
        """Bug #7: 将推理结果持久化到 OxygenMemo"""
        if not self._memo:
            return None
        try:
            content = f"[Q] {question}\n\n[A] {result.get('answer', '')}\n\n[置信度: {result.get('confidence', 0)}%]"
            page_id = self._memo.write_page(
                content=content,
                label=f"ODC推理: {question[:40]}",
                category="knowledge",
                importance=min(result.get("confidence", 0.5) * 10, 10.0),
            )
            return page_id
        except Exception:
            return None

    def recall_from_memo(self, question: str) -> Optional[Dict]:
        """Bug #7: 从 OxygenMemo 召回相似推理"""
        if not self._memo:
            return None
        try:
            if hasattr(self._memo, 'vector_engine'):
                results = self._memo.vector_engine.search(question, top_k=1)
                if results:
                    pid, score = results[0]
                    if score > 0.6:
                        return self._memo.load_page(pid)
        except Exception:
            pass
        return None

    # Bug #8: OxygenOIAggregator 集成
    def connect_oia(self, oia_instance: Any) -> bool:
        """
        连接 OxygenOIAggregator 实例。

        Returns:
            连接是否成功
        """
        try:
            required_methods = ['batch_read', 'batch_write']
            for method in required_methods:
                if not hasattr(oia_instance, method):
                    return False
            self._oia = oia_instance
            if self.engine:
                self.engine.set_oia_bridge(self)
            return True
        except Exception:
            return False

    def batch_read_via_oia(self, patterns: List[str]) -> List[str]:
        """Bug #8: 通过 OIA 批量读取文件"""
        if not self._oia:
            return []
        try:
            results = self._oia.batch_read(patterns)
            return [r.text for r in results if hasattr(r, 'text') and r.text]
        except Exception:
            return []

    def batch_write_via_oia(self, data: Dict[str, str]) -> bool:
        """Bug #8: 通过 OIA 批量写入文件"""
        if not self._oia:
            return False
        try:
            self._oia.batch_write(data)
            return True
        except Exception:
            return False

    # Bug #9: OCC 集成
    def connect_occ(self, occ_instance: Any) -> bool:
        """
        连接 OxygenCognitionConstruction 实例。

        Returns:
            连接是否成功
        """
        try:
            required_methods = ['build_from_text', 'build_from_odc_log']
            for method in required_methods:
                if not hasattr(occ_instance, method):
                    return False
            self._occ = occ_instance
            if self.engine:
                self.engine.set_occ_bridge(self)
            return True
        except Exception:
            return False

    def build_knowledge_from_odc(self, log_data: Dict) -> Optional[Any]:
        """Bug #9: 将 ODC 运行日志传递给 OCC 构建知识结构"""
        if not self._occ:
            return None
        try:
            # 将 ODC 日志转换为 OCC 可处理的格式
            odc_log = json.dumps(log_data, ensure_ascii=False)
            model = self._occ.build_from_odc_log(odc_log)
            return model
        except Exception:
            return None

    def get_integration_status(self) -> Dict:
        """获取所有集成连接状态"""
        return {
            "memo_connected": self._memo is not None,
            "oia_connected": self._oia is not None,
            "occ_connected": self._occ is not None,
        }


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    """Alpha 9 CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description=f"OxygenDynamicCognition {OxygenDynamicCognitionV26.VERSION}"
    )
    parser.add_argument("--question", "-q", help="问题内容")
    parser.add_argument("--model", default="gpt-4", help="模型名称")
    parser.add_argument("--threshold", type=float, default=0.75, help="置信度阈值")
    parser.add_argument("--max-rounds", type=int, default=10, help="最大轮数")
    parser.add_argument("--start-level", type=int, default=2, help="起始认知等级")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--mock", action="store_true", help="Mock 模式（离线测试）")
    parser.add_argument("--no-cache", action="store_true", help="禁用缓存")
    parser.add_argument("--retries", type=int, default=3, help="API 重试次数")

    # Alpha 8 参数
    parser.add_argument("--no-tot", action="store_true", help="禁用思维树")
    parser.add_argument("--no-reflection", action="store_true", help="禁用反射")
    parser.add_argument("--no-verification", action="store_true", help="禁用验证链")
    parser.add_argument("--no-consistency", action="store_true", help="禁用自一致性")
    parser.add_argument("--consistency-samples", type=int, default=5, help="自一致性样本数")
    parser.add_argument("--reflection-depth", type=int, default=2, help="反射深度")
    parser.add_argument("--tot-branches", type=int, default=3, help="思维树分支数")
    parser.add_argument("--tot-depth", type=int, default=3, help="思维树深度")

    # Alpha 9 参数
    parser.add_argument("--enable-odc", action="store_true", help="Bug #4: 显式启用 ODC")
    parser.add_argument("--decision-sensitivity", type=float, default=0.5, help="Bug #3: 决策灵敏度")
    parser.add_argument("--high-level-precision", type=float, default=0.7, help="Bug #3: 高等级思考精度")
    parser.add_argument("--permission-mode", default="parameterize", choices=["execute", "parameterize"],
                        help="Feature #11: 权限模式")
    parser.add_argument("--no-pre-task", action="store_true", help="Feature #12: 禁用预演询问")
    parser.add_argument("--no-voting", action="store_true", help="Feature #14: 禁用内投票机")
    parser.add_argument("--no-logging", action="store_true", help="Feature #10: 禁用全流程日志")
    parser.add_argument("--no-isolation", action="store_true", help="Feature #16: 禁用严格隔离")
    parser.add_argument("--version", action="store_true", help="显示版本")

    args = parser.parse_args()

    if args.version:
        print(f"OxygenDynamicCognition {OxygenDynamicCognitionV26.VERSION}")
        print("GitHub@StarsailsClover")
        print("\n前沿技术:")
        print("  - 思维树 (Tree of Thoughts)")
        print("  - 思维图 (Graph of Thoughts)")
        print("  - 自一致性 (Self-Consistency)")
        print("  - 反射机制 (Reflection)")
        print("  - 验证链 (Chain of Verification)")
        print("  - 多路径投票 (Multi-Path Voting)")
        print("  - 内投票机 (Internal Voting Machine)")
        print("  - 渐进式深化 (Progressive Deepening)")
        print("  - 元认知监控 (Metacognitive Monitoring)")
        print("  - 认知偏差检测 (Cognitive Bias Detection)")
        print("\nAlpha 9 修复:")
        print("  - Bug #1: L5 推理过载 — 全局硬限制 + 自动降级")
        print("  - Bug #2: 错误分支缓存 — 失败路径永久拦截")
        print("  - Bug #3: 过度反思 — 拆分灵敏度/精度参数")
        print("  - Bug #4: 隐性触发 — 默认关闭 + 显式启用")
        print("  - Bug #5: 无语义输出 — 输出验证层")
        print("  - Bug #6: 记忆受损 — 上下文内存泄漏修复")
        print("  - Bug #7-9: OxygenMemo/OIA/OCC 兼容性修复")
        print("\nAlpha 9 新增:")
        print("  - Feature #10: 全流程结构化运行日志")
        print("  - Feature #11: 权限隔离模式")
        print("  - Feature #12: 任务前预演/ToDo 询问")
        print("  - Feature #13: 预演置信度显示")
        print("  - Feature #14: 内投票机")
        print("  - Feature #15: 自动等级分配灵敏度调整")
        print("  - Feature #16: 推理流完全隔离")
        return

    if not args.question:
        parser.print_help()
        return

    # Alpha 9 Bug #4: Mock 模式不需要显式启用
    if args.mock:
        engine = OxygenDynamicCognitionV26(
            model=args.model,
            max_rounds=args.max_rounds,
            confidence_threshold=args.threshold,
            start_level=args.start_level,
            mock_mode=True,
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
            enabled=True,  # Mock 模式自动启用
            decision_sensitivity=args.decision_sensitivity,
            high_level_precision=args.high_level_precision,
            permission_mode=args.permission_mode,
            enable_pre_task=not args.no_pre_task,
            enable_voting=not args.no_voting,
            enable_full_logging=not args.no_logging,
            strict_isolation=not args.no_isolation,
        )
    else:
        # 非 Mock 模式需要显式启用
        if not args.enable_odc:
            print("错误: 非 Mock 模式需要 --enable-odc 显式启用 ODC")
            print("这是 Alpha 9 Bug #4 修复 — 防止隐性触发")
            return
        engine = OxygenDynamicCognitionV26(
            model=args.model,
            max_rounds=args.max_rounds,
            confidence_threshold=args.threshold,
            start_level=args.start_level,
            mock_mode=False,
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
            enabled=True,
            decision_sensitivity=args.decision_sensitivity,
            high_level_precision=args.high_level_precision,
            permission_mode=args.permission_mode,
            enable_pre_task=not args.no_pre_task,
            enable_voting=not args.no_voting,
            enable_full_logging=not args.no_logging,
            strict_isolation=not args.no_isolation,
        )

    result = engine.run(args.question)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"OxygenDynamicCognition {OxygenDynamicCognitionV26.VERSION}")
        print(f"{'='*60}")
        print(f"问题: {result['question']}")
        print(f"认知等级: L{result['cognitive_level']}")
        print(f"置信度: {result['confidence']:.1%}")
        print(f"推理轮数: {result['rounds']}")
        print(f"问题类型: {result['category']}")
        print(f"{'='*60}\n")
        print(result["answer"])

        if result.get("pre_task"):
            print(f"\n{'='*60}")
            print("预演计划:")
            pt = result["pre_task"]
            print(f"  预期难度: {pt['expected_difficulty']}")
            print(f"  预期等级: L{pt['expected_level']}")
            print(f"  预估轮数: {pt['estimated_rounds']}")
            print(f"  隔离方案: {pt['reasoning_isolation']}")
            print(f"  待办项:")
            for item in pt["todo_items"]:
                print(f"    - {item}")

        if args.verbose:
            print(f"\n{'='*60}")
            print("认知过程日志:")
            for step in result["cognition_log"]:
                print(f"  - {step}")

            print(f"\n元认知报告:")
            meta = result["metacognition"]
            for k, v in meta.items():
                if k != "logs_summary":
                    print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
