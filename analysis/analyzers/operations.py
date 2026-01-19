"""运营策略拆解分析器 - Sheet 7: 运营策略拆解"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from collections import Counter

from ..data_fetcher import BloggerAnalysisData

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.analysis_config import PUBLISH_TIME_CONFIG


@dataclass
class OperationsResult:
    """运营策略分析结果"""
    total_notes: int
    update_frequency: float  # 更新频率 (篇/周)
    publish_hour_distribution: Dict[int, int]  # 发布时段分布
    publish_weekday_distribution: Dict[str, int]  # 发布星期分布
    best_publish_hours: List[int]  # 最佳发布时段
    best_publish_weekdays: List[str]  # 最佳发布日
    avg_days_between_posts: float  # 平均发布间隔(天)
    consistency_score: float  # 发布一致性评分
    date_range_days: int  # 数据跨度(天)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_notes": self.total_notes,
            "update_frequency": self.update_frequency,
            "publish_hour_distribution": self.publish_hour_distribution,
            "publish_weekday_distribution": self.publish_weekday_distribution,
            "best_publish_hours": self.best_publish_hours,
            "best_publish_weekdays": self.best_publish_weekdays,
            "avg_days_between_posts": self.avg_days_between_posts,
            "consistency_score": self.consistency_score,
            "date_range_days": self.date_range_days,
        }


class OperationsAnalyzer:
    """运营策略分析器"""

    def __init__(self):
        self.weekday_names = PUBLISH_TIME_CONFIG["weekday_names"]

    def _parse_timestamp(self, timestamp: int) -> datetime:
        """解析时间戳"""
        if timestamp > 10000000000:  # 毫秒时间戳
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp)

    def _analyze_publish_times(self, notes) -> Tuple[Dict[int, int], Dict[str, int]]:
        """分析发布时间分布"""
        hour_counter = Counter()
        weekday_counter = Counter()

        for note in notes:
            if note.publish_time:
                try:
                    dt = self._parse_timestamp(note.publish_time)
                    hour_counter[dt.hour] += 1
                    weekday_counter[self.weekday_names[dt.weekday()]] += 1
                except (ValueError, OSError):
                    continue

        # 补全缺失的小时
        hour_distribution = {h: hour_counter.get(h, 0) for h in range(24)}

        # 补全缺失的星期
        weekday_distribution = {day: weekday_counter.get(day, 0) for day in self.weekday_names}

        return hour_distribution, weekday_distribution

    def _calculate_frequency(self, notes) -> Tuple[float, float, int]:
        """计算更新频率"""
        if len(notes) < 2:
            return 0, 0, 0

        # 获取有效的发布时间
        timestamps = []
        for note in notes:
            if note.publish_time:
                try:
                    dt = self._parse_timestamp(note.publish_time)
                    timestamps.append(dt)
                except (ValueError, OSError):
                    continue

        if len(timestamps) < 2:
            return 0, 0, 0

        timestamps.sort()
        date_range = (timestamps[-1] - timestamps[0]).days
        if date_range == 0:
            date_range = 1

        # 计算周更新频率
        weeks = date_range / 7.0 or 1
        frequency = len(timestamps) / weeks

        # 计算平均发布间隔
        avg_interval = date_range / (len(timestamps) - 1) if len(timestamps) > 1 else 0

        return round(frequency, 2), round(avg_interval, 1), date_range

    def _calculate_consistency(self, notes) -> float:
        """计算发布一致性评分 (0-100)"""
        if len(notes) < 3:
            return 0

        # 获取发布间隔
        timestamps = []
        for note in notes:
            if note.publish_time:
                try:
                    dt = self._parse_timestamp(note.publish_time)
                    timestamps.append(dt)
                except (ValueError, OSError):
                    continue

        if len(timestamps) < 3:
            return 0

        timestamps.sort()
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).days
            intervals.append(interval)

        if not intervals:
            return 0

        # 计算标准差
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval == 0:
            return 100

        variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = variance ** 0.5

        # 变异系数
        cv = std_dev / avg_interval if avg_interval > 0 else 0

        # 转换为分数 (变异系数越小越好)
        score = max(0, 100 - cv * 50)
        return round(score, 1)

    def analyze(self, data: BloggerAnalysisData) -> OperationsResult:
        """分析运营策略

        Args:
            data: 博主分析数据

        Returns:
            OperationsResult
        """
        notes = data.notes
        total_notes = len(notes)

        if total_notes == 0:
            return OperationsResult(
                total_notes=0,
                update_frequency=0,
                publish_hour_distribution={h: 0 for h in range(24)},
                publish_weekday_distribution={d: 0 for d in self.weekday_names},
                best_publish_hours=[],
                best_publish_weekdays=[],
                avg_days_between_posts=0,
                consistency_score=0,
                date_range_days=0,
            )

        # 分析发布时间分布
        hour_dist, weekday_dist = self._analyze_publish_times(notes)

        # 找出最佳发布时间
        sorted_hours = sorted(hour_dist.items(), key=lambda x: x[1], reverse=True)
        best_hours = [h for h, c in sorted_hours[:3] if c > 0]

        sorted_weekdays = sorted(weekday_dist.items(), key=lambda x: x[1], reverse=True)
        best_weekdays = [d for d, c in sorted_weekdays[:3] if c > 0]

        # 计算频率
        frequency, avg_interval, date_range = self._calculate_frequency(notes)

        # 计算一致性
        consistency = self._calculate_consistency(notes)

        return OperationsResult(
            total_notes=total_notes,
            update_frequency=frequency,
            publish_hour_distribution=hour_dist,
            publish_weekday_distribution=weekday_dist,
            best_publish_hours=best_hours,
            best_publish_weekdays=best_weekdays,
            avg_days_between_posts=avg_interval,
            consistency_score=consistency,
            date_range_days=date_range,
        )
