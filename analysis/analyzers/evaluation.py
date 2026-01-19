"""综合评估与行动计划分析器 - Sheet 10: 综合评估行动计划"""
from typing import Dict, Any, List
from dataclasses import dataclass

from .basic_info import BasicInfoResult
from .account_position import AccountPositionResult
from .topic_analysis import TopicAnalysisResult
from .content_format import ContentFormatResult
from .copywriting import CopywritingResult
from .operations import OperationsResult
from .viral_notes import ViralNotesResult

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.analysis_config import EVALUATION_CONFIG


@dataclass
class EvaluationResult:
    """综合评估结果"""
    strengths: List[str]  # 优势
    weaknesses: List[str]  # 待改进
    action_items: List[str]  # 行动建议
    overall_score: float  # 综合评分 (0-100)
    dimension_scores: Dict[str, float]  # 各维度评分

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "action_items": self.action_items,
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
        }


class EvaluationAnalyzer:
    """综合评估分析器"""

    def __init__(self):
        self.config = EVALUATION_CONFIG

    def _evaluate_engagement(self, basic_info: BasicInfoResult) -> tuple:
        """评估互动表现"""
        score = 0
        strengths = []
        weaknesses = []
        actions = []

        # 评估赞粉比
        ratio = basic_info.like_fan_ratio
        if ratio >= self.config["like_fan_ratio"]["excellent"]:
            score += 30
            strengths.append(f"赞粉比优秀 ({ratio:.2f})，粉丝质量高")
        elif ratio >= self.config["like_fan_ratio"]["good"]:
            score += 20
            strengths.append(f"赞粉比良好 ({ratio:.2f})")
        elif ratio >= self.config["like_fan_ratio"]["average"]:
            score += 10
            weaknesses.append(f"赞粉比一般 ({ratio:.2f})，可提高内容质量")
        else:
            weaknesses.append(f"赞粉比较低 ({ratio:.2f})，需提升内容吸引力")
            actions.append("优化内容质量，提高互动率")

        # 评估互动率
        engagement = basic_info.engagement_rate
        if engagement >= self.config["engagement_rate"]["excellent"] * 100:
            score += 20
            strengths.append(f"互动率高 ({engagement:.1f}%)")
        elif engagement >= self.config["engagement_rate"]["good"] * 100:
            score += 15
        elif engagement >= self.config["engagement_rate"]["average"] * 100:
            score += 10
        else:
            weaknesses.append(f"互动率偏低 ({engagement:.1f}%)")
            actions.append("增加互动引导，如提问、征集意见等")

        return score, strengths, weaknesses, actions

    def _evaluate_operations(self, operations: OperationsResult) -> tuple:
        """评估运营策略"""
        score = 0
        strengths = []
        weaknesses = []
        actions = []

        # 评估更新频率
        freq = operations.update_frequency
        if freq >= self.config["update_frequency"]["high"]:
            score += 20
            strengths.append(f"更新频率高 ({freq:.1f}篇/周)")
        elif freq >= self.config["update_frequency"]["medium"]:
            score += 15
            strengths.append(f"更新频率适中 ({freq:.1f}篇/周)")
        else:
            score += 5
            weaknesses.append(f"更新频率较低 ({freq:.1f}篇/周)")
            actions.append("建议提高更新频率至每周3-5篇")

        # 评估一致性
        consistency = operations.consistency_score
        if consistency >= 70:
            score += 15
            strengths.append("发布节奏稳定，用户粘性好")
        elif consistency >= 50:
            score += 10
        else:
            weaknesses.append("发布节奏不稳定")
            actions.append("制定固定的发布计划，保持更新节奏")

        return score, strengths, weaknesses, actions

    def _evaluate_content(self, topic: TopicAnalysisResult, copywriting: CopywritingResult) -> tuple:
        """评估内容质量"""
        score = 0
        strengths = []
        weaknesses = []
        actions = []

        # 评估标签使用
        if len(topic.top_tags) >= 5:
            score += 10
            strengths.append("标签使用丰富，利于被发现")
        else:
            weaknesses.append("标签使用较少")
            actions.append("增加相关标签，每篇笔记使用3-5个标签")

        # 评估标题技巧
        total = copywriting.total_notes
        if total > 0:
            number_ratio = copywriting.number_title_count / total * 100
            question_ratio = copywriting.question_title_count / total * 100

            if number_ratio >= 30 or question_ratio >= 20:
                score += 15
                strengths.append("标题技巧运用得当")
            else:
                actions.append("尝试使用数字型或问句型标题，提高点击率")

        # 评估钩子词使用
        if len(copywriting.hook_words) >= 5:
            score += 10
            strengths.append("善用钩子词吸引用户")
        else:
            actions.append("学习使用钩子词，如'必看'、'干货'、'宝藏'等")

        return score, strengths, weaknesses, actions

    def _evaluate_viral_potential(self, viral: ViralNotesResult) -> tuple:
        """评估爆款潜力"""
        score = 0
        strengths = []
        weaknesses = []
        actions = []

        if viral.avg_viral_likes >= 1000:
            score += 15
            strengths.append(f"已有高互动笔记 (TOP10平均点赞 {viral.avg_viral_likes:.0f})")
        elif viral.avg_viral_likes >= 500:
            score += 10
            strengths.append("具备一定的爆款能力")
        else:
            weaknesses.append("暂无高互动笔记")
            actions.append("分析竞品爆款，学习爆款特征")

        # 根据爆款特征给建议
        features = viral.viral_common_features
        if features:
            if features.get("has_number_ratio", 0) >= 50:
                strengths.append("爆款标题善用数字")
            if features.get("video_ratio", 0) >= 60:
                strengths.append("视频内容更容易获得高互动")
            elif features.get("video_ratio", 0) <= 40:
                strengths.append("图文内容更容易获得高互动")

        return score, strengths, weaknesses, actions

    def analyze(
        self,
        basic_info: BasicInfoResult,
        account_position: AccountPositionResult,
        topic: TopicAnalysisResult,
        content_format: ContentFormatResult,
        copywriting: CopywritingResult,
        operations: OperationsResult,
        viral: ViralNotesResult,
    ) -> EvaluationResult:
        """综合评估

        Args:
            各分析器的结果

        Returns:
            EvaluationResult
        """
        all_strengths = []
        all_weaknesses = []
        all_actions = []
        dimension_scores = {}

        # 评估各维度
        score1, s1, w1, a1 = self._evaluate_engagement(basic_info)
        dimension_scores["互动表现"] = score1
        all_strengths.extend(s1)
        all_weaknesses.extend(w1)
        all_actions.extend(a1)

        score2, s2, w2, a2 = self._evaluate_operations(operations)
        dimension_scores["运营策略"] = score2
        all_strengths.extend(s2)
        all_weaknesses.extend(w2)
        all_actions.extend(a2)

        score3, s3, w3, a3 = self._evaluate_content(topic, copywriting)
        dimension_scores["内容质量"] = score3
        all_strengths.extend(s3)
        all_weaknesses.extend(w3)
        all_actions.extend(a3)

        score4, s4, w4, a4 = self._evaluate_viral_potential(viral)
        dimension_scores["爆款潜力"] = score4
        all_strengths.extend(s4)
        all_weaknesses.extend(w4)
        all_actions.extend(a4)

        # 计算综合评分
        overall_score = sum(dimension_scores.values())

        # 添加通用建议
        if account_position.content_themes:
            all_strengths.insert(0, f"内容定位清晰: {', '.join(account_position.content_themes[:3])}")

        if operations.best_publish_hours:
            hours_str = ", ".join([f"{h}:00" for h in operations.best_publish_hours[:3]])
            all_actions.append(f"建议发布时间: {hours_str}")

        return EvaluationResult(
            strengths=all_strengths[:10],  # 最多10条
            weaknesses=all_weaknesses[:5],  # 最多5条
            action_items=all_actions[:8],  # 最多8条
            overall_score=overall_score,
            dimension_scores=dimension_scores,
        )
