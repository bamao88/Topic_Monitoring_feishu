"""文案结构拆解分析器 - Sheet 6: 文案结构拆解"""
import re
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from collections import Counter

from ..data_fetcher import BloggerAnalysisData

# 从配置导入
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.analysis_config import TITLE_ANALYSIS_CONFIG


@dataclass
class CopywritingResult:
    """文案分析结果"""
    total_notes: int
    avg_title_length: float  # 平均标题长度
    title_patterns: Dict[str, int]  # 标题模式统计
    number_title_count: int  # 数字型标题数量
    question_title_count: int  # 问句型标题数量
    emoji_title_count: int  # 含emoji标题数量
    hook_words: List[Tuple[str, int]]  # 常用钩子词
    opening_hooks: List[str]  # 开头钩子示例
    avg_desc_length: float  # 平均正文长度
    emoji_usage_rate: float  # emoji使用率

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_notes": self.total_notes,
            "avg_title_length": self.avg_title_length,
            "title_patterns": self.title_patterns,
            "number_title_count": self.number_title_count,
            "question_title_count": self.question_title_count,
            "emoji_title_count": self.emoji_title_count,
            "hook_words": self.hook_words,
            "opening_hooks": self.opening_hooks,
            "avg_desc_length": self.avg_desc_length,
            "emoji_usage_rate": self.emoji_usage_rate,
        }


class CopywritingAnalyzer:
    """文案分析器"""

    def __init__(self):
        self.number_patterns = TITLE_ANALYSIS_CONFIG["number_patterns"]
        self.question_patterns = TITLE_ANALYSIS_CONFIG["question_patterns"]
        self.hook_words = TITLE_ANALYSIS_CONFIG["hook_words"]

    def _has_number_pattern(self, title: str) -> bool:
        """检查标题是否包含数字模式"""
        for pattern in self.number_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return True
        return False

    def _has_question_pattern(self, title: str) -> bool:
        """检查标题是否是问句"""
        for pattern in self.question_patterns:
            if re.search(pattern, title):
                return True
        return False

    def _has_emoji(self, text: str) -> bool:
        """检查文本是否包含 emoji"""
        # emoji 范围的正则
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+"
        )
        return bool(emoji_pattern.search(text))

    def _count_emojis(self, text: str) -> int:
        """统计 emoji 数量"""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]"
        )
        return len(emoji_pattern.findall(text))

    def _extract_hook_words(self, notes) -> List[Tuple[str, int]]:
        """提取钩子词使用情况"""
        hook_counter = Counter()
        for note in notes:
            text = f"{note.title} {note.desc}".lower()
            for hook in self.hook_words:
                if hook in text:
                    hook_counter[hook] += 1
        return hook_counter.most_common(15)

    def _extract_opening_hooks(self, notes) -> List[str]:
        """提取开头钩子示例"""
        openings = []
        for note in notes:
            if note.desc:
                # 取前50个字符作为开头
                opening = note.desc[:50].strip()
                if opening:
                    openings.append(opening)
        # 返回前5个示例
        return openings[:5]

    def _analyze_title_patterns(self, notes) -> Dict[str, int]:
        """分析标题模式"""
        patterns = {
            "数字型": 0,
            "问句型": 0,
            "感叹型": 0,
            "陈述型": 0,
        }
        for note in notes:
            title = note.title
            if self._has_number_pattern(title):
                patterns["数字型"] += 1
            elif self._has_question_pattern(title):
                patterns["问句型"] += 1
            elif "!" in title or "！" in title:
                patterns["感叹型"] += 1
            else:
                patterns["陈述型"] += 1
        return patterns

    def analyze(self, data: BloggerAnalysisData) -> CopywritingResult:
        """分析文案结构

        Args:
            data: 博主分析数据

        Returns:
            CopywritingResult
        """
        notes = data.notes
        total_notes = len(notes)

        if total_notes == 0:
            return CopywritingResult(
                total_notes=0,
                avg_title_length=0,
                title_patterns={},
                number_title_count=0,
                question_title_count=0,
                emoji_title_count=0,
                hook_words=[],
                opening_hooks=[],
                avg_desc_length=0,
                emoji_usage_rate=0,
            )

        # 分析标题
        total_title_length = sum(len(n.title) for n in notes)
        avg_title_length = round(total_title_length / total_notes, 1)

        # 标题模式分析
        title_patterns = self._analyze_title_patterns(notes)
        number_title_count = sum(1 for n in notes if self._has_number_pattern(n.title))
        question_title_count = sum(1 for n in notes if self._has_question_pattern(n.title))
        emoji_title_count = sum(1 for n in notes if self._has_emoji(n.title))

        # 钩子词分析
        hook_words = self._extract_hook_words(notes)

        # 开头钩子
        opening_hooks = self._extract_opening_hooks(notes)

        # 正文分析
        total_desc_length = sum(len(n.desc) for n in notes)
        avg_desc_length = round(total_desc_length / total_notes, 1)

        # emoji 使用率
        emoji_notes_count = sum(1 for n in notes if self._has_emoji(n.title) or self._has_emoji(n.desc))
        emoji_usage_rate = round(emoji_notes_count / total_notes * 100, 1)

        return CopywritingResult(
            total_notes=total_notes,
            avg_title_length=avg_title_length,
            title_patterns=title_patterns,
            number_title_count=number_title_count,
            question_title_count=question_title_count,
            emoji_title_count=emoji_title_count,
            hook_words=hook_words,
            opening_hooks=opening_hooks,
            avg_desc_length=avg_desc_length,
            emoji_usage_rate=emoji_usage_rate,
        )
