"""
Reddit抓取器
通过RSS方式抓取Reddit内容
"""
import asyncio
import logging
import time
from typing import List, Dict, Any
from datetime import datetime

from .base_fetcher import BaseFetcher, NewsItem
from .rss_fetcher import RSSFetcher


class RedditFetcher(BaseFetcher):
    """Reddit抓取器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.subreddit = config.get("subreddit", "")
        self.rss_url = f"https://www.reddit.com/r/{self.subreddit}/.rss"
        self.logger = logging.getLogger(f"RedditFetcher.{self.name}")

        # 使用RSS抓取器作为后端
        rss_config = {
            "name": self.name,
            "url": self.rss_url,
            "language": self.language,
            "enabled": self.enabled,
            "priority": self.priority,
            "num_items": self.max_items,
            "filters": self.filters,
        }
        self.rss_fetcher = RSSFetcher(rss_config)

    async def fetch(self) -> List[NewsItem]:
        """
        抓取Reddit内容

        Returns:
            新闻条目列表
        """
        if not self.enabled:
            self.logger.info(f"数据源已禁用: {self.name}")
            return []

        if not self.subreddit:
            self.logger.error(f"Subreddit为空: {self.name}")
            return []

        self.logger.info(f"开始抓取Reddit: r/{self.subreddit}")
        start_time = time.time()

        try:
            # 使用RSS抓取器获取数据
            items = await self.rss_fetcher.fetch()

            # 为Reddit条目添加特定元数据
            for item in items:
                item.source_type = "reddit"
                item.metadata.update({
                    "subreddit": self.subreddit,
                    "platform": "reddit",
                })

                # 尝试从Reddit RSS条目中提取更多信息
                if "reddit" in item.url.lower():
                    # 可以添加Reddit特定处理逻辑
                    pass

            elapsed = time.time() - start_time
            self.logger.info(f"Reddit抓取完成: r/{self.subreddit}, 获取 {len(items)} 个条目, 耗时 {elapsed:.2f}秒")
            return items

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"抓取Reddit失败 r/{self.subreddit}, 耗时 {elapsed:.2f}秒: {e}")
            return []


class RedditAPIFetcher(BaseFetcher):
    """
    Reddit API抓取器（需要认证）
    注意：Reddit API需要OAuth2认证，此实现为示例
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.subreddit = config.get("subreddit", "")
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.user_agent = config.get("user_agent", "AI News Aggregator/1.0")
        self.logger = logging.getLogger(f"RedditAPIFetcher.{self.name}")

    async def fetch(self) -> List[NewsItem]:
        """
        使用Reddit API抓取内容（需要认证）

        Returns:
            新闻条目列表
        """
        if not self.enabled:
            self.logger.info(f"数据源已禁用: {self.name}")
            return []

        if not self.subreddit:
            self.logger.error(f"Subreddit为空: {self.name}")
            return []

        self.logger.warning("Reddit API抓取器需要OAuth2认证，当前使用RSS替代")
        # 回退到RSS方式
        rss_fetcher = RedditFetcher(self.config)
        return await rss_fetcher.fetch()