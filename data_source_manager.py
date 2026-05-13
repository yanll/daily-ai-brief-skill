#!/usr/bin/env python3
"""
AI新闻数据源管理器
负责从RSS、API和网页爬虫获取AI新闻数据
"""

import os
import sys
import yaml
import json
import time
import hashlib
import feedparser
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random
from urllib.parse import urlparse

class DataSourceManager:
    """数据源管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化数据源管理器"""
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        if config_path is None:
            config_path = os.path.join(self.base_dir, "data_sources.yaml")

        self.config = self.load_config(config_path)

        self.session = requests.Session()
        user_agent = self.config.get("fetch_config", {}).get("user_agent",
                                                           "AI-Daily-Brief/1.0")
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/rss+xml, application/xml, text/xml, application/json, text/html",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7"
        })

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """加载数据源配置文件"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ 数据源配置文件加载失败: {e}")
            return {}

    def get_cache_key(self, source_name: str, source_url: str) -> str:
        """生成缓存键"""
        cache_key = f"{source_name}_{source_url}"
        return hashlib.md5(cache_key.encode()).hexdigest()

    def fetch_rss_source(self, source_config: Dict) -> List[Dict]:
        """获取RSS源数据（增强版，带重试和容错机制）"""
        source_name = source_config.get("name", "未知源")
        source_url = source_config.get("url", "")
        language = source_config.get("language", "en")

        if not source_url:
            print(f"⚠️ 渠道 {source_name} URL为空，跳过")
            return []

        print(f"🔍 渠道 {source_name} 开始采集...")

        max_retries = self.config.get("fetch_config", {}).get("max_retries", 3)
        retry_delay = self.config.get("fetch_config", {}).get("retry_delay_seconds", 2)

        for attempt in range(max_retries):
            try:
                import socket
                socket.setdefaulttimeout(30)
                feed = feedparser.parse(source_url)

                bozo_error = False
                if hasattr(feed, 'bozo_exception') and feed.bozo_exception:
                    bozo_error = True
                    if attempt < max_retries - 1:
                        print(f"⚠️ 渠道 {source_name} RSS解析警告 (尝试 {attempt+1}/{max_retries}): {feed.bozo_exception}")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"⚠️ 渠道 {source_name} RSS解析错误，跳过: {feed.bozo_exception}")

                items = []
                max_items = self.config.get("fetch_config", {}).get("max_items_per_source", 10)

                if not hasattr(feed, 'entries') or not feed.entries:
                    if not bozo_error:
                        print(f"📭 渠道 {source_name} 没有可用的新闻条目")
                    return []

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
                            except:
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

                        min_length = self.config.get("fetch_config", {}).get("min_content_length", 20)
                        max_length = self.config.get("fetch_config", {}).get("max_content_length", 3000)

                        content = description or title
                        if len(content) < min_length or len(content) > max_length:
                            continue

                        items.append({
                            "title": title,
                            "description": description[:800],
                            "link": link,
                            "published": published.isoformat(),
                            "source": source_name,
                            "language": language,
                            "type": "rss"
                        })
                        items_collected += 1

                    except Exception as e:
                        continue

                if items:
                    print(f"✅ 渠道 {source_name} 采集到 {len(items)} 条数据")
                else:
                    print(f"📭 渠道 {source_name} 未采集到符合条件的数据")

                return items

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 渠道 {source_name} 采集失败 (尝试 {attempt+1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                else:
                    print(f"❌ 渠道 {source_name} 采集失败 (已重试 {max_retries} 次): {e}")

        return []

    def fetch_api_source(self, source_config: Dict) -> List[Dict]:
        """获取API源数据"""
        source_name = source_config.get("name", "未知源")
        source_type = source_config.get("type", "")
        endpoint = source_config.get("endpoint", "")

        if not endpoint:
            print(f"⚠️ 渠道 {source_name} endpoint为空，跳过")
            return []

        print(f"🔍 渠道 {source_name} 开始采集...")

        try:
            if source_type == "google_news":
                return self.fetch_google_news(source_config)
            elif source_type == "newsapi":
                return self.fetch_newsapi(source_config)
            elif source_type == "hackernews":
                return self.fetch_hackernews(source_config)
            elif source_type == "github":
                return self.fetch_github_api(source_config)
            else:
                return self.fetch_generic_api(source_config)

        except Exception as e:
            print(f"❌ 渠道 {source_name} API采集失败: {e}")
            return []

    def fetch_google_news(self, source_config: Dict) -> List[Dict]:
        """获取Google News数据（实际上是RSS）"""
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
        """获取NewsAPI数据（需要API密钥）"""
        print(f"⚠️ NewsAPI需要API密钥，跳过 {source_config.get('name')}")
        return []

    def fetch_hackernews(self, source_config: Dict) -> List[Dict]:
        """获取Hacker News数据"""
        source_name = source_config.get("name", "HackerNews")
        endpoint = source_config.get("endpoint", "https://hacker-news.firebaseio.com/v0/topstories.json")
        max_items = source_config.get("num_items",
                                       self.config.get("fetch_config", {}).get("max_items_per_source", 10))
        timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 30)

        try:
            response = self.session.get(endpoint, timeout=timeout)
            response.raise_for_status()
            story_ids = response.json()

            items = []
            for story_id in story_ids[:max_items]:
                try:
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    story_resp = self.session.get(story_url, timeout=timeout)
                    story_resp.raise_for_status()
                    story = story_resp.json()

                    if not story or story.get("type") != "story":
                        continue

                    title = story.get("title", "").strip()
                    if not title:
                        continue

                    score = story.get("score", 0)
                    if score < 5:
                        continue

                    if self.contains_excluded_keywords(title):
                        continue

                    published = datetime.fromtimestamp(story.get("time", 0))
                    max_age_hours = self.config.get("fetch_config", {}).get("max_age_hours", 72)
                    if datetime.now() - published > timedelta(hours=max_age_hours):
                        continue

                    link = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")

                    items.append({
                        "title": title,
                        "description": f"Score: {score} | Comments: {story.get('descendants', 0)}",
                        "link": link,
                        "published": published.isoformat(),
                        "source": source_name,
                        "language": "en",
                        "type": "api"
                    })

                    time.sleep(0.1)

                except Exception:
                    continue

            if items:
                print(f"✅ 渠道 {source_name} 采集到 {len(items)} 条数据")
            else:
                print(f"📭 渠道 {source_name} 未采集到符合条件的数据")

            return items

        except Exception as e:
            print(f"❌ 渠道 {source_name} HackerNews采集失败: {e}")
            return []

    def fetch_github_api(self, source_config: Dict) -> List[Dict]:
        """获取GitHub Trending数据"""
        source_name = source_config.get("name", "GitHub Trending")
        endpoint = source_config.get("endpoint", "")
        params = source_config.get("params", {})
        max_items = source_config.get("num_items", 8)
        timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 30)

        if not endpoint:
            print(f"⚠️ 渠道 {source_name} endpoint为空，跳过")
            return []

        try:
            response = self.session.get(endpoint, params=params, timeout=timeout)
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
                        except:
                            published = datetime.now()

                        items.append({
                            "title": title,
                            "description": desc_enhanced[:800],
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
                            "description": description[:800],
                            "link": repo.get("html_url", ""),
                            "published": repo.get("updated_at", datetime.now().isoformat()),
                            "source": source_name,
                            "language": "en",
                            "type": "api"
                        })
                    except Exception:
                        continue

            if items:
                print(f"✅ 渠道 {source_name} 采集到 {len(items)} 条数据")
            else:
                print(f"📭 渠道 {source_name} 未采集到符合条件的数据")

            return items

        except Exception as e:
            print(f"❌ 渠道 {source_name} GitHub API采集失败: {e}")
            return []

    def fetch_generic_api(self, source_config: Dict) -> List[Dict]:
        """获取通用API数据"""
        endpoint = source_config.get("endpoint", "")
        params = source_config.get("params", {})

        max_retries = self.config.get("fetch_config", {}).get("max_retries", 3)
        timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 30)

        for attempt in range(max_retries):
            try:
                response = self.session.get(endpoint, params=params, timeout=timeout)
                response.raise_for_status()

                data = response.json()

                items = []
                if "articles" in data:
                    for article in data.get("articles", [])[:10]:
                        items.append({
                            "title": article.get("title", ""),
                            "description": article.get("description", ""),
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
                            "description": article.get("abstract", article.get("description", "")),
                            "link": article.get("url", ""),
                            "published": article.get("published", datetime.now().isoformat()),
                            "source": source_config.get("name", "未知"),
                            "language": "en",
                            "type": "api"
                        })

                if items:
                    print(f"✅ 渠道 {source_config.get('name', '未知')} 采集到 {len(items)} 条数据")

                return items

            except Exception as e:
                if attempt < max_retries - 1:
                    delay = self.config.get("fetch_config", {}).get("retry_delay_seconds", 5)
                    time.sleep(delay)
                else:
                    raise e

        return []

    def fetch_web_scraper_source(self, source_config: Dict) -> List[Dict]:
        """网页爬虫数据源 - 尝试RSS方式获取，失败则跳过"""
        source_name = source_config.get("name", "未知源")
        source_url = source_config.get("url", "")
        language = source_config.get("language", "en")

        if not source_url:
            print(f"⚠️ 渠道 {source_name} URL为空，跳过")
            return []

        print(f"🔍 渠道 {source_name} (网页爬虫) 开始采集...")

        rss_url = source_url
        if not rss_url.endswith(("/feed", "/feed/", "/rss", "/rss.xml", "/atom.xml")):
            possible_rss = [
                rss_url.rstrip("/") + "/feed",
                rss_url.rstrip("/") + "/rss",
                rss_url.rstrip("/") + "/feed.xml",
                rss_url.rstrip("/") + "/atom.xml",
            ]
            rss_url = possible_rss[0]

        rss_config = {
            "name": source_name,
            "url": rss_url,
            "language": language,
            "filters": source_config.get("filters", {})
        }

        items = self.fetch_rss_source(rss_config)

        if not items:
            try:
                timeout = self.config.get("fetch_config", {}).get("timeout_seconds", 30)
                response = self.session.get(source_url, timeout=timeout)
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "")
                if "json" in content_type:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            for item in data[:5]:
                                items.append({
                                    "title": item.get("title", ""),
                                    "description": item.get("description", item.get("abstract", "")),
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
                                        "description": item.get("description", item.get("abstract", "")),
                                        "link": item.get("url", item.get("link", "")),
                                        "published": item.get("published", datetime.now().isoformat()),
                                        "source": source_name,
                                        "language": language,
                                        "type": "web"
                                    })
                    except json.JSONDecodeError:
                        pass

                if items:
                    print(f"✅ 渠道 {source_name} 网页采集到 {len(items)} 条数据")
                else:
                    print(f"📭 渠道 {source_name} 网页采集未获取到数据")

            except Exception as e:
                print(f"⚠️ 渠道 {source_name} 网页爬虫采集失败: {e}")

        return items

    def fetch_x_source(self, source_config: Dict) -> List[Dict]:
        """获取X/Twitter数据源（通过Nitter实例RSS）"""
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
            print(f"⚠️ 渠道 {source_name} 无用户名，跳过")
            return []

        print(f"🔍 渠道 {source_name} (X/Twitter) 开始采集...")

        nitter_instances = [
            "https://nitter.net",
            "https://nitter.poast.org",
            "https://nitter.privacydev.net",
        ]

        items = []

        for un in all_usernames[:3]:
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
                        break
                except Exception:
                    continue
                time.sleep(0.5)

        if items:
            print(f"✅ 渠道 {source_name} 采集到 {len(items)} 条数据")
        else:
            print(f"📭 渠道 {source_name} X/Twitter源未采集到数据")

        return items

    def contains_excluded_keywords(self, text: str) -> bool:
        """检查是否包含排除关键词"""
        exclude_keywords = self.config.get("fetch_config", {}).get("exclude_keywords", [])
        text_lower = text.lower()

        for keyword in exclude_keywords:
            if keyword.lower() in text_lower:
                return True

        return False

    def fetch_all_sources(self) -> List[Dict]:
        """从所有启用的数据源获取数据（增强版，带进度报告和容错）"""
        all_items = []
        successful_sources = 0
        total_sources = 0

        print("📡 开始从所有数据源采集数据...")

        # 获取RSS源数据
        rss_sources = self.config.get("rss_sources", [])
        enabled_rss_sources = [s for s in rss_sources if s.get("enabled", False)]
        total_sources += len(enabled_rss_sources)

        for i, source in enumerate(enabled_rss_sources, 1):
            source_name = source.get('name', f'RSS源{i}')
            print(f"\n[{i}/{len(enabled_rss_sources)}] 🔍 采集 {source_name}...")

            try:
                items = self.fetch_rss_source(source)
                if items:
                    all_items.extend(items)
                    successful_sources += 1
                    print(f"   ✅ 采集到 {len(items)} 条数据")
                else:
                    print(f"   📭 未采集到数据")
            except Exception as e:
                print(f"   ❌ 采集失败: {e}")

            time.sleep(0.5 + random.random() * 0.5)

        # 获取API源数据
        api_sources = self.config.get("api_sources", [])
        enabled_api_sources = [s for s in api_sources if s.get("enabled", False)]
        total_sources += len(enabled_api_sources)

        for i, source in enumerate(enabled_api_sources, 1):
            source_name = source.get('name', f'API源{i}')
            print(f"\n[{i}/{len(enabled_api_sources)}] 🔍 采集 {source_name}...")

            try:
                items = self.fetch_api_source(source)
                if items:
                    all_items.extend(items)
                    successful_sources += 1
                    print(f"   ✅ 采集到 {len(items)} 条数据")
                else:
                    print(f"   📭 未采集到数据")
            except Exception as e:
                print(f"   ❌ 采集失败: {e}")

            time.sleep(1 + random.random())

        # 获取网页爬虫数据
        web_scrapers = self.config.get("web_scrapers", [])
        enabled_web_scrapers = [s for s in web_scrapers if s.get("enabled", False)]
        total_sources += len(enabled_web_scrapers)

        for i, source in enumerate(enabled_web_scrapers, 1):
            source_name = source.get('name', f'网页源{i}')
            print(f"\n[{i}/{len(enabled_web_scrapers)}] 🔍 采集 {source_name}...")

            try:
                items = self.fetch_web_scraper_source(source)
                if items:
                    all_items.extend(items)
                    successful_sources += 1
                    print(f"   ✅ 采集到 {len(items)} 条数据")
                else:
                    print(f"   📭 未采集到数据")
            except Exception as e:
                print(f"   ❌ 采集失败: {e}")

            time.sleep(0.5 + random.random() * 0.5)

        # 获取X/Twitter数据
        x_sources = self.config.get("x_sources", [])
        enabled_x_sources = [s for s in x_sources if s.get("enabled", False)]
        total_sources += len(enabled_x_sources)

        for i, source in enumerate(enabled_x_sources, 1):
            source_name = source.get('name', f'X源{i}')
            print(f"\n[{i}/{len(enabled_x_sources)}] 🔍 采集 {source_name}...")

            try:
                items = self.fetch_x_source(source)
                if items:
                    all_items.extend(items)
                    successful_sources += 1
                    print(f"   ✅ 采集到 {len(items)} 条数据")
                else:
                    print(f"   📭 未采集到数据")
            except Exception as e:
                print(f"   ❌ 采集失败: {e}")

            time.sleep(0.5 + random.random() * 0.5)

        # 按发布时间排序（最新的在前）
        all_items.sort(key=lambda x: x.get("published", ""), reverse=True)

        # 去重（基于标题和链接的组合）
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

        print(f"\n📊 采集结果汇总:")
        print(f"   📡 数据源: {successful_sources}/{total_sources} 个成功")
        print(f"   📄 原始数据: {len(all_items)} 条")
        print(f"   🎯 唯一数据: {len(unique_items)} 条")

        if unique_items:
            print(f"\n📰 示例数据 (前3条):")
            for i, item in enumerate(unique_items[:3], 1):
                title = item.get("title", "无标题")
                source = item.get("source", "未知来源")
                print(f"   {i}. [{source}] {title[:60]}...")

        return unique_items

    def get_ai_news_summary(self) -> Dict[str, Any]:
        """获取AI新闻摘要（允许空数据）"""
        all_items = self.fetch_all_sources()

        if not all_items:
            print("📭 所有渠道均未采集到数据")
            return {
                "success": True,
                "items": [],
                "total": 0,
                "timestamp": datetime.now().isoformat()
            }

        total_max_items = 0
        for source_type in ["rss_sources", "x_sources", "web_scrapers", "api_sources"]:
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
    """测试数据源功能"""
    print("🧪 测试数据源管理器...")

    manager = DataSourceManager()

    summary = manager.get_ai_news_summary()

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
