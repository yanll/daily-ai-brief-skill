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
from .hotness_evaluator import HotnessEvaluator


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
        self.hotness_evaluator = HotnessEvaluator()

    def generate_daily_report(self, items: List[NewsItem], orchestrator=None) -> str:
        """
        生成每日报告

        Args:
            items: 新闻条目列表
            orchestrator: 协调器对象（可选），用于获取统计信息

        Returns:
            报告文件路径
        """
        # 评估热度
        evaluated_items = self.hotness_evaluator.evaluate_all(items)

        # 生成报告文件名
        date_str = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_news_report_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)

        # 生成报告内容 - 显示所有新闻
        report_content = self.hotness_evaluator.generate_hotness_report(evaluated_items, top_n=None)

        # 添加统计信息
        stats = self._generate_statistics(evaluated_items, orchestrator)
        report_content += "\n\n## 统计信息\n"
        report_content += stats

        # 保存报告
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
        # 评估热度
        evaluated_items = self.hotness_evaluator.evaluate_all(items)

        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_news_report_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        # 转换为字典列表
        items_dict = [item.to_dict() for item in evaluated_items]

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
        # 评估热度
        evaluated_items = self.hotness_evaluator.evaluate_all(items)

        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_news_summary_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)

        # 生成摘要内容
        summary_lines = []
        summary_lines.append("# AI新闻列表")
        summary_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary_lines.append(f"总条目数: {len(evaluated_items)}")
        if top_n is None:
            summary_lines.append("")
        else:
            summary_lines.append(f"显示前 {top_n} 个条目")
        summary_lines.append("")

        # 决定显示哪些条目
        if top_n is None:
            display_items = evaluated_items
        else:
            display_items = evaluated_items[:top_n]

        # 按频道分组
        channels = {}
        for item in display_items:
            channel = self._get_channel(item)
            if channel not in channels:
                channels[channel] = []
            channels[channel].append(item)

        # 按频道名称排序
        sorted_channels = sorted(channels.items())

        item_counter = 1
        for channel_name, channel_items in sorted_channels:
            summary_lines.append(f"## 🗂️ {channel_name} ({len(channel_items)}条)")
            summary_lines.append("")

            for item in channel_items:
                summary_lines.append(f"### {item_counter}. {item.title}")
                summary_lines.append(f"**热度**: {item.hotness_score:.1f}/10")
                summary_lines.append(f"**来源**: {item.source} ({item.source_type})")
                summary_lines.append(f"**发布时间**: {item.publish_date.strftime('%Y-%m-%d %H:%M') if item.publish_date else '未知'}")
                summary_lines.append(f"**链接**: [阅读原文]({item.url})")
                if item.summary:
                    summary_lines.append(f"**摘要**: {item.summary[:200]}...")
                summary_lines.append("")
                item_counter += 1

        # 统计信息
        summary_lines.append("## 📊 统计信息")
        summary_lines.append(f"- 总条目数: {len(evaluated_items)}")

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
        hot_items = len([item for item in items if item.hotness_score >= 7.0]) if items else 0

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
        stats_lines.append(f"- 总条目数: {total_items}")
        stats_lines.append(f"- 热门条目（≥7分）: {hot_items}")
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
            reports["daily"] = self.generate_daily_report(items, orchestrator)
        except Exception as e:
            self.logger.error(f"生成每日报告失败: {e}")

        try:
            reports["json"] = self.generate_json_report(items)
        except Exception as e:
            self.logger.error(f"生成JSON报告失败: {e}")

        try:
            reports["summary"] = self.generate_summary_report(items, orchestrator)
        except Exception as e:
            self.logger.error(f"生成摘要报告失败: {e}")

        return reports