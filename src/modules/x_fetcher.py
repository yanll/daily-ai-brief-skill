"""
X/Twitter抓取器
通过网页爬虫或第三方服务抓取X/Twitter内容
"""
import asyncio
import logging
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta

from .base_fetcher import BaseFetcher, NewsItem


class XFetcher(BaseFetcher):
    """X/Twitter抓取器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.username = config.get("username", "")
        self.usernames = config.get("usernames", [])
        self.logger = logging.getLogger(f"XFetcher.{self.name}")

        # 如果只有一个用户名，添加到列表中
        if self.username and not self.usernames:
            self.usernames = [self.username]

    async def fetch(self) -> List[NewsItem]:
        """
        抓取X/Twitter内容

        Returns:
            新闻条目列表
        """
        if not self.enabled:
            self.logger.info(f"数据源已禁用: {self.name}")
            return []

        if not self.usernames:
            self.logger.error(f"用户名列表为空: {self.name}")
            return []

        self.logger.info(f"开始抓取X/Twitter: {self.name} ({self.usernames})")
        start_time = time.time()

        # 尝试使用Playwright进行真实抓取
        try:
            # 创建Playwright抓取器配置
            playwright_config = self.config.copy()
            playwright_config["use_playwright"] = True
            playwright_fetcher = XPlaywrightFetcher(playwright_config)
            items = await playwright_fetcher.fetch()

            elapsed = time.time() - start_time
            if items:
                self.logger.info(f"X/Twitter Playwright抓取成功: {self.name}, 获取 {len(items)} 个条目, 耗时 {elapsed:.2f}秒")
                return items
            else:
                self.logger.warning(f"X/Twitter Playwright抓取返回空结果: {self.name}, 耗时 {elapsed:.2f}秒")
                return []

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.warning(f"X/Twitter Playwright抓取失败，跳过模拟数据: {self.name}, 耗时 {elapsed:.2f}秒, 错误: {e}")
            # 不返回模拟数据，只返回空列表
            return []





class XPlaywrightFetcher(BaseFetcher):
    """
    使用Playwright的X/Twitter抓取器
    需要安装Playwright: pip install playwright && playwright install
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.username = config.get("username", "")
        self.usernames = config.get("usernames", [])
        self.use_playwright = config.get("use_playwright", True)
        self.playwright_wait_seconds = config.get("playwright_wait_seconds", 2)
        self.logger = logging.getLogger(f"XPlaywrightFetcher.{self.name}")

    async def fetch(self) -> List[NewsItem]:
        """
        使用Playwright抓取X/Twitter内容

        Returns:
            新闻条目列表
        """
        if not self.use_playwright:
            self.logger.warning("Playwright未启用，返回空列表")
            return []

        self.logger.info(f"使用Playwright抓取X/Twitter: {self.name}")
        start_time = time.time()

        try:
            # 导入Playwright（延迟导入）
            from playwright.async_api import async_playwright

            items = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()

                for username in self.usernames:
                    user_items = await self._fetch_user_with_playwright(page, username)
                    items.extend(user_items)

                await browser.close()

            # 应用过滤
            filtered_items = self.apply_filters(items)
            elapsed = time.time() - start_time
            self.logger.info(f"Playwright抓取完成: {self.name}, 获取 {len(filtered_items)} 个条目, 耗时 {elapsed:.2f}秒")
            return filtered_items

        except ImportError:
            elapsed = time.time() - start_time
            self.logger.error(f"Playwright未安装，请运行: pip install playwright && playwright install, 耗时 {elapsed:.2f}秒")
            return []
        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"Playwright抓取失败, 耗时 {elapsed:.2f}秒: {e}")
            return []

    async def _fetch_user_with_playwright(self, page, username: str) -> List[NewsItem]:
        """
        使用Playwright抓取用户推文

        Args:
            page: Playwright页面对象
            username: 用户名

        Returns:
            新闻条目列表
        """
        self.logger.info(f"爬取用户: @{username}")

        # Nitter实例列表（按优先级排序）
        nitter_instances = [
            "https://nitter.net",
            "https://nitter.fdn.fr",
            "https://nitter.1d4.us",
            "https://nitter.unixfox.eu",
            "https://nitter.nixnet.services",
        ]

        for nitter_base in nitter_instances:
            try:
                # 使用Nitter进行无登录采集
                url = f"{nitter_base}/{username}"
                self.logger.info(f"尝试Nitter实例: {url}")
                response = await page.goto(url, wait_until="networkidle", timeout=15000)

                if response and response.status != 200:
                    self.logger.warning(f"Nitter实例返回状态码 {response.status}: {nitter_base}")
                    continue

                await page.wait_for_timeout(self.playwright_wait_seconds * 1000)

                # 检查页面是否包含有效内容
                content = await page.content()
                if len(content) < 100:
                    self.logger.warning(f"Nitter实例返回内容过少 ({len(content)} 字节): {nitter_base}")
                    continue

                # 检查是否有错误消息
                error_selectors = [
                    'text=User not found',
                    'text=User suspended',
                    'text=This account is private',
                    'text=Something went wrong',
                    'text=Rate limit exceeded',
                ]

                has_error = False
                for selector in error_selectors:
                    if await page.is_visible(selector):
                        self.logger.warning(f"页面包含错误: {selector}")
                        has_error = True
                        break

                if has_error:
                    continue

                # 这里需要根据X/Twitter页面结构提取推文
                # 实际实现需要分析页面DOM结构
                # 示例选择器（可能需要调整）
                tweet_selectors = [
                    'article[data-testid="tweet"]',
                    'div[data-testid="tweet"]',
                    'div[role="article"]',
                    '.tweet',
                    'article',
                ]

                items = []
                for selector in tweet_selectors:
                    tweets = await page.query_selector_all(selector)
                    if tweets:
                        self.logger.info(f"找到 {len(tweets)} 个推文 (选择器: {selector})")
                        for tweet in tweets[:self.max_items]:
                            try:
                                item = await self._parse_tweet_element(tweet, username)
                                if item:
                                    items.append(item)
                            except Exception as e:
                                self.logger.debug(f"解析推文失败: {e}")
                        break

                if items:
                    self.logger.info(f"成功从 {nitter_base} 获取 {len(items)} 个推文")
                    return items
                else:
                    self.logger.warning(f"从 {nitter_base} 未找到推文")

            except Exception as e:
                self.logger.warning(f"Nitter实例 {nitter_base} 失败: {e}")
                continue

        self.logger.error(f"所有Nitter实例均失败: @{username}")
        return []

    async def _parse_tweet_element(self, tweet_element, username: str) -> NewsItem:
        """
        解析推文元素

        Args:
            tweet_element: 推文元素
            username: 用户名

        Returns:
            新闻条目
        """
        # 这里需要实现具体的DOM解析逻辑
        # 由于X/Twitter页面结构可能变化，此代码需要定期更新

        # 示例解析逻辑（需要根据实际页面调整）
        title = await tweet_element.inner_text()
        title = title[:200]  # 截断

        # 尝试提取链接
        link_elements = await tweet_element.query_selector_all('a[href*="/status/"]')
        url = f"https://nitter.net/{username}"
        if link_elements:
            href = await link_elements[0].get_attribute("href")
            if href:
                url = f"https://nitter.net{href}"

        # 尝试提取时间
        time_elements = await tweet_element.query_selector_all('time')
        publish_date = datetime.now()
        if time_elements:
            datetime_str = await time_elements[0].get_attribute("datetime")
            if datetime_str:
                try:
                    publish_date = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

        title_clean = self.cleanup_content(title)
        item = NewsItem(
            title=title_clean,
            url=url,
            content=title_clean,
            summary=self.cleanup_content(title_clean[:150]),
            source=self.name,
            source_type="twitter",
            publish_date=publish_date,
            author=username,
            metadata={
                "username": username,
                "platform": "twitter",
                "fetched_with": "playwright",
            }
        )

        return item