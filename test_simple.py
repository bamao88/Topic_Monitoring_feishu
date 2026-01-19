#!/usr/bin/env python3
"""简单测试 - 直接通过浏览器获取博主信息"""
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
    """通过浏览器直接获取博主信息"""
    logger.info("开始测试...")

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

        # 直接访问博主主页
        logger.info(f"访问博主主页: {BLOGGER_URL}")
        await page.goto(BLOGGER_URL, timeout=60000)
        await asyncio.sleep(5)  # 等待页面加载

        # 从页面获取 __INITIAL_STATE__
        logger.info("提取页面数据...")

        try:
            # 获取用户基本信息
            user_data = await page.evaluate("""() => {
                if (window.__INITIAL_STATE__ &&
                    window.__INITIAL_STATE__.user &&
                    window.__INITIAL_STATE__.user.userPageData) {
                    const userPageData = window.__INITIAL_STATE__.user.userPageData;
                    const data = userPageData.value !== undefined ? userPageData.value : userPageData._value;
                    if (data) {
                        return JSON.stringify(data);
                    }
                }
                return "";
            }""")

            if user_data:
                data = json.loads(user_data)
                logger.info("=" * 50)
                logger.info("✅ 获取博主信息成功!")
                logger.info("=" * 50)

                basic_info = data.get("basicInfo", {})
                interactions = data.get("interactions", [])

                logger.info(f"昵称: {basic_info.get('nickname', 'N/A')}")
                logger.info(f"小红书号: {basic_info.get('redId', 'N/A')}")
                logger.info(f"简介: {basic_info.get('desc', 'N/A')}")
                logger.info(f"IP属地: {basic_info.get('ipLocation', 'N/A')}")

                for item in interactions:
                    logger.info(f"{item.get('name', '')}: {item.get('count', 0)}")
            else:
                logger.warning("未能从页面获取用户数据")

            # 获取笔记列表
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

            if notes_data:
                notes = json.loads(notes_data)
                # 展平数组
                flat_notes = []
                for item in notes:
                    if isinstance(item, list):
                        flat_notes.extend(item)
                    else:
                        flat_notes.append(item)

                logger.info("=" * 50)
                logger.info(f"✅ 获取到 {len(flat_notes)} 条笔记")
                logger.info("=" * 50)

                for i, note in enumerate(flat_notes[:5], 1):
                    title = note.get("display_title", "") or note.get("title", "无标题")
                    liked = note.get("liked_count", 0) or note.get("interact_info", {}).get("liked_count", 0)
                    logger.info(f"{i}. {title[:40]}... (点赞: {liked})")
            else:
                logger.warning("未能从页面获取笔记数据")

        except Exception as e:
            logger.error(f"提取数据出错: {e}")

        await browser.close()
        logger.info("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(test())
