#!/usr/bin/env python3
"""调试笔记详情提取 - 多种方式"""
import asyncio
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.async_api import async_playwright
from loguru import logger

# Cookie 字符串
COOKIE_STR = (PROJECT_ROOT / "config" / "cookie.txt").read_text().strip()

# 笔记 URL
NOTE_URL = "https://www.xiaohongshu.com/explore/696763a6000000002202fbe7?xsec_token=ABJ7UTxGpQYjzUFtwOyDw7Ac9KQhGtEhbXZy1HEbyLr14=&xsec_source=pc_note"


def parse_cookie_string(cookie_str: str) -> dict:
    cookie_dict = {}
    for item in cookie_str.split("; "):
        if "=" in item:
            key, value = item.split("=", 1)
            cookie_dict[key.strip()] = value.strip()
    return cookie_dict


async def test():
    """调试笔记详情"""
    logger.info("调试笔记详情提取...")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        )

        # 设置 Cookie
        cookie_dict = parse_cookie_string(COOKIE_STR)
        cookies = [{"name": k, "value": v, "domain": ".xiaohongshu.com", "path": "/"} for k, v in cookie_dict.items()]
        await context.add_cookies(cookies)

        # 加载反检测脚本
        stealth_js = PROJECT_ROOT / "MediaCrawler" / "libs" / "stealth.min.js"
        if stealth_js.exists():
            await context.add_init_script(path=str(stealth_js))

        page = await context.new_page()

        logger.info(f"访问笔记: {NOTE_URL}")
        await page.goto(NOTE_URL, timeout=60000)

        # 等待更长时间
        logger.info("等待页面加载...")
        await asyncio.sleep(8)

        # 方法1: 从 DOM 提取信息
        logger.info("\n方法1: 从 DOM 提取...")
        dom_data = await page.evaluate("""() => {
            const result = {};

            // 标题
            const titleEl = document.querySelector('#detail-title') ||
                           document.querySelector('.title') ||
                           document.querySelector('h1');
            result.title = titleEl ? titleEl.textContent.trim() : '';

            // 内容
            const descEl = document.querySelector('#detail-desc') ||
                          document.querySelector('.desc') ||
                          document.querySelector('.note-text');
            result.desc = descEl ? descEl.textContent.trim() : '';

            // 用户
            const userEl = document.querySelector('.author-wrapper .username') ||
                          document.querySelector('.user-name');
            result.user = userEl ? userEl.textContent.trim() : '';

            // 点赞数
            const likeEl = document.querySelector('.like-wrapper .count') ||
                          document.querySelector('[class*="like"] .count');
            result.likes = likeEl ? likeEl.textContent.trim() : '';

            // 收藏数
            const collectEl = document.querySelector('.collect-wrapper .count');
            result.collects = collectEl ? collectEl.textContent.trim() : '';

            // 评论数
            const commentEl = document.querySelector('.chat-wrapper .count');
            result.comments = commentEl ? commentEl.textContent.trim() : '';

            // 检查是否有图片
            const images = document.querySelectorAll('.swiper-slide img, .note-slider img');
            result.imageCount = images.length;

            return result;
        }""")
        logger.info(f"DOM 数据: {json.dumps(dom_data, ensure_ascii=False, indent=2)}")

        # 方法2: 检查 currentNoteId 并重新获取
        logger.info("\n方法2: 检查 currentNoteId...")
        note_id_data = await page.evaluate("""() => {
            if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note) {
                const note = window.__INITIAL_STATE__.note;
                return {
                    currentNoteId: note.currentNoteId,
                    firstNoteId: note.firstNoteId,
                    noteDetailMapKeys: Object.keys(note.noteDetailMap || {}),
                };
            }
            return null;
        }""")
        logger.info(f"Note ID 数据: {json.dumps(note_id_data, ensure_ascii=False, indent=2)}")

        # 方法3: 尝试通过 currentNoteId 获取
        if note_id_data and note_id_data.get("currentNoteId"):
            current_id = note_id_data["currentNoteId"]
            logger.info(f"\n使用 currentNoteId: {current_id}")

            detail_by_id = await page.evaluate(f"""() => {{
                try {{
                    const note = window.__INITIAL_STATE__.note;
                    const map = note.noteDetailMap;
                    const id = "{current_id}";

                    // 尝试多种方式访问
                    let detail = map[id];
                    if (!detail && map._value) detail = map._value[id];
                    if (!detail && map.value) detail = map.value[id];

                    if (detail && detail.note) {{
                        return {{
                            title: detail.note.title,
                            desc: detail.note.desc,
                            type: detail.note.type,
                            interactInfo: detail.note.interactInfo,
                        }};
                    }}
                    return {{ error: "detail not found for id: " + id }};
                }} catch (e) {{
                    return {{ error: e.toString() }};
                }}
            }}""")
            logger.info(f"通过 ID 获取: {json.dumps(detail_by_id, ensure_ascii=False, indent=2)}")

        # 方法4: 截图查看页面实际显示
        screenshot_path = PROJECT_ROOT / "data" / "debug_screenshot.png"
        await page.screenshot(path=str(screenshot_path))
        logger.info(f"\n截图已保存: {screenshot_path}")

        # 方法5: 获取当前页面 URL 看是否被重定向
        current_url = page.url
        logger.info(f"\n当前 URL: {current_url}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test())
