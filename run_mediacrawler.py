#!/usr/bin/env python3
"""
使用 MediaCrawler 抓取博主数据

使用方法:
    python run_mediacrawler.py

这个脚本会：
1. 配置 MediaCrawler 使用 creator 模式
2. 使用 Cookie 登录
3. 抓取指定博主的笔记和评论
4. 数据保存到 MediaCrawler/data/xhs/ 目录
"""
import os
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 将 MediaCrawler 添加到 Python 路径
MEDIA_CRAWLER_PATH = PROJECT_ROOT / "MediaCrawler"
sys.path.insert(0, str(MEDIA_CRAWLER_PATH))

# 切换工作目录到 MediaCrawler
os.chdir(MEDIA_CRAWLER_PATH)

# 读取 Cookie
cookie_file = PROJECT_ROOT / "config" / "cookie.txt"
if cookie_file.exists():
    COOKIE_STR = cookie_file.read_text().strip()
else:
    print("错误: 请先创建 config/cookie.txt 文件")
    sys.exit(1)

# 博主 URL 列表
BLOGGER_URLS = [
    "https://www.xiaohongshu.com/user/profile/695b82df0000000037031eca?xsec_token=ABJ7UTxGpQYjzUFtwOyDw7Ac9KQhGtEhbXZy1HEbyLr14=&xsec_source=pc_note",
]

# 修改 MediaCrawler 配置
import config

# 基础配置
config.PLATFORM = "xhs"
config.CRAWLER_TYPE = "creator"  # 创作者模式
config.LOGIN_TYPE = "cookie"  # Cookie 登录
config.COOKIES = COOKIE_STR
config.HEADLESS = False  # 显示浏览器
config.ENABLE_CDP_MODE = False  # 不使用 CDP 模式
config.SAVE_DATA_OPTION = "json"  # 保存为 JSON
config.SAVE_LOGIN_STATE = True

# 爬取配置
config.CRAWLER_MAX_NOTES_COUNT = 50  # 最多抓取50条笔记
config.CRAWLER_MAX_SLEEP_SEC = 2  # 请求间隔
config.MAX_CONCURRENCY_NUM = 1  # 并发数
config.ENABLE_GET_COMMENTS = True  # 获取评论
config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 20  # 每条笔记最多20条评论
config.ENABLE_GET_SUB_COMMENTS = False  # 不获取二级评论
config.ENABLE_GET_MEIDAS = False  # 不下载媒体

# 设置博主 URL 列表
config.XHS_CREATOR_ID_LIST = BLOGGER_URLS

print("=" * 60)
print("MediaCrawler 配置")
print("=" * 60)
print(f"平台: {config.PLATFORM}")
print(f"模式: {config.CRAWLER_TYPE}")
print(f"登录方式: {config.LOGIN_TYPE}")
print(f"博主数量: {len(BLOGGER_URLS)}")
print(f"最大笔记数: {config.CRAWLER_MAX_NOTES_COUNT}")
print(f"获取评论: {config.ENABLE_GET_COMMENTS}")
print(f"数据保存: {config.SAVE_DATA_OPTION}")
print("=" * 60)

# 运行爬虫
if __name__ == "__main__":
    import asyncio
    from media_platform.xhs.core import XiaoHongShuCrawler

    async def main():
        crawler = XiaoHongShuCrawler()
        await crawler.start()

    print("\n开始运行爬虫...\n")
    asyncio.run(main())

    print("\n" + "=" * 60)
    print("爬取完成!")
    print(f"数据保存位置: {MEDIA_CRAWLER_PATH}/data/xhs/")
    print("=" * 60)
