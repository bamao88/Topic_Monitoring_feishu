"""数据模型定义"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class BloggerInfo(BaseModel):
    """博主信息"""
    blogger_id: str = Field(..., description="用户ID")
    nickname: str = Field(default="", description="昵称")
    avatar: str = Field(default="", description="头像URL")
    desc: str = Field(default="", description="个人简介")
    fans_count: int = Field(default=0, description="粉丝数")
    notes_count: int = Field(default=0, description="笔记数")
    liked_count: int = Field(default=0, description="获赞与收藏数")
    ip_location: str = Field(default="", description="IP属地")

    def to_feishu_record(self) -> dict:
        """转换为飞书记录格式"""
        return {
            "blogger_id": self.blogger_id,
            "nickname": self.nickname,
            "avatar": {"link": self.avatar} if self.avatar else None,
            "desc": self.desc,
            "fans_count": self.fans_count,
            "notes_count": self.notes_count,
            "liked_count": self.liked_count,
        }


class NoteInfo(BaseModel):
    """笔记信息"""
    note_id: str = Field(..., description="笔记ID")
    blogger_id: str = Field(default="", description="博主ID")
    title: str = Field(default="", description="标题")
    desc: str = Field(default="", description="正文内容")
    type: str = Field(default="normal", description="笔记类型: normal/video")
    cover_url: str = Field(default="", description="封面图URL")
    image_urls: List[str] = Field(default_factory=list, description="图片链接列表")
    video_url: str = Field(default="", description="视频链接")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    liked_count: int = Field(default=0, description="点赞数")
    collected_count: int = Field(default=0, description="收藏数")
    comment_count: int = Field(default=0, description="评论数")
    share_count: int = Field(default=0, description="分享数")
    publish_time: Optional[int] = Field(default=None, description="发布时间戳(毫秒)")
    xsec_token: str = Field(default="", description="安全token")
    xsec_source: str = Field(default="", description="来源")

    def to_feishu_record(self) -> dict:
        """转换为飞书记录格式"""
        record = {
            "note_id": self.note_id,
            "blogger_id": self.blogger_id,
            "title": self.title,
            "desc": self.desc,
            "type": self.type,
            "cover_url": {"link": self.cover_url} if self.cover_url else None,
            "tags": ",".join(self.tags) if self.tags else "",
            "liked_count": self.liked_count,
            "collected_count": self.collected_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "note_url": f"https://www.xiaohongshu.com/explore/{self.note_id}",
        }
        if self.publish_time:
            record["publish_time"] = self.publish_time
        return record


class CommentInfo(BaseModel):
    """评论信息"""
    comment_id: str = Field(..., description="评论ID")
    note_id: str = Field(..., description="笔记ID")
    parent_id: str = Field(default="", description="父评论ID")
    user_id: str = Field(default="", description="评论者ID")
    user_nickname: str = Field(default="", description="评论者昵称")
    content: str = Field(default="", description="评论内容")
    liked_count: int = Field(default=0, description="点赞数")
    create_time: Optional[int] = Field(default=None, description="评论时间戳(毫秒)")

    def to_feishu_record(self) -> dict:
        """转换为飞书记录格式"""
        record = {
            "comment_id": self.comment_id,
            "note_id": self.note_id,
            "parent_id": self.parent_id,
            "user_id": self.user_id,
            "user_nickname": self.user_nickname,
            "content": self.content,
            "liked_count": self.liked_count,
        }
        if self.create_time:
            record["create_time"] = self.create_time
        return record
