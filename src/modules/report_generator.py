"""
报告生成器
将抓取结果保存为文件
"""
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from .base_fetcher import NewsItem


class ReportGenerator:
    """报告生成器"""

    def __init__(self, output_dir: str = None):
        """
        初始化报告生成器

        Args:
            output_dir: 输出目录，默认为项目根目录下的reports目录
        """
        if output_dir is None:
            # 默认输出目录
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.output_dir = os.path.join(current_dir, "..", "reports")
        else:
            self.output_dir = output_dir

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        self.logger = logging.getLogger(__name__)

    def generate_daily_report(self, items: List[NewsItem], orchestrator=None) -> str:
        """
        生成每日报告

        Args:
            items: 新闻条目列表
            orchestrator: 协调器对象（可选），用于获取统计信息

        Returns:
            报告文件路径
        """
        # 按发布时间降序排序
        sorted_items = sorted(items, key=lambda x: x.publish_date, reverse=True)

        # 生成报告文件名
        date_str = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_news_report_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)

        # 生成简单报告内容
        report_lines = []
        report_lines.append("# 今日AI新闻")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"总条目数: {len(sorted_items)}")
        report_lines.append("")

        # 按频道分组
        channels = {}
        for item in sorted_items:
            channel = self._get_channel(item)
            if channel not in channels:
                channels[channel] = []
            channels[channel].append(item)

        # 按频道名称排序，确保"其他来源"在最后
        def channel_sort_key(channel_item):
            channel_name, _ = channel_item
            if channel_name == "其他来源":
                return (1, channel_name)
            else:
                return (0, channel_name)

        sorted_channels = sorted(channels.items(), key=channel_sort_key)

        item_counter = 1
        for channel_name, channel_items in sorted_channels:
            report_lines.append(f"## 🗂️ {channel_name} ({len(channel_items)}条)")
            report_lines.append("")

            for item in channel_items:
                report_lines.append(f"### {item_counter}. {item.title}")
                report_lines.append(f"**来源**: {item.source}")
                report_lines.append(f"**发布时间**: {item.publish_date.strftime('%Y-%m-%d %H:%M') if item.publish_date else '未知'}")
                report_lines.append(f"**链接**: [阅读原文]({item.url})")
                if item.summary:
                    report_lines.append(f"**摘要**:")
                    report_lines.append(f"{item.summary[:300]}...")
                report_lines.append("")
                item_counter += 1

        # 添加统计信息
        stats = self._generate_statistics(sorted_items, orchestrator)
        report_lines.append("## 统计信息")
        report_lines.append(stats)

        # 保存报告
        report_content = "\n".join(report_lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)

        self.logger.info(f"报告已保存: {filepath}")
        return filepath

    def generate_json_report(self, items: List[NewsItem]) -> str:
        """
        生成JSON格式报告

        Args:
            items: 新闻条目列表

        Returns:
            JSON报告文件路径
        """
        # 按发布时间降序排序
        sorted_items = sorted(items, key=lambda x: x.publish_date, reverse=True)

        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_news_report_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        # 转换为字典列表
        items_dict = [item.to_dict() for item in sorted_items]

        # 添加元数据
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_items": len(items_dict),
                "source_count": len(set(item["source"] for item in items_dict)),
            },
            "items": items_dict
        }

        # 保存JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(f"JSON报告已保存: {filepath}")
        return filepath

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

    def _get_category(self, item: NewsItem) -> str:
        """
        根据新闻内容确定分类

        Args:
            item: 新闻条目

        Returns:
            分类名称
        """
        text = f"{item.title} {item.summary} {item.content}".lower()

        # 技术突破关键词
        breakthrough_keywords = [
            "breakthrough", "state of the art", "sota", "record", "里程碑",
            "革命性", "颠覆", "重大突破", "突破性", "创新", "novel", "innovative",
            "groundbreaking", "pioneering", "新模型", "算法改进", "性能提升"
        ]

        # 产品动态关键词
        product_keywords = [
            "product", "产品", "update", "更新", "上线", "launch", "发布",
            "feature", "功能", "用户体验", "user experience", "改进", "改进版"
        ]

        # 行业应用关键词
        industry_keywords = [
            "industry", "行业", "application", "应用", "落地", "case", "案例",
            "商业合作", "合作", "partnership", "enterprise", "企业", "制造业",
            "医疗", "教育", "金融", "finance", "healthcare", "education"
        ]

        # 开源项目关键词
        open_source_keywords = [
            "open source", "开源", "github", "repo", "repository", "project",
            "项目", "version", "版本", "release", "发布", "contribute", "贡献"
        ]

        # 学术前沿关键词
        academic_keywords = [
            "paper", "论文", "research", "研究", "academic", "学术", "conference",
            "会议", "预印本", "preprint", "arxiv", "期刊", "journal", "发表"
        ]

        # 政策监管关键词
        policy_keywords = [
            "policy", "政策", "regulation", "监管", "law", "法律", "法规",
            "合规", "compliance", "标准", "standard", "治理", "governance"
        ]

        # 投融资讯关键词
        funding_keywords = [
            "funding", "融资", "investment", "投资", "并购", "acquisition",
            "ipo", "上市", "venture", "风投", "capital", "资本", "融资轮",
            "seed", "series", "round", "估值", "valuation"
        ]

        # 专家观点关键词
        expert_keywords = [
            "expert", "专家", "opinion", "观点", "commentary", "评论",
            "interview", "访谈", "speech", "演讲", "statement", "声明",
            "分析", "analysis", "perspective", "视角"
        ]

        # 检查每个类别的关键词匹配数
        category_scores = {
            "技术突破": sum(1 for kw in breakthrough_keywords if kw in text),
            "产品动态": sum(1 for kw in product_keywords if kw in text),
            "行业应用": sum(1 for kw in industry_keywords if kw in text),
            "开源项目": sum(1 for kw in open_source_keywords if kw in text),
            "学术前沿": sum(1 for kw in academic_keywords if kw in text),
            "政策监管": sum(1 for kw in policy_keywords if kw in text),
            "投融资讯": sum(1 for kw in funding_keywords if kw in text),
            "专家观点": sum(1 for kw in expert_keywords if kw in text),
        }

        # 找到分数最高的类别
        max_score = max(category_scores.values())
        if max_score > 0:
            # 返回分数最高的类别
            for category, score in category_scores.items():
                if score == max_score:
                    return category

        # 默认类别
        return "行业动态"

    def generate_summary_report(self, items: List[NewsItem], orchestrator=None, top_n: int = None) -> str:
        """
        生成摘要报告（简洁版）

        Args:
            items: 新闻条目列表
            orchestrator: 协调器对象（可选），用于获取统计信息
            top_n: 显示前N个条目，None表示显示所有

        Returns:
            摘要报告文件路径
        """
        # 按发布时间降序排序
        sorted_items = sorted(items, key=lambda x: x.publish_date, reverse=True)

        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_news_summary_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)

        # 生成摘要内容
        summary_lines = []
        summary_lines.append("# AI新闻摘要")
        summary_lines.append("")

        # 决定显示哪些条目
        if top_n is None:
            display_items = sorted_items
            display_count = len(sorted_items)
        else:
            display_items = sorted_items[:top_n]
            display_count = top_n

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
            summary_lines.append(f"## 🗂️ {channel_name} ({len(channel_items)}条)")
            summary_lines.append("")

            for item in channel_items:
                summary_lines.append(f"### {item_counter}. {item.title}")
                summary_lines.append(f"**来源**: {item.source}")
                summary_lines.append(f"**发布时间**: {item.publish_date.strftime('%Y-%m-%d %H:%M') if item.publish_date else '未知'}")
                summary_lines.append(f"**链接**: [阅读原文]({item.url})")
                if item.summary:
                    summary_lines.append(f"**摘要**:")
                    summary_lines.append(f"{item.summary[:200]}...")
                summary_lines.append("")
                item_counter += 1

        # 统计信息
        summary_lines.append("## 📊 统计信息")
        summary_lines.append(f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary_lines.append(f"- **总条目数**: {len(sorted_items)}")
        if top_n is None:
            summary_lines.append(f"- **显示**: 所有新闻条目 ({display_count}条)")
        else:
            summary_lines.append(f"- **显示**: 前 {display_count} 个条目")

        # 抓取器统计
        if orchestrator:
            stats = orchestrator.get_statistics()
            total_fetchers = stats.get("total_fetchers", 0)
            successful_fetchers = stats.get("successful_fetchers", 0)
            failed_fetchers = stats.get("failed_fetchers", 0)

            if total_fetchers > 0:
                summary_lines.append(f"- 抓取成功率: {successful_fetchers}/{total_fetchers} ({successful_fetchers/total_fetchers*100:.1f}%)")
                if failed_fetchers > 0:
                    failed_sources = stats.get("failed_sources", [])
                    summary_lines.append(f"- 失败来源: {failed_fetchers} 个")
                    if failed_sources:
                        summary_lines.append(f"  - {', '.join(failed_sources[:3])}")
                        if len(failed_sources) > 3:
                            summary_lines.append(f"    （共 {len(failed_sources)} 个失败来源）")

        # 保存摘要
        summary_content = "\n".join(summary_lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary_content)

        self.logger.info(f"摘要报告已保存: {filepath}")
        return filepath

    def generate_structured_report(self, items: List[NewsItem], orchestrator=None) -> str:
        """
        生成结构化报告，按照用户建议的每日简报结构组织

        Args:
            items: 新闻条目列表
            orchestrator: 协调器对象（可选），用于获取统计信息

        Returns:
            结构化报告文件路径
        """
        # 按发布时间降序排序
        sorted_items = sorted(items, key=lambda x: x.publish_date, reverse=True)

        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_news_report_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)

        # 生成报告内容
        report_lines = []
        # 获取当前日期
        current_date = datetime.now()
        # 格式化为"年月日 今日AI简报"
        date_str = current_date.strftime("%Y年%m月%d日")
        report_lines.append(f"# {date_str} 行业简报")
        report_lines.append("")

        # 按分类分组
        categories = {
            "今日头条": [],
            "技术突破": [],
            "产品动态": [],
            "行业应用": [],
            "开源项目": [],
            "学术前沿": [],
            "政策监管": [],
            "投融资讯": [],
            "专家观点": [],
        }

        # 首先找出今日头条（最新的1-2条）
        if sorted_items:
            # 取最新的2条作为今日头条
            top_items = sorted_items[:2]
            categories["今日头条"] = top_items

            # 其他新闻按分类分组
            other_items = sorted_items[2:]
            for item in other_items:
                category = self._get_category(item)
                # 如果分类不在预定义列表中，放入技术突破
                if category not in categories:
                    category = "技术突破"
                categories[category].append(item)

        # 生成每个分类的内容
        for category_name, category_items in categories.items():
            if not category_items:
                continue

            report_lines.append(f"## {category_name}")
            report_lines.append("")

            for i, item in enumerate(category_items, 1):
                report_lines.append(f"### {i}. {item.title}")
                report_lines.append(f"**来源**: {item.source}")
                report_lines.append(f"**发布时间**: {item.publish_date.strftime('%Y-%m-%d %H:%M') if item.publish_date else '未知'}")
                report_lines.append(f"**链接**: [阅读原文]({item.url})")
                if item.summary:
                    report_lines.append(f"**摘要**:")
                    report_lines.append(f"{item.summary[:250]}...")
                report_lines.append("")

        # 添加统计信息
        report_lines.append("## 📊 统计信息")
        stats = self._generate_statistics(sorted_items, orchestrator)
        report_lines.append(stats)

        # 保存报告
        report_content = "\n".join(report_lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)

        self.logger.info(f"结构化报告已保存: {filepath}")
        return filepath

    def _generate_statistics(self, items: List[NewsItem], orchestrator=None) -> str:
        """
        生成统计信息

        Args:
            items: 新闻条目列表
            orchestrator: 协调器对象（可选），用于获取失败信息

        Returns:
            统计信息文本
        """
        # 基本统计
        total_items = len(items)

        # 抓取器统计
        if orchestrator:
            stats = orchestrator.get_statistics()
            total_fetchers = stats.get("total_fetchers", 0)
            successful_fetchers = stats.get("successful_fetchers", 0)
            failed_fetchers = stats.get("failed_fetchers", 0)
            failed_sources = stats.get("failed_sources", [])
        else:
            total_fetchers = successful_fetchers = failed_fetchers = 0
            failed_sources = []

        # 来源统计
        source_counts = {}
        source_type_counts = {}
        language_counts = {}
        for item in items:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1
            source_type_counts[item.source_type] = source_type_counts.get(item.source_type, 0) + 1
            language_counts[item.language] = language_counts.get(item.language, 0) + 1

        # 时间统计
        now = datetime.now()
        recent_24h = len([item for item in items
                         if item.publish_date and (now - item.publish_date).total_seconds() <= 86400])

        # 生成统计文本
        stats_lines = []
        stats_lines.append(f"- 24小时内新闻: {recent_24h}")

        if total_fetchers > 0:
            stats_lines.append(f"- 抓取器统计: {successful_fetchers}/{total_fetchers} 成功")
            if failed_fetchers > 0:
                stats_lines.append(f"- 失败抓取器: {failed_fetchers} 个")
                if failed_sources:
                    stats_lines.append(f"- 失败来源: {', '.join(failed_sources[:5])}")
                    if len(failed_sources) > 5:
                        stats_lines.append(f"  （共 {len(failed_sources)} 个失败来源）")

        stats_lines.append("")

        # 只在有数据时显示来源分布
        if source_type_counts:
            stats_lines.append("### 来源分布")
            for source_type, count in sorted(source_type_counts.items(), key=lambda x: x[1], reverse=True):
                stats_lines.append(f"- {source_type}: {count} 条")

        if language_counts:
            stats_lines.append("")
            stats_lines.append("### 语言分布")
            for language, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
                stats_lines.append(f"- {language}: {count} 条")

        if source_counts:
            stats_lines.append("")
            stats_lines.append("### 热门来源（前5）")
            top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            for source, count in top_sources:
                stats_lines.append(f"- {source}: {count} 条")

        return "\n".join(stats_lines)

    def generate_all_reports(self, items: List[NewsItem], orchestrator=None) -> Dict[str, str]:
        """
        生成所有类型的报告

        Args:
            items: 新闻条目列表
            orchestrator: 协调器对象（可选），用于获取统计信息

        Returns:
            报告文件路径字典
        """
        reports = {}

        try:
            # 只生成结构化报告（最全最优的Markdown报告）
            reports["structured"] = self.generate_structured_report(items, orchestrator)
        except Exception as e:
            self.logger.error(f"生成结构化报告失败: {e}")

        try:
            # 保留JSON报告作为机器可读格式
            reports["json"] = self.generate_json_report(items)
        except Exception as e:
            self.logger.error(f"生成JSON报告失败: {e}")

        return reports