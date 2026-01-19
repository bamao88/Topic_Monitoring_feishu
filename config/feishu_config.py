"""飞书配置"""
import os

# 飞书应用凭证
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "cli_a9805d1addbed00e")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "NmBJylxcYa6h1K4rj80qxfXsnbRrjsd2")

# 多维表格配置 (从表格URL获取)
# URL格式: https://xxx.feishu.cn/base/xxxAPP_TOKEN?table=xxxTABLE_ID
FEISHU_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "VhTkbe4cuaxYWXsLUvecr4Wxnhg")

# 分析报告文档存储文件夹
# 文件夹 URL: https://li4p2wlpvm5.feishu.cn/drive/folder/MxwZf1dLglYkJfd0uP5c35qdnXg
FEISHU_REPORT_FOLDER_TOKEN = os.getenv("FEISHU_REPORT_FOLDER_TOKEN", "MxwZf1dLglYkJfd0uP5c35qdnXg")

# 飞书域名 (用于生成文档链接)
FEISHU_DOMAIN = os.getenv("FEISHU_DOMAIN", "li4p2wlpvm5.feishu.cn")

# 表格ID
TABLE_IDS = {
    "bloggers": os.getenv("FEISHU_TABLE_BLOGGERS", "tbl1igxHSIzgav79"),
    "notes": os.getenv("FEISHU_TABLE_NOTES", "tblwrbjtjRb0Tq1N"),
    "comments": os.getenv("FEISHU_TABLE_COMMENTS", "tbl961MT6VZssl8x"),
}

# 字段映射配置 - 用于创建多维表格时的字段定义
FIELD_DEFINITIONS = {
    "bloggers": [
        {"field_name": "blogger_id", "type": 1, "description": "小红书用户ID"},
        {"field_name": "nickname", "type": 1, "description": "昵称"},
        {"field_name": "avatar", "type": 15, "description": "头像链接"},
        {"field_name": "desc", "type": 1, "description": "个人简介"},
        {"field_name": "fans_count", "type": 2, "description": "粉丝数"},
        {"field_name": "notes_count", "type": 2, "description": "笔记数"},
        {"field_name": "liked_count", "type": 2, "description": "获赞数"},
        {"field_name": "last_sync_at", "type": 5, "description": "最后同步时间"},
        {"field_name": "analysis_doc_url", "type": 15, "description": "拆解分析文档链接"},
    ],
    "notes": [
        {"field_name": "note_id", "type": 1, "description": "笔记ID"},
        {"field_name": "blogger_id", "type": 1, "description": "博主ID"},
        {"field_name": "blogger_nickname", "type": 1, "description": "博主名称"},
        {"field_name": "title", "type": 1, "description": "标题"},
        {"field_name": "desc", "type": 1, "description": "正文内容"},
        {"field_name": "type", "type": 3, "description": "类型(图文/视频)"},
        {"field_name": "cover_url", "type": 15, "description": "封面图"},
        {"field_name": "tags", "type": 1, "description": "标签"},
        {"field_name": "liked_count", "type": 2, "description": "点赞数"},
        {"field_name": "collected_count", "type": 2, "description": "收藏数"},
        {"field_name": "comment_count", "type": 2, "description": "评论数"},
        {"field_name": "share_count", "type": 2, "description": "分享数"},
        {"field_name": "publish_time", "type": 5, "description": "发布时间"},
        {"field_name": "crawl_time", "type": 5, "description": "抓取时间"},
        {"field_name": "note_url", "type": 15, "description": "笔记链接"},
    ],
    "comments": [
        {"field_name": "comment_id", "type": 1, "description": "评论ID"},
        {"field_name": "note_id", "type": 1, "description": "关联笔记ID"},
        {"field_name": "note_title", "type": 1, "description": "笔记标题"},
        {"field_name": "parent_id", "type": 1, "description": "父评论ID"},
        {"field_name": "user_id", "type": 1, "description": "评论者ID"},
        {"field_name": "user_nickname", "type": 1, "description": "评论者昵称"},
        {"field_name": "content", "type": 1, "description": "评论内容"},
        {"field_name": "liked_count", "type": 2, "description": "点赞数"},
        {"field_name": "ip_location", "type": 1, "description": "IP属地"},
        {"field_name": "create_time", "type": 5, "description": "评论时间"},
        {"field_name": "crawl_time", "type": 5, "description": "抓取时间"},
    ],
}
