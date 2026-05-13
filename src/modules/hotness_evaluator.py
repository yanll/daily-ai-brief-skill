"""
热度评估模块
根据规则参考.md中的标准评估新闻条目的热度
"""
import logging
import re
from typing import List, Dict, Any
from datetime import datetime, timedelta

from .base_fetcher import NewsItem


class HotnessEvaluator:
    """热度评估器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 热度信号权重（来自规则参考.md）
        self.weights = {
            "multiple_sources": 3.0,      # 多家媒体报道同一事件
            "viral_community": 3.0,       # 社区病毒传播证据
            "authoritative_source": 3.0,  # 来自权威来源
            "user_experience": 2.0,       # 实际用户体验分享
            "technical_breakthrough": 2.0, # 技术突破性/影响范围
            "controversy": 2.0,           # 争议性（安全、伦理讨论）
            "recency": 1.0,               # 时效性
        }

        # 权威来源关键词
        self.authoritative_keywords = [
            "openai", "anthropic", "google", "deepmind", "meta", "microsoft",
            "arxiv", "neurips", "icml", "iclr", "acl", "emnlp",
            "nature", "science", "cell", "lancet",
            "mit", "stanford", "harvard", "oxford", "cambridge",
            "官方", "公告", "发布", "research", "paper", "预印本"
        ]

        # 社区病毒传播关键词
        self.viral_keywords = [
            "viral", "trending", "爆火", "刷屏", "刷爆", "疯传",
            "github trending", "star", "fork", "热门",
            "everyone is talking about", "everywhere", "exploding",
            "hacker news", "reddit", "twitter", "微博", "朋友圈"
        ]

        # 技术突破关键词
        self.breakthrough_keywords = [
            "breakthrough", "state of the art", "sota", "record", "里程碑",
            "革命性", "颠覆", "重大突破", "突破性", "创新",
            "novel", "innovative", "groundbreaking", "pioneering"
        ]

        # 争议性关键词
        self.controversy_keywords = [
            "controversy", "debate", "争议", "讨论", "ethical", "伦理",
            "safety", "安全", "risk", "危险", "warning", "警告",
            "concern", "担忧", "problem", "issue", "挑战", "challenge"
        ]

    def evaluate_all(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        评估所有条目的热度

        Args:
            items: 新闻条目列表

        Returns:
            评估后的新闻条目列表（按热度排序）
        """
        self.logger.info(f"开始评估 {len(items)} 个条目的热度")

        # 首先识别重复/相似条目（多家媒体报道同一事件）
        grouped_items = self._group_similar_items(items)

        # 评估每个条目的热度
        evaluated_items = []
        for group in grouped_items:
            for item in group:
                score = self.evaluate_single(item, group)
                item.hotness_score = score
                evaluated_items.append(item)

        # 按热度分数降序排序
        evaluated_items.sort(key=lambda x: x.hotness_score, reverse=True)

        self.logger.info(f"热度评估完成，最高分: {evaluated_items[0].hotness_score if evaluated_items else 0}")
        return evaluated_items

    def evaluate_single(self, item: NewsItem, similar_items: List[NewsItem] = None) -> float:
        """
        评估单个条目的热度

        Args:
            item: 新闻条目
            similar_items: 相似条目列表（用于计算多家媒体报道）

        Returns:
            热度分数（0-10）
        """
        score = 0.0

        # 1. 多家媒体报道同一事件
        if similar_items and len(similar_items) > 1:
            source_count = len(similar_items)
            if source_count >= 3:
                score += self.weights["multiple_sources"] * 1.0
            elif source_count == 2:
                score += self.weights["multiple_sources"] * 0.5

        # 2. 社区病毒传播证据
        viral_score = self._check_viral_evidence(item)
        score += self.weights["viral_community"] * viral_score

        # 3. 来自权威来源
        authoritative_score = self._check_authoritative_source(item)
        score += self.weights["authoritative_source"] * authoritative_score

        # 4. 实际用户体验分享
        user_exp_score = self._check_user_experience(item)
        score += self.weights["user_experience"] * user_exp_score

        # 5. 技术突破性/影响范围
        breakthrough_score = self._check_technical_breakthrough(item)
        score += self.weights["technical_breakthrough"] * breakthrough_score

        # 6. 争议性
        controversy_score = self._check_controversy(item)
        score += self.weights["controversy"] * controversy_score

        # 7. 时效性
        recency_score = self._check_recency(item)
        score += self.weights["recency"] * recency_score

        # 限制分数在0-10之间
        return min(10.0, max(0.0, score))

    def _group_similar_items(self, items: List[NewsItem]) -> List[List[NewsItem]]:
        """
        将相似条目分组（基于标题相似性）

        Args:
            items: 新闻条目列表

        Returns:
            分组后的条目列表
        """
        if not items:
            return []

        # 简单基于关键词的分组
        groups = []
        used_indices = set()

        for i, item in enumerate(items):
            if i in used_indices:
                continue

            # 创建新组
            group = [item]
            used_indices.add(i)

            # 查找相似条目
            for j, other_item in enumerate(items[i+1:], start=i+1):
                if j in used_indices:
                    continue

                if self._are_items_similar(item, other_item):
                    group.append(other_item)
                    used_indices.add(j)

            groups.append(group)

        # 记录分组统计
        multi_source_count = sum(1 for group in groups if len(group) > 1)
        self.logger.info(f"条目分组完成: {len(groups)} 个组，{multi_source_count} 个多源组")

        return groups

    def _are_items_similar(self, item1: NewsItem, item2: NewsItem) -> bool:
        """
        判断两个条目是否相似

        Args:
            item1: 第一个条目
            item2: 第二个条目

        Returns:
            是否相似
        """
        # 方法1: 标题关键词重叠
        title1 = item1.title.lower()
        title2 = item2.title.lower()

        # 提取关键词（去除常见词）
        words1 = set(re.findall(r'\b\w{4,}\b', title1))
        words2 = set(re.findall(r'\b\w{4,}\b', title2))

        common_words = words1.intersection(words2)
        if len(common_words) >= 2:
            return True

        # 方法2: 检查是否指向同一事件（基于命名实体）
        # 这里简化处理，实际可以使用更复杂的NLP方法

        return False

    def _check_viral_evidence(self, item: NewsItem) -> float:
        """
        检查社区病毒传播证据

        Args:
            item: 新闻条目

        Returns:
            病毒传播分数（0-1）
        """
        text = f"{item.title} {item.content} {item.summary}".lower()

        # 检查病毒传播关键词
        viral_count = 0
        for keyword in self.viral_keywords:
            if keyword.lower() in text:
                viral_count += 1

        # 检查来源类型
        if item.source_type in ["reddit", "twitter", "hackernews"]:
            viral_count += 1

        # 检查元数据中的社区指标
        metadata = item.metadata
        if metadata.get("score", 0) > 100:  # Reddit/HN分数
            viral_count += 1
        if metadata.get("descendants", 0) > 50:  # HN评论数
            viral_count += 1

        # 归一化到0-1
        return min(1.0, viral_count / 5.0)

    def _check_authoritative_source(self, item: NewsItem) -> float:
        """
        检查是否来自权威来源

        Args:
            item: 新闻条目

        Returns:
            权威性分数（0-1）
        """
        text = f"{item.title} {item.content} {item.summary} {item.source}".lower()

        # 检查权威关键词
        authoritative_count = 0
        for keyword in self.authoritative_keywords:
            if keyword.lower() in text:
                authoritative_count += 1

        # 检查已知权威来源
        authoritative_sources = [
            "openai", "anthropic", "google", "deepmind", "meta", "microsoft",
            "arxiv", "neurips", "icml", "iclr", "mit", "stanford",
            "nature", "science", "36氪", "机器之心", "量子位"
        ]

        source_lower = item.source.lower()
        for auth_source in authoritative_sources:
            if auth_source in source_lower:
                authoritative_count += 2
                break

        # 归一化到0-1
        return min(1.0, authoritative_count / 5.0)

    def _check_user_experience(self, item: NewsItem) -> float:
        """
        检查实际用户体验分享

        Args:
            item: 新闻条目

        Returns:
            用户体验分数（0-1）
        """
        text = f"{item.title} {item.content} {item.summary}".lower()

        # 用户体验相关关键词
        user_exp_keywords = [
            "tutorial", "guide", "how to", "使用", "体验", "评测",
            "review", "hands-on", "实践", "案例", "example",
            "demo", "演示", "试用", "尝试", "亲自"
        ]

        user_exp_count = 0
        for keyword in user_exp_keywords:
            if keyword.lower() in text:
                user_exp_count += 1

        # 检查来源类型（教程、博客等）
        if any(tag in item.tags for tag in ["tutorial", "guide", "review", "demo"]):
            user_exp_count += 1

        # 归一化到0-1
        return min(1.0, user_exp_count / 5.0)

    def _check_technical_breakthrough(self, item: NewsItem) -> float:
        """
        检查技术突破性

        Args:
            item: 新闻条目

        Returns:
            技术突破分数（0-1）
        """
        text = f"{item.title} {item.content} {item.summary}".lower()

        breakthrough_count = 0
        for keyword in self.breakthrough_keywords:
            if keyword.lower() in text:
                breakthrough_count += 1

        # 检查学术相关标签
        if any(tag in item.tags for tag in ["research", "paper", "academic", "study"]):
            breakthrough_count += 1

        # 检查来源类型
        if item.source_type in ["arxiv", "research"]:
            breakthrough_count += 1

        # 归一化到0-1
        return min(1.0, breakthrough_count / 5.0)

    def _check_controversy(self, item: NewsItem) -> float:
        """
        检查争议性

        Args:
            item: 新闻条目

        Returns:
            争议性分数（0-1）
        """
        text = f"{item.title} {item.content} {item.summary}".lower()

        controversy_count = 0
        for keyword in self.controversy_keywords:
            if keyword.lower() in text:
                controversy_count += 1

        # 归一化到0-1
        return min(1.0, controversy_count / 5.0)

    def _check_recency(self, item: NewsItem) -> float:
        """
        检查时效性

        Args:
            item: 新闻条目

        Returns:
            时效性分数（0-1）
        """
        if not item.publish_date:
            return 0.0

        now = datetime.now()
        age_hours = (now - item.publish_date).total_seconds() / 3600

        # 越新分数越高
        if age_hours <= 1:
            return 1.0
        elif age_hours <= 6:
            return 0.8
        elif age_hours <= 24:
            return 0.6
        elif age_hours <= 48:
            return 0.4
        elif age_hours <= 72:
            return 0.2
        else:
            return 0.0

    def _get_channel(self, item: NewsItem) -> str:
        """
        根据新闻条目属性确定频道分组

        Args:
            item: 新闻条目

        Returns:
            频道名称
        """
        source_type = item.source_type.lower()
        source = item.source.lower()
        language = item.language.lower()

        # 根据source_type和language判断频道
        if source_type == "rss":
            if language == "zh":
                return "国内媒体"
            elif language == "en":
                # 进一步根据来源判断
                if "arxiv" in source:
                    return "学术研究"
                elif any(kw in source for kw in ["openai", "anthropic", "google", "deepmind", "meta", "microsoft", "huggingface"]):
                    return "官方博客"
                elif any(kw in source for kw in ["mit", "techcrunch", "theverge", "arstechnica", "venturebeat", "wired", "cnbc"]):
                    return "国际媒体"
                else:
                    return "英文媒体"
            else:
                return "其他语言媒体"
        elif source_type == "reddit":
            return "社区讨论 (Reddit)"
        elif source_type == "twitter" or source_type == "x":
            return "社交媒体 (X/Twitter)"
        elif source_type == "web_scraper":
            return "网页爬虫"
        elif source_type == "api":
            return "API数据"
        elif source_type == "hackernews":
            return "社区讨论 (Hacker News)"
        else:
            return "其他来源"

    def generate_hotness_report(self, items: List[NewsItem], top_n: int = None) -> str:
        """
        生成热度报告

        Args:
            items: 新闻条目列表
            top_n: 显示前N个条目，None表示显示所有

        Returns:
            报告文本
        """
        if not items:
            return "没有找到新闻条目"

        # 如果top_n为None，显示所有新闻
        if top_n is None:
            display_items = items
            display_count = len(items)
        else:
            display_items = items[:top_n]
            display_count = len(display_items)

        report_lines = []
        report_lines.append("# AI新闻完整报告")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"总条目数: {len(items)}")
        if top_n is None:
            report_lines.append("")
        else:
            report_lines.append(f"显示前 {display_count} 个热点")
        report_lines.append("")

        # 按频道分组
        channels = {}
        for item in display_items:
            channel = self._get_channel(item)
            if channel not in channels:
                channels[channel] = []
            channels[channel].append(item)

        # 按频道名称排序，确保"其他来源"在最后
        def channel_sort_key(channel_item):
            channel_name, _ = channel_item
            # 如果频道是"其他来源"，返回一个大值确保排在最后
            if channel_name == "其他来源":
                return (1, channel_name)  # 1表示排在最后
            else:
                return (0, channel_name)  # 0表示正常排序

        sorted_channels = sorted(channels.items(), key=channel_sort_key)

        item_counter = 1
        for channel_name, channel_items in sorted_channels:
            report_lines.append(f"## 🗂️ {channel_name} ({len(channel_items)}条)")
            report_lines.append("")

            for item in channel_items:
                report_lines.append(f"### {item_counter}. {item.title}")
                report_lines.append(f"**热度**: {item.hotness_score:.1f}/10")
                report_lines.append(f"**来源**: {item.source} ({item.source_type})")
                report_lines.append(f"**发布时间**: {item.publish_date.strftime('%Y-%m-%d %H:%M') if item.publish_date else '未知'}")
                report_lines.append(f"**链接**: [阅读原文]({item.url})")
                if item.summary:
                    report_lines.append(f"**摘要**: {item.summary[:300]}...")
                else:
                    report_lines.append(f"**摘要**: {item.content[:300]}..." if item.content else "**摘要**: 无")
                report_lines.append("")
                item_counter += 1

        return "\n".join(report_lines)