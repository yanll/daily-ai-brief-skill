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
from typing import Dict, List, Any, Optional, Tuple
import random
from urllib.parse import urlparse

class DataSourceManager:
    """数据源管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化数据源管理器"""
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 加载数据源配置
        if config_path is None:
            config_path = os.path.join(self.base_dir, "data_sources.yaml")
        
        self.config = self.load_config(config_path)
        
        # 初始化缓存目录
        self.cache_dir = self.config.get("fetch_config", {}).get("cache_dir", "./cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 初始化HTTP会话
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
            # 返回空配置
            return {}
    
    def get_cache_key(self, source_name: str, source_url: str) -> str:
        """生成缓存键"""
        cache_key = f"{source_name}_{source_url}"
        return hashlib.md5(cache_key.encode()).hexdigest()
    
    def get_cached_data(self, cache_key: str) -> Optional[List[Dict]]:
        """获取缓存数据"""
        if not self.config.get("fetch_config", {}).get("cache_enabled", True):
            return None
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if not os.path.exists(cache_file):
            return None
        
        # 检查缓存是否过期
        cache_ttl = self.config.get("fetch_config", {}).get("cache_ttl_minutes", 60)
        file_mtime = os.path.getmtime(cache_file)
        if time.time() - file_mtime > cache_ttl * 60:
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    
    def save_to_cache(self, cache_key: str, data: List[Dict]):
        """保存数据到缓存"""
        if not self.config.get("fetch_config", {}).get("cache_enabled", True):
            return
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 缓存保存失败: {e}")
    
    def fetch_rss_source(self, source_config: Dict) -> List[Dict]:
        """获取RSS源数据"""
        source_name = source_config.get("name", "未知源")
        source_url = source_config.get("url", "")
        language = source_config.get("language", "en")
        category = source_config.get("category", "industry")
        
        if not source_url:
            print(f"⚠️ 渠道 {source_name} URL为空，跳过")
            return []
        
        # 检查缓存
        cache_key = self.get_cache_key(source_name, source_url)
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            print(f"📄 渠道 {source_name} 使用缓存数据")
            return cached_data
        
        print(f"🔍 渠道 {source_name} 开始采集...")
        
        try:
            # 使用feedparser解析RSS
            feed = feedparser.parse(source_url)
            
            # 检查是否有错误
            if hasattr(feed, 'bozo_exception') and feed.bozo_exception:
                print(f"⚠️ 渠道 {source_name} RSS解析错误: {feed.bozo_exception}")
                return []
            
            items = []
            max_items = self.config.get("fetch_config", {}).get("max_items_per_source", 10)
            
            # 检查是否有条目
            if not hasattr(feed, 'entries') or not feed.entries:
                print(f"📭 渠道 {source_name} 没有可用的新闻条目")
                return []
            
            for entry in feed.entries[:max_items]:
                # 提取发布时间
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                else:
                    published = datetime.now()
                
                # 检查时间范围
                max_age_hours = self.config.get("fetch_config", {}).get("max_age_hours", 48)
                if datetime.now() - published > timedelta(hours=max_age_hours):
                    continue
                
                # 提取内容
                title = getattr(entry, 'title', '')
                description = getattr(entry, 'description', '')
                link = getattr(entry, 'link', '')
                
                # 检查是否包含需要的关键词（如果配置了include_keywords）
                include_keywords = source_config.get("filters", {}).get("include_keywords", [])
                if include_keywords:
                    content_text = (title + " " + description).lower()
                    has_include_keyword = False
                    for keyword in include_keywords:
                        if keyword.lower() in content_text:
                            has_include_keyword = True
                            break
                    if not has_include_keyword:
                        continue  # 不包含所需关键词，跳过
                
                # 过滤广告内容
                if self.contains_excluded_keywords(title + " " + description):
                    continue
                
                # 检查内容长度
                min_length = self.config.get("fetch_config", {}).get("min_content_length", 30)  # 降低最小长度
                max_length = self.config.get("fetch_config", {}).get("max_content_length", 2000)  # 增加最大长度
                
                content = description or title
                if len(content) < min_length or len(content) > max_length:
                    continue
                
                # 确定分类
                item_category = self.determine_category(title + " " + description, category)
                
                items.append({
                    "title": title,
                    "description": description[:500],  # 限制描述长度
                    "link": link,
                    "published": published.isoformat(),
                    "source": source_name,
                    "language": language,
                    "category": item_category,
                    "type": "rss"
                })
            
            # 保存到缓存
            if items:
                self.save_to_cache(cache_key, items)
            
            return items
            
        except Exception as e:
            print(f"❌ 渠道 {source_name} RSS采集失败: {e}")
            return []
    
    def fetch_api_source(self, source_config: Dict) -> List[Dict]:
        """获取API源数据"""
        source_name = source_config.get("name", "未知源")
        source_type = source_config.get("type", "")
        endpoint = source_config.get("endpoint", "")
        
        if not endpoint:
            print(f"⚠️ 渠道 {source_name} endpoint为空，跳过")
            return []
        
        # 检查缓存
        cache_key = self.get_cache_key(source_name, endpoint)
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            print(f"📄 渠道 {source_name} 使用缓存数据")
            return cached_data
        
        print(f"🔍 渠道 {source_name} 开始采集...")
        
        try:
            if source_type == "google_news":
                return self.fetch_google_news(source_config)
            elif source_type == "newsapi":
                return self.fetch_newsapi(source_config)
            else:
                return self.fetch_generic_api(source_config)
                
        except Exception as e:
            print(f"❌ 渠道 {source_name} API采集失败: {e}")
            return []
    
    def fetch_google_news(self, source_config: Dict) -> List[Dict]:
        """获取Google News数据（实际上是RSS）"""
        endpoint = source_config.get("endpoint", "")
        params = source_config.get("params", {})
        
        # 构建RSS URL
        rss_url = f"{endpoint}?q={params.get('q', 'artificial intelligence')}"
        
        # 临时修改配置作为RSS源处理
        rss_config = {
            "name": source_config.get("name"),
            "url": rss_url,
            "language": params.get("hl", "en"),
            "category": "industry"
        }
        
        return self.fetch_rss_source(rss_config)
    
    def fetch_newsapi(self, source_config: Dict) -> List[Dict]:
        """获取NewsAPI数据（需要API密钥）"""
        # 这里只是示例，实际需要API密钥
        print(f"⚠️ NewsAPI需要API密钥，跳过 {source_config.get('name')}")
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
                
                # 这里需要根据具体API响应格式解析
                # 示例：假设API返回articles数组
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
                            "category": self.determine_category(article.get("title", "")),
                            "type": "api"
                        })
                
                return items
                
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = self.config.get("fetch_config", {}).get("retry_delay_seconds", 5)
                    time.sleep(delay)
                else:
                    raise e
        
        return []
    
    def contains_excluded_keywords(self, text: str) -> bool:
        """检查是否包含排除关键词"""
        exclude_keywords = self.config.get("fetch_config", {}).get("exclude_keywords", [])
        text_lower = text.lower()
        
        for keyword in exclude_keywords:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    def determine_category(self, text: str, default_category: str = "industry") -> str:
        """根据文本内容确定分类"""
        text_lower = text.lower()
        
        category_mapping = self.config.get("category_mapping", {}).get("keywords_to_categories", [])
        
        for mapping in category_mapping:
            keywords = mapping.get("keywords", [])
            category = mapping.get("category", "")
            
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return category
        
        return default_category
    
    def fetch_all_sources(self) -> List[Dict]:
        """从所有启用的数据源获取数据（每个渠道独立采集，采集不到就空着）"""
        all_items = []
        
        # 获取RSS源数据
        rss_sources = self.config.get("rss_sources", [])
        for source in rss_sources:
            if source.get("enabled", False):
                try:
                    items = self.fetch_rss_source(source)
                    all_items.extend(items)
                    print(f"✅ 渠道 {source.get('name')} 采集到 {len(items)} 条数据")
                except Exception as e:
                    print(f"⚠️ 渠道 {source.get('name')} 采集失败: {e}")
                    # 失败时不添加任何数据，保持为空
                
                # 避免请求过快
                time.sleep(0.5)
        
        # 获取API源数据
        api_sources = self.config.get("api_sources", [])
        for source in api_sources:
            if source.get("enabled", False):
                try:
                    items = self.fetch_api_source(source)
                    all_items.extend(items)
                    print(f"✅ 渠道 {source.get('name')} 采集到 {len(items)} 条数据")
                except Exception as e:
                    print(f"⚠️ 渠道 {source.get('name')} 采集失败: {e}")
                    # 失败时不添加任何数据，保持为空
                
                # 避免请求过快
                time.sleep(1)
        
        # 按发布时间排序（最新的在前）
        all_items.sort(key=lambda x: x.get("published", ""), reverse=True)
        
        # 去重（基于标题）
        seen_titles = set()
        unique_items = []
        
        for item in all_items:
            title = item.get("title", "").strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_items.append(item)
        
        print(f"📊 总计采集到 {len(unique_items)} 条唯一数据")
        return unique_items
    
    def get_ai_news_summary(self) -> Dict[str, Any]:
        """获取AI新闻摘要（允许空数据）"""
        all_items = self.fetch_all_sources()
        
        # 即使没有数据也返回成功，但包含空列表
        if not all_items:
            print("📭 所有渠道均未采集到数据")
            return {
                "success": True,  # 仍然返回成功，表示采集过程正常
                "items": [],
                "total": 0,
                "categories": {},
                "timestamp": datetime.now().isoformat()
            }
        
        # 计算所有数据源的总num_items
        total_max_items = 0
        for source_type in ["rss_sources", "x_sources", "web_scrapers", "api_sources"]:
            sources = self.config.get(source_type, [])
            for source in sources:
                if source.get("enabled", False):
                    total_max_items += source.get("num_items", 5)  # 默认5条
        
        # 限制总条数，但不超过实际采集到的条数
        max_items = min(total_max_items, len(all_items))
        
        # 按类别统计
        categories = {}
        for item in all_items[:max_items]:
            category = item.get("category", "其他")
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        # 选择最重要的新闻
        selected_items = all_items[:max_items]
        
        return {
            "success": True,
            "items": selected_items,
            "total": len(selected_items),
            "categories": categories,
            "timestamp": datetime.now().isoformat()
        }

def test_data_sources():
    """测试数据源功能"""
    print("🧪 测试数据源管理器...")
    
    manager = DataSourceManager()
    
    # 测试获取数据
    summary = manager.get_ai_news_summary()
    
    if summary["success"]:
        print(f"✅ 成功获取 {summary['total']} 条新闻")
        print(f"📊 分类统计: {summary['categories']}")
        
        for i, item in enumerate(summary["items"], 1):
            print(f"\n{i}. {item['title']}")
            print(f"   来源: {item['source']}")
            print(f"   分类: {item['category']}")
            print(f"   时间: {item['published']}")
    else:
        print(f"❌ 获取失败: {summary['error']}")

if __name__ == "__main__":
    test_data_sources()