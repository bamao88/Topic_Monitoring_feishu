"""账号定位分析器 - Sheet 2: 账号定位分析"""
import re
from typing import Dict, Any, List
from dataclasses import dataclass, field
from collections import Counter

from ..data_fetcher import BloggerAnalysisData


@dataclass
class AccountPositionResult:
    """账号定位分析结果"""
    nickname: str
    nickname_keywords: List[str]  # 昵称关键词
    desc: str  # 简介内容
    desc_keywords: List[str]  # 简介关键词
    main_tags: List[str]  # 主要标签
    content_style: str  # 内容风格: 图文型/视频型/混合型
    video_ratio: float  # 视频占比
    image_ratio: float  # 图文占比
    content_themes: List[str]  # 内容主题

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nickname": self.nickname,
            "nickname_keywords": self.nickname_keywords,
            "desc": self.desc,
            "desc_keywords": self.desc_keywords,
            "main_tags": self.main_tags,
            "content_style": self.content_style,
            "video_ratio": self.video_ratio,
            "image_ratio": self.image_ratio,
            "content_themes": self.content_themes,
        }


class AccountPositionAnalyzer:
    """账号定位分析器"""

    def __init__(self):
        # 常见领域关键词
        self.domain_keywords = {
            "美妆": ["护肤", "化妆", "美妆", "口红", "眼影", "粉底", "防晒", "面膜", "精华", "美白"],
            "穿搭": ["穿搭", "搭配", "ootd", "时尚", "衣服", "裙子", "外套", "显瘦", "气质"],
            "美食": ["美食", "食谱", "做饭", "烘焙", "甜品", "菜谱", "好吃", "探店"],
            "旅行": ["旅行", "旅游", "攻略", "景点", "酒店", "民宿", "打卡"],
            "健身": ["健身", "减肥", "瘦身", "运动", "瑜伽", "跑步", "塑形"],
            "家居": ["家居", "装修", "收纳", "好物", "家装", "布置"],
            "母婴": ["母婴", "宝宝", "育儿", "带娃", "辅食", "早教"],
            "数码": ["数码", "手机", "电脑", "相机", "科技", "测评"],
            "学习": ["学习", "考研", "考公", "英语", "自律", "效率"],
            "职场": ["职场", "工作", "面试", "简历", "副业", "赚钱"],
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        if not text:
            return []

        # 简单的关键词提取：按标点和空格分割，过滤短词
        # 移除特殊字符，保留中文、英文、数字
        clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
        words = clean_text.split()

        # 过滤太短的词
        keywords = [w for w in words if len(w) >= 2]

        return keywords[:10]  # 返回前10个

    def _analyze_tags(self, notes) -> List[str]:
        """分析笔记标签"""
        all_tags = []
        for note in notes:
            if note.tags:
                # 标签可能是逗号分隔或空格分隔
                tags = re.split(r'[,，\s]+', note.tags)
                all_tags.extend([t.strip() for t in tags if t.strip()])

        # 统计频率
        tag_counter = Counter(all_tags)
        # 返回最常见的标签
        return [tag for tag, _ in tag_counter.most_common(10)]

    def _determine_content_style(self, notes) -> tuple:
        """判断内容风格"""
        if not notes:
            return "未知", 0, 0

        video_count = sum(1 for n in notes if n.type == "视频" or n.type == "video")
        image_count = len(notes) - video_count

        video_ratio = video_count / len(notes) * 100
        image_ratio = image_count / len(notes) * 100

        if video_ratio >= 70:
            style = "视频型"
        elif image_ratio >= 70:
            style = "图文型"
        else:
            style = "混合型"

        return style, round(video_ratio, 1), round(image_ratio, 1)

    def _detect_content_themes(self, notes, desc: str) -> List[str]:
        """检测内容主题"""
        # 合并所有文本
        all_text = desc + " "
        for note in notes:
            all_text += f"{note.title} {note.desc} {note.tags} "

        all_text = all_text.lower()

        # 检测匹配的领域
        detected_themes = []
        for theme, keywords in self.domain_keywords.items():
            match_count = sum(1 for kw in keywords if kw in all_text)
            if match_count >= 2:  # 至少匹配2个关键词
                detected_themes.append((theme, match_count))

        # 按匹配数排序
        detected_themes.sort(key=lambda x: x[1], reverse=True)
        return [t[0] for t in detected_themes[:5]]

    def analyze(self, data: BloggerAnalysisData) -> AccountPositionResult:
        """分析账号定位

        Args:
            data: 博主分析数据

        Returns:
            AccountPositionResult
        """
        blogger = data.blogger
        notes = data.notes

        # 提取昵称和简介关键词
        nickname_keywords = self._extract_keywords(blogger.nickname)
        desc_keywords = self._extract_keywords(blogger.desc)

        # 分析标签
        main_tags = self._analyze_tags(notes)

        # 判断内容风格
        content_style, video_ratio, image_ratio = self._determine_content_style(notes)

        # 检测内容主题
        content_themes = self._detect_content_themes(notes, blogger.desc)

        return AccountPositionResult(
            nickname=blogger.nickname,
            nickname_keywords=nickname_keywords,
            desc=blogger.desc,
            desc_keywords=desc_keywords,
            main_tags=main_tags,
            content_style=content_style,
            video_ratio=video_ratio,
            image_ratio=image_ratio,
            content_themes=content_themes,
        )
