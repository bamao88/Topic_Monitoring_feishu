# 小红书对标博主内容自动沉淀系统

定期抓取指定小红书博主的内容与评论，结构化写入飞书多维表格，为后续做选题趋势/爆款拆解/评论挖掘提供数据基础。

## 功能特性

- **博主信息抓取**: 粉丝数、笔记数、获赞数等动态数据
- **笔记内容抓取**: 标题、正文、封面、标签、互动数据
- **评论数据抓取**: 一级评论及回复、评论者信息、点赞数
- **飞书多维表格同步**: 自动写入结构化数据，支持增量更新
- **定时自动执行**: 通过 cron 配置定时同步任务

## 数据流程

```
小红书网页 → Playwright 抓取 → 数据结构化 → 飞书多维表格
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd /Volumes/ExtSSD2601/ws/xiaohongshu_bozhu

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装浏览器驱动
playwright install chromium
```

### 2. 配置飞书

1. 登录 [飞书开放平台](https://open.feishu.cn/app)
2. 创建企业自建应用
3. 开通权限: `bitable:app`（多维表格读写）
4. 获取 `App ID` 和 `App Secret`
5. 创建多维表格，获取 `app_token`（URL中的token）
6. 在多维表格中创建3张数据表（博主、笔记、评论）

编辑 `config/feishu_config.py`:

```python
FEISHU_APP_ID = "cli_xxxx"
FEISHU_APP_SECRET = "xxxx"
FEISHU_APP_TOKEN = "VhTkbe4cuaxYWXsLUvecr4Wxnhg"  # 多维表格token

TABLE_IDS = {
    "bloggers": "tblXXX",  # 博主表ID
    "notes": "tblYYY",     # 笔记表ID
    "comments": "tblZZZ",  # 评论表ID
}
```

### 3. 配置小红书 Cookie

1. 在浏览器登录 [小红书网页版](https://www.xiaohongshu.com)
2. 打开开发者工具 (F12) → Application → Cookies
3. 复制所有 Cookie 值

创建 `config/cookie.txt`:
```
web_session=xxxx; a1=xxxx; webId=xxxx; ...
```

或设置环境变量:
```bash
export XHS_COOKIE="web_session=xxxx; a1=xxxx; ..."
```

### 4. 配置博主列表

编辑 `config/bloggers.yaml`:

```yaml
bloggers:
  - url: "https://www.xiaohongshu.com/user/profile/xxx?xsec_token=xxx&xsec_source=pc_note"
    name: "博主昵称"
    sync_comments: true
```

获取博主 URL:
1. 打开小红书网页版
2. 搜索进入目标博主主页
3. 复制浏览器地址栏完整 URL

### 5. 运行同步

```bash
# 测试模式（只同步第一个博主）
python main.py --test

# 正常模式
python main.py

# 无头模式（服务器环境）
python main.py --headless
```

## 定时任务配置

使用脚本自动配置 cron:

```bash
./scripts/setup_cron.sh
```

或手动配置:

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每周一凌晨2点执行）
0 2 * * 1 cd /Volumes/ExtSSD2601/ws/xiaohongshu_bozhu && .venv/bin/python main.py --headless >> logs/cron.log 2>&1
```

常用 cron 配置:
- `0 2 * * 1` - 每周一凌晨2点
- `0 2 * * *` - 每天凌晨2点
- `0 */6 * * *` - 每6小时

## 项目结构

```
xiaohongshu_bozhu/
├── config/
│   ├── base_config.py      # 爬虫配置
│   ├── feishu_config.py    # 飞书配置
│   ├── bloggers.yaml       # 博主列表
│   └── cookie.txt          # 小红书Cookie
├── crawler/
│   ├── xhs_crawler.py      # 小红书爬虫
│   └── data_models.py      # 数据模型
├── feishu/
│   ├── client.py           # 飞书API客户端
│   └── table_sync.py       # 表格同步逻辑
├── sync/
│   └── blogger_sync.py     # 同步协调器
├── scripts/
│   ├── setup_cron.sh       # Cron配置脚本
│   └── run_sync.sh         # 运行脚本
├── utils/
│   └── logger.py           # 日志配置
├── logs/                   # 日志目录
├── main.py                 # 主入口
└── requirements.txt        # 依赖
```

## 飞书多维表格结构

### 博主表 (bloggers)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| blogger_id | 文本 | 小红书用户ID |
| nickname | 文本 | 昵称 |
| avatar | URL | 头像链接 |
| desc | 文本 | 个人简介 |
| fans_count | 数字 | 粉丝数 |
| notes_count | 数字 | 笔记数 |
| liked_count | 数字 | 获赞数 |
| last_sync_at | 日期 | 最后同步时间 |

### 笔记表 (notes)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| note_id | 文本 | 笔记ID |
| blogger_id | 文本 | 博主ID |
| title | 文本 | 标题 |
| desc | 多行文本 | 正文内容 |
| type | 单选 | 图文/视频 |
| cover_url | URL | 封面图 |
| tags | 文本 | 标签列表 |
| liked_count | 数字 | 点赞数 |
| collected_count | 数字 | 收藏数 |
| comment_count | 数字 | 评论数 |
| share_count | 数字 | 分享数 |
| publish_time | 日期 | 发布时间 |
| crawl_time | 日期 | 抓取时间 |
| note_url | URL | 笔记链接 |

### 评论表 (comments)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| comment_id | 文本 | 评论ID |
| note_id | 文本 | 笔记ID |
| parent_id | 文本 | 父评论ID |
| user_id | 文本 | 评论者ID |
| user_nickname | 文本 | 评论者昵称 |
| content | 多行文本 | 评论内容 |
| liked_count | 数字 | 点赞数 |
| ip_location | 文本 | IP属地 |
| create_time | 日期 | 评论时间 |
| crawl_time | 日期 | 抓取时间 |

## 增量更新策略

- **博主信息**: 每次全量更新
- **笔记内容**: 新笔记创建，已有笔记更新互动数据
- **评论数据**: 只新增不存在的评论

## 常见问题

### Cookie 失效

小红书 Cookie 有效期约为30天，失效后需重新获取:
1. 在浏览器重新登录小红书
2. 更新 `config/cookie.txt`

### xsec_token 失效

博主主页 URL 中的 xsec_token 有时效性:
1. 重新访问博主主页
2. 复制新的完整 URL 到配置

### 飞书权限问题

确保应用已开通以下权限:
- `bitable:app` - 读写多维表格

### 抓取失败

1. 检查 Cookie 是否有效
2. 查看 `logs/` 目录下的日志文件
3. 确认网络连接正常

## 日志

日志文件位于 `logs/` 目录:
- `sync_YYYY-MM-DD.log` - 每日同步日志
- `cron.log` - 定时任务日志

查看日志:
```bash
tail -f logs/sync_$(date +%Y-%m-%d).log
```

## 依赖

- Python 3.10+
- playwright - 浏览器自动化
- lark-oapi - 飞书SDK
- pydantic - 数据验证
- loguru - 日志
- pyyaml - YAML解析

## 注意事项

1. 请合理控制抓取频率，避免对小红书服务器造成压力
2. 本项目仅供学习研究使用
3. Cookie 和配置文件包含敏感信息，请勿泄露

## License

MIT
