"""从飞书获取博主分析数据"""
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from feishu import FeishuClient
from utils.logger import logger


@dataclass
class BloggerInfo:
    """博主信息数据结构"""
    blogger_id: str
    nickname: str = ""
    avatar: str = ""
    desc: str = ""
    fans_count: int = 0
    notes_count: int = 0
    liked_count: int = 0
    last_sync_at: int = 0
    record_id: str = ""

    @classmethod
    def from_feishu_record(cls, record: Dict[str, Any]) -> "BloggerInfo":
        """从飞书记录创建 BloggerInfo"""
        return cls(
            blogger_id=str(record.get("blogger_id", "")),
            nickname=str(record.get("nickname", "")),
            avatar=str(record.get("avatar", "")),
            desc=str(record.get("desc", "")),
            fans_count=int(record.get("fans_count", 0) or 0),
            notes_count=int(record.get("notes_count", 0) or 0),
            liked_count=int(record.get("liked_count", 0) or 0),
            last_sync_at=int(record.get("last_sync_at", 0) or 0),
            record_id=str(record.get("record_id", "")),
        )


@dataclass
class NoteInfo:
    """笔记信息数据结构"""
    note_id: str
    blogger_id: str = ""
    title: str = ""
    desc: str = ""
    type: str = ""  # 图文/视频
    cover_url: str = ""
    tags: str = ""
    liked_count: int = 0
    collected_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    publish_time: int = 0
    crawl_time: int = 0
    note_url: str = ""
    record_id: str = ""

    @classmethod
    def from_feishu_record(cls, record: Dict[str, Any]) -> "NoteInfo":
        """从飞书记录创建 NoteInfo"""
        return cls(
            note_id=str(record.get("note_id", "")),
            blogger_id=str(record.get("blogger_id", "")),
            title=str(record.get("title", "")),
            desc=str(record.get("desc", "")),
            type=str(record.get("type", "")),
            cover_url=str(record.get("cover_url", "")),
            tags=str(record.get("tags", "")),
            liked_count=int(record.get("liked_count", 0) or 0),
            collected_count=int(record.get("collected_count", 0) or 0),
            comment_count=int(record.get("comment_count", 0) or 0),
            share_count=int(record.get("share_count", 0) or 0),
            publish_time=int(record.get("publish_time", 0) or 0),
            crawl_time=int(record.get("crawl_time", 0) or 0),
            note_url=str(record.get("note_url", "")),
            record_id=str(record.get("record_id", "")),
        )

    @property
    def total_interactions(self) -> int:
        """总互动数"""
        return self.liked_count + self.collected_count + self.comment_count + self.share_count


@dataclass
class CommentInfo:
    """评论信息数据结构"""
    comment_id: str
    note_id: str = ""
    parent_id: str = ""
    user_id: str = ""
    user_nickname: str = ""
    content: str = ""
    liked_count: int = 0
    ip_location: str = ""
    create_time: int = 0
    crawl_time: int = 0
    record_id: str = ""

    @classmethod
    def from_feishu_record(cls, record: Dict[str, Any]) -> "CommentInfo":
        """从飞书记录创建 CommentInfo"""
        return cls(
            comment_id=str(record.get("comment_id", "")),
            note_id=str(record.get("note_id", "")),
            parent_id=str(record.get("parent_id", "")),
            user_id=str(record.get("user_id", "")),
            user_nickname=str(record.get("user_nickname", "")),
            content=str(record.get("content", "")),
            liked_count=int(record.get("liked_count", 0) or 0),
            ip_location=str(record.get("ip_location", "")),
            create_time=int(record.get("create_time", 0) or 0),
            crawl_time=int(record.get("crawl_time", 0) or 0),
            record_id=str(record.get("record_id", "")),
        )


@dataclass
class BloggerAnalysisData:
    """博主分析所需的全部数据"""
    blogger: BloggerInfo
    notes: List[NoteInfo] = field(default_factory=list)
    comments: List[CommentInfo] = field(default_factory=list)


class AnalysisDataFetcher:
    """从飞书获取分析数据"""

    def __init__(self):
        self.client = FeishuClient()
        self._bloggers_cache: Optional[List[Dict]] = None
        self._notes_cache: Optional[List[Dict]] = None
        self._comments_cache: Optional[List[Dict]] = None

    def _load_all_data(self):
        """加载所有数据到缓存"""
        if self._bloggers_cache is None:
            logger.info("正在加载博主数据...")
            self._bloggers_cache = self.client.get_all_records("bloggers")
            logger.info(f"已加载 {len(self._bloggers_cache)} 个博主")

        if self._notes_cache is None:
            logger.info("正在加载笔记数据...")
            self._notes_cache = self.client.get_all_records("notes")
            logger.info(f"已加载 {len(self._notes_cache)} 条笔记")

        if self._comments_cache is None:
            logger.info("正在加载评论数据...")
            self._comments_cache = self.client.get_all_records("comments")
            logger.info(f"已加载 {len(self._comments_cache)} 条评论")

    def get_all_bloggers(self) -> List[BloggerInfo]:
        """获取所有博主列表"""
        self._load_all_data()
        return [BloggerInfo.from_feishu_record(b) for b in self._bloggers_cache]

    def get_blogger_data(self, blogger_id: str) -> Optional[BloggerAnalysisData]:
        """获取博主的全部数据（博主信息 + 笔记 + 评论）

        Args:
            blogger_id: 博主ID

        Returns:
            BloggerAnalysisData 或 None（如果博主不存在）
        """
        self._load_all_data()

        # 查找博主
        blogger_record = None
        for b in self._bloggers_cache:
            if b.get("blogger_id") == blogger_id:
                blogger_record = b
                break

        if not blogger_record:
            logger.warning(f"未找到博主: {blogger_id}")
            return None

        blogger = BloggerInfo.from_feishu_record(blogger_record)

        # 获取博主的所有笔记
        notes = []
        note_ids = set()
        for n in self._notes_cache:
            if n.get("blogger_id") == blogger_id:
                note = NoteInfo.from_feishu_record(n)
                notes.append(note)
                note_ids.add(note.note_id)

        # 获取笔记的所有评论
        comments = []
        for c in self._comments_cache:
            if c.get("note_id") in note_ids:
                comments.append(CommentInfo.from_feishu_record(c))

        logger.info(f"博主 {blogger.nickname} 数据: {len(notes)} 条笔记, {len(comments)} 条评论")

        return BloggerAnalysisData(
            blogger=blogger,
            notes=notes,
            comments=comments,
        )

    def refresh_cache(self):
        """刷新缓存"""
        self._bloggers_cache = None
        self._notes_cache = None
        self._comments_cache = None
        self._load_all_data()
