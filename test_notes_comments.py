#!/usr/bin/env python3
"""测试获取博主的笔记详情和评论"""
import asyncio
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "MediaCrawler"))

from playwright.async_api import async_playwright
from loguru import logger

# Cookie 字符串
COOKIE_STR = """a1=19ac980b62fx4xvs1awfxvv2s2tok4epvfqdp823f30000287521; webId=ddcadc908378d82dcd46a396dafb0078; gid=yj0SjY8SW0hKyj0SjY8DKiYJJiC4ChMy0EiCAqihhJMJ9fq8lT4dUU888JYW2Jy8q2KdD00j; x-user-id-ad.xiaohongshu.com=691d96ca155d000000000001; customerClientId=155263573799033; abRequestId=ddcadc908378d82dcd46a396dafb0078; sensorsdata2015jssdkcross=%7B%22%24device_id%22%3A%2219adec4a057817-0d3b77cb9d90ae8-1d525631-2073600-19adec4a0581161%22%7D; x-user-id-xue.xiaohongshu.com=676d709d000000001900a119; access-token-xue.xiaohongshu.com=customer.xue.AT-68c517581486518856089601dabeatt9kvcellov; x-user-id-pgy.xiaohongshu.com=691d96ca155d000000000001; customer-sso-sid=68c51759512243013556635064cgjzz6somcuqs5; x-user-id-creator.xiaohongshu.com=676d709d000000001900a119; access-token-creator.xiaohongshu.com=customer.creator.AT-68c5175951224301355335841jpwfqwxkelv0x8m; galaxy_creator_session_id=HDzBCOeQBtZf88BI2hPILUvvuocC273rGUnH; galaxy.creator.beaker.session.id=1768377244977066024799; acw_tc=0a00d88117687117733155619e181a8cd282946b731843b0c48718e275c82d; webBuild=5.7.0; xsecappid=xhs-pc-web; loadts=1768711784116; websectiga=16f444b9ff5e3d7e258b5f7674489196303a0b160e16647c6c2b4dcb609f4134; sec_poison_id=972fcb2d-3575-4cf8-97b0-fa911bd5e7a3; web_session=040069b9f8213af390fbc02e593b4b6abc98d2; id_token=VjEAALiKXlAl3jcZQmMXRdCS3HSVzhPOHumcdYUsM3IsKV7xZN3DaUQnWRh18WmRB3OA91u9N5npG219nv0UrNb6o1VSoLi3G+CGg0yhHyuJPwOeFKnorlt3OsjhcM+Vcdk3GC/g; unread={%22ub%22:%22696751100000000009039180%22%2C%22ue%22:%226945032e000000001d03ce6d%22%2C%22uc%22:28}"""

# 博主 URL
BLOGGER_URL = "https://www.xiaohongshu.com/user/profile/695b82df0000000037031eca?xsec_token=ABJ7UTxGpQYjzUFtwOyDw7Ac9KQhGtEhbXZy1HEbyLr14=&xsec_source=pc_note"


def parse_cookie_string(cookie_str: str) -> dict:
    """解析 cookie 字符串为字典"""
    cookie_dict = {}
    for item in cookie_str.split("; "):
        if "=" in item:
            key, value = item.split("=", 1)
            cookie_dict[key.strip()] = value.strip()
    return cookie_dict


async def get_note_detail(page, note_id: str, xsec_token: str):
    """获取笔记详情"""
    note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source=pc_note"
    logger.info(f"访问笔记: {note_url}")

    await page.goto(note_url, timeout=60000)
    await asyncio.sleep(3)

    # 提取笔记详情
    note_data = await page.evaluate("""() => {
        if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note) {
            const noteData = window.__INITIAL_STATE__.note;
            // 获取笔记详情
            let noteDetail = null;
            if (noteData.noteDetailMap) {
                const detailMap = noteData.noteDetailMap.value || noteData.noteDetailMap._value || noteData.noteDetailMap;
                if (detailMap && typeof detailMap === 'object') {
                    // 获取第一个笔记详情
                    const keys = Object.keys(detailMap);
                    if (keys.length > 0) {
                        noteDetail = detailMap[keys[0]];
                    }
                }
            }
            return JSON.stringify(noteDetail);
        }
        return "";
    }""")

    return json.loads(note_data) if note_data else None


async def get_note_comments(page, note_id: str, xsec_token: str):
    """获取笔记评论"""
    # 评论数据通常在笔记详情页面的 __INITIAL_STATE__ 中
    comments_data = await page.evaluate("""() => {
        if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note) {
            const noteData = window.__INITIAL_STATE__.note;
            // 获取评论
            if (noteData.noteDetailMap) {
                const detailMap = noteData.noteDetailMap.value || noteData.noteDetailMap._value || noteData.noteDetailMap;
                if (detailMap && typeof detailMap === 'object') {
                    const keys = Object.keys(detailMap);
                    if (keys.length > 0) {
                        const detail = detailMap[keys[0]];
                        if (detail && detail.comments) {
                            return JSON.stringify(detail.comments);
                        }
                    }
                }
            }
            // 尝试其他路径获取评论
            if (noteData.comments) {
                const comments = noteData.comments.value || noteData.comments._value || noteData.comments;
                return JSON.stringify(comments);
            }
        }
        return "";
    }""")

    return json.loads(comments_data) if comments_data else None


async def test():
    """测试获取笔记详情和评论"""
    logger.info("=" * 60)
    logger.info("开始测试获取笔记详情和评论")
    logger.info("=" * 60)

    cookie_dict = parse_cookie_string(COOKIE_STR)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        )

        # 设置 Cookie
        cookies_for_playwright = []
        for name, value in cookie_dict.items():
            cookies_for_playwright.append({
                "name": name,
                "value": value,
                "domain": ".xiaohongshu.com",
                "path": "/",
            })
        await context.add_cookies(cookies_for_playwright)

        # 加载反检测脚本
        stealth_js = PROJECT_ROOT / "MediaCrawler" / "libs" / "stealth.min.js"
        if stealth_js.exists():
            await context.add_init_script(path=str(stealth_js))

        page = await context.new_page()

        # 1. 首先获取博主的笔记列表
        logger.info(f"\n步骤1: 获取博主笔记列表")
        logger.info("-" * 40)

        await page.goto(BLOGGER_URL, timeout=60000)
        await asyncio.sleep(3)

        notes_data = await page.evaluate("""() => {
            if (window.__INITIAL_STATE__ &&
                window.__INITIAL_STATE__.user &&
                window.__INITIAL_STATE__.user.notes) {
                const notes = window.__INITIAL_STATE__.user.notes;
                const data = notes.value !== undefined ? notes.value : notes._value;
                if (data) {
                    return JSON.stringify(data);
                }
            }
            return "";
        }""")

        notes = []
        if notes_data:
            raw_notes = json.loads(notes_data)
            for item in raw_notes:
                if isinstance(item, list):
                    notes.extend(item)
                else:
                    notes.append(item)

        if not notes:
            logger.warning("未获取到笔记列表")
            await browser.close()
            return

        logger.info(f"获取到 {len(notes)} 条笔记")

        # 显示笔记列表
        for i, note in enumerate(notes, 1):
            note_id = note.get("note_id", "") or note.get("id", "")
            title = note.get("display_title", "") or note.get("title", "") or "无标题"
            xsec_token = note.get("xsec_token", "")
            logger.info(f"  {i}. [{note_id}] {title[:30]}")

        # 2. 获取每条笔记的详情和评论
        logger.info(f"\n步骤2: 获取笔记详情和评论")
        logger.info("-" * 40)

        for i, note in enumerate(notes, 1):
            note_id = note.get("note_id", "") or note.get("id", "")
            xsec_token = note.get("xsec_token", "")
            title = note.get("display_title", "") or note.get("title", "") or "无标题"

            if not note_id or not xsec_token:
                logger.warning(f"笔记 {i} 缺少必要参数，跳过")
                continue

            logger.info(f"\n{'='*60}")
            logger.info(f"笔记 {i}: {title[:40]}")
            logger.info(f"{'='*60}")

            # 访问笔记详情页
            note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source=pc_note"
            await page.goto(note_url, timeout=60000)
            await asyncio.sleep(4)  # 等待页面和评论加载

            # 提取笔记详情
            detail_data = await page.evaluate("""() => {
                if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note) {
                    const noteData = window.__INITIAL_STATE__.note;
                    if (noteData.noteDetailMap) {
                        const detailMap = noteData.noteDetailMap.value || noteData.noteDetailMap._value || noteData.noteDetailMap;
                        if (detailMap && typeof detailMap === 'object') {
                            const keys = Object.keys(detailMap);
                            if (keys.length > 0) {
                                return JSON.stringify(detailMap[keys[0]]);
                            }
                        }
                    }
                }
                return "";
            }""")

            if detail_data:
                detail = json.loads(detail_data)
                note_card = detail.get("note", {})

                logger.info(f"\n📝 笔记详情:")
                logger.info(f"   标题: {note_card.get('title', 'N/A')}")
                logger.info(f"   类型: {note_card.get('type', 'N/A')}")
                logger.info(f"   内容: {note_card.get('desc', 'N/A')[:100]}...")

                interact = note_card.get("interactInfo", {})
                logger.info(f"   点赞: {interact.get('likedCount', 0)}")
                logger.info(f"   收藏: {interact.get('collectedCount', 0)}")
                logger.info(f"   评论: {interact.get('commentCount', 0)}")
                logger.info(f"   分享: {interact.get('shareCount', 0)}")

                # 标签
                tags = note_card.get("tagList", [])
                if tags:
                    tag_names = [t.get("name", "") for t in tags[:5]]
                    logger.info(f"   标签: {', '.join(tag_names)}")

            # 提取评论
            comments_data = await page.evaluate("""() => {
                if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note) {
                    const noteData = window.__INITIAL_STATE__.note;
                    // 尝试从 comments 获取
                    if (noteData.comments) {
                        const comments = noteData.comments.value || noteData.comments._value;
                        if (comments) {
                            return JSON.stringify(comments);
                        }
                    }
                    // 尝试从 noteDetailMap 获取
                    if (noteData.noteDetailMap) {
                        const detailMap = noteData.noteDetailMap.value || noteData.noteDetailMap._value || noteData.noteDetailMap;
                        if (detailMap && typeof detailMap === 'object') {
                            const keys = Object.keys(detailMap);
                            if (keys.length > 0) {
                                const detail = detailMap[keys[0]];
                                if (detail && detail.comments) {
                                    return JSON.stringify(detail.comments);
                                }
                            }
                        }
                    }
                }
                return "";
            }""")

            if comments_data:
                comments = json.loads(comments_data)
                if isinstance(comments, list) and len(comments) > 0:
                    logger.info(f"\n💬 评论 ({len(comments)} 条):")
                    for j, comment in enumerate(comments[:10], 1):
                        user = comment.get("userInfo", {})
                        content = comment.get("content", "")
                        likes = comment.get("likeCount", 0)
                        logger.info(f"   {j}. [{user.get('nickname', '匿名')}]: {content[:50]}... (👍{likes})")

                        # 显示子评论
                        sub_comments = comment.get("subComments", [])
                        if sub_comments:
                            for sub in sub_comments[:3]:
                                sub_user = sub.get("userInfo", {})
                                sub_content = sub.get("content", "")
                                logger.info(f"      ↳ [{sub_user.get('nickname', '匿名')}]: {sub_content[:40]}...")
                else:
                    logger.info(f"\n💬 暂无评论")
            else:
                logger.info(f"\n💬 未获取到评论数据")

            await asyncio.sleep(2)  # 请求间隔

        await browser.close()
        logger.info("\n" + "=" * 60)
        logger.info("测试完成!")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test())
