"""爆款笔记拆解分析器 - Sheet 9: 爆款笔记拆解"""
import re
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from collections import Counter

from ..data_fetcher import BloggerAnalysisData, NoteInfo

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.analysis_config import VIRAL_NOTES_CONFIG


@dataclass
class ViralNoteDetail:
    """爆款笔记详情"""
    rank: int
    note_id: str
    title: str
    type: str
    liked_count: int
    collected_count: int
    comment_count: int
    share_count: int
    total_interactions: int
    note_url: str
    tags: str
    cover_url: str = ""  # 封面图片
    desc: str = ""  # 正文内容

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "note_id": self.note_id,
            "title": self.title,
            "type": self.type,
            "liked_count": self.liked_count,
            "collected_count": self.collected_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "total_interactions": self.total_interactions,
            "note_url": self.note_url,
            "tags": self.tags,
            "cover_url": self.cover_url,
            "desc": self.desc,
        }


@dataclass
class ViralNotesResult:
    """爆款笔记分析结果"""
    total_notes: int
    top_notes: List[ViralNoteDetail]  # TOP N 笔记
    viral_common_features: Dict[str, Any]  # 爆款共同特征
    avg_viral_likes: float  # 爆款平均点赞
    avg_viral_interactions: float  # 爆款平均互动
    viral_content_type: str  # 爆款内容类型偏好
    viral_tags: List[Tuple[str, int]]  # 爆款标签

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_notes": self.total_notes,
            "top_notes": [n.to_dict() for n in self.top_notes],
            "viral_common_features": self.viral_common_features,
            "avg_viral_likes": self.avg_viral_likes,
            "avg_viral_interactions": self.avg_viral_interactions,
            "viral_content_type": self.viral_content_type,
            "viral_tags": self.viral_tags,
        }


class ViralNotesAnalyzer:
    """爆款笔记分析器"""

    def __init__(self):
        self.top_count = VIRAL_NOTES_CONFIG["top_count"]

    def _get_top_notes(self, notes: List[NoteInfo]) -> List[ViralNoteDetail]:
        """获取 TOP N 高互动笔记"""
        # 按总互动数排序
        sorted_notes = sorted(notes, key=lambda x: x.total_interactions, reverse=True)

        top_notes = []
        for i, note in enumerate(sorted_notes[:self.top_count], 1):
            detail = ViralNoteDetail(
                rank=i,
                note_id=note.note_id,
                title=note.title,
                type=note.type,
                liked_count=note.liked_count,
                collected_count=note.collected_count,
                comment_count=note.comment_count,
                share_count=note.share_count,
                total_interactions=note.total_interactions,
                note_url=note.note_url or f"https://www.xiaohongshu.com/explore/{note.note_id}",
                tags=note.tags,
                cover_url=note.cover_url,
                desc=note.desc,
            )
            top_notes.append(detail)

        return top_notes

    def _analyze_common_features(self, top_notes: List[NoteInfo]) -> Dict[str, Any]:
        """分析爆款笔记的共同特征"""
        if not top_notes:
            return {}

        features = {
            "avg_title_length": 0,
            "has_number_ratio": 0,
            "has_question_ratio": 0,
            "has_emoji_ratio": 0,
            "video_ratio": 0,
            "common_keywords": [],
        }

        # 分析标题
        number_pattern = r'\d+'
        question_pattern = r'[?？如何怎么为什么]'
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "]"
        )

        title_lengths = []
        has_number = 0
        has_question = 0
        has_emoji = 0
        video_count = 0

        for note in top_notes:
            title_lengths.append(len(note.title))
            if re.search(number_pattern, note.title):
                has_number += 1
            if re.search(question_pattern, note.title):
                has_question += 1
            if emoji_pattern.search(note.title):
                has_emoji += 1
            if note.type in ("视频", "video"):
                video_count += 1

        n = len(top_notes)
        features["avg_title_length"] = round(sum(title_lengths) / n, 1)
        features["has_number_ratio"] = round(has_number / n * 100, 1)
        features["has_question_ratio"] = round(has_question / n * 100, 1)
        features["has_emoji_ratio"] = round(has_emoji / n * 100, 1)
        features["video_ratio"] = round(video_count / n * 100, 1)

        # 提取共同关键词
        all_text = " ".join([f"{note.title} {note.tags}" for note in top_notes])
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}', all_text)
        word_counter = Counter(words)
        features["common_keywords"] = [w for w, _ in word_counter.most_common(10)]

        return features

    def _analyze_viral_tags(self, top_notes: List[NoteInfo]) -> List[Tuple[str, int]]:
        """分析爆款笔记标签"""
        tag_counter = Counter()
        for note in top_notes:
            if note.tags:
                tags = re.split(r'[,，\s#]+', note.tags)
                for tag in tags:
                    tag = tag.strip()
                    if tag and len(tag) >= 2:
                        tag_counter[tag] += 1
        return tag_counter.most_common(10)

    def _determine_viral_content_type(self, top_notes: List[NoteInfo]) -> str:
        """判断爆款内容类型偏好"""
        if not top_notes:
            return "未知"

        video_count = sum(1 for n in top_notes if n.type in ("视频", "video"))
        image_count = len(top_notes) - video_count

        if video_count > image_count:
            return "视频型"
        elif image_count > video_count:
            return "图文型"
        else:
            return "混合型"

    def analyze(self, data: BloggerAnalysisData) -> ViralNotesResult:
        """分析爆款笔记

        Args:
            data: 博主分析数据

        Returns:
            ViralNotesResult
        """
        notes = data.notes
        total_notes = len(notes)

        if total_notes == 0:
            return ViralNotesResult(
                total_notes=0,
                top_notes=[],
                viral_common_features={},
                avg_viral_likes=0,
                avg_viral_interactions=0,
                viral_content_type="未知",
                viral_tags=[],
            )

        # 获取 TOP 笔记
        top_notes_detail = self._get_top_notes(notes)

        # 获取用于分析的原始笔记数据
        sorted_notes = sorted(notes, key=lambda x: x.total_interactions, reverse=True)
        top_notes_raw = sorted_notes[:self.top_count]

        # 分析共同特征
        common_features = self._analyze_common_features(top_notes_raw)

        # 计算爆款平均数据
        avg_likes = sum(n.liked_count for n in top_notes_raw) / len(top_notes_raw) if top_notes_raw else 0
        avg_interactions = sum(n.total_interactions for n in top_notes_raw) / len(top_notes_raw) if top_notes_raw else 0

        # 分析爆款内容类型
        viral_content_type = self._determine_viral_content_type(top_notes_raw)

        # 分析爆款标签
        viral_tags = self._analyze_viral_tags(top_notes_raw)

        return ViralNotesResult(
            total_notes=total_notes,
            top_notes=top_notes_detail,
            viral_common_features=common_features,
            avg_viral_likes=round(avg_likes, 1),
            avg_viral_interactions=round(avg_interactions, 1),
            viral_content_type=viral_content_type,
            viral_tags=viral_tags,
        )
