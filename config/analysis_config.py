"""分析模块配置"""
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 报告输出目录
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# 爆款笔记分析配置
VIRAL_NOTES_CONFIG = {
    "top_count": 10,  # 分析 TOP N 笔记
    "min_interactions": 100,  # 最低互动数阈值
}

# 标题分析配置
TITLE_ANALYSIS_CONFIG = {
    "min_title_length": 5,  # 最小标题长度
    "max_title_length": 50,  # 最大标题长度
    "number_patterns": [
        r"\d+个",
        r"\d+种",
        r"\d+款",
        r"\d+招",
        r"\d+步",
        r"\d+天",
        r"\d+年",
        r"第\d+",
        r"TOP\s*\d+",
        r"\d+%",
    ],
    "question_patterns": [
        r"如何",
        r"怎么",
        r"为什么",
        r"什么",
        r"哪里",
        r"哪个",
        r"谁",
        r"\?",
        r"？",
    ],
    "hook_words": [
        "必看", "必收藏", "强烈推荐", "超实用", "干货",
        "绝了", "太香了", "真香", "yyds", "神器",
        "宝藏", "小众", "冷门", "平价", "学生党",
        "打工人", "懒人", "新手", "入门", "保姆级",
        "手把手", "教程", "攻略", "合集", "盘点",
        "避雷", "踩坑", "测评", "对比", "真实",
        "亲测", "实测", "良心", "省钱", "白嫖",
    ],
}

# 发布时间分析配置
PUBLISH_TIME_CONFIG = {
    "peak_hours": [7, 8, 9, 12, 13, 18, 19, 20, 21, 22],  # 高峰发布时段
    "weekday_names": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
}

# 内容类型
CONTENT_TYPES = {
    "video": "视频",
    "normal": "图文",
}

# 标签分析配置
TAG_ANALYSIS_CONFIG = {
    "top_count": 10,  # 显示 TOP N 标签
    "min_frequency": 2,  # 最小出现次数
}

# 综合评估配置
EVALUATION_CONFIG = {
    # 互动率评估标准 (互动数/粉丝数)
    "engagement_rate": {
        "excellent": 0.05,  # 优秀: > 5%
        "good": 0.02,  # 良好: > 2%
        "average": 0.01,  # 一般: > 1%
    },
    # 赞粉比评估标准
    "like_fan_ratio": {
        "excellent": 2.0,  # 优秀: > 2
        "good": 1.0,  # 良好: > 1
        "average": 0.5,  # 一般: > 0.5
    },
    # 更新频率评估 (篇/周)
    "update_frequency": {
        "high": 5,  # 高频: > 5篇/周
        "medium": 2,  # 中频: > 2篇/周
        "low": 1,  # 低频: < 2篇/周
    },
}
