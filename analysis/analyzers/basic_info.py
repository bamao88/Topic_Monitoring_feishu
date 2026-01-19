"""基础信息分析器 - Sheet 1: 基础信息汇总"""
from typing import Dict, Any, List
from dataclasses import dataclass

from ..data_fetcher import BloggerAnalysisData


@dataclass
class BasicInfoResult:
    """基础信息分析结果"""
    blogger_id: str
    nickname: str
    avatar: str
    fans_count: int
    notes_count: int
    liked_count: int
    collected_count: int
    comment_count: int
    share_count: int
    like_fan_ratio: float  # 赞粉比
    avg_likes_per_note: float  # 平均每篇点赞
    avg_interactions_per_note: float  # 平均每篇互动
    engagement_rate: float  # 互动率 (总互动/粉丝数)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blogger_id": self.blogger_id,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "fans_count": self.fans_count,
            "notes_count": self.notes_count,
            "liked_count": self.liked_count,
            "collected_count": self.collected_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "like_fan_ratio": self.like_fan_ratio,
            "avg_likes_per_note": self.avg_likes_per_note,
            "avg_interactions_per_note": self.avg_interactions_per_note,
            "engagement_rate": self.engagement_rate,
        }


class BasicInfoAnalyzer:
    """基础信息分析器"""

    def analyze(self, data: BloggerAnalysisData) -> BasicInfoResult:
        """分析博主基础信息

        Args:
            data: 博主分析数据

        Returns:
            BasicInfoResult
        """
        blogger = data.blogger
        notes = data.notes

        # 计算笔记汇总数据
        total_liked = sum(n.liked_count for n in notes)
        total_collected = sum(n.collected_count for n in notes)
        total_comments = sum(n.comment_count for n in notes)
        total_shares = sum(n.share_count for n in notes)
        total_interactions = total_liked + total_collected + total_comments + total_shares

        # 计算比率
        notes_count = len(notes) if notes else blogger.notes_count
        fans_count = blogger.fans_count or 1  # 避免除零

        like_fan_ratio = blogger.liked_count / fans_count if fans_count > 0 else 0
        avg_likes = total_liked / notes_count if notes_count > 0 else 0
        avg_interactions = total_interactions / notes_count if notes_count > 0 else 0
        engagement_rate = (total_interactions / fans_count * 100) if fans_count > 0 else 0

        return BasicInfoResult(
            blogger_id=blogger.blogger_id,
            nickname=blogger.nickname,
            avatar=blogger.avatar,
            fans_count=blogger.fans_count,
            notes_count=notes_count,
            liked_count=blogger.liked_count,
            collected_count=total_collected,
            comment_count=total_comments,
            share_count=total_shares,
            like_fan_ratio=round(like_fan_ratio, 2),
            avg_likes_per_note=round(avg_likes, 1),
            avg_interactions_per_note=round(avg_interactions, 1),
            engagement_rate=round(engagement_rate, 2),
        )
