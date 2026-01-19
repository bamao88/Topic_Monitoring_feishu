#!/usr/bin/env python3
"""
将抓取的数据同步到飞书多维表格

使用方法:
    python sync_to_feishu.py
"""
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger
from feishu.table_sync import FeishuTableSync


def load_crawled_data():
    """加载 MediaCrawler 抓取的数据"""
    data_dir = PROJECT_ROOT / "MediaCrawler" / "data" / "xhs" / "json"

    creators = []
    notes = []
    comments = []

    # 查找最新的数据文件
    creator_files = sorted(data_dir.glob("creator_creators_*.json"), reverse=True)
    content_files = sorted(data_dir.glob("creator_contents_*.json"), reverse=True)
    comment_files = sorted(data_dir.glob("creator_comments_*.json"), reverse=True)

    if creator_files:
        latest_creator = creator_files[0]
        logger.info(f"加载博主数据: {latest_creator.name}")
        with open(latest_creator, "r", encoding="utf-8") as f:
            creators_raw = json.load(f)
            # 去重（按 user_id）
            seen = set()
            for c in creators_raw:
                if c.get("user_id") not in seen:
                    creators.append(c)
                    seen.add(c.get("user_id"))
    else:
        logger.warning("未找到博主数据文件")

    if content_files:
        latest_content = content_files[0]
        logger.info(f"加载笔记数据: {latest_content.name}")
        with open(latest_content, "r", encoding="utf-8") as f:
            notes = json.load(f)
    else:
        logger.warning("未找到笔记数据文件")

    if comment_files:
        latest_comments = comment_files[0]
        logger.info(f"加载评论数据: {latest_comments.name}")
        with open(latest_comments, "r", encoding="utf-8") as f:
            comments = json.load(f)
    else:
        logger.warning("未找到评论数据文件")

    return creators, notes, comments


def transform_note(note: dict, blogger_nickname_map: dict = None) -> dict:
    """转换笔记数据格式以匹配飞书表格字段"""
    # 处理时间戳
    publish_time = note.get("time")
    if publish_time and isinstance(publish_time, int):
        # 已经是毫秒时间戳
        pass

    # 处理 URL 字段 - 飞书 URL 字段需要特殊格式
    cover_url = note.get("image_list", "").split(",")[0] if note.get("image_list") else ""
    note_url = note.get("note_url", "")

    # 获取博主名称
    blogger_id = note.get("user_id", "")
    blogger_nickname = ""
    if blogger_nickname_map:
        blogger_nickname = blogger_nickname_map.get(blogger_id, "")

    return {
        "note_id": note.get("note_id", ""),
        "blogger_id": blogger_id,
        "blogger_nickname": blogger_nickname,  # 添加博主名称
        "title": note.get("title", ""),
        "desc": note.get("desc", ""),
        "type": "视频" if note.get("video_url") else "图文",
        "cover_url": {"text": "封面", "link": cover_url} if cover_url else None,
        "tags": note.get("tag_list", ""),
        "liked_count": int(note.get("liked_count", 0) or 0),
        "collected_count": int(note.get("collected_count", 0) or 0),
        "comment_count": int(note.get("comment_count", 0) or 0),
        "share_count": int(note.get("share_count", 0) or 0),
        "publish_time": publish_time,
        "note_url": {"text": "查看笔记", "link": note_url} if note_url else None,
    }


def transform_comment(comment: dict, note_title_map: dict = None) -> dict:
    """转换评论数据格式以匹配飞书表格字段"""
    # 获取笔记标题
    note_id = comment.get("note_id", "")
    note_title = ""
    if note_title_map:
        note_title = note_title_map.get(note_id, "")

    return {
        "comment_id": comment.get("comment_id", ""),
        "note_id": note_id,
        "note_title": note_title,  # 添加笔记标题
        "parent_id": str(comment.get("parent_comment_id", "")) if comment.get("parent_comment_id") else "",
        "user_id": comment.get("user_id", ""),
        "user_nickname": comment.get("nickname", ""),
        "content": comment.get("content", ""),
        "liked_count": int(comment.get("like_count", 0) or 0),
        "ip_location": comment.get("ip_location", ""),
        "create_time": comment.get("create_time"),
    }


def transform_creator(creator: dict) -> dict:
    """转换博主数据格式以匹配飞书表格字段"""
    avatar = creator.get("avatar", "")

    return {
        "blogger_id": creator.get("user_id", ""),
        "nickname": creator.get("nickname", ""),
        "avatar": {"text": "头像", "link": avatar} if avatar else None,
        "desc": creator.get("desc", ""),
        "fans_count": int(creator.get("fans", 0) or 0),
        "notes_count": 0,  # 需要从笔记数量统计
        "liked_count": int(creator.get("interaction", 0) or 0),
    }


def main():
    print("=" * 60)
    print("同步数据到飞书多维表格")
    print("=" * 60)

    # 加载抓取的数据
    creators_raw, notes_raw, comments_raw = load_crawled_data()

    if not notes_raw and not comments_raw and not creators_raw:
        print("\n没有找到可同步的数据")
        print("请先运行 python run_mediacrawler.py 抓取数据")
        return

    print(f"\n找到 {len(creators_raw)} 个博主, {len(notes_raw)} 条笔记, {len(comments_raw)} 条评论")

    # 初始化同步器
    try:
        sync = FeishuTableSync()
        print("飞书客户端初始化成功")
    except Exception as e:
        print(f"飞书客户端初始化失败: {e}")
        return

    # 加载已存在的数据（用于增量更新）
    print("\n加载已存在的数据...")
    sync.load_existing_data()

    # 构建映射表
    blogger_nickname_map = {c.get("user_id"): c.get("nickname", "") for c in creators_raw}
    note_title_map = {n.get("note_id"): n.get("title", "") for n in notes_raw}

    # 同步博主信息
    print("\n[同步博主信息]")
    for creator in creators_raw:
        blogger_info = transform_creator(creator)
        # 统计该博主的笔记数
        blogger_id = blogger_info.get("blogger_id")
        notes_count = sum(1 for n in notes_raw if n.get("user_id") == blogger_id)
        blogger_info["notes_count"] = notes_count

        if blogger_info.get("blogger_id"):
            # 检查博主是否已存在，如果存在则回填历史笔记的 blogger_nickname
            nickname = blogger_info.get("nickname", "")
            if sync.is_blogger_exists(blogger_id):
                last_sync_at = sync.get_blogger_last_sync_at(blogger_id)
                if last_sync_at:
                    last_sync_time = datetime.fromtimestamp(last_sync_at / 1000)
                    print(f"  博主已存在，上次同步: {last_sync_time.strftime('%Y-%m-%d %H:%M:%S')}")

                # 回填历史笔记的 blogger_nickname 字段
                backfill_count = sync.backfill_blogger_nickname(blogger_id, nickname)
                if backfill_count > 0:
                    print(f"    - 已回填 {backfill_count} 条历史笔记的博主名称")

            sync.sync_blogger(blogger_info)
            print(f"  博主: {blogger_info.get('nickname', 'Unknown')}")
            print(f"    - 简介: {blogger_info.get('desc', '')[:30]}...")
            print(f"    - 粉丝: {blogger_info.get('fans_count')}, 获赞: {blogger_info.get('liked_count')}, 笔记: {notes_count}")

    # 同步笔记（添加博主名称）
    print("\n[同步笔记数据]")
    notes_transformed = [transform_note(n, blogger_nickname_map) for n in notes_raw]
    new_notes_count = sync.sync_notes(notes_transformed)
    print(f"  新增: {new_notes_count} 条")
    print(f"  更新: {len(notes_transformed) - new_notes_count} 条")

    # 同步评论（添加笔记标题）
    print("\n[同步评论数据]")
    comments_transformed = [transform_comment(c, note_title_map) for c in comments_raw]
    new_comments_count = sync.sync_comments(comments_transformed)
    print(f"  新增: {new_comments_count} 条")

    # 统计
    stats = sync.get_stats()
    print("\n" + "=" * 60)
    print("同步完成!")
    print("=" * 60)
    print(f"飞书表格数据统计:")
    print(f"  博主: {stats['bloggers']} 个")
    print(f"  笔记: {stats['notes']} 条")
    print(f"  评论: {stats['comments']} 条")
    print(f"\n查看数据: https://li4p2wlpvm5.feishu.cn/base/VhTkbe4cuaxYWXsLUvecr4Wxnhg")


if __name__ == "__main__":
    main()
