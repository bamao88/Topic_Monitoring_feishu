"""分析模块入口"""
import sys
from pathlib import Path
from typing import Optional, List

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.logger import logger
from .data_fetcher import AnalysisDataFetcher
from .report_generator import BloggerReportGenerator
from .analyzers import (
    BasicInfoAnalyzer,
    AccountPositionAnalyzer,
    TopicAnalyzer,
    ContentFormatAnalyzer,
    CopywritingAnalyzer,
    OperationsAnalyzer,
    ViralNotesAnalyzer,
    EvaluationAnalyzer,
)


def analyze_blogger(blogger_id: str) -> Optional[Path]:
    """分析单个博主并生成报告

    Args:
        blogger_id: 博主ID

    Returns:
        报告文件路径，失败返回 None
    """
    logger.info(f"开始分析博主: {blogger_id}")

    # 初始化数据获取器
    fetcher = AnalysisDataFetcher()

    # 获取博主数据
    data = fetcher.get_blogger_data(blogger_id)
    if not data:
        logger.error(f"无法获取博主数据: {blogger_id}")
        return None

    logger.info(f"获取到博主 {data.blogger.nickname} 的数据: {len(data.notes)} 条笔记, {len(data.comments)} 条评论")

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
    logger.info("正在分析基础信息...")
    basic_info = basic_analyzer.analyze(data)

    logger.info("正在分析账号定位...")
    account_position = position_analyzer.analyze(data)

    logger.info("正在分析选题内容...")
    topic = topic_analyzer.analyze(data)

    logger.info("正在分析内容形式...")
    content_format = format_analyzer.analyze(data)

    logger.info("正在分析文案结构...")
    copywriting = copywriting_analyzer.analyze(data)

    logger.info("正在分析运营策略...")
    operations = operations_analyzer.analyze(data)

    logger.info("正在分析爆款笔记...")
    viral = viral_analyzer.analyze(data)

    logger.info("正在生成综合评估...")
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
    logger.info("正在生成分析报告...")
    generator = BloggerReportGenerator()
    report_path = generator.generate(
        blogger_id=blogger_id,
        basic_info=basic_info,
        account_position=account_position,
        topic=topic,
        content_format=content_format,
        copywriting=copywriting,
        operations=operations,
        viral=viral,
        evaluation=evaluation,
    )

    logger.info(f"分析完成! 报告已保存至: {report_path}")
    return report_path


def analyze_all_bloggers() -> List[Path]:
    """分析所有博主并生成报告

    Returns:
        成功生成的报告文件路径列表
    """
    logger.info("开始分析所有博主...")

    # 初始化数据获取器
    fetcher = AnalysisDataFetcher()

    # 获取所有博主
    bloggers = fetcher.get_all_bloggers()
    if not bloggers:
        logger.warning("没有找到任何博主数据")
        return []

    logger.info(f"共找到 {len(bloggers)} 个博主")

    # 分析每个博主
    report_paths = []
    for i, blogger in enumerate(bloggers, 1):
        logger.info(f"[{i}/{len(bloggers)}] 分析博主: {blogger.nickname} ({blogger.blogger_id})")
        try:
            report_path = analyze_blogger(blogger.blogger_id)
            if report_path:
                report_paths.append(report_path)
        except Exception as e:
            logger.error(f"分析博主 {blogger.blogger_id} 失败: {e}")
            continue

    logger.info(f"分析完成! 共生成 {len(report_paths)} 份报告")
    return report_paths


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="小红书博主分析工具")
    parser.add_argument(
        "blogger_id",
        nargs="?",
        help="要分析的博主ID，不指定则分析所有博主",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="分析所有博主",
    )
    args = parser.parse_args()

    if args.blogger_id:
        analyze_blogger(args.blogger_id)
    elif args.all:
        analyze_all_bloggers()
    else:
        print("请指定博主ID或使用 --all 参数分析所有博主")
        print("用法: python -m analysis.main BLOGGER_ID")
        print("      python -m analysis.main --all")
