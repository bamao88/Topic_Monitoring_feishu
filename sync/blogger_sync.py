"""博主数据同步模块"""
import asyncio
import os
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler import MediaCrawlerAdapter, BloggerInfo, NoteInfo, CommentInfo
from feishu import FeishuTableSync
from utils.logger import logger

# 导入致命错误类型
try:
    from MediaCrawler.media_platform.xhs.exception import FatalCrawlerError, CaptchaRequiredError, CookieExpiredError
except ImportError:
    # 如果导入失败，定义本地版本
    class FatalCrawlerError(Exception):
        pass
    class CaptchaRequiredError(FatalCrawlerError):
        pass
    class CookieExpiredError(FatalCrawlerError):
        pass

# 爬取配置
CRAWLER_MAX_NOTES_COUNT = 100
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 100
CRAWLER_MAX_SLEEP_SEC = 2
HEADLESS = False

# 错误处理配置
MAX_CONSECUTIVE_FAILURES = 3  # 连续失败次数上限，超过则停止


def load_bloggers_config() -> List[Dict[str, Any]]:
    """加载博主配置"""
    config_path = PROJECT_ROOT / "config" / "bloggers.yaml"
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        return []

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    bloggers = config.get("bloggers", [])
    # 过滤掉空的配置
    return [b for b in bloggers if b.get("url")]


def load_cookie() -> str:
    """从环境变量或配置文件加载 Cookie"""
    # 优先从环境变量获取
    cookie = os.getenv("XHS_COOKIE", "")
    if cookie:
        return cookie

    # 从配置文件获取
    cookie_file = PROJECT_ROOT / "config" / "cookie.txt"
    if cookie_file.exists():
        return cookie_file.read_text().strip()

    return ""


async def sync_single_blogger(
    crawler: MediaCrawlerAdapter,
    feishu_sync: FeishuTableSync,
    blogger_config: Dict[str, Any],
) -> Dict[str, int]:
    """同步单个博主的数据

    Args:
        crawler: 爬虫实例
        feishu_sync: 飞书同步实例
        blogger_config: 博主配置

    Returns:
        同步统计信息
    """
    stats = {"notes": 0, "comments": 0}

    url = blogger_config.get("url", "")
    name = blogger_config.get("name", "")
    sync_comments = blogger_config.get("sync_comments", True)

    # 解析URL
    url_info = MediaCrawlerAdapter.parse_creator_url(url)
    if not url_info.get("user_id"):
        logger.error(f"无法解析博主URL: {url}")
        return stats

    user_id = url_info["user_id"]
    xsec_token = url_info.get("xsec_token", "")
    xsec_source = url_info.get("xsec_source", "pc_note")

    logger.info(f"开始同步博主: {name or user_id}")

    # 获取上次同步时间（用于增量抓取）
    last_sync_at = feishu_sync.get_blogger_last_sync_at(user_id)
    if last_sync_at:
        logger.info(f"上次同步时间: {last_sync_at}，将只抓取此后的新笔记")
    else:
        # 首次同步：只抓取近6个月的笔记
        from datetime import datetime, timedelta
        six_months_ago = datetime.now() - timedelta(days=180)
        last_sync_at = int(six_months_ago.timestamp() * 1000)
        logger.info(f"首次同步，将只抓取近6个月的笔记 (since: {last_sync_at})")

    # 1. 获取博主信息
    blogger_info = await crawler.get_blogger_info(
        user_id=user_id,
        xsec_token=xsec_token,
        xsec_source=xsec_source,
    )

    if blogger_info:
        feishu_sync.sync_blogger(blogger_info.to_feishu_record())
        logger.info(f"博主信息已同步: {blogger_info.nickname} (粉丝: {blogger_info.fans_count})")
    else:
        logger.warning(f"无法获取博主信息: {user_id}")

    await asyncio.sleep(CRAWLER_MAX_SLEEP_SEC)

    # 2. 获取博主笔记和评论（增量模式）
    notes, comments = await crawler.get_blogger_notes_with_details(
        user_id=user_id,
        xsec_token=xsec_token,
        xsec_source=xsec_source,
        max_count=CRAWLER_MAX_NOTES_COUNT,
        crawl_interval=CRAWLER_MAX_SLEEP_SEC,
        fetch_comments=sync_comments,
        since_time=last_sync_at,  # 增量抓取：只获取上次同步后的新笔记
    )

    # 3. 同步笔记（填入博主昵称）
    if notes:
        blogger_nickname = blogger_info.nickname if blogger_info else ""
        note_records = []
        for n in notes:
            n.blogger_nickname = blogger_nickname  # 填入博主昵称
            note_records.append(n.to_feishu_record())
        new_count = feishu_sync.sync_notes(note_records)
        stats["notes"] = new_count
        logger.info(f"笔记同步完成: 新增 {new_count} 条")

    # 4. 同步评论
    if comments:
        comment_records = [c.to_feishu_record() for c in comments]
        new_count = feishu_sync.sync_comments(comment_records)
        stats["comments"] = new_count
        logger.info(f"评论同步完成: 新增 {new_count} 条")

    return stats


async def sync_bloggers(test_mode: bool = False, cookie_str: str = ""):
    """同步所有博主数据

    Args:
        test_mode: 测试模式，只同步第一个博主
        cookie_str: Cookie 字符串，如果不提供则从环境变量或配置文件读取
    """
    logger.info("=" * 50)
    logger.info("开始博主数据同步任务")
    logger.info("=" * 50)

    # 加载博主配置
    bloggers = load_bloggers_config()
    if not bloggers:
        logger.error("没有配置任何博主，请编辑 config/bloggers.yaml")
        return

    if test_mode:
        bloggers = bloggers[:1]
        logger.info("测试模式: 只同步第一个博主")

    logger.info(f"共需同步 {len(bloggers)} 个博主")

    # 加载 Cookie
    if not cookie_str:
        cookie_str = load_cookie()

    if not cookie_str:
        logger.error("未提供 Cookie，请设置 XHS_COOKIE 环境变量或创建 config/cookie.txt 文件")
        return

    # 初始化飞书同步
    try:
        feishu_sync = FeishuTableSync()
        feishu_sync.load_existing_data()
    except Exception as e:
        logger.error(f"初始化飞书同步失败: {e}")
        logger.error("请检查飞书配置是否正确")
        return

    # 初始化爬虫（使用 MediaCrawler API 方案，返回正确的 xsec_token）
    crawler = MediaCrawlerAdapter(headless=HEADLESS, cookie_str=cookie_str)

    try:
        await crawler.start()

        total_stats = {"notes": 0, "comments": 0}
        consecutive_failures = 0  # 连续失败计数

        for i, blogger in enumerate(bloggers, 1):
            logger.info(f"[{i}/{len(bloggers)}] 处理博主: {blogger.get('name', blogger.get('url', ''))}")

            try:
                stats = await sync_single_blogger(crawler, feishu_sync, blogger)
                total_stats["notes"] += stats["notes"]
                total_stats["comments"] += stats["comments"]
                consecutive_failures = 0  # 成功则重置计数

            except (CaptchaRequiredError, CookieExpiredError) as e:
                # 致命错误，立即停止整个程序
                logger.error("=" * 50)
                logger.error(f"致命错误，停止爬取: {e}")
                logger.error("请检查 Cookie 是否有效，或稍后重试")
                logger.error("=" * 50)
                break

            except FatalCrawlerError as e:
                # 其他致命错误
                logger.error(f"致命错误，停止爬取: {e}")
                break

            except Exception as e:
                consecutive_failures += 1
                logger.error(f"同步博主失败 ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): {e}")

                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error("=" * 50)
                    logger.error(f"连续失败 {MAX_CONSECUTIVE_FAILURES} 次，停止爬取")
                    logger.error("可能原因: Cookie 过期、IP 被限制、网络问题")
                    logger.error("请检查 Cookie 是否有效，或稍后重试")
                    logger.error("=" * 50)
                    break
                continue

            # 博主之间等待
            if i < len(bloggers):
                await asyncio.sleep(CRAWLER_MAX_SLEEP_SEC * 2)

        logger.info("=" * 50)
        logger.info("同步任务完成!")
        logger.info(f"总计: 新增笔记 {total_stats['notes']} 条, 新增评论 {total_stats['comments']} 条")
        logger.info(f"当前数据: {feishu_sync.get_stats()}")
        logger.info("=" * 50)

    finally:
        await crawler.close()
