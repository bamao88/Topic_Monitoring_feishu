#!/usr/bin/env python3
"""抓取数据并保存到 JSON 文件"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from crawler import XHSCrawler
from loguru import logger

# Cookie 字符串
COOKIE_STR = (PROJECT_ROOT / "config" / "cookie.txt").read_text().strip()

# 博主 URL
BLOGGER_URL = "https://www.xiaohongshu.com/user/profile/695b82df0000000037031eca?xsec_token=ABJ7UTxGpQYjzUFtwOyDw7Ac9KQhGtEhbXZy1HEbyLr14=&xsec_source=pc_note"

# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR.mkdir(exist_ok=True)


async def test():
    """抓取数据并保存"""
    logger.info("开始抓取数据...")

    # 解析博主URL
    url_info = XHSCrawler.parse_creator_url(BLOGGER_URL)
    user_id = url_info["user_id"]
    xsec_token = url_info["xsec_token"]
    xsec_source = url_info["xsec_source"]

    # 创建爬虫
    crawler = XHSCrawler(headless=False, cookie_str=COOKIE_STR)

    result = {
        "crawl_time": datetime.now().isoformat(),
        "blogger": None,
        "notes": [],
        "comments": [],
    }

    try:
        await crawler.start()

        # 1. 获取博主信息
        logger.info("获取博主信息...")
        blogger_info = await crawler.get_blogger_info(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
        )

        if blogger_info:
            result["blogger"] = blogger_info.to_feishu_record()
            logger.info(f"博主: {blogger_info.nickname}")

        await asyncio.sleep(2)

        # 2. 获取笔记和评论
        logger.info("获取笔记和评论...")
        notes, comments = await crawler.get_blogger_notes_with_details(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
            max_count=10,
            crawl_interval=2,
            fetch_comments=True,
        )

        result["notes"] = [n.to_feishu_record() for n in notes]
        result["comments"] = [c.to_feishu_record() for c in comments]

        logger.info(f"获取到 {len(notes)} 条笔记, {len(comments)} 条评论")

    finally:
        await crawler.close()

    # 保存到文件
    output_file = OUTPUT_DIR / f"crawl_result_{user_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"\n数据已保存到: {output_file}")
    logger.info(f"\n查看命令: cat {output_file}")

    return output_file


if __name__ == "__main__":
    output_file = asyncio.run(test())
    print(f"\n输出文件: {output_file}")
