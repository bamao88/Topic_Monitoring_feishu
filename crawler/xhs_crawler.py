"""小红书爬虫封装 - 基于 Playwright 直接提取页面数据"""
import asyncio
import json
import os
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright, BrowserContext, Page
from utils.logger import logger

from .data_models import BloggerInfo, NoteInfo, CommentInfo

# MediaCrawler 路径 (用于加载反检测脚本)
MEDIA_CRAWLER_PATH = Path(__file__).parent.parent / "MediaCrawler"


class XHSCrawler:
    """小红书爬虫封装类 - 使用 Playwright 直接提取页面数据"""

    def __init__(
        self,
        headless: bool = False,
        cookie_str: str = "",
    ):
        """
        Args:
            headless: 是否无头模式
            cookie_str: Cookie 字符串
        """
        self.headless = headless
        self.cookie_str = cookie_str
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self._playwright = None
        self._browser = None
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    def _parse_cookie_string(self, cookie_str: str) -> dict:
        """解析 cookie 字符串为字典"""
        cookie_dict = {}
        for item in cookie_str.split("; "):
            if "=" in item:
                key, value = item.split("=", 1)
                cookie_dict[key.strip()] = value.strip()
        return cookie_dict

    async def start(self):
        """启动浏览器"""
        logger.info("正在启动浏览器...")

        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self.browser_context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=self.user_agent,
        )

        # 设置 Cookie
        if self.cookie_str:
            cookie_dict = self._parse_cookie_string(self.cookie_str)
            cookies_for_playwright = []
            for name, value in cookie_dict.items():
                cookies_for_playwright.append({
                    "name": name,
                    "value": value,
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                })
            await self.browser_context.add_cookies(cookies_for_playwright)
            logger.info(f"Cookie 已设置 ({len(cookie_dict)} 项)")

        # 加载反检测脚本
        stealth_js = MEDIA_CRAWLER_PATH / "libs" / "stealth.min.js"
        if stealth_js.exists():
            await self.browser_context.add_init_script(path=str(stealth_js))
            logger.info("反检测脚本已加载")

        # 创建页面
        self.context_page = await self.browser_context.new_page()

        logger.info("浏览器启动成功")

    async def close(self):
        """关闭浏览器"""
        if self.browser_context:
            await self.browser_context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("浏览器已关闭")

    async def check_cookie_valid(self) -> bool:
        """检查 Cookie 是否有效

        通过访问小红书首页并检查是否能获取到用户登录状态来判断

        Returns:
            bool: Cookie 是否有效
        """
        try:
            logger.info("正在验证 Cookie 有效性...")

            # 访问小红书首页
            await self.context_page.goto("https://www.xiaohongshu.com/explore", timeout=30000)
            await asyncio.sleep(3)

            # 检查是否触发验证码
            page_content = await self.context_page.content()
            if "请通过验证" in page_content or "验证码" in page_content:
                logger.error("检测到验证码页面")
                return False

            # 检查是否有登录态 - 查找"我"按钮或用户头像
            try:
                # 尝试查找用户相关元素
                user_element = await self.context_page.query_selector("xpath=//a[contains(@href, '/user/profile/')]")
                if user_element:
                    logger.info("检测到用户登录元素，Cookie 有效")
                    return True

                # 备用检查：查找登录按钮（如果有登录按钮说明未登录）
                login_btn = await self.context_page.query_selector("text=登录")
                if login_btn:
                    logger.warning("检测到登录按钮，Cookie 可能已过期")
                    return False

                # 如果都没找到，尝试通过页面内容判断
                if "请登录" in page_content or "立即登录" in page_content:
                    logger.warning("页面提示需要登录")
                    return False

                # 无法明确判断，假设有效
                logger.info("未检测到明确的登录/未登录标识，假设 Cookie 有效")
                return True

            except Exception as e:
                logger.warning(f"检查登录状态时出错: {e}")
                return True  # 出错时假设有效，继续尝试

        except Exception as e:
            logger.error(f"验证 Cookie 时发生错误: {e}")
            return False

    async def _extract_initial_state(self, page: Page, path: str) -> Any:
        """从页面提取 __INITIAL_STATE__ 中的数据

        Args:
            page: Playwright 页面对象
            path: 数据路径，如 "user.userPageData"

        Returns:
            提取的数据
        """
        js_code = f"""() => {{
            try {{
                const paths = "{path}".split(".");
                let obj = window.__INITIAL_STATE__;
                for (const p of paths) {{
                    if (!obj) return "";
                    obj = obj[p];
                }}
                if (!obj) return "";
                // 处理 Vue3 的响应式对象
                const data = obj.value !== undefined ? obj.value : (obj._value !== undefined ? obj._value : obj);
                return JSON.stringify(data);
            }} catch (e) {{
                return "";
            }}
        }}"""

        result = await page.evaluate(js_code)
        if result:
            return json.loads(result)
        return None

    async def get_blogger_info(
        self,
        user_id: str,
        xsec_token: str = "",
        xsec_source: str = "pc_note",
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
            # 构建URL
            url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
            if xsec_token:
                url += f"?xsec_token={xsec_token}&xsec_source={xsec_source}"

            logger.info(f"访问博主主页: {user_id}")
            await self.context_page.goto(url, timeout=60000)
            await asyncio.sleep(3)

            # 提取用户数据
            user_data = await self._extract_initial_state(self.context_page, "user.userPageData")

            if not user_data:
                logger.warning("未能从页面获取博主数据")
                return None

            basic_info = user_data.get("basicInfo", {})
            interactions = user_data.get("interactions", [])

            # 解析互动数据
            fans_count = 0
            notes_count = 0
            liked_count = 0
            following_count = 0

            for item in interactions:
                name = item.get("name", "")
                count = item.get("count", 0)
                if "粉丝" in name:
                    fans_count = self._parse_count(count)
                elif "关注" in name:
                    following_count = self._parse_count(count)
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

        except Exception as e:
            logger.error(f"获取博主信息失败: {e}")
            return None

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
        xsec_source: str = "pc_note",
        max_count: int = 100,
        crawl_interval: float = 2.0,
    ) -> List[NoteInfo]:
        """获取博主的笔记列表

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
            # 先访问博主主页
            url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
            if xsec_token:
                url += f"?xsec_token={xsec_token}&xsec_source={xsec_source}"

            logger.info(f"访问博主主页获取笔记列表: {user_id}")
            await self.context_page.goto(url, timeout=60000)
            await asyncio.sleep(3)

            # 从页面提取笔记数据
            notes_data = await self._extract_initial_state(self.context_page, "user.notes")

            if not notes_data:
                logger.warning("未能从页面获取笔记列表")
                return notes

            # 展平数组 (可能是嵌套的)
            flat_notes = []
            for item in notes_data:
                if isinstance(item, list):
                    flat_notes.extend(item)
                else:
                    flat_notes.append(item)

            logger.info(f"从页面获取到 {len(flat_notes)} 条笔记")

            # 获取当前页面的 xsec_token 作为备用
            current_url = self.context_page.url
            fallback_token = ""
            if "xsec_token=" in current_url:
                fallback_token = current_url.split("xsec_token=")[1].split("&")[0]

            # 解析笔记
            for item in flat_notes[:max_count]:
                note_id = item.get("note_id", "") or item.get("id", "")
                if not note_id:
                    continue

                # 获取 xsec_token：优先从笔记数据中获取，否则用页面 URL 中的
                note_token = item.get("xsec_token", "") or fallback_token

                note = NoteInfo(
                    note_id=note_id,
                    blogger_id=user_id,
                    title=item.get("display_title", "") or item.get("title", ""),
                    desc=item.get("desc", ""),
                    type="video" if item.get("type") == "video" else "normal",
                    cover_url=item.get("cover", {}).get("url", "") if isinstance(item.get("cover"), dict) else "",
                    liked_count=self._parse_count(item.get("liked_count", 0) or item.get("interact_info", {}).get("liked_count", 0)),
                    xsec_token=note_token,
                    xsec_source=item.get("xsec_source", xsec_source),
                )
                notes.append(note)

            logger.info(f"共解析 {len(notes)} 条笔记")

        except Exception as e:
            logger.error(f"获取笔记列表失败: {e}")

        return notes

    async def get_note_detail(
        self,
        note_id: str,
        xsec_token: str,
        xsec_source: str = "pc_note",
    ) -> Optional[NoteInfo]:
        """获取笔记详情

        Args:
            note_id: 笔记ID
            xsec_token: 安全token
            xsec_source: 来源

        Returns:
            NoteInfo 对象
        """
        try:
            url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source={xsec_source}"

            logger.info(f"访问笔记详情: {note_id}")
            await self.context_page.goto(url, timeout=60000)
            await asyncio.sleep(4)

            # 检查是否遇到内容限制页面
            page_content = await self.context_page.content()
            if "当前笔记暂时无法浏览" in page_content:
                logger.warning(f"笔记 {note_id} 暂时无法浏览（可能需要App查看），跳过")
                return None
            if "404" in self.context_page.url or "你访问的页面不见了" in page_content:
                logger.warning(f"笔记 {note_id} 不存在或已被删除，跳过")
                return None

            # 提取笔记详情
            detail_data = await self.context_page.evaluate("""() => {
                if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note) {
                    const noteData = window.__INITIAL_STATE__.note;
                    if (noteData.noteDetailMap) {
                        const detailMap = noteData.noteDetailMap.value || noteData.noteDetailMap._value || noteData.noteDetailMap;
                        if (detailMap && typeof detailMap === 'object') {
                            const keys = Object.keys(detailMap);
                            if (keys.length > 0) {
                                return JSON.stringify(detailMap[keys[0]]);
                            }
                        }
                    }
                }
                return "";
            }""")

            if not detail_data:
                logger.warning(f"未能获取笔记详情: {note_id}")
                return None

            detail = json.loads(detail_data)
            note_card = detail.get("note", {})

            # 解析图片列表
            image_list = note_card.get("imageList", [])
            image_urls = []
            for img in image_list:
                url_info = img.get("urlDefault", "") or img.get("url", "")
                if url_info:
                    image_urls.append(url_info)

            # 解析标签
            tag_list = note_card.get("tagList", [])
            tags = [t.get("name", "") for t in tag_list if t.get("name")]

            # 解析互动数据
            interact_info = note_card.get("interactInfo", {})

            # 解析视频URL
            video_url = ""
            if note_card.get("type") == "video":
                video_info = note_card.get("video", {})
                media = video_info.get("media", {})
                stream = media.get("stream", {})
                h264 = stream.get("h264", [])
                if h264 and len(h264) > 0:
                    video_url = h264[0].get("masterUrl", "")

            return NoteInfo(
                note_id=note_id,
                blogger_id=note_card.get("user", {}).get("userId", ""),
                title=note_card.get("title", ""),
                desc=note_card.get("desc", ""),
                type="video" if note_card.get("type") == "video" else "normal",
                cover_url=image_urls[0] if image_urls else "",
                image_urls=image_urls,
                video_url=video_url,
                tags=tags,
                liked_count=self._parse_count(interact_info.get("likedCount", 0)),
                collected_count=self._parse_count(interact_info.get("collectedCount", 0)),
                comment_count=self._parse_count(interact_info.get("commentCount", 0)),
                share_count=self._parse_count(interact_info.get("shareCount", 0)),
                publish_time=note_card.get("time", None),
                xsec_token=xsec_token,
                xsec_source=xsec_source,
            )

        except Exception as e:
            logger.error(f"获取笔记详情失败: {e}")
            return None

    async def get_note_comments(
        self,
        note_id: str,
        xsec_token: str,
        xsec_source: str = "pc_note",
        max_count: int = 100,
        crawl_interval: float = 1.0,
    ) -> List[CommentInfo]:
        """获取笔记评论

        Args:
            note_id: 笔记ID
            xsec_token: 安全token
            xsec_source: 来源
            max_count: 最大评论数
            crawl_interval: 抓取间隔

        Returns:
            CommentInfo 列表
        """
        comments = []

        try:
            # 先访问笔记详情页
            url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source={xsec_source}"

            logger.info(f"访问笔记页面获取评论: {note_id}")
            await self.context_page.goto(url, timeout=60000)
            await asyncio.sleep(4)

            # 提取评论数据
            comments_data = await self.context_page.evaluate("""() => {
                if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note) {
                    const noteData = window.__INITIAL_STATE__.note;
                    // 尝试从 comments 获取
                    if (noteData.comments) {
                        const comments = noteData.comments.value || noteData.comments._value;
                        if (comments) {
                            return JSON.stringify(comments);
                        }
                    }
                    // 尝试从 noteDetailMap 获取
                    if (noteData.noteDetailMap) {
                        const detailMap = noteData.noteDetailMap.value || noteData.noteDetailMap._value || noteData.noteDetailMap;
                        if (detailMap && typeof detailMap === 'object') {
                            const keys = Object.keys(detailMap);
                            if (keys.length > 0) {
                                const detail = detailMap[keys[0]];
                                if (detail && detail.comments) {
                                    return JSON.stringify(detail.comments);
                                }
                            }
                        }
                    }
                }
                return "";
            }""")

            if not comments_data:
                logger.info(f"笔记 {note_id} 暂无评论或评论未加载")
                return comments

            raw_comments = json.loads(comments_data)

            if not isinstance(raw_comments, list):
                return comments

            # 解析评论
            for item in raw_comments[:max_count]:
                comment = self._parse_comment(item, note_id)
                comments.append(comment)

                # 解析子评论
                sub_comments = item.get("subComments", [])
                for sub_item in sub_comments:
                    sub_comment = self._parse_comment(sub_item, note_id, parent_id=comment.comment_id)
                    comments.append(sub_comment)

            logger.info(f"笔记 {note_id} 共获取 {len(comments)} 条评论")

        except Exception as e:
            logger.error(f"获取评论失败: {e}")

        return comments

    def _parse_comment(self, item: Dict, note_id: str, parent_id: str = "") -> CommentInfo:
        """解析评论"""
        user_info = item.get("userInfo", {})

        return CommentInfo(
            comment_id=item.get("id", ""),
            note_id=note_id,
            parent_id=parent_id or item.get("targetCommentId", "") or "",
            user_id=user_info.get("userId", ""),
            user_nickname=user_info.get("nickname", ""),
            content=item.get("content", ""),
            liked_count=item.get("likeCount", 0),
            create_time=item.get("createTime", None),
        )

    async def get_blogger_notes_with_details(
        self,
        user_id: str,
        xsec_token: str = "",
        xsec_source: str = "pc_note",
        max_count: int = 100,
        crawl_interval: float = 2.0,
        fetch_comments: bool = True,
    ) -> tuple[List[NoteInfo], List[CommentInfo]]:
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
                logger.warning(f"笔记 {note.note_id} 缺少 xsec_token，跳过")
                all_notes.append(note)
                continue

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
                    comments = await self.get_note_comments(
                        note_id=note.note_id,
                        xsec_token=note.xsec_token,
                        xsec_source=note.xsec_source or xsec_source,
                    )
                    all_comments.extend(comments)
            else:
                all_notes.append(note)

            await asyncio.sleep(crawl_interval)

        return all_notes, all_comments

    @staticmethod
    def parse_creator_url(url: str) -> Dict[str, str]:
        """解析博主URL，提取 user_id, xsec_token, xsec_source

        Args:
            url: 博主主页URL

        Returns:
            包含 user_id, xsec_token, xsec_source 的字典
        """
        result = {
            "user_id": "",
            "xsec_token": "",
            "xsec_source": "pc_note",
        }

        try:
            # 提取 user_id
            # URL格式: https://www.xiaohongshu.com/user/profile/xxx?...
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
