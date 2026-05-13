"""
X/Twitter抓取器
通过网页爬虫或第三方服务抓取X/Twitter内容
"""
import asyncio
import logging
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

        # 由于X/Twitter API限制严格，这里返回示例数据
        # 实际实现应使用Playwright进行网页爬取或使用第三方服务

        items = []
        for username in self.usernames:
            try:
                # 模拟数据 - 实际应爬取真实内容
                mock_items = await self._fetch_user_tweets(username)
                items.extend(mock_items)
            except Exception as e:
                self.logger.error(f"抓取用户 {username} 失败: {e}")

        # 应用过滤
        filtered_items = self.apply_filters(items)

        self.logger.info(f"X/Twitter抓取完成: {self.name}, 获取 {len(filtered_items)} 个条目")
        return filtered_items

    async def _fetch_user_tweets(self, username: str) -> List[NewsItem]:
        """
        抓取用户推文（模拟实现）

        Args:
            username: 用户名

        Returns:
            新闻条目列表
        """
        # 这里应该使用Playwright或Selenium爬取X/Twitter页面
        # 由于时间限制，返回模拟数据

        self.logger.warning(f"X/Twitter抓取器使用模拟数据，需要实现真实爬取逻辑: {username}")

        # 模拟数据
        mock_tweets = [
            {
                "title": f"AI breakthrough announced by {username}",
                "content": f"Exciting news about AI developments from {username}. This is a simulated tweet content.",
                "url": f"https://twitter.com/{username}/status/1234567890",
                "date": datetime.now() - timedelta(hours=2),
            },
            {
                "title": f"New research paper from {username}",
                "content": f"Just published a new paper on machine learning. Read more at the link.",
                "url": f"https://twitter.com/{username}/status/1234567891",
                "date": datetime.now() - timedelta(days=1),
            },
        ]

        items = []
        for tweet in mock_tweets:
            content = self.cleanup_content(tweet["content"])
            item = NewsItem(
                title=tweet["title"],
                url=tweet["url"],
                content=content,
                summary=self.cleanup_content(content[:200]),
                source=self.name,
                source_type="twitter",
                language=self.language,
                publish_date=tweet["date"],
                author=username,
                tags=["twitter", "ai"],
                metadata={
                    "username": username,
                    "platform": "twitter",
                    "simulated": True,  # 标记为模拟数据
                }
            )
            items.append(item)

        return items


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
            self.logger.warning("Playwright未启用，使用基本抓取器")
            basic_fetcher = XFetcher(self.config)
            return await basic_fetcher.fetch()

        self.logger.info(f"使用Playwright抓取X/Twitter: {self.name}")

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
            self.logger.info(f"Playwright抓取完成: {self.name}, 获取 {len(filtered_items)} 个条目")
            return filtered_items

        except ImportError:
            self.logger.error("Playwright未安装，请运行: pip install playwright && playwright install")
            return []
        except Exception as e:
            self.logger.error(f"Playwright抓取失败: {e}")
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

        try:
            url = f"https://twitter.com/{username}"
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(self.playwright_wait_seconds * 1000)

            # 这里需要根据X/Twitter页面结构提取推文
            # 实际实现需要分析页面DOM结构
            # 示例选择器（可能需要调整）
            tweet_selectors = [
                'article[data-testid="tweet"]',
                'div[data-testid="tweet"]',
                'div[role="article"]',
            ]

            items = []
            for selector in tweet_selectors:
                tweets = await page.query_selector_all(selector)
                if tweets:
                    for tweet in tweets[:self.max_items]:
                        try:
                            item = await self._parse_tweet_element(tweet, username)
                            if item:
                                items.append(item)
                        except Exception as e:
                            self.logger.debug(f"解析推文失败: {e}")
                    break

            return items

        except Exception as e:
            self.logger.error(f"爬取用户 @{username} 失败: {e}")
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
        url = f"https://twitter.com/{username}"
        if link_elements:
            href = await link_elements[0].get_attribute("href")
            if href:
                url = f"https://twitter.com{href}"

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
            language=self.language,
            publish_date=publish_date,
            author=username,
            metadata={
                "username": username,
                "platform": "twitter",
                "fetched_with": "playwright",
            }
        )

        return item