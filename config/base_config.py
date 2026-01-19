"""基础配置"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# MediaCrawler 路径
MEDIA_CRAWLER_PATH = PROJECT_ROOT / "MediaCrawler"

# 日志目录
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 浏览器配置
HEADLESS = False  # 是否无头模式
SAVE_LOGIN_STATE = True  # 是否保存登录状态
USER_DATA_DIR = "xhs_user_data_dir"

# 爬取配置
CRAWLER_MAX_SLEEP_SEC = 2  # 爬取间隔时间(秒)
CRAWLER_MAX_NOTES_COUNT = 100  # 单个博主最大抓取笔记数
MAX_CONCURRENCY_NUM = 1  # 并发数
ENABLE_GET_COMMENTS = True  # 是否爬取评论
ENABLE_GET_SUB_COMMENTS = True  # 是否爬取二级评论
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 100  # 单笔记最大评论数

# 登录方式: qrcode | cookie
LOGIN_TYPE = "qrcode"
COOKIES = ""

# 是否启用 CDP 模式
ENABLE_CDP_MODE = True
CDP_DEBUG_PORT = 9222
CDP_HEADLESS = False

# 是否下载媒体文件
ENABLE_GET_MEIDAS = False
