#!/usr/bin/env python3
"""
AI新闻数据源管理器
负责从RSS、API和网页爬虫获取AI新闻数据
支持并行采集，大幅提升采集速度
集成Playwright浏览器渲染，解决JS渲染页面采集问题
"""

import os
import re
import sys
import yaml
import json
import time
import hashlib
import feedparser
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

_thread_local = threading.local()

_ILLEGAL_XML_RE = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]"
)


def _fix_rss_content(content: bytes) -> bytes:
    if not content:
        return content
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        return content

    text = _ILLEGAL_XML_RE.sub("", text)

    text = re.sub(r"&(?!(?:[a-zA-Z][a-zA-Z0-9]*|#\d+|#x[0-9a-fA-F]+);)", "&amp;", text)

    return text.encode("utf-8", errors="replace")


def _discover_feed_url(html_content: str, original_url: str) -> Optional[str]:
    if not html_content or not BS4_AVAILABLE:
        return None
    try:
        from bs4 import BeautifulSoup as _BS
        soup = _BS(html_content, "lxml")
        link_tags = soup.find_all("link", rel=True, type=True)
        for link in link_tags:
            rel = link.get("rel", [])
            link_type = link.get("type", "")
            href = link.get("href", "")
            is_feed = (
                "alternate" in rel
                and link_type in ("application/rss+xml", "application/atom+xml", "application/feed+json")
            ) or (
                "feed" in rel
            )
            if is_feed and href:
                if href.startswith("http"):
                    return href
                return urljoin(original_url, href)
    except Exception:
        pass
    return None


BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

_playwright_lock = threading.Lock()
_playwright_instance = None
_browser_instance = None


def _get_playwright_browser():
    global _playwright_instance, _browser_instance
    with _playwright_lock:
        if _browser_instance is None and PLAYWRIGHT_AVAILABLE:
            try:
                _playwright_instance = sync_playwright().start()
                _browser_instance = _playwright_instance.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
            except Exception as e:
                print(f"⚠️ Playwright浏览器启动失败: {e}")
                _browser_instance = None
    return _browser_instance


def _close_playwright():
    global _playwright_instance, _browser_instance
    with _playwright_lock:
        try:
            if _browser_instance:
                _browser_instance.close()
                _browser_instance = None
            if _playwright_instance:
                _playwright_instance.stop()
                _playwright_instance = None
        except Exception:
            pass


def _fetch_with_playwright(url: str, wait_seconds: int = 3) -> Optional[str]:
    if not PLAYWRIGHT_AVAILABLE:
        return None

    browser = _get_playwright_browser()
    if not browser:
        return None

    try:
        context = browser.new_context(
            user_agent=BROWSER_USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = context.new_page()
        page.set_default_timeout(15000)
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(wait_seconds * 1000)
        content = page.content()
        context.close()
        return content
    except Exception:
        return None


def _get_thread_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        session = requests.Session()
        session.headers.update({
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/rss+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
        })
        _thread_local.session = session
    return _thread_local.session


class DataSourceManager:
    """数据源管理器（并行采集版 + Playwright渲染兜底）"""

    def __init__(self, config_path: Optional[str] = None, max_workers: int = 20):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        if config_path is None:
            config_path = os.path.join(self.base_dir, "data_sources.yaml")

        self.config = self.load_config(config_path)
        self.max_workers = max_workers

        self._print_lock = threading.Lock()
        self._pw_lock = threading.Lock()

    def _log(self, msg: str):
        with self._print_lock:
            print(msg)

    def load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ 数据源配置文件加载失败: {e}")
            return {}

    def get_cache_key(self, source_name: str, source_url: str) -> str:
        cache_key = f"{source_name}_{source_url}"
        return hashlib.md5(cache_key.encode()).hexdigest()

    def _fetch_url_with_fallback(self, url: str, timeout: int = 15,
                                  headers: Optional[Dict] = None) -> Tuple[Optional[bytes], Optional[str]]:
        session = _get_thread_session()

        fetch_headers = dict(session.headers)
        if headers:
            fetch_headers.update(headers)

        try:
            resp = session.get(url, timeout=timeout, headers=fetch_headers,
                               allow_redirects=True)
            if resp.status_code >= 400 and resp.status_code < 500:
                return None, f"HTTP {resp.status_code}"
            resp.raise_for_status()
            return resp.content, None
        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, "status_code", 0) if e.response else 0
            if 400 <= status < 500:
                return None, f"HTTP {status}"
            return None, f"HTTPError: {e}"
        except requests.exceptions.Timeout:
            return None, "timeout"
        except requests.exceptions.ConnectionError as e:
            return None, f"connection: {e}"
        except Exception as e:
            return None, str(e)

    def fetch_rss_source(self, source_config: Dict) -> List[Dict]:
        source_name = source_config.get("name", "未知源")
        source_url = source_config.get("url", "")
        language = source_config.get("language", "en")

        if not source_url:
            self._log(f"⚠️ 渠道 {source_name} URL为空，跳过")
            return []

        self._log(f"🔍 渠道 {source_name} 开始采集...")

        max_retries = self.config.get("fetch_config", {}).get("max_retries", 3)
        retry_delay = self.config.get("fetch_config", {}).get("retry_delay_seconds", 2)
        timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 20)

        network_errors = 0
        for attempt in range(max_retries):
            try:
                content, fetch_error = self._fetch_url_with_fallback(source_url, timeout=timeout)

                if fetch_error:
                    is_client_error = fetch_error.startswith("HTTP 4") or fetch_error.startswith("HTTP 403") or fetch_error.startswith("HTTP 404")
                    if is_client_error:
                        self._log(f"🚫 渠道 {source_name} 请求被拒绝 ({fetch_error})，不再重试")
                        return []
                    if fetch_error == "timeout" or fetch_error.startswith("connection"):
                        network_errors += 1
                        if network_errors < max_retries:
                            self._log(f"⚠️ 渠道 {source_name} 网络错误 ({fetch_error}, 第{network_errors}次)，重试...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            self._log(f"❌ 渠道 {source_name} 网络错误已重试{max_retries}次: {fetch_error}")
                            return []
                    self._log(f"❌ 渠道 {source_name} 请求失败: {fetch_error}")
                    return []

                feed = feedparser.parse(content)

                bozo = getattr(feed, 'bozo', False)
                bozo_exception = getattr(feed, 'bozo_exception', None)
                has_entries = hasattr(feed, 'entries') and len(feed.entries) > 0

                if has_entries:
                    if bozo and bozo_exception:
                        self._log(f"⚠️ 渠道 {source_name} RSS有解析警告但存在条目，继续提取 ({len(feed.entries)}条)")
                    return self._extract_rss_items(feed, source_config, source_name, language)

                if bozo and bozo_exception and not has_entries:
                    fixed_content = _fix_rss_content(content)
                    if fixed_content != content:
                        self._log(f"🔧 渠道 {source_name} RSS解析失败，尝试修复内容后重新解析...")
                        feed = feedparser.parse(fixed_content)
                        if hasattr(feed, 'entries') and len(feed.entries) > 0:
                            self._log(f"✅ 渠道 {source_name} 修复后成功解析 ({len(feed.entries)}条)")
                            return self._extract_rss_items(feed, source_config, source_name, language)

                    content_type = type(bozo_exception).__name__
                    if content_type in ("CharacterEncodingOverride", "NonXMLContentType"):
                        self._log(f"⚠️ 渠道 {source_name} 编码问题({content_type})，强制解析")
                        feed = feedparser.parse(content, response_headers={"content-type": "text/xml"})
                        if hasattr(feed, 'entries') and len(feed.entries) > 0:
                            return self._extract_rss_items(feed, source_config, source_name, language)

                    try:
                        text = content.decode("utf-8", errors="replace")[:2000]
                        feed_url = _discover_feed_url(text, source_url)
                        if feed_url and feed_url != source_url:
                            self._log(f"🔗 渠道 {source_name} 发现真实Feed地址: {feed_url}")
                            real_content, real_error = self._fetch_url_with_fallback(feed_url, timeout=timeout)
                            if real_content and not real_error:
                                feed = feedparser.parse(real_content)
                                if hasattr(feed, 'entries') and len(feed.entries) > 0:
                                    return self._extract_rss_items(feed, source_config, source_name, language)
                    except Exception:
                        pass

                    self._log(f"⚠️ 渠道 {source_name} RSS解析失败，所有修复手段均无效: {bozo_exception}")
                    return []

                if not has_entries:
                    if content and not bozo:
                        try:
                            text = content.decode("utf-8", errors="replace")[:2000]
                            feed_url = _discover_feed_url(text, source_url)
                            if feed_url and feed_url != source_url:
                                self._log(f"🔗 渠道 {source_name} 页面无条目，发现Feed地址: {feed_url}")
                                real_content, real_error = self._fetch_url_with_fallback(feed_url, timeout=timeout)
                                if real_content and not real_error:
                                    feed = feedparser.parse(real_content)
                                    if hasattr(feed, 'entries') and len(feed.entries) > 0:
                                        return self._extract_rss_items(feed, source_config, source_name, language)
                        except Exception:
                            pass

                    self._log(f"📭 渠道 {source_name} 没有可用的新闻条目")
                    return []

            except Exception as e:
                network_errors += 1
                if network_errors < max_retries:
                    self._log(f"⚠️ 渠道 {source_name} 采集异常 (第{network_errors}次): {e}")
                    time.sleep(retry_delay)
                else:
                    self._log(f"❌ 渠道 {source_name} 采集异常 (已重试{max_retries}次): {e}")

        return []

    def _extract_rss_items(self, feed, source_config: Dict,
                            source_name: str, language: str) -> List[Dict]:
        items = []
        max_items = source_config.get("num_items",
            self.config.get("fetch_config", {}).get("max_items_per_source", 10))

        items_collected = 0
        for entry in feed.entries:
            if items_collected >= max_items:
                break

            try:
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                elif hasattr(entry, 'date'):
                    try:
                        published = datetime.strptime(entry.date, "%Y-%m-%dT%H:%M:%SZ")
                    except Exception:
                        published = datetime.now()
                else:
                    published = datetime.now()

                max_age_hours = self.config.get("fetch_config", {}).get("max_age_hours", 72)
                if datetime.now() - published > timedelta(hours=max_age_hours):
                    continue

                title = getattr(entry, 'title', '').strip()
                description = getattr(entry, 'description', '').strip()
                link = getattr(entry, 'link', '').strip()

                if not title:
                    continue

                include_keywords = source_config.get("filters", {}).get("include_keywords", [])
                if include_keywords:
                    content_text = (title + " " + description).lower()
                    has_include_keyword = False
                    for keyword in include_keywords:
                        if keyword.lower() in content_text:
                            has_include_keyword = True
                            break
                    if not has_include_keyword:
                        continue

                if self.contains_excluded_keywords(title + " " + description):
                    continue

                min_length = self.config.get("fetch_config", {}).get("min_content_length", 10)
                max_length = self.config.get("fetch_config", {}).get("max_content_length", 5000)

                content = description if description else title
                if len(content) < min_length:
                    if description:
                        continue

                if len(content) > max_length:
                    content = content[:max_length]

                items.append({
                    "title": title,
                    "content": content[:800],
                    "link": link,
                    "published": published.isoformat(),
                    "source": source_name,
                    "language": language,
                    "type": "rss"
                })
                items_collected += 1

            except Exception:
                continue

        if items:
            self._log(f"✅ 渠道 {source_name} 采集到 {len(items)} 条数据")
        else:
            self._log(f"📭 渠道 {source_name} 未采集到符合条件的数据")

        return items

    def fetch_api_source(self, source_config: Dict) -> List[Dict]:
        source_name = source_config.get("name", "未知源")
        source_type = source_config.get("type", "")
        endpoint = source_config.get("endpoint", "")

        if not endpoint and source_type != "reddit":
            self._log(f"⚠️ 渠道 {source_name} endpoint为空，跳过")
            return []

        self._log(f"🔍 渠道 {source_name} 开始采集...")

        try:
            if source_type == "google_news":
                return self.fetch_google_news(source_config)
            elif source_type == "newsapi":
                return self.fetch_newsapi(source_config)
            elif source_type == "hackernews":
                return self.fetch_hackernews(source_config)
            elif source_type == "github":
                return self.fetch_github_api(source_config)
            elif source_type == "reddit":
                return self.fetch_reddit_api(source_config)
            else:
                return self.fetch_generic_api(source_config)

        except Exception as e:
            self._log(f"❌ 渠道 {source_name} API采集失败: {e}")
            return []

    def fetch_google_news(self, source_config: Dict) -> List[Dict]:
        endpoint = source_config.get("endpoint", "")
        params = source_config.get("params", {})

        rss_url = f"{endpoint}?q={params.get('q', 'artificial intelligence')}"

        rss_config = {
            "name": source_config.get("name"),
            "url": rss_url,
            "language": params.get("hl", "en")
        }

        return self.fetch_rss_source(rss_config)

    def fetch_newsapi(self, source_config: Dict) -> List[Dict]:
        self._log(f"⚠️ NewsAPI需要API密钥，跳过 {source_config.get('name')}")
        return []

    def fetch_reddit_api(self, source_config: Dict) -> List[Dict]:
        source_name = source_config.get("name", "Reddit")
        subreddit = source_config.get("subreddit", "")
        max_items = source_config.get("num_items",
            self.config.get("fetch_config", {}).get("max_items_per_source", 10))
        timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 20)

        if not subreddit:
            self._log(f"⚠️ 渠道 {source_name} 无subreddit配置，跳过")
            return []

        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={max_items}"

        try:
            session = _get_thread_session()
            headers = {
                "User-Agent": BROWSER_USER_AGENT,
                "Accept": "application/json",
            }
            response = session.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()

            data = response.json()
            items = []

            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                title = post.get("title", "").strip()
                if not title:
                    continue

                score = post.get("score", 0)
                if score < 3:
                    continue

                permalink = post.get("permalink", "")
                link = f"https://www.reddit.com{permalink}" if permalink else ""
                url_external = post.get("url", "")
                if url_external and not url_external.startswith("https://www.reddit.com"):
                    link = url_external

                selftext = post.get("selftext", "")[:200]
                description = f"⬆️ {score} | {selftext}" if selftext else f"⬆️ {score}"

                created_utc = post.get("created_utc", 0)
                published = datetime.utcfromtimestamp(created_utc) if created_utc else datetime.now()

                max_age_hours = self.config.get("fetch_config", {}).get("max_age_hours", 72)
                if datetime.now() - published > timedelta(hours=max_age_hours):
                    continue

                items.append({
                    "title": title,
                    "content": description[:800],
                    "link": link,
                    "published": published.isoformat(),
                    "source": source_name,
                    "language": "en",
                    "type": "api"
                })

            if items:
                self._log(f"✅ 渠道 {source_name} 采集到 {len(items)} 条数据")
            else:
                self._log(f"📭 渠道 {source_name} 未采集到符合条件的数据")

            return items

        except Exception as e:
            self._log(f"❌ 渠道 {source_name} Reddit API采集失败: {e}")
            return []

    def fetch_hackernews(self, source_config: Dict) -> List[Dict]:
        source_name = source_config.get("name", "HackerNews")
        endpoint = source_config.get("endpoint", "https://hacker-news.firebaseio.com/v0/topstories.json")
        max_items = source_config.get("num_items",
                                       self.config.get("fetch_config", {}).get("max_items_per_source", 10))
        timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 20)

        try:
            session = _get_thread_session()
            response = session.get(endpoint, timeout=timeout)
            response.raise_for_status()
            story_ids = response.json()

            def fetch_hn_story(story_id: str) -> Optional[Dict]:
                try:
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    story_resp = session.get(story_url, timeout=timeout)
                    story_resp.raise_for_status()
                    story = story_resp.json()

                    if not story or story.get("type") != "story":
                        return None

                    title = story.get("title", "").strip()
                    if not title:
                        return None

                    score = story.get("score", 0)
                    if score < 5:
                        return None

                    if self.contains_excluded_keywords(title):
                        return None

                    published = datetime.fromtimestamp(story.get("time", 0))
                    max_age_hours = self.config.get("fetch_config", {}).get("max_age_hours", 72)
                    if datetime.now() - published > timedelta(hours=max_age_hours):
                        return None

                    link = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")

                    return {
                        "title": title,
                        "content": f"Score: {score} | Comments: {story.get('descendants', 0)}",
                        "link": link,
                        "published": published.isoformat(),
                        "source": source_name,
                        "language": "en",
                        "type": "api"
                    }
                except Exception:
                    return None

            items = []
            with ThreadPoolExecutor(max_workers=min(8, max_items)) as inner_pool:
                futures = {inner_pool.submit(fetch_hn_story, sid): sid for sid in story_ids[:max_items]}
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        items.append(result)

            if items:
                items.sort(key=lambda x: x.get("published", ""), reverse=True)
                self._log(f"✅ 渠道 {source_name} 采集到 {len(items)} 条数据")
            else:
                self._log(f"📭 渠道 {source_name} 未采集到符合条件的数据")

            return items

        except Exception as e:
            self._log(f"❌ 渠道 {source_name} HackerNews采集失败: {e}")
            return []

    def fetch_github_api(self, source_config: Dict) -> List[Dict]:
        source_name = source_config.get("name", "GitHub Trending")
        endpoint = source_config.get("endpoint", "")
        params = source_config.get("params", {})
        max_items = source_config.get("num_items", 8)
        timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 20)

        if not endpoint:
            self._log(f"⚠️ 渠道 {source_name} endpoint为空，跳过")
            return []

        try:
            session = _get_thread_session()
            response = session.get(endpoint, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            items = []

            if "items" in data:
                for repo in data.get("items", [])[:max_items]:
                    try:
                        full_name = repo.get("full_name", "")
                        description = repo.get("description", "") or ""
                        title = f"{full_name}: {description}" if description else full_name

                        if self.contains_excluded_keywords(title):
                            continue

                        stars = repo.get("stargazers_count", 0)
                        language = repo.get("language", "")
                        desc_enhanced = f"⭐ {stars} | Language: {language} | {description}"

                        updated_at = repo.get("updated_at", "")
                        try:
                            published = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%SZ")
                        except Exception:
                            published = datetime.now()

                        items.append({
                            "title": title,
                            "content": desc_enhanced[:800],
                            "link": repo.get("html_url", ""),
                            "published": published.isoformat(),
                            "source": source_name,
                            "language": "en",
                            "type": "api"
                        })
                    except Exception:
                        continue
            elif isinstance(data, list):
                for repo in data[:max_items]:
                    try:
                        full_name = repo.get("full_name", "")
                        description = repo.get("description", "") or ""
                        title = f"{full_name}: {description}" if description else full_name

                        items.append({
                            "title": title,
                            "content": description[:800],
                            "link": repo.get("html_url", ""),
                            "published": repo.get("updated_at", datetime.now().isoformat()),
                            "source": source_name,
                            "language": "en",
                            "type": "api"
                        })
                    except Exception:
                        continue

            if items:
                self._log(f"✅ 渠道 {source_name} 采集到 {len(items)} 条数据")
            else:
                self._log(f"📭 渠道 {source_name} 未采集到符合条件的数据")

            return items

        except Exception as e:
            self._log(f"❌ 渠道 {source_name} GitHub API采集失败: {e}")
            return []

    def fetch_generic_api(self, source_config: Dict) -> List[Dict]:
        endpoint = source_config.get("endpoint", "")
        params = source_config.get("params", {})
        source_name = source_config.get("name", "未知源")

        max_retries = self.config.get("fetch_config", {}).get("max_retries", 3)
        timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 20)

        network_errors = 0
        for attempt in range(max_retries):
            try:
                session = _get_thread_session()
                response = session.get(endpoint, params=params, timeout=timeout)

                if response.status_code >= 400 and response.status_code < 500:
                    self._log(f"🚫 渠道 {source_name} API请求被拒绝 (HTTP {response.status_code})，不再重试")
                    return []

                response.raise_for_status()

                data = response.json()

                items = []
                if "articles" in data:
                    for article in data.get("articles", [])[:10]:
                        items.append({
                            "title": article.get("title", ""),
                            "content": article.get("description", ""),
                            "link": article.get("url", ""),
                            "published": article.get("publishedAt", datetime.now().isoformat()),
                            "source": article.get("source", {}).get("name", "未知"),
                            "language": "en",
                            "type": "api"
                        })
                elif "results" in data:
                    for article in data.get("results", [])[:10]:
                        items.append({
                            "title": article.get("title", ""),
                            "content": article.get("abstract", article.get("description", "")),
                            "link": article.get("url", ""),
                            "published": article.get("published", datetime.now().isoformat()),
                            "source": source_config.get("name", "未知"),
                            "language": "en",
                            "type": "api"
                        })

                if items:
                    self._log(f"✅ 渠道 {source_name} 采集到 {len(items)} 条数据")

                return items

            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", 0) if e.response else 0
                if 400 <= status < 500:
                    self._log(f"🚫 渠道 {source_name} API请求被拒绝 (HTTP {status})，不再重试")
                    return []
                network_errors += 1
                if network_errors < max_retries:
                    delay = self.config.get("fetch_config", {}).get("retry_delay_seconds", 5)
                    time.sleep(delay)
                else:
                    self._log(f"❌ 渠道 {source_name} API采集失败 (已重试{max_retries}次): {e}")
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                network_errors += 1
                if network_errors < max_retries:
                    delay = self.config.get("fetch_config", {}).get("retry_delay_seconds", 5)
                    time.sleep(delay)
                else:
                    self._log(f"❌ 渠道 {source_name} API网络错误 (已重试{max_retries}次): {e}")
            except json.JSONDecodeError as e:
                self._log(f"⚠️ 渠道 {source_name} API返回非JSON数据，不再重试: {e}")
                return []
            except Exception as e:
                self._log(f"❌ 渠道 {source_name} API采集异常: {e}")
                return []

        return []

    def fetch_web_scraper_source(self, source_config: Dict) -> List[Dict]:
        source_name = source_config.get("name", "未知源")
        source_url = source_config.get("url", "")
        language = source_config.get("language", "en")

        if not source_url:
            self._log(f"⚠️ 渠道 {source_name} URL为空，跳过")
            return []

        self._log(f"🔍 渠道 {source_name} (网页爬虫) 开始采集...")

        possible_rss_urls = [source_url]
        if not source_url.endswith(("/feed", "/feed/", "/rss", "/rss.xml", "/atom.xml")):
            possible_rss_urls = [
                source_url.rstrip("/") + "/feed",
                source_url.rstrip("/") + "/rss",
                source_url.rstrip("/") + "/feed.xml",
                source_url.rstrip("/") + "/atom.xml",
                source_url,
            ]

        for rss_url in possible_rss_urls:
            rss_config = {
                "name": source_name,
                "url": rss_url,
                "language": language,
                "filters": source_config.get("filters", {}),
                "num_items": source_config.get("num_items", 5),
            }
            items = self.fetch_rss_source(rss_config)
            if items:
                return items

        items = self._try_json_endpoint(source_url, source_name, language)
        if items:
            return items

        if BS4_AVAILABLE:
            items = self._try_html_scraping(source_url, source_name, language,
                                             source_config.get("selector", ""))
            if items:
                return items

        items = self._try_playwright_scraping(source_url, source_name, language,
                                               source_config.get("selector", ""))
        if items:
            return items

        self._log(f"📭 渠道 {source_name} 网页爬虫全部方式均未获取到数据")
        return []

    def _try_json_endpoint(self, source_url: str, source_name: str,
                           language: str) -> List[Dict]:
        items = []
        try:
            timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 20)
            session = _get_thread_session()

            json_urls = [source_url]
            parsed = urlparse(source_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            json_urls.extend([
                source_url.rstrip("/") + ".json",
                base + "/api/v1/posts",
            ])

            for url in json_urls:
                try:
                    headers = {
                        "User-Agent": BROWSER_USER_AGENT,
                        "Accept": "application/json, text/plain, */*",
                    }
                    response = session.get(url, timeout=timeout, headers=headers)
                    if response.status_code != 200:
                        continue

                    content_type = response.headers.get("Content-Type", "")
                    if "json" not in content_type and not url.endswith(".json"):
                        continue

                    data = response.json()
                    if isinstance(data, list):
                        for item in data[:5]:
                            items.append({
                                "title": item.get("title", ""),
                                "content": item.get("description", item.get("abstract", "")),
                                "link": item.get("url", item.get("link", "")),
                                "published": item.get("published", item.get("date", datetime.now().isoformat())),
                                "source": source_name,
                                "language": language,
                                "type": "web"
                            })
                    elif isinstance(data, dict):
                        results = data.get("results", data.get("data", data.get("items", [])))
                        if isinstance(results, list):
                            for item in results[:5]:
                                items.append({
                                    "title": item.get("title", ""),
                                    "content": item.get("description", item.get("abstract", "")),
                                    "link": item.get("url", item.get("link", "")),
                                    "published": item.get("published", datetime.now().isoformat()),
                                    "source": source_name,
                                    "language": language,
                                    "type": "web"
                                })
                    if items:
                        self._log(f"✅ 渠道 {source_name} JSON端点采集到 {len(items)} 条数据")
                        return items
                except Exception:
                    continue

        except Exception as e:
            self._log(f"⚠️ 渠道 {source_name} JSON端点尝试失败: {e}")

        return items

    def _try_html_scraping(self, source_url: str, source_name: str,
                            language: str, selector: str) -> List[Dict]:
        if not BS4_AVAILABLE:
            return []

        items = []
        try:
            timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 20)
            session = _get_thread_session()
            headers = {
                "User-Agent": BROWSER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            response = session.get(source_url, timeout=timeout, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")

            items = self._extract_items_from_soup(soup, source_url, source_name, language, selector)

            if items:
                self._log(f"✅ 渠道 {source_name} HTML解析采集到 {len(items)} 条数据")
            return items

        except Exception as e:
            self._log(f"⚠️ 渠道 {source_name} HTML解析失败: {e}")
            return []

    def _try_playwright_scraping(self, source_url: str, source_name: str,
                                  language: str, selector: str) -> List[Dict]:
        if not PLAYWRIGHT_AVAILABLE:
            return []

        with self._pw_lock:
            try:
                html_content = _fetch_with_playwright(source_url, wait_seconds=3)
                if not html_content:
                    return []

                if not BS4_AVAILABLE:
                    return []

                soup = BeautifulSoup(html_content, "lxml")
                items = self._extract_items_from_soup(soup, source_url, source_name, language, selector)

                if items:
                    self._log(f"✅ 渠道 {source_name} Playwright渲染采集到 {len(items)} 条数据")
                return items

            except Exception as e:
                self._log(f"⚠️ 渠道 {source_name} Playwright渲染失败: {e}")
                return []

    def _extract_items_from_soup(self, soup, source_url: str, source_name: str,
                                  language: str, selector: str) -> List[Dict]:
        items = []

        article_selectors = [
            selector,
            "article",
            ".article", ".post", ".entry",
            ".news-item", ".card", ".item",
            ".ContentItem", ".topic-item",
            "[class*='article']", "[class*='post']",
            "main .content",
        ]

        elements = []
        for sel in article_selectors:
            if not sel:
                continue
            found = soup.select(sel)
            if found and len(found) >= 2:
                elements = found
                break

        if not elements:
            links = soup.find_all("a", href=True)
            seen_titles = set()
            for a_tag in links[:30]:
                text = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                if text and len(text) > 8 and text not in seen_titles:
                    seen_titles.add(text)
                    if not href.startswith("http"):
                        parsed = urlparse(source_url)
                        base = f"{parsed.scheme}://{parsed.netloc}"
                        href = base + href if href.startswith("/") else source_url + href
                    items.append({
                        "title": text,
                        "content": text,
                        "link": href,
                        "published": datetime.now().isoformat(),
                        "source": source_name,
                        "language": language,
                        "type": "web"
                    })
        else:
            for elem in elements[:10]:
                try:
                    title_tag = elem.find(["h1", "h2", "h3", "h4"]) or elem.find("a")
                    title = title_tag.get_text(strip=True) if title_tag else ""

                    link_tag = elem.find("a", href=True)
                    link = link_tag.get("href", "") if link_tag else ""
                    if link and not link.startswith("http"):
                        parsed = urlparse(source_url)
                        base = f"{parsed.scheme}://{parsed.netloc}"
                        link = base + link if link.startswith("/") else source_url + link

                    desc_tag = elem.find(["p", ".summary", ".description", ".excerpt"])
                    desc = desc_tag.get_text(strip=True)[:200] if desc_tag else title

                    if title and len(title) > 3:
                        items.append({
                            "title": title,
                            "content": desc[:800] if desc else title,
                            "link": link,
                            "published": datetime.now().isoformat(),
                            "source": source_name,
                            "language": language,
                            "type": "web"
                        })
                except Exception:
                    continue

        return items

    def fetch_x_source(self, source_config: Dict) -> List[Dict]:
        source_name = source_config.get("name", "未知源")
        username = source_config.get("username", "")
        usernames = source_config.get("usernames", [])
        language = source_config.get("language", "en")

        all_usernames = []
        if username:
            all_usernames.append(username)
        if usernames:
            all_usernames.extend(usernames)

        if not all_usernames:
            self._log(f"⚠️ 渠道 {source_name} 无用户名，跳过")
            return []

        self._log(f"🔍 渠道 {source_name} (X/Twitter) 开始采集...")

        nitter_instances = [
            "https://nitter.net",
            "https://nitter.poast.org",
            "https://nitter.privacydev.net",
            "https://nitter.cz",
            "https://nitter.unixfox.eu",
            "https://nitter.ktachibana.party",
        ]

        items = []

        for un in all_usernames[:3]:
            fetched_for_user = False
            for nitter_base in nitter_instances:
                rss_url = f"{nitter_base}/{un}/rss"
                rss_config = {
                    "name": f"{source_name} (@{un})",
                    "url": rss_url,
                    "language": language,
                }
                try:
                    fetched = self.fetch_rss_source(rss_config)
                    if fetched:
                        items.extend(fetched)
                        fetched_for_user = True
                        break
                except Exception:
                    continue

            if not fetched_for_user and BS4_AVAILABLE:
                for nitter_base in nitter_instances[:2]:
                    try:
                        profile_url = f"{nitter_base}/{un}"
                        timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 15)
                        session = _get_thread_session()
                        headers = {"User-Agent": BROWSER_USER_AGENT}
                        resp = session.get(profile_url, timeout=timeout, headers=headers)
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.content, "lxml")
                            tweets = soup.select(".timeline-item")
                            for tweet in tweets[:5]:
                                try:
                                    body = tweet.select_one(".tweet-content")
                                    if body:
                                        text = body.get_text(strip=True)
                                        if text and len(text) > 10:
                                            items.append({
                                                "title": text[:100],
                                                "content": text[:800],
                                                "link": f"https://x.com/{un}",
                                                "published": datetime.now().isoformat(),
                                                "source": f"{source_name} (@{un})",
                                                "language": language,
                                                "type": "x"
                                            })
                                except Exception:
                                    continue
                            if items:
                                fetched_for_user = True
                                break
                    except Exception:
                        continue

        if items:
            self._log(f"✅ 渠道 {source_name} 采集到 {len(items)} 条数据")
        else:
            self._log(f"📭 渠道 {source_name} X/Twitter源未采集到数据")

        return items

    def contains_excluded_keywords(self, text: str) -> bool:
        exclude_keywords = self.config.get("fetch_config", {}).get("exclude_keywords", [])
        text_lower = text.lower()

        for keyword in exclude_keywords:
            if keyword.lower() in text_lower:
                return True

        return False

    def _fetch_single_source(self, source_config: Dict, source_type: str) -> Tuple[str, List[Dict], bool]:
        source_name = source_config.get("name", "未知源")
        try:
            if source_type == "rss":
                items = self.fetch_rss_source(source_config)
            elif source_type == "api":
                items = self.fetch_api_source(source_config)
            elif source_type == "web":
                items = self.fetch_web_scraper_source(source_config)
            elif source_type == "x":
                items = self.fetch_x_source(source_config)
            else:
                items = []
            return (source_name, items, bool(items))
        except Exception as e:
            self._log(f"❌ 渠道 {source_name} 采集异常: {e}")
            return (source_name, [], False)

    def fetch_all_sources(self) -> List[Dict]:
        all_items = []
        successful_sources = 0
        total_sources = 0

        start_time = time.time()
        self._log("📡 开始并行采集所有数据源...")

        all_tasks = []

        rss_sources = self.config.get("rss_sources", [])
        for s in rss_sources:
            if s.get("enabled", False):
                all_tasks.append((s, "rss"))

        api_sources = self.config.get("api_sources", [])
        for s in api_sources:
            if s.get("enabled", False):
                all_tasks.append((s, "api"))

        web_scrapers = self.config.get("web_scrapers", [])
        for s in web_scrapers:
            if s.get("enabled", False):
                all_tasks.append((s, "web"))

        x_sources = self.config.get("x_sources", [])
        for s in x_sources:
            if s.get("enabled", False):
                all_tasks.append((s, "x"))

        reddit_sources = self.config.get("reddit_sources", [])
        for s in reddit_sources:
            if s.get("enabled", False):
                all_tasks.append((s, "api"))

        total_sources = len(all_tasks)
        completed = 0

        workers = min(self.max_workers, total_sources)
        self._log(f"🚀 共 {total_sources} 个数据源，使用 {workers} 个并行线程采集")

        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_source = {}
            for source_config, source_type in all_tasks:
                source_name = source_config.get("name", "未知源")
                future = pool.submit(self._fetch_single_source, source_config, source_type)
                future_to_source[future] = source_name

            for future in as_completed(future_to_source):
                source_name = future_to_source[future]
                completed += 1
                try:
                    name, items, success = future.result()
                    if success:
                        all_items.extend(items)
                        successful_sources += 1
                        self._log(f"[{completed}/{total_sources}] ✅ {name}: {len(items)} 条")
                    else:
                        self._log(f"[{completed}/{total_sources}] 📭 {name}: 无数据")
                except Exception as e:
                    self._log(f"[{completed}/{total_sources}] ❌ {source_name}: {e}")

        all_items.sort(key=lambda x: x.get("published", ""), reverse=True)

        seen_keys = set()
        unique_items = []

        for item in all_items:
            title = item.get("title", "").strip().lower()
            link = item.get("link", "").strip().lower()

            if title:
                key = title[:100]
                if link:
                    key = f"{title[:50]}|{link[:50]}"

                if key not in seen_keys:
                    seen_keys.add(key)
                    unique_items.append(item)

        elapsed = time.time() - start_time

        self._log(f"\n📊 采集结果汇总:")
        self._log(f"   📡 数据源: {successful_sources}/{total_sources} 个成功")
        self._log(f"   📄 原始数据: {len(all_items)} 条")
        self._log(f"   🎯 唯一数据: {len(unique_items)} 条")
        self._log(f"   ⏱️ 总耗时: {elapsed:.1f} 秒 ({workers}线程并行)")

        if unique_items:
            self._log(f"\n📰 示例数据 (前3条):")
            for i, item in enumerate(unique_items[:3], 1):
                title = item.get("title", "无标题")
                source = item.get("source", "未知来源")
                self._log(f"   {i}. [{source}] {title[:60]}...")

        return unique_items

    def get_ai_news_summary(self) -> Dict[str, Any]:
        all_items = self.fetch_all_sources()

        if not all_items:
            self._log("📭 所有渠道均未采集到数据")
            return {
                "success": True,
                "items": [],
                "total": 0,
                "timestamp": datetime.now().isoformat()
            }

        total_max_items = 0
        for source_type in ["rss_sources", "x_sources", "web_scrapers", "api_sources", "reddit_sources"]:
            sources = self.config.get(source_type, [])
            for source in sources:
                if source.get("enabled", False):
                    total_max_items += source.get("num_items", 5)

        max_items = min(total_max_items, len(all_items))

        selected_items = all_items[:max_items]

        return {
            "success": True,
            "items": selected_items,
            "total": len(selected_items),
            "timestamp": datetime.now().isoformat()
        }


def test_data_sources():
    print("🧪 测试数据源管理器（并行版 + Playwright）...")

    manager = DataSourceManager()

    summary = manager.get_ai_news_summary()

    _close_playwright()

    if summary["success"]:
        print(f"✅ 成功获取 {summary['total']} 条新闻")

        for i, item in enumerate(summary["items"], 1):
            print(f"\n{i}. {item['title']}")
            print(f"   来源: {item['source']}")
            print(f"   时间: {item['published']}")
    else:
        print(f"❌ 获取失败: {summary.get('error')}")

if __name__ == "__main__":
    test_data_sources()
