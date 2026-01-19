#!/usr/bin/env python3
"""测试获取博主的笔记详情和评论 - V2 通过点击方式"""
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

        # 访问博主主页
        logger.info(f"\n访问博主主页...")
        await page.goto(BLOGGER_URL, timeout=60000)
        await asyncio.sleep(3)

        # 获取博主信息
        user_data = await page.evaluate("""() => {
            if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.user && window.__INITIAL_STATE__.user.userPageData) {
                const userPageData = window.__INITIAL_STATE__.user.userPageData;
                const data = userPageData.value !== undefined ? userPageData.value : userPageData._value;
                return data ? JSON.stringify(data) : "";
            }
            return "";
        }""")

        if user_data:
            data = json.loads(user_data)
            basic_info = data.get("basicInfo", {})
            logger.info(f"\n👤 博主: {basic_info.get('nickname', 'N/A')}")

        # 查找笔记卡片
        logger.info(f"\n查找笔记卡片...")

        # 等待笔记卡片加载
        try:
            await page.wait_for_selector("section.note-item", timeout=10000)
        except:
            logger.warning("未找到 note-item，尝试其他选择器")

        # 获取所有笔记链接
        note_links = await page.evaluate("""() => {
            const links = [];
            // 尝试多种选择器
            const selectors = [
                'section.note-item a',
                'div[class*="note"] a[href*="/explore/"]',
                'a[href*="/explore/"]',
                'a[href*="/search_result/"]'
            ];

            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    const href = el.getAttribute('href');
                    if (href && href.includes('/explore/')) {
                        links.push(href);
                    }
                });
                if (links.length > 0) break;
            }
            return [...new Set(links)];  // 去重
        }""")

        logger.info(f"找到 {len(note_links)} 个笔记链接")

        if not note_links:
            # 尝试直接从 __INITIAL_STATE__ 获取笔记信息
            logger.info("尝试从页面数据获取笔记...")

            notes_data = await page.evaluate("""() => {
                if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.user && window.__INITIAL_STATE__.user.notes) {
                    const notes = window.__INITIAL_STATE__.user.notes;
                    const data = notes.value !== undefined ? notes.value : notes._value;
                    return data ? JSON.stringify(data) : "";
                }
                return "";
            }""")

            if notes_data:
                raw_notes = json.loads(notes_data)
                notes = []
                for item in raw_notes:
                    if isinstance(item, list):
                        notes.extend(item)
                    else:
                        notes.append(item)

                for note in notes:
                    note_id = note.get("note_id", "") or note.get("id", "")
                    if note_id:
                        # 尝试获取 xsec_token
                        xsec_token = note.get("xsec_token", "")
                        if not xsec_token:
                            # 从当前页面URL获取
                            current_url = page.url
                            if "xsec_token=" in current_url:
                                xsec_token = current_url.split("xsec_token=")[1].split("&")[0]

                        note_links.append(f"/explore/{note_id}?xsec_token={xsec_token}&xsec_source=pc_note")

        # 遍历笔记获取详情
        for i, link in enumerate(note_links[:5], 1):  # 最多处理5条
            logger.info(f"\n{'='*60}")
            logger.info(f"处理笔记 {i}/{len(note_links)}")
            logger.info(f"{'='*60}")

            # 构建完整URL
            if link.startswith("/"):
                full_url = f"https://www.xiaohongshu.com{link}"
            else:
                full_url = link

            logger.info(f"URL: {full_url[:80]}...")

            try:
                await page.goto(full_url, timeout=60000)
                await asyncio.sleep(4)

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
                    logger.info(f"   标题: {note_card.get('title', '无标题')}")
                    logger.info(f"   类型: {note_card.get('type', 'normal')}")

                    desc = note_card.get('desc', '')
                    if desc:
                        logger.info(f"   内容: {desc[:150]}{'...' if len(desc) > 150 else ''}")

                    interact = note_card.get("interactInfo", {})
                    logger.info(f"   👍 点赞: {interact.get('likedCount', 0)}")
                    logger.info(f"   ⭐ 收藏: {interact.get('collectedCount', 0)}")
                    logger.info(f"   💬 评论: {interact.get('commentCount', 0)}")
                    logger.info(f"   🔗 分享: {interact.get('shareCount', 0)}")

                    # 标签
                    tags = note_card.get("tagList", [])
                    if tags:
                        tag_names = [t.get("name", "") for t in tags[:5]]
                        logger.info(f"   🏷️ 标签: {', '.join(tag_names)}")

                    # 图片
                    images = note_card.get("imageList", [])
                    if images:
                        logger.info(f"   📷 图片: {len(images)} 张")

                # 提取评论
                comments_data = await page.evaluate("""() => {
                    if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note) {
                        const noteData = window.__INITIAL_STATE__.note;
                        if (noteData.comments) {
                            const comments = noteData.comments.value || noteData.comments._value;
                            if (comments) return JSON.stringify(comments);
                        }
                    }
                    return "";
                }""")

                if comments_data:
                    comments = json.loads(comments_data)
                    if isinstance(comments, list) and len(comments) > 0:
                        logger.info(f"\n💬 评论 (共 {len(comments)} 条):")
                        for j, comment in enumerate(comments[:5], 1):
                            user = comment.get("userInfo", {})
                            content = comment.get("content", "")
                            likes = comment.get("likeCount", 0)
                            time_str = comment.get("createTime", "")

                            logger.info(f"\n   [{j}] {user.get('nickname', '匿名')} (👍{likes})")
                            logger.info(f"       {content[:80]}{'...' if len(content) > 80 else ''}")

                            # 子评论
                            sub_comments = comment.get("subComments", [])
                            if sub_comments:
                                for sub in sub_comments[:2]:
                                    sub_user = sub.get("userInfo", {})
                                    sub_content = sub.get("content", "")
                                    logger.info(f"       ↳ {sub_user.get('nickname', '匿名')}: {sub_content[:50]}...")
                    else:
                        logger.info(f"\n💬 暂无评论")
                else:
                    logger.info(f"\n💬 评论数据未加载")

            except Exception as e:
                logger.error(f"处理笔记出错: {e}")

            await asyncio.sleep(2)

        await browser.close()
        logger.info("\n" + "=" * 60)
        logger.info("✅ 测试完成!")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test())
