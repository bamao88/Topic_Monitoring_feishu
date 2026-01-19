#!/usr/bin/env python3
"""
调试版本 - 检查页面数据提取
"""
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from utils.logger import logger
from crawler.xhs_crawler import XHSCrawler


async def debug_crawler(url: str):
    """调试爬虫数据提取"""

    # 解析 URL
    url_info = XHSCrawler.parse_creator_url(url)
    user_id = url_info["user_id"]
    xsec_token = url_info.get("xsec_token", "")
    xsec_source = url_info.get("xsec_source", "pc_search")

    logger.info(f"博主ID: {user_id}")

    # 加载 cookie
    cookie_file = PROJECT_ROOT / "config" / "cookie.txt"
    cookie_str = cookie_file.read_text().strip() if cookie_file.exists() else ""

    # 初始化爬虫
    crawler = XHSCrawler(headless=False, cookie_str=cookie_str)

    try:
        await crawler.start()

        # 1. 访问博主主页
        profile_url = f"https://www.xiaohongshu.com/user/profile/{user_id}?xsec_token={xsec_token}&xsec_source={xsec_source}"
        logger.info(f"访问: {profile_url}")
        await crawler.context_page.goto(profile_url, timeout=60000)
        await asyncio.sleep(4)

        # 2. 提取 __INITIAL_STATE__ 全部内容 (处理循环引用)
        logger.info("提取 __INITIAL_STATE__...")
        initial_state = await crawler.context_page.evaluate("""() => {
            if (!window.__INITIAL_STATE__) return null;

            // 处理循环引用的 JSON.stringify
            const seen = new WeakSet();
            const replacer = (key, value) => {
                if (typeof value === 'object' && value !== null) {
                    if (seen.has(value)) {
                        return '[Circular]';
                    }
                    seen.add(value);
                }
                // 处理 Vue ref 对象
                if (value && typeof value === 'object') {
                    if ('_value' in value) return value._value;
                    if ('value' in value && Object.keys(value).length <= 2) return value.value;
                }
                return value;
            };

            try {
                return JSON.stringify(window.__INITIAL_STATE__, replacer, 2);
            } catch (e) {
                return JSON.stringify({error: e.message});
            }
        }""")

        if initial_state:
            state_data = json.loads(initial_state)
            # 保存完整状态
            debug_file = PROJECT_ROOT / "data" / "test" / f"{user_id}_initial_state.json"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            debug_file.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"已保存 __INITIAL_STATE__ 到: {debug_file}")

            # 分析结构
            logger.info(f"顶层键: {list(state_data.keys())}")

            if "user" in state_data:
                user_data = state_data["user"]
                logger.info(f"user 键: {list(user_data.keys()) if isinstance(user_data, dict) else type(user_data)}")

                if "notes" in user_data:
                    notes = user_data["notes"]
                    # 处理可能的 ref 结构
                    if isinstance(notes, dict) and ("value" in notes or "_value" in notes):
                        notes = notes.get("value") or notes.get("_value", [])
                    logger.info(f"笔记数量: {len(notes) if isinstance(notes, list) else 'N/A'}")

                    if isinstance(notes, list) and len(notes) > 0:
                        first_note = notes[0]
                        if isinstance(first_note, list) and len(first_note) > 0:
                            first_note = first_note[0]
                        logger.info(f"第一条笔记键: {list(first_note.keys()) if isinstance(first_note, dict) else type(first_note)}")
                        # 保存第一条笔记样例
                        sample_file = PROJECT_ROOT / "data" / "test" / f"{user_id}_note_sample.json"
                        sample_file.write_text(json.dumps(first_note, ensure_ascii=False, indent=2), encoding="utf-8")
                        logger.info(f"已保存笔记样例到: {sample_file}")
        else:
            logger.error("无法获取 __INITIAL_STATE__")

        # 3. 获取第一条笔记的详情
        notes_data = await crawler._extract_initial_state(crawler.context_page, "user.notes")
        if notes_data and len(notes_data) > 0:
            first_note_data = notes_data[0]
            if isinstance(first_note_data, list) and len(first_note_data) > 0:
                first_note_data = first_note_data[0]

            note_id = first_note_data.get("note_id", "") or first_note_data.get("id", "")
            note_token = first_note_data.get("xsec_token", "") or xsec_token

            logger.info(f"\n尝试获取笔记详情: {note_id}")
            logger.info(f"使用 token: {note_token[:20]}..." if note_token else "无 token")

            # 访问笔记详情页
            note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={note_token}&xsec_source={xsec_source}"
            logger.info(f"访问: {note_url}")
            await crawler.context_page.goto(note_url, timeout=60000)
            await asyncio.sleep(5)

            # 提取笔记详情页的 __INITIAL_STATE__ (处理循环引用)
            note_state = await crawler.context_page.evaluate("""() => {
                if (!window.__INITIAL_STATE__) return null;

                const seen = new WeakSet();
                const replacer = (key, value) => {
                    if (typeof value === 'object' && value !== null) {
                        if (seen.has(value)) return '[Circular]';
                        seen.add(value);
                    }
                    if (value && typeof value === 'object') {
                        if ('_value' in value) return value._value;
                        if ('value' in value && Object.keys(value).length <= 2) return value.value;
                    }
                    return value;
                };

                try {
                    return JSON.stringify(window.__INITIAL_STATE__, replacer, 2);
                } catch (e) {
                    return JSON.stringify({error: e.message});
                }
            }""")

            if note_state:
                note_state_data = json.loads(note_state)
                note_debug_file = PROJECT_ROOT / "data" / "test" / f"{user_id}_note_detail_state.json"
                note_debug_file.write_text(json.dumps(note_state_data, ensure_ascii=False, indent=2), encoding="utf-8")
                logger.info(f"已保存笔记详情 __INITIAL_STATE__ 到: {note_debug_file}")
                logger.info(f"笔记详情顶层键: {list(note_state_data.keys())}")

                if "note" in note_state_data:
                    note_data = note_state_data["note"]
                    logger.info(f"note 键: {list(note_data.keys()) if isinstance(note_data, dict) else type(note_data)}")

                    if "noteDetailMap" in note_data:
                        detail_map = note_data["noteDetailMap"]
                        # 处理 ref 结构
                        if isinstance(detail_map, dict):
                            if "value" in detail_map or "_value" in detail_map:
                                detail_map = detail_map.get("value") or detail_map.get("_value", {})
                            logger.info(f"noteDetailMap 键: {list(detail_map.keys()) if isinstance(detail_map, dict) else type(detail_map)}")

                            if isinstance(detail_map, dict) and len(detail_map) > 0:
                                first_key = list(detail_map.keys())[0]
                                detail = detail_map[first_key]
                                detail_file = PROJECT_ROOT / "data" / "test" / f"{user_id}_note_detail_extracted.json"
                                detail_file.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
                                logger.info(f"已保存提取的笔记详情到: {detail_file}")

                                if isinstance(detail, dict) and "note" in detail:
                                    note_card = detail["note"]
                                    logger.info(f"笔记内容键: {list(note_card.keys())}")
                                    logger.info(f"标题: {note_card.get('title', 'N/A')[:50]}...")
                                    logger.info(f"类型: {note_card.get('type', 'N/A')}")

                                    interact_info = note_card.get("interactInfo", {})
                                    logger.info(f"点赞: {interact_info.get('likedCount', 'N/A')}")
                                    logger.info(f"收藏: {interact_info.get('collectedCount', 'N/A')}")
            else:
                logger.error("无法获取笔记详情页 __INITIAL_STATE__")

    finally:
        await crawler.close()


if __name__ == "__main__":
    url = "https://www.xiaohongshu.com/user/profile/676d709d000000001900a119?xsec_token=ABjQ3ccn8YJ5Usx61h8QS13qJn5X3BDq6dO4D8j5qsKMs%3D&xsec_source=pc_search"
    asyncio.run(debug_crawler(url))
