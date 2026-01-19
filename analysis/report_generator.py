"""Markdown 报告生成器"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import sys
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.analysis_config import REPORTS_DIR
from utils.logger import logger

from .analyzers.basic_info import BasicInfoResult
from .analyzers.account_position import AccountPositionResult
from .analyzers.topic_analysis import TopicAnalysisResult
from .analyzers.content_format import ContentFormatResult
from .analyzers.copywriting import CopywritingResult
from .analyzers.operations import OperationsResult
from .analyzers.viral_notes import ViralNotesResult
from .analyzers.evaluation import EvaluationResult


class BloggerReportGenerator:
    """博主分析报告生成器"""

    def __init__(self):
        self.reports_dir = REPORTS_DIR

    def generate(
        self,
        blogger_id: str,
        basic_info: BasicInfoResult,
        account_position: AccountPositionResult,
        topic: TopicAnalysisResult,
        content_format: ContentFormatResult,
        copywriting: CopywritingResult,
        operations: OperationsResult,
        viral: ViralNotesResult,
        evaluation: EvaluationResult,
    ) -> Path:
        """生成 Markdown 格式的分析报告

        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 构建报告内容
        sections = [
            self._generate_header(basic_info.nickname, timestamp, evaluation.overall_score),
            self._generate_basic_info(basic_info),
            self._generate_account_position(account_position),
            self._generate_topic_analysis(topic),
            self._generate_content_format(content_format),
            self._generate_copywriting(copywriting),
            self._generate_operations(operations),
            self._generate_viral_notes(viral),
            self._generate_evaluation(evaluation),
            self._generate_footer(),
        ]

        report_content = "\n\n".join(sections)

        # 写入文件
        report_path = self.reports_dir / f"{blogger_id}_analysis.md"
        report_path.write_text(report_content, encoding="utf-8")

        logger.info(f"报告已生成: {report_path}")
        return report_path

    def _generate_header(self, nickname: str, timestamp: str, score: float) -> str:
        """生成报告头部"""
        return f"""# 博主分析报告: {nickname}

> 生成时间: {timestamp}
>
> 综合评分: **{score:.0f}** / 100"""

    def _generate_basic_info(self, info: BasicInfoResult) -> str:
        """生成基础信息部分"""
        return f"""## 1. 基础信息汇总

| 指标 | 数值 |
|------|------|
| 粉丝数 | {info.fans_count:,} |
| 笔记数 | {info.notes_count:,} |
| 获赞数 | {info.liked_count:,} |
| 总收藏数 | {info.collected_count:,} |
| 总评论数 | {info.comment_count:,} |
| 赞粉比 | {info.like_fan_ratio:.2f} |
| 平均每篇点赞 | {info.avg_likes_per_note:.0f} |
| 平均每篇互动 | {info.avg_interactions_per_note:.0f} |
| 互动率 | {info.engagement_rate:.2f}% |"""

    def _generate_account_position(self, info: AccountPositionResult) -> str:
        """生成账号定位部分"""
        themes = ", ".join(info.content_themes) if info.content_themes else "暂无明显主题"
        tags = ", ".join(info.main_tags[:10]) if info.main_tags else "暂无标签"

        return f"""## 2. 账号定位分析

### 基本信息
- **昵称**: {info.nickname}
- **简介**: {info.desc or '暂无'}

### 内容定位
- **内容主题**: {themes}
- **内容风格**: {info.content_style} (图文 {info.image_ratio}% / 视频 {info.video_ratio}%)
- **主要标签**: {tags}"""

    def _generate_topic_analysis(self, info: TopicAnalysisResult) -> str:
        """生成选题拆解部分"""
        tags_list = "\n".join([f"| {tag} | {count} |" for tag, count in info.top_tags[:10]])
        keywords_list = ", ".join([f"{word}({count})" for word, count in info.top_keywords[:10]])
        title_keywords = ", ".join([f"{word}({count})" for word, count in info.title_keywords[:8]])

        return f"""## 4. 选题拆解

### 内容类型分布
- **图文笔记**: {info.image_count} 篇 ({info.image_ratio}%)
- **视频笔记**: {info.video_count} 篇 ({info.video_ratio}%)

### 高频标签 TOP 10
| 标签 | 出现次数 |
|------|----------|
{tags_list}

### 内容关键词
{keywords_list}

### 标题高频词
{title_keywords}"""

    def _generate_content_format(self, info: ContentFormatResult) -> str:
        """生成内容形式部分"""
        return f"""## 5. 内容形式拆解

| 维度 | 数据 |
|------|------|
| 图文笔记占比 | {info.image_ratio}% ({info.image_notes_count} 篇) |
| 视频笔记占比 | {info.video_ratio}% ({info.video_notes_count} 篇) |
| 平均标题长度 | {info.avg_title_length:.0f} 字 |
| 平均正文长度 | {info.avg_desc_length:.0f} 字 |
| 封面覆盖率 | {info.cover_ratio}% |"""

    def _generate_copywriting(self, info: CopywritingResult) -> str:
        """生成文案结构部分"""
        patterns = "\n".join([f"| {k} | {v} |" for k, v in info.title_patterns.items()])
        hooks = ", ".join([f"{word}({count})" for word, count in info.hook_words[:10]])
        openings = "\n".join([f"> {opening}..." for opening in info.opening_hooks[:3]])

        return f"""## 6. 文案结构拆解

### 标题分析
- **平均标题长度**: {info.avg_title_length:.0f} 字
- **数字型标题**: {info.number_title_count} 篇
- **问句型标题**: {info.question_title_count} 篇
- **含 emoji 标题**: {info.emoji_title_count} 篇

### 标题模式分布
| 模式 | 数量 |
|------|------|
{patterns}

### 常用钩子词
{hooks}

### 开头钩子示例
{openings}

### 内容特征
- **平均正文长度**: {info.avg_desc_length:.0f} 字
- **emoji 使用率**: {info.emoji_usage_rate:.0f}%"""

    def _generate_operations(self, info: OperationsResult) -> str:
        """生成运营策略部分"""
        # 生成时段分布表
        hour_rows = []
        for h in range(24):
            count = info.publish_hour_distribution.get(h, 0)
            if count > 0:
                bar = "█" * min(count, 20)
                hour_rows.append(f"| {h:02d}:00 | {count} | {bar} |")

        hour_table = "\n".join(hour_rows) if hour_rows else "| - | - | - |"

        weekday_rows = "\n".join([
            f"| {day} | {info.publish_weekday_distribution.get(day, 0)} |"
            for day in ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        ])

        best_hours = ", ".join([f"{h}:00" for h in info.best_publish_hours]) if info.best_publish_hours else "数据不足"
        best_days = ", ".join(info.best_publish_weekdays) if info.best_publish_weekdays else "数据不足"

        return f"""## 7. 运营策略拆解

### 更新频率
- **周更新频率**: {info.update_frequency:.1f} 篇/周
- **平均发布间隔**: {info.avg_days_between_posts:.1f} 天
- **发布一致性评分**: {info.consistency_score:.0f}/100
- **数据跨度**: {info.date_range_days} 天

### 最佳发布时间
- **最佳发布时段**: {best_hours}
- **最佳发布日**: {best_days}

### 发布时段分布
| 时段 | 笔记数 | 分布 |
|------|--------|------|
{hour_table}

### 发布星期分布
| 星期 | 笔记数 |
|------|--------|
{weekday_rows}"""

    def _generate_viral_notes(self, info: ViralNotesResult) -> str:
        """生成爆款笔记部分"""
        # TOP 笔记表格（简略版）
        note_rows = []
        for note in info.top_notes:
            title_short = note.title[:30] + "..." if len(note.title) > 30 else note.title
            note_rows.append(
                f"| {note.rank} | {title_short} | {note.type} | {note.liked_count:,} | "
                f"{note.collected_count:,} | {note.comment_count:,} | [链接]({note.note_url}) |"
            )
        notes_table = "\n".join(note_rows) if note_rows else "| - | - | - | - | - | - | - |"

        # 生成详细笔记卡片
        note_cards = []
        for note in info.top_notes:
            # 封面图片
            cover_section = f"![封面]({note.cover_url})" if note.cover_url else "*无封面图片*"

            # 正文（限制长度，避免过长）
            desc_text = note.desc if note.desc else "*无正文内容*"
            if len(desc_text) > 500:
                desc_text = desc_text[:500] + "..."

            # 标签
            tags_text = note.tags if note.tags else "*无标签*"

            card = f"""#### {note.rank}. {note.title}

**基础数据**: 👍 {note.liked_count:,} | ⭐ {note.collected_count:,} | 💬 {note.comment_count:,} | 类型: {note.type}

**封面**:
{cover_section}

**正文**:
> {desc_text}

**标签**: {tags_text}

**链接**: [查看原文]({note.note_url})

---"""
            note_cards.append(card)

        note_cards_text = "\n\n".join(note_cards) if note_cards else "暂无数据"

        # 爆款特征
        features = info.viral_common_features
        features_list = []
        if features:
            features_list.append(f"- 平均标题长度: {features.get('avg_title_length', 0):.0f} 字")
            features_list.append(f"- 数字型标题占比: {features.get('has_number_ratio', 0):.0f}%")
            features_list.append(f"- 问句型标题占比: {features.get('has_question_ratio', 0):.0f}%")
            features_list.append(f"- emoji 使用占比: {features.get('has_emoji_ratio', 0):.0f}%")
            features_list.append(f"- 视频占比: {features.get('video_ratio', 0):.0f}%")
            if features.get('common_keywords'):
                features_list.append(f"- 共同关键词: {', '.join(features['common_keywords'][:8])}")
        features_text = "\n".join(features_list) if features_list else "数据不足"

        # 爆款标签
        viral_tags = ", ".join([f"{tag}({count})" for tag, count in info.viral_tags[:8]]) if info.viral_tags else "暂无"

        return f"""## 9. 爆款笔记拆解

### 数据概览
- **爆款内容类型偏好**: {info.viral_content_type}
- **TOP10 平均点赞**: {info.avg_viral_likes:,.0f}
- **TOP10 平均互动**: {info.avg_viral_interactions:,.0f}

### TOP 10 高互动笔记
| 排名 | 标题 | 类型 | 点赞 | 收藏 | 评论 | 链接 |
|------|------|------|------|------|------|------|
{notes_table}

### 爆款笔记详情

{note_cards_text}

### 爆款特征分析
{features_text}

### 爆款高频标签
{viral_tags}"""

    def _generate_evaluation(self, info: EvaluationResult) -> str:
        """生成综合评估部分"""
        strengths = "\n".join([f"- {s}" for s in info.strengths]) if info.strengths else "- 暂无"
        weaknesses = "\n".join([f"- {w}" for w in info.weaknesses]) if info.weaknesses else "- 暂无"
        actions = "\n".join([f"{i+1}. {a}" for i, a in enumerate(info.action_items)]) if info.action_items else "1. 暂无"

        scores = "\n".join([f"| {dim} | {score:.0f} |" for dim, score in info.dimension_scores.items()])

        return f"""## 10. 综合评估与行动计划

### 各维度评分
| 维度 | 得分 |
|------|------|
{scores}
| **总分** | **{info.overall_score:.0f}** |

### 优势
{strengths}

### 待改进
{weaknesses}

### 行动建议
{actions}"""

    def _generate_footer(self) -> str:
        """生成报告尾部"""
        return """---

*注: 粉丝画像分析和变现模式分析需要外部数据，暂不支持*

*报告由「小红书对标博主拆解系统」自动生成*"""
