"""飞书多维表格同步逻辑"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from .client import FeishuClient
from utils import logger


class FeishuTableSync:
    """飞书表格数据同步"""

    def __init__(self):
        self.client = FeishuClient()
        # 博主数据缓存（用于获取 last_sync_at）
        self._blogger_record_map: Dict[str, str] = {}  # blogger_id -> record_id
        self._blogger_data_cache: Dict[str, Dict[str, Any]] = {}  # blogger_id -> full data

    def load_existing_data(self):
        """加载已存在的博主数据（用于获取 last_sync_at 进行增量抓取）

        注意：笔记和评论不再全量加载，因为使用增量抓取模式
        """
        logger.info("正在加载博主数据...")

        # 只加载博主数据（需要获取 last_sync_at）
        bloggers = self.client.get_all_records("bloggers")
        for b in bloggers:
            blogger_id = b.get("blogger_id")
            if blogger_id:
                self._blogger_record_map[blogger_id] = b.get("record_id")
                self._blogger_data_cache[blogger_id] = b  # 缓存完整数据
        logger.info(f"已加载 {len(self._blogger_record_map)} 个博主记录")

        # 笔记和评论不再预加载，使用增量抓取模式
        # 增量抓取基于博主的 last_sync_at 时间，只抓取新笔记

    def sync_blogger(self, blogger_data: Dict[str, Any]) -> str:
        """同步博主信息

        Args:
            blogger_data: 博主数据，包含以下字段:
                - blogger_id: 用户ID
                - nickname: 昵称
                - avatar: 头像URL
                - desc: 个人简介
                - fans_count: 粉丝数
                - notes_count: 笔记数
                - liked_count: 获赞数

        Returns:
            记录ID
        """
        blogger_id = blogger_data.get("blogger_id")
        if not blogger_id:
            raise ValueError("blogger_id 不能为空")

        # 添加同步时间
        blogger_data["last_sync_at"] = int(datetime.now().timestamp() * 1000)

        # 检查是否已存在
        if blogger_id in self._blogger_record_map:
            # 更新现有记录
            record_id = self._blogger_record_map[blogger_id]
            blogger_data["record_id"] = record_id
            self.client.update_records("bloggers", [blogger_data])
            logger.info(f"更新博主: {blogger_data.get('nickname', blogger_id)}")
            return record_id
        else:
            # 创建新记录
            record_ids = self.client.create_records("bloggers", [blogger_data])
            if record_ids:
                self._blogger_record_map[blogger_id] = record_ids[0]
                logger.info(f"新增博主: {blogger_data.get('nickname', blogger_id)}")
                return record_ids[0]
            return ""

    def sync_notes(self, notes: List[Dict[str, Any]]) -> int:
        """同步笔记数据（增量模式，直接创建新笔记）

        Args:
            notes: 笔记列表（增量抓取，理论上都是新笔记）

        Returns:
            新增笔记数
        """
        if not notes:
            return 0

        # 添加抓取时间
        for note in notes:
            note["crawl_time"] = int(datetime.now().timestamp() * 1000)

        # 直接批量创建（增量抓取保证都是新笔记）
        self.client.create_records("notes", notes)
        logger.info(f"新增 {len(notes)} 条笔记")

        return len(notes)

    def sync_comments(self, comments: List[Dict[str, Any]]) -> int:
        """同步评论数据（增量模式，直接创建新评论）

        Args:
            comments: 评论列表（来自新笔记，理论上都是新评论）

        Returns:
            新增评论数
        """
        if not comments:
            return 0

        # 添加抓取时间
        for comment in comments:
            comment["crawl_time"] = int(datetime.now().timestamp() * 1000)

        # 分批处理，每批最多500条
        batch_size = 500
        for i in range(0, len(comments), batch_size):
            batch = comments[i:i + batch_size]
            self.client.create_records("comments", batch)

        logger.info(f"新增 {len(comments)} 条评论")

        return len(comments)

    def get_stats(self) -> Dict[str, int]:
        """获取当前数据统计（从飞书实时查询）"""
        # 实时查询飞书获取统计数据
        notes_count = len(self.client.get_all_records("notes"))
        comments_count = len(self.client.get_all_records("comments"))
        return {
            "bloggers": len(self._blogger_record_map),
            "notes": notes_count,
            "comments": comments_count,
        }

    def get_blogger_last_sync_at(self, blogger_id: str) -> Optional[int]:
        """获取博主的上次同步时间

        Args:
            blogger_id: 博主ID

        Returns:
            上次同步时间戳（毫秒），如果不存在返回 None
        """
        if blogger_id in self._blogger_data_cache:
            return self._blogger_data_cache[blogger_id].get("last_sync_at")
        return None

    def is_blogger_exists(self, blogger_id: str) -> bool:
        """检查博主是否已存在"""
        return blogger_id in self._blogger_record_map

    def backfill_blogger_nickname(self, blogger_id: str, nickname: str) -> int:
        """为指定博主的所有笔记回填 blogger_nickname 字段

        Args:
            blogger_id: 博主ID
            nickname: 博主昵称

        Returns:
            更新的笔记数量
        """
        # 获取该博主的所有笔记
        notes = self.client.get_all_records("notes")
        notes_to_update = []

        for note in notes:
            if note.get("blogger_id") == blogger_id:
                # 检查是否缺少 blogger_nickname
                current_nickname = note.get("blogger_nickname", "")
                if not current_nickname or current_nickname != nickname:
                    notes_to_update.append({
                        "record_id": note.get("record_id"),
                        "blogger_nickname": nickname,
                    })

        if notes_to_update:
            # 分批更新
            batch_size = 500
            for i in range(0, len(notes_to_update), batch_size):
                batch = notes_to_update[i:i + batch_size]
                self.client.update_records("notes", batch)

            logger.info(f"已回填 {len(notes_to_update)} 条笔记的博主名称: {nickname}")

        return len(notes_to_update)
