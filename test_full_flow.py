"""测试完整流程：抓取 + 分析 + 上传飞书"""
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from crawler import MediaCrawlerAdapter
from feishu import FeishuTableSync
from sync.blogger_sync import load_cookie
from analysis.main import analyze_blogger
from utils.logger import logger

# 测试配置
TEST_URL = "https://www.xiaohongshu.com/user/profile/66665c13000000000d02783c?xsec_token=AB21dFsHbgqS7Mkat8v9sj5f0TnfK8ga1y7--O5lIdyvY=&xsec_source=pc_search"
MAX_NOTES = 5  # 只抓取5篇笔记


async def test_full_flow():
    """测试完整流程"""
    logger.info("=" * 50)
    logger.info("开始测试完整流程")
    logger.info("=" * 50)

    # 解析 URL
    url_info = MediaCrawlerAdapter.parse_creator_url(TEST_URL)
    user_id = url_info.get("user_id")
    xsec_token = url_info.get("xsec_token", "")
    xsec_source = url_info.get("xsec_source", "pc_search")

    if not user_id:
        logger.error(f"无法解析博主URL: {TEST_URL}")
        return

    logger.info(f"博主ID: {user_id}")

    # 加载 Cookie
    cookie_str = load_cookie()
    if not cookie_str:
        logger.error("未找到 Cookie")
        return

    # 初始化飞书同步
    feishu_sync = FeishuTableSync()
    feishu_sync.load_existing_data()

    # 初始化爬虫
    crawler = MediaCrawlerAdapter(headless=False, cookie_str=cookie_str)

    try:
        await crawler.start()

        # 1. 获取博主信息
        logger.info("正在获取博主信息...")
        blogger_info = await crawler.get_blogger_info(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
        )

        if blogger_info:
            feishu_sync.sync_blogger(blogger_info.to_feishu_record())
            logger.info(f"博主: {blogger_info.nickname} (粉丝: {blogger_info.fans_count})")
        else:
            logger.error("无法获取博主信息")
            return

        await asyncio.sleep(2)

        # 2. 获取笔记和评论（限制5篇）
        logger.info(f"正在获取笔记（最多{MAX_NOTES}篇）...")
        notes, comments = await crawler.get_blogger_notes_with_details(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
            max_count=MAX_NOTES,
            crawl_interval=2,
            fetch_comments=True,
        )

        # 3. 同步笔记
        if notes:
            blogger_nickname = blogger_info.nickname if blogger_info else ""
            note_records = []
            for n in notes:
                n.blogger_nickname = blogger_nickname
                note_records.append(n.to_feishu_record())
            new_count = feishu_sync.sync_notes(note_records)
            logger.info(f"笔记同步完成: {new_count} 条")

        # 4. 同步评论
        if comments:
            comment_records = [c.to_feishu_record() for c in comments]
            new_count = feishu_sync.sync_comments(comment_records)
            logger.info(f"评论同步完成: {new_count} 条")

        logger.info("=" * 50)
        logger.info("数据同步完成，开始分析...")
        logger.info("=" * 50)

    finally:
        await crawler.close()

    # 5. 分析博主并生成报告（含上传飞书）
    report_path = analyze_blogger(user_id)

    if report_path:
        logger.info("=" * 50)
        logger.info("测试完成!")
        logger.info(f"本地报告: {report_path}")
        logger.info("飞书云文档已自动更新到博主表的 analysis_doc_url 字段")
        logger.info("=" * 50)
    else:
        logger.error("分析失败")


if __name__ == "__main__":
    asyncio.run(test_full_flow())
