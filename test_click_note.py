#!/usr/bin/env python3
"""通过点击方式访问笔记 - 模拟真实用户行为"""
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

# 博主 URL
BLOGGER_URL = "https://www.xiaohongshu.com/user/profile/695b82df0000000037031eca?xsec_token=ABJ7UTxGpQYjzUFtwOyDw7Ac9KQhGtEhbXZy1HEbyLr14=&xsec_source=pc_note"


def parse_cookie_string(cookie_str: str) -> dict:
    cookie_dict = {}
    for item in cookie_str.split("; "):
        if "=" in item:
            key, value = item.split("=", 1)
            cookie_dict[key.strip()] = value.strip()
    return cookie_dict


async def test():
    """通过点击方式访问笔记"""
    logger.info("通过点击方式访问笔记...")

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

        # 1. 访问博主主页
        logger.info(f"访问博主主页: {BLOGGER_URL}")
        await page.goto(BLOGGER_URL, timeout=60000)
        await asyncio.sleep(5)

        # 2. 查找笔记卡片
        logger.info("查找笔记卡片...")

        # 等待笔记列表加载
        try:
            await page.wait_for_selector("section.note-item", timeout=10000)
            logger.info("找到笔记列表")
        except:
            logger.warning("未找到 section.note-item")

        # 获取笔记卡片数量
        note_count = await page.evaluate("""() => {
            const items = document.querySelectorAll('section.note-item');
            return items.length;
        }""")
        logger.info(f"找到 {note_count} 个笔记卡片")

        all_notes = []

        if note_count > 0:
            # 只处理第一条
            logger.info(f"\n{'='*50}")
            logger.info(f"处理笔记 1/{note_count}")
            logger.info(f"{'='*50}")

            # 点击笔记
            await page.click("section.note-item:first-child")
            await asyncio.sleep(5)

            # 先检查数据结构
            debug_info = await page.evaluate("""() => {
                const result = {
                    hasInitialState: !!window.__INITIAL_STATE__,
                    hasNote: false,
                    currentNoteId: null,
                    noteDetailMapKeys: [],
                    mapType: null,
                };

                if (window.__INITIAL_STATE__) {
                    result.hasNote = !!window.__INITIAL_STATE__.note;

                    if (window.__INITIAL_STATE__.note) {
                        const note = window.__INITIAL_STATE__.note;
                        result.currentNoteId = note.currentNoteId;

                        if (note.noteDetailMap) {
                            result.mapType = typeof note.noteDetailMap;
                            result.mapHasValue = 'value' in note.noteDetailMap;
                            result.mapHas_Value = '_value' in note.noteDetailMap;

                            // 尝试获取 keys
                            try {
                                const map = note.noteDetailMap._value || note.noteDetailMap.value || note.noteDetailMap;
                                if (map && typeof map === 'object') {
                                    result.noteDetailMapKeys = Object.keys(map);
                                }
                            } catch (e) {
                                result.mapError = e.toString();
                            }
                        }
                    }
                }

                return result;
            }""")

            logger.info(f"调试信息: {json.dumps(debug_info, ensure_ascii=False, indent=2)}")

            # 使用 currentNoteId 获取详情
            if debug_info.get("currentNoteId"):
                note_id = debug_info["currentNoteId"]
                logger.info(f"使用 noteId: {note_id}")

                note_data = await page.evaluate(f"""() => {{
                    try {{
                        const noteState = window.__INITIAL_STATE__.note;
                        const noteId = "{note_id}";
                        const map = noteState.noteDetailMap;

                        // 获取详情
                        let detail = null;
                        if (map._value && map._value[noteId]) {{
                            detail = map._value[noteId];
                        }} else if (map.value && map.value[noteId]) {{
                            detail = map.value[noteId];
                        }} else if (map[noteId]) {{
                            detail = map[noteId];
                        }}

                        if (!detail) {{
                            return {{ error: "detail not found", noteId: noteId, availableKeys: Object.keys(map._value || map.value || map) }};
                        }}

                        if (!detail.note) {{
                            return {{ error: "detail.note not found", detailKeys: Object.keys(detail) }};
                        }}

                        const note = detail.note;
                        return {{
                            noteId: noteId,
                            title: note.title || '',
                            desc: note.desc || '',
                            type: note.type || 'normal',
                            time: note.time || '',
                            user: note.user ? {{
                                userId: note.user.userId || '',
                                nickname: note.user.nickname || '',
                            }} : null,
                            interact: note.interactInfo ? {{
                                likedCount: note.interactInfo.likedCount || 0,
                                collectedCount: note.interactInfo.collectedCount || 0,
                                commentCount: note.interactInfo.commentCount || 0,
                                shareCount: note.interactInfo.shareCount || 0,
                            }} : null,
                            tags: (note.tagList || []).map(t => t.name || '').filter(n => n),
                            imageCount: (note.imageList || []).length,
                            source: '__INITIAL_STATE__',
                        }};
                    }} catch (e) {{
                        return {{ error: e.toString() }};
                    }}
                }}""")

                logger.info(f"\n提取到的数据:")
                logger.info(json.dumps(note_data, ensure_ascii=False, indent=2))

                if note_data and not note_data.get("error"):
                    all_notes.append(note_data)

            # 截图
            screenshot_path = PROJECT_ROOT / "data" / "note_detail_screenshot.png"
            await page.screenshot(path=str(screenshot_path))
            logger.info(f"\n截图已保存: {screenshot_path}")

        # 保存所有数据
        output_file = PROJECT_ROOT / "data" / "notes_clicked.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_notes, f, ensure_ascii=False, indent=2)
        logger.info(f"\n所有数据已保存: {output_file}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test())
