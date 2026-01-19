"""MediaCrawler 适配器 - 使用 MediaCrawler 的 API 客户端获取数据"""
import asyncio
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.async_api import async_playwright, BrowserContext, Page

# 项目根目录和 MediaCrawler 路径
PROJECT_ROOT = Path(__file__).parent.parent
MEDIA_CRAWLER_PATH = PROJECT_ROOT / "MediaCrawler"

from utils.logger import logger
from .data_models import BloggerInfo, NoteInfo, CommentInfo

# 延迟导入 MediaCrawler 模块，避免循环导入和 config 冲突
_xhs_client_class = None
_xhs_extractor_class = None
_convert_cookie_func = None
_get_user_agent_func = None


def _load_module_direct(module_name: str, file_path: Path):
    """直接从文件加载模块，完全绕过包的 __init__.py"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _lazy_import_mediacrawler():
    """延迟导入 MediaCrawler 模块

    使用 importlib.util 直接加载所需文件，完全绕过包的 __init__.py，
    避免触发不需要的模块导入链（如 proxy 模块）。
    """
    global _xhs_client_class, _xhs_extractor_class, _convert_cookie_func, _get_user_agent_func

    if _xhs_client_class is not None:
        return

    import types

    # 保存原始 sys.path
    original_path = sys.path.copy()

    try:
        # MediaCrawler 必须在最前面才能找到依赖
        sys.path.insert(0, str(MEDIA_CRAWLER_PATH))

        # 1. 创建最小化的 config 模块（只包含 client.py 需要的配置）
        config_module = types.ModuleType("config")
        config_module.ENABLE_GET_SUB_COMMENTS = False  # 不爬取二级评论
        config_module.CRAWLER_MAX_NOTES_COUNT = 100  # 最大笔记数
        sys.modules["config"] = config_module

        # 2. 创建 tools 包和 utils 模块
        tools_pkg = types.ModuleType("tools")
        sys.modules["tools"] = tools_pkg

        # 创建 logger
        import logging
        mc_logger = logging.getLogger("MediaCrawler")
        mc_logger.setLevel(logging.INFO)

        utils_module = types.ModuleType("tools.utils")
        utils_module.logger = mc_logger
        sys.modules["tools.utils"] = utils_module

        # 设置 tools 包属性
        tools_pkg.utils = utils_module

        # 3. 加载 crawler_util（需要一些依赖）
        _load_module_direct("tools.time_util", MEDIA_CRAWLER_PATH / "tools" / "time_util.py")
        _load_module_direct("tools.slider_util", MEDIA_CRAWLER_PATH / "tools" / "slider_util.py")
        _load_module_direct("tools.crawler_util", MEDIA_CRAWLER_PATH / "tools" / "crawler_util.py")

        # 从已加载的模块获取函数
        crawler_util = sys.modules["tools.crawler_util"]
        _convert_cookie_func = crawler_util.convert_str_cookie_to_dict
        _get_user_agent_func = crawler_util.get_user_agent

        # 4. 创建 base 包
        base_pkg = types.ModuleType("base")
        sys.modules["base"] = base_pkg

        _load_module_direct("base.base_crawler", MEDIA_CRAWLER_PATH / "base" / "base_crawler.py")

        # 5. 创建 proxy 包和 proxy_mixin 模块
        proxy_pkg = types.ModuleType("proxy")
        sys.modules["proxy"] = proxy_pkg

        proxy_mixin = types.ModuleType("proxy.proxy_mixin")

        class DummyProxyRefreshMixin:
            """空的代理刷新混入类"""
            _proxy_ip_pool = None
            def init_proxy_pool(self, proxy_ip_pool):
                pass
            async def _refresh_proxy_if_expired(self):
                pass

        proxy_mixin.ProxyRefreshMixin = DummyProxyRefreshMixin
        sys.modules["proxy.proxy_mixin"] = proxy_mixin
        proxy_pkg.proxy_mixin = proxy_mixin

        # 6. 创建 media_platform 包
        mp_pkg = types.ModuleType("media_platform")
        sys.modules["media_platform"] = mp_pkg

        mp_xhs_pkg = types.ModuleType("media_platform.xhs")
        sys.modules["media_platform.xhs"] = mp_xhs_pkg
        mp_pkg.xhs = mp_xhs_pkg

        # 7. 加载 xhs 相关模块
        _load_module_direct("media_platform.xhs.exception", MEDIA_CRAWLER_PATH / "media_platform" / "xhs" / "exception.py")
        _load_module_direct("media_platform.xhs.field", MEDIA_CRAWLER_PATH / "media_platform" / "xhs" / "field.py")
        _load_module_direct("media_platform.xhs.help", MEDIA_CRAWLER_PATH / "media_platform" / "xhs" / "help.py")
        _load_module_direct("media_platform.xhs.xhs_sign", MEDIA_CRAWLER_PATH / "media_platform" / "xhs" / "xhs_sign.py")
        _load_module_direct("media_platform.xhs.playwright_sign", MEDIA_CRAWLER_PATH / "media_platform" / "xhs" / "playwright_sign.py")
        _load_module_direct("media_platform.xhs.extractor", MEDIA_CRAWLER_PATH / "media_platform" / "xhs" / "extractor.py")

        # 获取 extractor 类
        extractor_module = sys.modules["media_platform.xhs.extractor"]
        _xhs_extractor_class = extractor_module.XiaoHongShuExtractor

        # 8. 加载 client
        _load_module_direct("media_platform.xhs.client", MEDIA_CRAWLER_PATH / "media_platform" / "xhs" / "client.py")
        client_module = sys.modules["media_platform.xhs.client"]
        _xhs_client_class = client_module.XiaoHongShuClient

    finally:
        # 恢复 sys.path
        sys.path.clear()
        sys.path.extend(original_path)


class MediaCrawlerAdapter:
    """MediaCrawler 适配器 - 使用 MediaCrawler 的 XHSClient 获取数据"""

    def __init__(
        self,
        headless: bool = False,
        cookie_str: str = "",
    ):
        """
        初始化适配器

        Args:
            headless: 是否无头模式
            cookie_str: Cookie 字符串
        """
        self.headless = headless
        self.cookie_str = cookie_str
        self.cookie_dict: Dict[str, str] = {}
        self._playwright = None
        self._browser = None
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.xhs_client = None
        self._extractor = None
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    async def start(self):
        """启动浏览器和初始化客户端"""
        logger.info("正在启动浏览器...")

        # 延迟导入 MediaCrawler 模块
        _lazy_import_mediacrawler()

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)

        self.browser_context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=self.user_agent,
        )

        # 解析 Cookie
        if self.cookie_str:
            self.cookie_dict = _convert_cookie_func(self.cookie_str)
            cookies_for_playwright = []
            for name, value in self.cookie_dict.items():
                cookies_for_playwright.append({
                    "name": name,
                    "value": value,
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                })
            await self.browser_context.add_cookies(cookies_for_playwright)
            logger.info(f"Cookie 已设置 ({len(self.cookie_dict)} 项)")

        # 加载反检测脚本
        stealth_js = MEDIA_CRAWLER_PATH / "libs" / "stealth.min.js"
        if stealth_js.exists():
            await self.browser_context.add_init_script(path=str(stealth_js))
            logger.info("反检测脚本已加载")

        # 创建页面
        self.context_page = await self.browser_context.new_page()

        # 访问小红书主页以初始化签名环境
        logger.info("初始化签名环境...")
        await self.context_page.goto("https://www.xiaohongshu.com", timeout=60000)
        await asyncio.sleep(3)

        # 初始化 XHSClient 和 Extractor
        self._extractor = _xhs_extractor_class()

        headers = {
            "User-Agent": self.user_agent,
            "Cookie": self.cookie_str,
            "Origin": "https://www.xiaohongshu.com",
            "Referer": "https://www.xiaohongshu.com/",
            "Content-Type": "application/json;charset=UTF-8",
        }

        self.xhs_client = _xhs_client_class(
            timeout=60,
            headers=headers,
            playwright_page=self.context_page,
            cookie_dict=self.cookie_dict,
        )

        logger.info("浏览器和客户端初始化成功")

    async def close(self):
        """关闭浏览器"""
        if self.browser_context:
            await self.browser_context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("浏览器已关闭")

    async def get_blogger_info(
        self,
        user_id: str,
        xsec_token: str = "",
        xsec_source: str = "pc_search",
    ) -> Optional[BloggerInfo]:
        """获取博主信息

        Args:
            user_id: 用户ID
            xsec_token: 安全token
            xsec_source: 来源

        Returns:
            BloggerInfo 对象
        """
        try:
            logger.info(f"获取博主信息: {user_id}")

            # 直接通过页面访问获取数据（更可靠）
            url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
            if xsec_token:
                url += f"?xsec_token={xsec_token}&xsec_source={xsec_source}"

            logger.info(f"访问博主主页: {url}")
            await self.context_page.goto(url, timeout=60000)
            await asyncio.sleep(3)

            # 从页面提取 __INITIAL_STATE__
            html_content = await self.context_page.content()

            # 使用自定义解析器（extractor 的正则可能有问题）
            creator_info = self._extract_creator_info_from_html(html_content)

            if not creator_info:
                logger.warning("未能从页面获取博主信息")
                # 尝试打印部分 HTML 内容用于调试
                page_title = await self.context_page.title()
                logger.info(f"页面标题: {page_title}")
                if "__INITIAL_STATE__" in html_content:
                    logger.info("页面包含 __INITIAL_STATE__，但解析失败")
                else:
                    logger.warning("页面不包含 __INITIAL_STATE__，可能被反爬或需要登录")
                    # 打印页面 URL 确认
                    current_url = self.context_page.url
                    logger.info(f"当前页面URL: {current_url}")
                return None

            logger.info(f"成功获取博主原始数据")
            return self._convert_blogger_info(user_id, creator_info)

        except Exception as e:
            logger.error(f"获取博主信息失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_creator_info_from_html(self, html: str) -> Optional[Dict]:
        """从 HTML 提取用户信息

        改进版本，使用非贪婪匹配避免 JSON 解析错误
        """
        import re
        import json

        # 使用非贪婪匹配
        match = re.search(
            r"<script>window\.__INITIAL_STATE__=(.+?)</script>",
            html,
            re.DOTALL
        )

        if match is None:
            return None

        try:
            json_str = match.group(1).replace(":undefined", ":null")
            info = json.loads(json_str, strict=False)
            if info is None:
                return None
            return info.get("user", {}).get("userPageData")
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")
            # 尝试找到正确的 JSON 结束位置
            try:
                json_str = match.group(1).replace(":undefined", ":null")
                # 找到最后一个有效的 } 位置
                depth = 0
                end_pos = 0
                for i, char in enumerate(json_str):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            end_pos = i + 1
                            break
                if end_pos > 0:
                    json_str = json_str[:end_pos]
                    info = json.loads(json_str, strict=False)
                    return info.get("user", {}).get("userPageData")
            except Exception as e2:
                logger.error(f"JSON 修复失败: {e2}")
            return None

    def _convert_blogger_info(self, user_id: str, data: Dict) -> BloggerInfo:
        """转换博主信息格式"""
        basic_info = data.get("basicInfo", {})
        interactions = data.get("interactions", [])

        # 解析互动数据
        fans_count = 0
        notes_count = 0
        liked_count = 0

        for item in interactions:
            name = item.get("name", "")
            count = item.get("count", 0)
            if "粉丝" in name:
                fans_count = self._parse_count(count)
            elif "笔记" in name:
                notes_count = self._parse_count(count)
            elif "赞" in name or "收藏" in name:
                liked_count = self._parse_count(count)

        return BloggerInfo(
            blogger_id=user_id,
            nickname=basic_info.get("nickname", ""),
            avatar=basic_info.get("imageb", "") or basic_info.get("images", ""),
            desc=basic_info.get("desc", ""),
            fans_count=fans_count,
            notes_count=notes_count,
            liked_count=liked_count,
            ip_location=basic_info.get("ipLocation", ""),
        )

    def _parse_count(self, count) -> int:
        """解析数量字符串，如 '1.2万' -> 12000"""
        if isinstance(count, int):
            return count
        if isinstance(count, str):
            count = count.strip()
            if "万" in count:
                return int(float(count.replace("万", "")) * 10000)
            elif "亿" in count:
                return int(float(count.replace("亿", "")) * 100000000)
            else:
                try:
                    return int(count)
                except ValueError:
                    return 0
        return 0

    async def get_blogger_notes(
        self,
        user_id: str,
        xsec_token: str = "",
        xsec_source: str = "pc_feed",
        max_count: int = 100,
        crawl_interval: float = 2.0,
    ) -> List[NoteInfo]:
        """获取博主的笔记列表（通过 API）

        Args:
            user_id: 用户ID
            xsec_token: 安全token
            xsec_source: 来源
            max_count: 最大抓取数量
            crawl_interval: 抓取间隔(秒)

        Returns:
            NoteInfo 列表
        """
        notes = []

        try:
            logger.info(f"获取博主笔记列表: {user_id} (最多 {max_count} 条)")

            notes_has_more = True
            notes_cursor = ""

            while notes_has_more and len(notes) < max_count:
                # 随机延迟
                await asyncio.sleep(crawl_interval + random.uniform(0, 1))

                # 使用 XHSClient 的 API 获取笔记列表
                notes_res = await self.xhs_client.get_notes_by_creator(
                    creator=user_id,
                    cursor=notes_cursor,
                    page_size=30,
                    xsec_token=xsec_token,
                    xsec_source=xsec_source,
                )

                if not notes_res:
                    logger.warning("API 返回空数据，可能被限制")
                    break

                notes_has_more = notes_res.get("has_more", False)
                notes_cursor = notes_res.get("cursor", "")

                if "notes" not in notes_res:
                    logger.info("响应中没有 notes 字段")
                    break

                raw_notes = notes_res["notes"]
                logger.info(f"本次获取到 {len(raw_notes)} 条笔记")

                for item in raw_notes:
                    if len(notes) >= max_count:
                        break

                    note = self._convert_note_from_list(item, user_id)
                    notes.append(note)

            logger.info(f"共获取 {len(notes)} 条笔记")

        except Exception as e:
            logger.error(f"获取笔记列表失败: {e}")
            import traceback
            traceback.print_exc()

        return notes

    def _convert_note_from_list(self, item: Dict, user_id: str) -> NoteInfo:
        """从列表数据转换笔记信息"""
        note_id = item.get("note_id", "") or item.get("id", "")

        # 解析互动信息
        interact_info = item.get("interact_info", {})

        return NoteInfo(
            note_id=note_id,
            blogger_id=user_id,
            title=item.get("display_title", "") or item.get("title", ""),
            desc=item.get("desc", ""),
            type="video" if item.get("type") == "video" else "normal",
            cover_url=item.get("cover", {}).get("url", "") if isinstance(item.get("cover"), dict) else "",
            liked_count=self._parse_count(interact_info.get("liked_count", 0)),
            xsec_token=item.get("xsec_token", ""),
            xsec_source=item.get("xsec_source", "pc_feed"),
        )

    async def get_note_detail(
        self,
        note_id: str,
        xsec_token: str,
        xsec_source: str = "pc_feed",
    ) -> Optional[NoteInfo]:
        """获取笔记详情（通过 API）

        Args:
            note_id: 笔记ID
            xsec_token: 安全token
            xsec_source: 来源

        Returns:
            NoteInfo 对象
        """
        try:
            logger.info(f"获取笔记详情: {note_id}")

            # 使用 XHSClient 的 API 获取笔记详情
            note_card = await self.xhs_client.get_note_by_id(
                note_id=note_id,
                xsec_source=xsec_source,
                xsec_token=xsec_token,
            )

            if not note_card:
                # 尝试 HTML 备用方案
                logger.info(f"API 返回空，尝试 HTML 备用方案: {note_id}")
                note_card = await self.xhs_client.get_note_by_id_from_html(
                    note_id=note_id,
                    xsec_source=xsec_source,
                    xsec_token=xsec_token,
                    enable_cookie=True,
                )

            if not note_card:
                logger.warning(f"无法获取笔记详情: {note_id}")
                return None

            return self._convert_note_detail(note_id, note_card, xsec_token, xsec_source)

        except Exception as e:
            logger.error(f"获取笔记详情失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _convert_note_detail(
        self,
        note_id: str,
        note_card: Dict,
        xsec_token: str,
        xsec_source: str,
    ) -> NoteInfo:
        """从 API 响应转换笔记详情"""
        # 解析图片列表
        image_list = note_card.get("image_list", []) or note_card.get("imageList", [])
        image_urls = []
        for img in image_list:
            url_info = img.get("url_default", "") or img.get("urlDefault", "") or img.get("url", "")
            if url_info:
                image_urls.append(url_info)

        # 解析标签
        tag_list = note_card.get("tag_list", []) or note_card.get("tagList", [])
        tags = [t.get("name", "") for t in tag_list if t.get("name")]

        # 解析互动数据
        interact_info = note_card.get("interact_info", {}) or note_card.get("interactInfo", {})

        # 解析视频URL
        video_url = ""
        if note_card.get("type") == "video":
            video_info = note_card.get("video", {})
            media = video_info.get("media", {})
            stream = media.get("stream", {})
            h264 = stream.get("h264", [])
            if h264 and len(h264) > 0:
                video_url = h264[0].get("master_url", "") or h264[0].get("masterUrl", "")

        # 获取用户ID
        user_info = note_card.get("user", {})
        blogger_id = user_info.get("user_id", "") or user_info.get("userId", "")

        return NoteInfo(
            note_id=note_id,
            blogger_id=blogger_id,
            title=note_card.get("title", ""),
            desc=note_card.get("desc", ""),
            type="video" if note_card.get("type") == "video" else "normal",
            cover_url=image_urls[0] if image_urls else "",
            image_urls=image_urls,
            video_url=video_url,
            tags=tags,
            liked_count=self._parse_count(
                interact_info.get("liked_count", 0) or interact_info.get("likedCount", 0)
            ),
            collected_count=self._parse_count(
                interact_info.get("collected_count", 0) or interact_info.get("collectedCount", 0)
            ),
            comment_count=self._parse_count(
                interact_info.get("comment_count", 0) or interact_info.get("commentCount", 0)
            ),
            share_count=self._parse_count(
                interact_info.get("share_count", 0) or interact_info.get("shareCount", 0)
            ),
            publish_time=note_card.get("time", None),
            xsec_token=xsec_token,
            xsec_source=xsec_source,
        )

    async def get_note_comments(
        self,
        note_id: str,
        xsec_token: str,
        max_count: int = 100,
        crawl_interval: float = 1.0,
    ) -> List[CommentInfo]:
        """获取笔记评论（通过 API）

        Args:
            note_id: 笔记ID
            xsec_token: 安全token
            max_count: 最大评论数
            crawl_interval: 抓取间隔

        Returns:
            CommentInfo 列表
        """
        comments = []

        try:
            logger.info(f"获取笔记评论: {note_id}")

            # 使用 XHSClient 的 API 获取评论
            raw_comments = await self.xhs_client.get_note_all_comments(
                note_id=note_id,
                xsec_token=xsec_token,
                crawl_interval=crawl_interval,
                max_count=max_count,
            )

            for item in raw_comments[:max_count]:
                comment = self._convert_comment(item, note_id)
                comments.append(comment)

            logger.info(f"笔记 {note_id} 共获取 {len(comments)} 条评论")

        except Exception as e:
            logger.error(f"获取评论失败: {e}")

        return comments

    def _convert_comment(self, item: Dict, note_id: str) -> CommentInfo:
        """转换评论格式"""
        user_info = item.get("user_info", {}) or item.get("userInfo", {})

        return CommentInfo(
            comment_id=item.get("id", ""),
            note_id=note_id,
            parent_id=item.get("target_comment_id", "") or item.get("targetCommentId", "") or "",
            user_id=user_info.get("user_id", "") or user_info.get("userId", ""),
            user_nickname=user_info.get("nickname", ""),
            content=item.get("content", ""),
            liked_count=item.get("like_count", 0) or item.get("likeCount", 0),
            create_time=item.get("create_time", None) or item.get("createTime", None),
        )

    async def get_blogger_notes_with_details(
        self,
        user_id: str,
        xsec_token: str = "",
        xsec_source: str = "pc_feed",
        max_count: int = 100,
        crawl_interval: float = 2.0,
        fetch_comments: bool = True,
    ) -> Tuple[List[NoteInfo], List[CommentInfo]]:
        """获取博主的笔记列表及详情

        Args:
            user_id: 用户ID
            xsec_token: 安全token
            xsec_source: 来源
            max_count: 最大抓取数量
            crawl_interval: 抓取间隔(秒)
            fetch_comments: 是否获取评论

        Returns:
            (NoteInfo 列表, CommentInfo 列表)
        """
        all_notes = []
        all_comments = []

        # 获取笔记列表
        notes = await self.get_blogger_notes(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
            max_count=max_count,
            crawl_interval=crawl_interval,
        )

        # 获取每条笔记的详情和评论
        for i, note in enumerate(notes, 1):
            logger.info(f"处理笔记 {i}/{len(notes)}: {note.note_id}")

            if not note.xsec_token:
                logger.warning(f"笔记 {note.note_id} 缺少 xsec_token，跳过详情获取")
                all_notes.append(note)
                continue

            # 随机延迟
            await asyncio.sleep(crawl_interval + random.uniform(0, 1))

            # 获取详情
            detail = await self.get_note_detail(
                note_id=note.note_id,
                xsec_token=note.xsec_token,
                xsec_source=note.xsec_source or xsec_source,
            )

            if detail:
                all_notes.append(detail)

                # 获取评论
                if fetch_comments:
                    await asyncio.sleep(crawl_interval + random.uniform(0, 0.5))
                    comments = await self.get_note_comments(
                        note_id=note.note_id,
                        xsec_token=note.xsec_token,
                    )
                    all_comments.extend(comments)
            else:
                # 详情获取失败，使用列表数据
                all_notes.append(note)

        return all_notes, all_comments

    @staticmethod
    def parse_creator_url(url: str) -> Dict[str, str]:
        """解析博主URL，提取 user_id, xsec_token, xsec_source

        Args:
            url: 博主主页URL

        Returns:
            包含 user_id, xsec_token, xsec_source 的字典
        """
        import re

        result = {
            "user_id": "",
            "xsec_token": "",
            "xsec_source": "pc_search",
        }

        try:
            # 提取 user_id
            match = re.search(r"/user/profile/([a-zA-Z0-9]+)", url)
            if match:
                result["user_id"] = match.group(1)

            # 提取 xsec_token
            if "xsec_token=" in url:
                token_match = re.search(r"xsec_token=([^&]+)", url)
                if token_match:
                    result["xsec_token"] = token_match.group(1)

            # 提取 xsec_source
            if "xsec_source=" in url:
                source_match = re.search(r"xsec_source=([^&]+)", url)
                if source_match:
                    result["xsec_source"] = source_match.group(1)

        except Exception as e:
            logger.error(f"解析博主URL失败: {e}")

        return result
