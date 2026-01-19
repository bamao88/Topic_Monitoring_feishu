#!/usr/bin/env python3
"""
小红书对标博主内容自动沉淀系统 - 主入口

功能:
    定期抓取指定小红书博主的内容与评论，结构化写入飞书多维表格
    分析博主数据并生成结构化分析报告

使用方法:
    1. 配置飞书凭证 (环境变量或 .env 文件)
    2. 配置 Cookie (环境变量 XHS_COOKIE 或 config/cookie.txt)
    3. 配置 config/bloggers.yaml 添加要跟踪的博主
    4. 运行: python main.py

参数:
    --test          测试模式，只同步第一个博主
    --headless      无头模式运行浏览器
    --cookie        直接指定 Cookie 字符串
    --analyze       分析指定博主并生成报告
    --analyze-all   分析所有博主并生成报告
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv(PROJECT_ROOT / ".env")

# 先导入 logger 模块以初始化日志配置
from utils.logger import logger

from sync.blogger_sync import sync_bloggers, HEADLESS


def main():
    parser = argparse.ArgumentParser(
        description="小红书对标博主内容自动沉淀系统"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="测试模式，只同步第一个博主",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式运行浏览器",
    )
    parser.add_argument(
        "--cookie",
        type=str,
        default="",
        help="直接指定 Cookie 字符串",
    )
    parser.add_argument(
        "--analyze",
        type=str,
        metavar="BLOGGER_ID",
        help="分析指定博主并生成报告",
    )
    parser.add_argument(
        "--analyze-all",
        action="store_true",
        help="分析所有博主并生成报告",
    )
    args = parser.parse_args()

    # 处理分析模式
    if args.analyze or args.analyze_all:
        from analysis.main import analyze_blogger, analyze_all_bloggers

        logger.info("=" * 50)
        logger.info("小红书博主分析系统")
        logger.info("=" * 50)

        try:
            if args.analyze:
                logger.info(f"分析博主: {args.analyze}")
                analyze_blogger(args.analyze)
            else:
                logger.info("分析所有博主")
                analyze_all_bloggers()
        except KeyboardInterrupt:
            logger.info("用户中断")
        except Exception as e:
            logger.error(f"分析失败: {e}")
            raise
        return

    # 如果指定了 headless，更新配置
    if args.headless:
        import sync.blogger_sync as blogger_sync
        blogger_sync.HEADLESS = True

    logger.info("=" * 50)
    logger.info("小红书对标博主内容自动沉淀系统 v1.0")
    logger.info("=" * 50)
    logger.info(f"项目目录: {PROJECT_ROOT}")
    logger.info(f"测试模式: {args.test}")
    logger.info(f"无头模式: {args.headless}")

    try:
        asyncio.run(sync_bloggers(test_mode=args.test, cookie_str=args.cookie))
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"运行失败: {e}")
        raise


if __name__ == "__main__":
    main()
