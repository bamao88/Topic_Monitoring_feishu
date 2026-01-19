#!/usr/bin/env python3
"""完整测试 - 使用更新后的爬虫模块"""
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from crawler import XHSCrawler
from loguru import logger

# Cookie 字符串
COOKIE_STR = """a1=19ac980b62fx4xvs1awfxvv2s2tok4epvfqdp823f30000287521; webId=ddcadc908378d82dcd46a396dafb0078; gid=yj0SjY8SW0hKyj0SjY8DKiYJJiC4ChMy0EiCAqihhJMJ9fq8lT4dUU888JYW2Jy8q2KdD00j; x-user-id-ad.xiaohongshu.com=691d96ca155d000000000001; customerClientId=155263573799033; abRequestId=ddcadc908378d82dcd46a396dafb0078; sensorsdata2015jssdkcross=%7B%22%24device_id%22%3A%2219adec4a057817-0d3b77cb9d90ae8-1d525631-2073600-19adec4a0581161%22%7D; x-user-id-xue.xiaohongshu.com=676d709d000000001900a119; access-token-xue.xiaohongshu.com=customer.xue.AT-68c517581486518856089601dabeatt9kvcellov; x-user-id-pgy.xiaohongshu.com=691d96ca155d000000000001; customer-sso-sid=68c51759512243013556635064cgjzz6somcuqs5; x-user-id-creator.xiaohongshu.com=676d709d000000001900a119; access-token-creator.xiaohongshu.com=customer.creator.AT-68c5175951224301355335841jpwfqwxkelv0x8m; galaxy_creator_session_id=HDzBCOeQBtZf88BI2hPILUvvuocC273rGUnH; galaxy.creator.beaker.session.id=1768377244977066024799; acw_tc=0a00d88117687117733155619e181a8cd282946b731843b0c48718e275c82d; webBuild=5.7.0; xsecappid=xhs-pc-web; loadts=1768711784116; websectiga=16f444b9ff5e3d7e258b5f7674489196303a0b160e16647c6c2b4dcb609f4134; sec_poison_id=972fcb2d-3575-4cf8-97b0-fa911bd5e7a3; web_session=040069b9f8213af390fbc02e593b4b6abc98d2; id_token=VjEAALiKXlAl3jcZQmMXRdCS3HSVzhPOHumcdYUsM3IsKV7xZN3DaUQnWRh18WmRB3OA91u9N5npG219nv0UrNb6o1VSoLi3G+CGg0yhHyuJPwOeFKnorlt3OsjhcM+Vcdk3GC/g; unread={%22ub%22:%22696751100000000009039180%22%2C%22ue%22:%226945032e000000001d03ce6d%22%2C%22uc%22:28}"""

# 博主 URL
BLOGGER_URL = "https://www.xiaohongshu.com/user/profile/695b82df0000000037031eca?xsec_token=ABJ7UTxGpQYjzUFtwOyDw7Ac9KQhGtEhbXZy1HEbyLr14=&xsec_source=pc_note"


async def test():
    """完整测试爬虫功能"""
    logger.info("=" * 60)
    logger.info("完整测试 - 使用更新后的爬虫模块")
    logger.info("=" * 60)

    # 解析博主URL
    url_info = XHSCrawler.parse_creator_url(BLOGGER_URL)
    logger.info(f"解析博主URL: {url_info}")

    user_id = url_info["user_id"]
    xsec_token = url_info["xsec_token"]
    xsec_source = url_info["xsec_source"]

    # 创建爬虫
    crawler = XHSCrawler(headless=False, cookie_str=COOKIE_STR)

    try:
        await crawler.start()

        # 1. 获取博主信息
        logger.info("\n" + "=" * 60)
        logger.info("步骤 1: 获取博主信息")
        logger.info("=" * 60)

        blogger_info = await crawler.get_blogger_info(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
        )

        if blogger_info:
            logger.info(f"\n博主信息:")
            logger.info(f"  昵称: {blogger_info.nickname}")
            logger.info(f"  ID: {blogger_info.blogger_id}")
            logger.info(f"  简介: {blogger_info.desc or '无'}")
            logger.info(f"  粉丝: {blogger_info.fans_count}")
            logger.info(f"  笔记: {blogger_info.notes_count}")
            logger.info(f"  获赞: {blogger_info.liked_count}")
            logger.info(f"  IP属地: {blogger_info.ip_location or '未知'}")
        else:
            logger.error("获取博主信息失败")

        await asyncio.sleep(2)

        # 2. 获取博主笔记和评论
        logger.info("\n" + "=" * 60)
        logger.info("步骤 2: 获取博主笔记和评论")
        logger.info("=" * 60)

        notes, comments = await crawler.get_blogger_notes_with_details(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
            max_count=5,  # 测试只获取5条
            crawl_interval=2,
            fetch_comments=True,
        )

        logger.info(f"\n获取到 {len(notes)} 条笔记, {len(comments)} 条评论")

        # 显示笔记详情
        for i, note in enumerate(notes, 1):
            logger.info(f"\n--- 笔记 {i} ---")
            logger.info(f"  ID: {note.note_id}")
            logger.info(f"  标题: {note.title or '无标题'}")
            logger.info(f"  类型: {note.type}")
            logger.info(f"  点赞: {note.liked_count}")
            logger.info(f"  收藏: {note.collected_count}")
            logger.info(f"  评论: {note.comment_count}")
            logger.info(f"  分享: {note.share_count}")
            if note.tags:
                logger.info(f"  标签: {', '.join(note.tags[:5])}")
            if note.desc:
                logger.info(f"  内容: {note.desc[:100]}...")

        # 显示评论
        if comments:
            logger.info(f"\n--- 评论列表 ({len(comments)} 条) ---")
            for i, comment in enumerate(comments[:10], 1):
                parent_tag = " [回复]" if comment.parent_id else ""
                logger.info(f"  {i}. [{comment.user_nickname}]{parent_tag}: {comment.content[:50]}... (赞: {comment.liked_count})")

        # 3. 测试数据模型转换
        logger.info("\n" + "=" * 60)
        logger.info("步骤 3: 测试数据模型转换")
        logger.info("=" * 60)

        if blogger_info:
            record = blogger_info.to_feishu_record()
            logger.info(f"\n博主飞书记录: {list(record.keys())}")

        if notes:
            record = notes[0].to_feishu_record()
            logger.info(f"笔记飞书记录: {list(record.keys())}")

        if comments:
            record = comments[0].to_feishu_record()
            logger.info(f"评论飞书记录: {list(record.keys())}")

        logger.info("\n" + "=" * 60)
        logger.info("测试完成!")
        logger.info("=" * 60)

    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(test())
