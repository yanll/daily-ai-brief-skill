#!/usr/bin/env python3
"""
增强版AI每日简报生成器
集成真实数据源，从RSS和API获取AI新闻
优化版：默认生成日报，无启动参数
"""

import os
import sys
import json
import yaml
from datetime import datetime
from typing import Dict, Any, Optional, List
import random

# 导入数据源管理器
try:
    from data_source_manager import DataSourceManager
    DATA_SOURCE_AVAILABLE = True
except ImportError:
    print("⚠️ 数据源管理器不可用，将使用随机生成内容")
    DATA_SOURCE_AVAILABLE = False

class EnhancedAIBrief:
    """增强版AI日报生成器（集成真实数据源）"""
    
    def __init__(self, config_path: Optional[str] = None, data_source_config: Optional[str] = None):
        """初始化"""
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.reports_dir = os.path.join(self.base_dir, "reports")
        
        # 创建必要目录
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # 加载简报配置
        self.config = self.load_config(config_path)
        
        # 初始化数据源管理器
        self.data_source_manager = None
        if DATA_SOURCE_AVAILABLE:
            try:
                self.data_source_manager = DataSourceManager(data_source_config)
                print("✅ 数据源管理器初始化成功")
            except Exception as e:
                print(f"⚠️ 数据源管理器初始化失败: {e}")
                self.data_source_manager = None
        
        # 从配置中获取备用数据
        self.ai_topics = self.config.get("topics", [
            "大语言模型进展",
            "AI工具更新", 
            "开源项目发布",
            "AI研究突破",
            "行业应用案例",
            "AI安全与伦理",
            "AI硬件发展",
            "AI政策动态"
        ])
        
        self.ai_models = self.config.get("models", [
            "GPT-4", "Claude 3", "Gemini", "Llama 3", "Mistral",
            "Qwen", "DeepSeek", "Yi", "Baichuan", "通义千问"
        ])
        
        self.companies = self.config.get("companies", [
            "OpenAI", "Anthropic", "Google", "Meta", "Microsoft",
            "阿里云", "腾讯", "百度", "字节跳动", "华为"
        ])
        
        self.generation_config = self.config.get("generation", {
            "num_items": 5,
            "auto_save": True,
            "format": "markdown",
            "use_real_data": True,  # 新增：是否使用真实数据
            "min_real_items": 3,    # 新增：最少真实数据项数
            "fallback_enabled": True  # 新增：是否启用备用生成
        })
    
    def load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        if config_path is None:
            config_path = os.path.join(self.base_dir, "config.yaml")
        
        if not os.path.exists(config_path):
            # 返回默认配置
            return {}
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ 配置文件加载失败: {e}")
            return {}
    
    def get_real_ai_news(self) -> Dict[str, Any]:
        """从真实数据源获取AI新闻"""
        if not self.data_source_manager:
            return {
                "success": False,
                "error": "数据源管理器不可用",
                "items": [],
                "total": 0
            }
        
        try:
            # 获取真实AI新闻
            news_summary = self.data_source_manager.get_ai_news_summary(
                max_items=self.generation_config.get("min_real_items", 3) * 2
            )
            
            if news_summary.get("success", False):
                news_items = news_summary.get("items", [])
                # 确保news_items是列表
                if not isinstance(news_items, list):
                    news_items = []
                
                return {
                    "success": True,
                    "items": news_items,
                    "total": len(news_items)
                }
            else:
                return {
                    "success": False,
                    "error": news_summary.get("error", "获取真实数据失败"),
                    "items": [],
                    "total": 0
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "items": [],
                "total": 0
            }
    
    def generate_ai_content(self, num_items: int) -> List[Dict[str, Any]]:
        """生成AI相关内容"""
        items = []
        
        for i in range(num_items):
            # 随机选择主题和模型
            topic = random.choice(self.ai_topics)
            model = random.choice(self.ai_models)
            company = random.choice(self.companies)
            
            # 生成内容模板
            content_templates = [
                f"{company}在{topic}领域取得新突破。",
                f"研究人员在{topic}领域取得新进展。",
                f"{company}发布{model}新版本，性能提升显著。",
                f"{topic}领域的新研究引起广泛关注。",
                f"{company}宣布推出{topic}相关的新工具。"
            ]
            
            content = random.choice(content_templates)
            
            items.append({
                "title": f"{topic}：{model}相关进展",
                "content": content,
                "source": "生成内容",
                "category": self.categorize_content(topic),
                "is_generated": True,
                "link": None
            })
        
        return items
    
    def categorize_content(self, content: str) -> str:
        """根据内容分类"""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ["模型", "gpt", "claude", "参数", "llm"]):
            return "模型发布/更新"
        elif any(keyword in content_lower for keyword in ["工具", "产品", "应用", "平台", "开源"]):
            return "产品发布/更新"
        elif any(keyword in content_lower for keyword in ["研究", "论文", "学术", "突破", "框架"]):
            return "论文研究"
        elif any(keyword in content_lower for keyword in ["行业", "融资", "ipo", "估值", "市场"]):
            return "行业动态"
        elif any(keyword in content_lower for keyword in ["安全", "伦理", "合规", "监管"]):
            return "安全伦理"
        elif any(keyword in content_lower for keyword in ["硬件", "芯片", "算力", "基础设施"]):
            return "硬件发展"
        elif any(keyword in content_lower for keyword in ["政策", "法规", "标准", "指南"]):
            return "政策动态"
        else:
            return "其他"
    
    def generate_daily_brief(self) -> Dict[str, Any]:
        """生成每日AI简报"""
        print("📊 开始生成AI每日简报...")
        
        target_items = self.generation_config.get("num_items", 5)
        use_real_data = self.generation_config.get("use_real_data", True)
        min_real_items = self.generation_config.get("min_real_items", 3)
        fallback_enabled = self.generation_config.get("fallback_enabled", True)
        
        all_items = []
        real_items_count = 0
        generated_items_count = 0
        
        # 获取真实数据
        if use_real_data and DATA_SOURCE_AVAILABLE:
            print("🔍 获取真实AI新闻数据...")
            real_news_result = self.get_real_ai_news()
            
            if real_news_result["success"]:
                real_items = real_news_result["items"]
                real_items_count = len(real_items)
                all_items.extend(real_items)
                print(f"✅ 成功获取 {real_items_count} 条真实新闻")
            else:
                print(f"⚠️ 获取真实数据失败: {real_news_result.get('error', '未知错误')}")
        
        # 检查是否需要生成补充内容
        if real_items_count < min_real_items and fallback_enabled:
            needed_items = target_items - real_items_count
            if needed_items > 0:
                print(f"⚠️ 真实数据不足 ({real_items_count}/{min_real_items})，生成 {needed_items} 条补充内容")
                generated_items = self.generate_ai_content(needed_items)
                generated_items_count = len(generated_items)
                all_items.extend(generated_items)
        
        # 如果还是没有足够内容，生成全部内容
        if len(all_items) < target_items:
            needed_items = target_items - len(all_items)
            print(f"📝 生成 {needed_items} 条额外内容")
            generated_items = self.generate_ai_content(needed_items)
            generated_items_count += len(generated_items)
            all_items.extend(generated_items)
        
        # 限制总条目数
        all_items = all_items[:target_items]
        
        # 分类统计
        categories = {}
        for item in all_items:
            category = item.get("category", "其他")
            categories[category] = categories.get(category, 0) + 1
        
        # 生成报告
        report = self.generate_report(all_items, categories, real_items_count, generated_items_count)
        
        # 保存报告
        filepath = None
        if self.generation_config.get("auto_save", True):
            filepath = self.save_report(report)
        
        return {
            "success": True,
            "total_items": len(all_items),
            "real_items": real_items_count,
            "generated_items": generated_items_count,
            "categories": categories,
            "report": report,
            "filepath": filepath,
            "used_real_data": real_items_count > 0
        }
    
    def generate_report(self, items: List[Dict[str, Any]], categories: Dict[str, int], 
                       real_items: int, generated_items: int) -> str:
        """生成简报报告"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        report_lines = [
            f"# {today} AI每日简报",
            "",
            "## 📊 简报摘要",
            "",
            f"- **总条目数**: {len(items)} 条",
            f"- **真实新闻**: {real_items} 条",
            f"- **生成内容**: {generated_items} 条",
            f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 🏷️ 内容分类",
            ""
        ]
        
        # 添加分类
        for category, count in categories.items():
            report_lines.append(f"- **{category}**: {count} 条")
        
        report_lines.extend([
            "",
            "## 📰 今日AI热点",
            ""
        ])
        
        # 添加新闻条目
        for i, item in enumerate(items, 1):
            source_marker = "🔗" if item.get("link") else "📄"
            source_text = f"*来源: {item.get('source', '未知来源')}*"
            if item.get("link"):
                source_text += f"  [阅读原文]({item['link']})"
            
            # 获取内容，如果不存在则使用标题
            content = item.get('content', item.get('title', '无内容'))
            
            report_lines.extend([
                f"### {i}. {source_marker} {item.get('title', '未命名条目')}",
                content,
                "",
                source_text,
                ""
            ])
        
        # 添加趋势分析
        report_lines.extend([
            "## 📈 趋势分析",
            "",
            "1. **真实新闻覆盖全面**：今日简报包含多个来源的真实AI新闻",
            "2. **行业动态活跃**：AI技术在各行业应用持续扩展",
            "3. **技术迭代加速**：大模型和AI工具更新频繁",
            "4. **安全关注提升**：AI伦理和安全讨论日益重要",
            "",
            "## 💡 建议关注",
            "",
            "- 关注主流AI模型的更新动态",
            "- 探索开源AI工具的实际应用",
            "- 注意AI应用的合规与安全",
            "- 关注AI硬件和技术基础设施发展",
            "",
            "## 🔗 数据来源",
            ""
        ])
        
        # 添加数据来源
        sources = set()
        for item in items:
            if not item.get("is_generated", False):
                sources.add(item.get("source", "未知来源"))
        
        if sources:
            for source in sources:
                report_lines.append(f"- {source}")
        else:
            report_lines.append("- 今日简报使用生成内容")
        
        report_lines.extend([
            "",
            "---",
            f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "*注：部分内容为生成示例，实际内容以真实新闻为准*"
        ])
        
        return "\n".join(report_lines)
    
    def save_report(self, report: str) -> str:
        """保存报告到文件"""
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"今日AI简报_{today}.md"
        filepath = os.path.join(self.reports_dir, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"💾 简报已保存到: {filepath}")
            return filepath
        except Exception as e:
            print(f"⚠️ 保存报告失败: {e}")
            return ""
    
    def get_summary(self, result: Optional[Dict[str, Any]] = None) -> str:
        """获取简报摘要"""
        # 如果没有提供result，则生成简报
        if result is None:
            result = self.generate_daily_brief()
        
        if result.get("success", False):
            summary_lines = [
                "📰 AI每日简报（增强版）",
                "",
                f"**数据来源**: {'✅ 真实数据 + 生成内容' if result.get('real_items', 0) > 0 else '⚠️ 生成内容'}",
                f"**状态**: ✅ 已生成",
                f"**内容数量**: {result.get('total_items', 0)} 条",
                f"**真实新闻**: {result.get('real_items', 0)} 条",
                f"**生成内容**: {result.get('generated_items', 0)} 条",
            ]
            
            if result.get("filepath"):
                summary_lines.append(f"**保存位置**: {result['filepath']}")
            
            summary_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return "\n".join(summary_lines)
        else:
            return f"❌ AI简报生成失败\n原因: {result.get('error', '未知错误')}"
    
    def show_report(self):
        """显示完整报告"""
        result = self.generate_daily_brief()
        
        if not result.get("success", False):
            print(f"❌ AI简报生成失败\n原因: {result.get('error', '未知错误')}")
            return
        
        print(result.get("report", "报告内容不可用"))

def main():
    """主函数 - 优化版：默认生成日报"""
    print("🚀 AI每日简报生成器启动")
    print("=" * 50)
    
    # 创建简报实例
    brief = EnhancedAIBrief()
    
    # 默认生成简报
    print("📊 正在生成今日AI简报...")
    result = brief.generate_daily_brief()
    
    if result.get("success", False):
        print("\n✅ AI每日简报生成成功！")
        print("=" * 50)
        
        # 显示摘要信息
        print(f"📈 简报统计:")
        print(f"  总条目数: {result.get('total_items', 0)} 条")
        print(f"  真实新闻: {result.get('real_items', 0)} 条")
        print(f"  生成内容: {result.get('generated_items', 0)} 条")
        
        # 显示分类信息
        categories = result.get("categories", {})
        if categories:
            print(f"\n🏷️ 内容分类:")
            for category, count in categories.items():
                print(f"  - {category}: {count} 条")
        
        # 显示文件路径
        filepath = result.get("filepath", "")
        if filepath:
            print(f"\n💾 保存位置: {filepath}")
        
        # 显示简报摘要
        print("\n📰 简报摘要:")
        # 直接从result生成摘要，避免重复生成简报
        summary_lines = [
            "📰 AI每日简报（增强版）",
            "",
            f"**数据来源**: {'✅ 真实数据 + 生成内容' if result['real_items'] > 0 else '⚠️ 生成内容'}",
            f"**状态**: ✅ 已生成",
            f"**内容数量**: {result['total_items']} 条",
            f"**真实新闻**: {result['real_items']} 条",
            f"**生成内容**: {result['generated_items']} 条",
        ]
        
        if result.get("filepath"):
            summary_lines.append(f"**保存位置**: {result['filepath']}")
        
        summary_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n".join(summary_lines))
        
        print("\n" + "=" * 50)
        print("🎉 AI每日简报生成完成！")
    else:
        print(f"\n❌ 简报生成失败: {result.get('error', '未知错误')}")

if __name__ == "__main__":
    main()