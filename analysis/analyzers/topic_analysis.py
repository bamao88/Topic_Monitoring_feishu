"""选题拆解分析器 - Sheet 4: 选题拆解"""
import re
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from collections import Counter

from ..data_fetcher import BloggerAnalysisData


@dataclass
class TopicAnalysisResult:
    """选题分析结果"""
    total_notes: int
    image_count: int  # 图文数量
    video_count: int  # 视频数量
    image_ratio: float  # 图文占比
    video_ratio: float  # 视频占比
    top_tags: List[Tuple[str, int]]  # TOP标签及出现次数
    top_keywords: List[Tuple[str, int]]  # TOP关键词及出现次数
    title_keywords: List[Tuple[str, int]]  # 标题高频词

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_notes": self.total_notes,
            "image_count": self.image_count,
            "video_count": self.video_count,
            "image_ratio": self.image_ratio,
            "video_ratio": self.video_ratio,
            "top_tags": self.top_tags,
            "top_keywords": self.top_keywords,
            "title_keywords": self.title_keywords,
        }


class TopicAnalyzer:
    """选题分析器"""

    def __init__(self):
        # 停用词列表
        self.stopwords = {
            "的", "了", "是", "在", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这", "那",
            "啊", "吧", "呢", "吗", "哦", "嘛", "呀", "哈", "啦",
        }

    def _count_content_types(self, notes) -> Tuple[int, int]:
        """统计内容类型"""
        video_count = 0
        image_count = 0
        for note in notes:
            if note.type in ("视频", "video"):
                video_count += 1
            else:
                image_count += 1
        return image_count, video_count

    def _extract_tags(self, notes) -> Counter:
        """提取并统计所有标签"""
        tag_counter = Counter()
        for note in notes:
            if note.tags:
                # 分割标签
                tags = re.split(r'[,，\s#]+', note.tags)
                for tag in tags:
                    tag = tag.strip()
                    if tag and len(tag) >= 2:
                        tag_counter[tag] += 1
        return tag_counter

    def _extract_keywords(self, texts: List[str], top_n: int = 10) -> List[Tuple[str, int]]:
        """从文本列表中提取关键词"""
        word_counter = Counter()

        for text in texts:
            if not text:
                continue
            # 简单分词：提取中文词汇（2-6个字）
            chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
            for word in chinese_words:
                if word not in self.stopwords:
                    word_counter[word] += 1

            # 提取英文词汇
            english_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
            for word in english_words:
                word_counter[word] += 1

        return word_counter.most_common(top_n)

    def analyze(self, data: BloggerAnalysisData) -> TopicAnalysisResult:
        """分析选题内容

        Args:
            data: 博主分析数据

        Returns:
            TopicAnalysisResult
        """
        notes = data.notes
        total_notes = len(notes)

        if total_notes == 0:
            return TopicAnalysisResult(
                total_notes=0,
                image_count=0,
                video_count=0,
                image_ratio=0,
                video_ratio=0,
                top_tags=[],
                top_keywords=[],
                title_keywords=[],
            )

        # 统计内容类型
        image_count, video_count = self._count_content_types(notes)
        image_ratio = round(image_count / total_notes * 100, 1)
        video_ratio = round(video_count / total_notes * 100, 1)

        # 提取标签
        tag_counter = self._extract_tags(notes)
        top_tags = tag_counter.most_common(10)

        # 提取正文关键词
        desc_texts = [n.desc for n in notes]
        top_keywords = self._extract_keywords(desc_texts, 15)

        # 提取标题关键词
        title_texts = [n.title for n in notes]
        title_keywords = self._extract_keywords(title_texts, 10)

        return TopicAnalysisResult(
            total_notes=total_notes,
            image_count=image_count,
            video_count=video_count,
            image_ratio=image_ratio,
            video_ratio=video_ratio,
            top_tags=top_tags,
            top_keywords=top_keywords,
            title_keywords=title_keywords,
        )
