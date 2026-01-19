"""日志配置"""
import sys
from pathlib import Path
from loguru import logger

# 获取日志目录
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 移除默认处理器
logger.remove()

# 添加控制台输出
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

# 添加文件输出
logger.add(
    LOG_DIR / "sync_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="00:00",  # 每天轮转
    retention="30 days",  # 保留30天
    encoding="utf-8",
)
