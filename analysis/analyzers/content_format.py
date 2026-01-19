"""内容形式拆解分析器 - Sheet 5: 内容形式拆解"""
import re
from typing import Dict, Any, List
from dataclasses import dataclass
from collections import Counter

from ..data_fetcher import BloggerAnalysisData


@dataclass
class ContentFormatResult:
    """内容形式分析结果"""
    total_notes: int
    image_notes_count: int  # 图文笔记数
    video_notes_count: int  # 视频笔记数
    image_ratio: float  # 图文占比
    video_ratio: float  # 视频占比
    avg_desc_length: float  # 平均正文长度
    avg_title_length: float  # 平均标题长度
    has_cover_count: int  # 有封面的笔记数
    cover_ratio: float  # 封面覆盖率

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_notes": self.total_notes,
            "image_notes_count": self.image_notes_count,
            "video_notes_count": self.video_notes_count,
            "image_ratio": self.image_ratio,
            "video_ratio": self.video_ratio,
            "avg_desc_length": self.avg_desc_length,
            "avg_title_length": self.avg_title_length,
            "has_cover_count": self.has_cover_count,
            "cover_ratio": self.cover_ratio,
        }


class ContentFormatAnalyzer:
    """内容形式分析器"""

    def analyze(self, data: BloggerAnalysisData) -> ContentFormatResult:
        """分析内容形式

        Args:
            data: 博主分析数据

        Returns:
            ContentFormatResult
        """
        notes = data.notes
        total_notes = len(notes)

        if total_notes == 0:
            return ContentFormatResult(
                total_notes=0,
                image_notes_count=0,
                video_notes_count=0,
                image_ratio=0,
                video_ratio=0,
                avg_desc_length=0,
                avg_title_length=0,
                has_cover_count=0,
                cover_ratio=0,
            )

        # 统计内容类型
        video_count = 0
        image_count = 0
        for note in notes:
            if note.type in ("视频", "video"):
                video_count += 1
            else:
                image_count += 1

        image_ratio = round(image_count / total_notes * 100, 1)
        video_ratio = round(video_count / total_notes * 100, 1)

        # 计算平均长度
        total_desc_length = sum(len(n.desc) for n in notes)
        total_title_length = sum(len(n.title) for n in notes)
        avg_desc_length = round(total_desc_length / total_notes, 1)
        avg_title_length = round(total_title_length / total_notes, 1)

        # 统计封面
        has_cover_count = sum(1 for n in notes if n.cover_url)
        cover_ratio = round(has_cover_count / total_notes * 100, 1)

        return ContentFormatResult(
            total_notes=total_notes,
            image_notes_count=image_count,
            video_notes_count=video_count,
            image_ratio=image_ratio,
            video_ratio=video_ratio,
            avg_desc_length=avg_desc_length,
            avg_title_length=avg_title_length,
            has_cover_count=has_cover_count,
            cover_ratio=cover_ratio,
        )
