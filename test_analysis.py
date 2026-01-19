#!/usr/bin/env python3
"""
测试分析报告生成 - 直接抓取数据并分析，可选上传到飞书
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from utils.logger import logger
from crawler import XHSCrawler, MediaCrawlerAdapter, BloggerInfo as CrawlerBloggerInfo, NoteInfo as CrawlerNoteInfo, CommentInfo as CrawlerCommentInfo

# Analysis imports
from analysis.data_fetcher import BloggerInfo, NoteInfo, CommentInfo, BloggerAnalysisData
from analysis.report_generator import BloggerReportGenerator
from analysis.analyzers import (
    BasicInfoAnalyzer,
    AccountPositionAnalyzer,
    TopicAnalyzer,
    ContentFormatAnalyzer,
    CopywritingAnalyzer,
    OperationsAnalyzer,
    ViralNotesAnalyzer,
    EvaluationAnalyzer,
)


def convert_crawler_to_analysis_blogger(crawler_blogger: CrawlerBloggerInfo) -> BloggerInfo:
    """将爬虫博主数据转换为分析数据格式"""
    return BloggerInfo(
        blogger_id=crawler_blogger.blogger_id,
        nickname=crawler_blogger.nickname,
        avatar=crawler_blogger.avatar,
        desc=crawler_blogger.desc,
        fans_count=crawler_blogger.fans_count,
        notes_count=crawler_blogger.notes_count,
        liked_count=crawler_blogger.liked_count,
    )


def convert_crawler_to_analysis_note(crawler_note: CrawlerNoteInfo) -> NoteInfo:
    """将爬虫笔记数据转换为分析数据格式"""
    # 处理类型
    note_type = "视频" if crawler_note.type == "video" else "图文"
    # 处理标签
    tags = ",".join(crawler_note.tags) if crawler_note.tags else ""

    return NoteInfo(
        note_id=crawler_note.note_id,
        blogger_id=crawler_note.blogger_id,
        title=crawler_note.title,
        desc=crawler_note.desc,
        type=note_type,
        cover_url=crawler_note.cover_url,
        tags=tags,
        liked_count=crawler_note.liked_count,
        collected_count=crawler_note.collected_count,
        comment_count=crawler_note.comment_count,
        share_count=crawler_note.share_count,
        publish_time=crawler_note.publish_time or 0,
        note_url=f"https://www.xiaohongshu.com/explore/{crawler_note.note_id}",
    )


def convert_crawler_to_analysis_comment(crawler_comment: CrawlerCommentInfo) -> CommentInfo:
    """将爬虫评论数据转换为分析数据格式"""
    return CommentInfo(
        comment_id=crawler_comment.comment_id,
        note_id=crawler_comment.note_id,
        parent_id=crawler_comment.parent_id,
        user_id=crawler_comment.user_id,
        user_nickname=crawler_comment.user_nickname,
        content=crawler_comment.content,
        liked_count=crawler_comment.liked_count,
        create_time=crawler_comment.create_time or 0,
    )


def run_analysis(data: BloggerAnalysisData) -> tuple[Path, str]:
    """运行分析并生成报告

    Returns:
        (report_path, blogger_name) 元组
    """
    logger.info(f"开始分析博主: {data.blogger.nickname}")
    logger.info(f"数据: {len(data.notes)} 条笔记, {len(data.comments)} 条评论")

    # 初始化分析器
    basic_analyzer = BasicInfoAnalyzer()
    position_analyzer = AccountPositionAnalyzer()
    topic_analyzer = TopicAnalyzer()
    format_analyzer = ContentFormatAnalyzer()
    copywriting_analyzer = CopywritingAnalyzer()
    operations_analyzer = OperationsAnalyzer()
    viral_analyzer = ViralNotesAnalyzer()
    evaluation_analyzer = EvaluationAnalyzer()

    # 执行各维度分析
    logger.info("分析基础信息...")
    basic_info = basic_analyzer.analyze(data)

    logger.info("分析账号定位...")
    account_position = position_analyzer.analyze(data)

    logger.info("分析选题内容...")
    topic = topic_analyzer.analyze(data)

    logger.info("分析内容形式...")
    content_format = format_analyzer.analyze(data)

    logger.info("分析文案结构...")
    copywriting = copywriting_analyzer.analyze(data)

    logger.info("分析运营策略...")
    operations = operations_analyzer.analyze(data)

    logger.info("分析爆款笔记...")
    viral = viral_analyzer.analyze(data)

    logger.info("生成综合评估...")
    evaluation = evaluation_analyzer.analyze(
        basic_info=basic_info,
        account_position=account_position,
        topic=topic,
        content_format=content_format,
        copywriting=copywriting,
        operations=operations,
        viral=viral,
    )

    # 生成报告
    logger.info("生成分析报告...")
    generator = BloggerReportGenerator()
    report_path = generator.generate(
        blogger_id=data.blogger.blogger_id,
        basic_info=basic_info,
        account_position=account_position,
        topic=topic,
        content_format=content_format,
        copywriting=copywriting,
        operations=operations,
        viral=viral,
        evaluation=evaluation,
    )

    return report_path, data.blogger.nickname


async def crawl_and_analyze(
    url: str,
    cookie_str: str = "",
    months: int = 6,
    max_notes: int = 500,
    fetch_comments: bool = False,
    use_api: bool = True,
    upload_to_feishu: bool = False,
    sync_to_feishu: bool = False,
) -> Optional[Path]:
    """抓取博主数据并分析

    Args:
        url: 博主主页URL
        cookie_str: Cookie 字符串
        months: 抓取近几个月的笔记，默认6个月
        max_notes: 最大抓取笔记数上限，默认500
        fetch_comments: 是否抓取评论
        use_api: 是否使用 API 模式（MediaCrawler），默认 True
        upload_to_feishu: 是否上传报告到飞书，默认 False
        sync_to_feishu: 是否同步数据到飞书多维表格，默认 False
    """

    # 解析 URL
    url_info = MediaCrawlerAdapter.parse_creator_url(url) if use_api else XHSCrawler.parse_creator_url(url)
    if not url_info.get("user_id"):
        logger.error(f"无法解析博主URL: {url}")
        return None

    user_id = url_info["user_id"]
    xsec_token = url_info.get("xsec_token", "")
    xsec_source = url_info.get("xsec_source", "pc_search")

    logger.info(f"博主ID: {user_id}")
    logger.info(f"xsec_token: {xsec_token[:20]}..." if xsec_token else "xsec_token: 无")
    logger.info(f"使用模式: {'API (MediaCrawler)' if use_api else '页面渲染'}")

    # 如果没有提供 cookie，尝试从文件加载
    if not cookie_str:
        cookie_file = PROJECT_ROOT / "config" / "cookie.txt"
        if cookie_file.exists():
            cookie_str = cookie_file.read_text().strip()
            logger.info("从 config/cookie.txt 加载 Cookie")
        else:
            logger.warning("未提供 Cookie，可能无法获取完整数据")

    # 初始化爬虫
    if use_api:
        crawler = MediaCrawlerAdapter(headless=False, cookie_str=cookie_str)
    else:
        crawler = XHSCrawler(headless=False, cookie_str=cookie_str)

    try:
        await crawler.start()

        # 获取博主信息
        logger.info("获取博主信息...")
        blogger_info = await crawler.get_blogger_info(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
        )

        if not blogger_info:
            logger.error("无法获取博主信息")
            return None

        logger.info(f"博主: {blogger_info.nickname}")
        logger.info(f"粉丝: {blogger_info.fans_count}, 笔记: {blogger_info.notes_count}, 获赞: {blogger_info.liked_count}")

        await asyncio.sleep(2)

        # 计算时间范围
        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(days=months * 30)
        cutoff_timestamp = int(cutoff_time.timestamp() * 1000)  # 转换为毫秒时间戳

        # 获取笔记列表
        logger.info(f"获取笔记列表 (近 {months} 个月，上限 {max_notes} 条)...")
        notes, comments = await crawler.get_blogger_notes_with_details(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
            max_count=max_notes,
            crawl_interval=2,
            fetch_comments=fetch_comments,
        )

        # 按时间过滤笔记（只保留近 N 个月的）
        original_count = len(notes)
        notes = [n for n in notes if n.publish_time and n.publish_time >= cutoff_timestamp]
        filtered_count = original_count - len(notes)

        # 同时过滤评论（只保留属于过滤后笔记的评论）
        note_ids = {n.note_id for n in notes}
        comments = [c for c in comments if c.note_id in note_ids]

        logger.info(f"获取到 {original_count} 条笔记，过滤掉 {filtered_count} 条超过 {months} 个月的")
        logger.info(f"最终: {len(notes)} 条笔记, {len(comments)} 条评论")

        # 保存原始数据到本地 (可选)
        data_dir = PROJECT_ROOT / "data" / "test"
        data_dir.mkdir(parents=True, exist_ok=True)

        raw_data = {
            "blogger": blogger_info.model_dump(),
            "notes": [n.model_dump() for n in notes],
            "comments": [c.model_dump() for c in comments],
        }

        data_file = data_dir / f"{user_id}_raw.json"
        data_file.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"原始数据已保存: {data_file}")

        # 同步数据到飞书多维表格
        if sync_to_feishu:
            logger.info("正在同步数据到飞书多维表格...")
            try:
                from feishu.table_sync import FeishuTableSync

                sync = FeishuTableSync()
                sync.load_existing_data()

                # 检查博主是否已存在，如果存在则回填历史笔记的 blogger_nickname
                if sync.is_blogger_exists(blogger_info.blogger_id):
                    last_sync_at = sync.get_blogger_last_sync_at(blogger_info.blogger_id)
                    if last_sync_at:
                        from datetime import datetime
                        last_sync_time = datetime.fromtimestamp(last_sync_at / 1000)
                        logger.info(f"博主已存在，上次同步时间: {last_sync_time.strftime('%Y-%m-%d %H:%M:%S')}")

                    # 回填历史笔记的 blogger_nickname 字段
                    backfill_count = sync.backfill_blogger_nickname(blogger_info.blogger_id, blogger_info.nickname)
                    if backfill_count > 0:
                        logger.info(f"已回填 {backfill_count} 条历史笔记的博主名称")
                else:
                    logger.info(f"博主 {blogger_info.nickname} 是新增博主")

                # 同步博主信息
                blogger_record = {
                    "blogger_id": blogger_info.blogger_id,
                    "nickname": blogger_info.nickname,
                    "avatar": {"text": "头像", "link": blogger_info.avatar} if blogger_info.avatar else None,
                    "desc": blogger_info.desc,
                    "fans_count": blogger_info.fans_count,
                    "notes_count": blogger_info.notes_count,
                    "liked_count": blogger_info.liked_count,
                }
                sync.sync_blogger(blogger_record)
                logger.info(f"已同步博主: {blogger_info.nickname}")

                # 同步笔记信息（添加博主名称）
                notes_records = []
                note_title_map = {}  # 用于评论关联笔记标题
                for note in notes:
                    note_title_map[note.note_id] = note.title  # 构建映射
                    note_record = {
                        "note_id": note.note_id,
                        "blogger_id": note.blogger_id,
                        "blogger_nickname": blogger_info.nickname,  # 添加博主名称
                        "title": note.title,
                        "desc": note.desc,
                        "type": "视频" if note.type == "video" else "图文",
                        "cover_url": {"text": "封面", "link": note.cover_url} if note.cover_url else None,
                        "tags": ",".join(note.tags) if note.tags else "",
                        "liked_count": note.liked_count,
                        "collected_count": note.collected_count,
                        "comment_count": note.comment_count,
                        "share_count": note.share_count,
                        "publish_time": note.publish_time,
                        "note_url": {"text": "查看笔记", "link": f"https://www.xiaohongshu.com/explore/{note.note_id}"} if note.note_id else None,
                    }
                    notes_records.append(note_record)
                new_notes = sync.sync_notes(notes_records)
                logger.info(f"已同步笔记: 新增 {new_notes} 条, 更新 {len(notes_records) - new_notes} 条")

                # 同步评论信息（添加笔记标题）
                if comments:
                    comments_records = []
                    for comment in comments:
                        comment_record = {
                            "comment_id": comment.comment_id,
                            "note_id": comment.note_id,
                            "note_title": note_title_map.get(comment.note_id, ""),  # 添加笔记标题
                            "parent_id": comment.parent_id or "",
                            "user_id": comment.user_id,
                            "user_nickname": comment.user_nickname,
                            "content": comment.content,
                            "liked_count": comment.liked_count,
                            "create_time": comment.create_time,
                        }
                        comments_records.append(comment_record)
                    new_comments = sync.sync_comments(comments_records)
                    logger.info(f"已同步评论: 新增 {new_comments} 条")

                logger.info("数据同步完成!")
            except Exception as e:
                logger.error(f"同步飞书多维表格失败: {e}")

        # 转换数据格式
        analysis_blogger = convert_crawler_to_analysis_blogger(blogger_info)
        analysis_notes = [convert_crawler_to_analysis_note(n) for n in notes]
        analysis_comments = [convert_crawler_to_analysis_comment(c) for c in comments]

        # 创建分析数据对象
        analysis_data = BloggerAnalysisData(
            blogger=analysis_blogger,
            notes=analysis_notes,
            comments=analysis_comments,
        )

        # 运行分析
        report_path, blogger_name = run_analysis(analysis_data)

        logger.info("=" * 50)
        logger.info(f"分析完成! 报告已保存至: {report_path}")
        logger.info("=" * 50)

        # 上传到飞书
        if upload_to_feishu:
            logger.info("正在上传报告到飞书...")
            try:
                from feishu.client import FeishuClient

                feishu_client = FeishuClient()

                # 读取报告内容
                markdown_content = report_path.read_text(encoding="utf-8")

                # 上传报告
                doc_info = feishu_client.upload_analysis_report(
                    blogger_id=user_id,
                    blogger_name=blogger_name,
                    markdown_content=markdown_content,
                )

                if doc_info:
                    logger.info("=" * 50)
                    logger.info(f"报告已上传到飞书: {doc_info['url']}")
                    logger.info("=" * 50)
                    # 上传成功后删除本地文件
                    if report_path.exists():
                        report_path.unlink()
                        logger.info(f"已删除本地报告文件: {report_path}")
                else:
                    logger.error("上传飞书失败，本地报告已保留")
            except Exception as e:
                logger.error(f"上传飞书时出错: {e}")

        return report_path

    finally:
        await crawler.close()


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="测试博主分析报告生成")
    parser.add_argument("url", help="博主主页URL")
    parser.add_argument("--cookie", type=str, default="", help="Cookie 字符串")
    parser.add_argument("--months", type=int, default=6, help="抓取近几个月的笔记，默认6个月")
    parser.add_argument("--max-notes", type=int, default=500, help="最大抓取笔记数上限，默认500")
    parser.add_argument("--with-comments", action="store_true", help="是否抓取评论")
    parser.add_argument("--no-api", action="store_true", help="不使用 API 模式，使用页面渲染模式")
    parser.add_argument("--upload-feishu", action="store_true", help="上传报告到飞书文档")
    parser.add_argument("--sync-feishu", action="store_true", help="同步数据到飞书多维表格")

    args = parser.parse_args()

    await crawl_and_analyze(
        url=args.url,
        cookie_str=args.cookie,
        months=args.months,
        max_notes=args.max_notes,
        fetch_comments=args.with_comments,
        use_api=not args.no_api,
        upload_to_feishu=args.upload_feishu,
        sync_to_feishu=args.sync_feishu,
    )


if __name__ == "__main__":
    asyncio.run(main())
