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


# 导入数据源管理器
try:
    from data_source_manager import DataSourceManager
    DATA_SOURCE_AVAILABLE = True
except ImportError:
    print("⚠️ 数据源管理器不可用，将使用随机生成内容")
    DATA_SOURCE_AVAILABLE = False

class EnhancedAIBrief:
    """增强版AI日报生成器（集成真实数据源）"""
    
    def __init__(self):
        """初始化"""
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.reports_dir = os.path.join(self.base_dir, "reports")
        
        # 创建必要目录
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # 初始化数据源管理器
        self.data_source_manager = None
        if DATA_SOURCE_AVAILABLE:
            try:
                self.data_source_manager = DataSourceManager()
                print("✅ 数据源管理器初始化成功")
            except Exception as e:
                print(f"⚠️ 数据源管理器初始化失败: {e}")
                self.data_source_manager = None
        
        # 设置默认配置
        self.generation_config = {
            "auto_save": True,  # 默认保存
            "format": "markdown",  # 默认格式
            "data_source_config": "data_sources.yaml"  # 默认数据源配置
        }
    

    
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
            news_summary = self.data_source_manager.get_ai_news_summary()
            
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
    

    
    def categorize_content(self, content: str) -> str:
        """根据内容分类（改进版）"""
        content_lower = content.lower()
        
        # 优先级顺序很重要，先检查更具体的分类
        
        # 1. 硬件相关（包含芯片关键词）
        if any(keyword in content_lower for keyword in ["芯片", "gpu", "tpu", "处理器", "英伟达", "nvidia", "英特尔", "intel"]):
            return "硬件发展"
        
        # 2. 模型相关（特定模型名称和参数）
        if any(keyword in content_lower for keyword in ["gpt-", "gpt4", "gpt-4", "gpt5", "gpt-5", "llama", "gemini", "claude 3", "claude-3", "参数", "token", "上下文"]):
            return "模型发布/更新"
        
        # 3. 产品/工具相关（包含具体产品类型）
        if any(keyword in content_lower for keyword in ["工具", "编辑器", "ide", "平台", "应用", "软件", "系统", "界面", "开源"]):
            return "产品发布/更新"
        
        # 4. 研究/论文相关
        if any(keyword in content_lower for keyword in ["论文", "顶会", "acm", "期刊", "实验室", "研究院", "学术"]):
            return "论文研究"
        
        # 5. 行业/商业相关
        if any(keyword in content_lower for keyword in ["融资", "ipo", "估值", "投资", "市值", "营收", "利润", "市场", "竞争"]):
            return "行业动态"
        
        # 6. 安全/合规相关
        if any(keyword in content_lower for keyword in ["安全", "漏洞", "攻击", "防御", "合规", "监管", "法律", "隐私"]):
            return "安全伦理"
        
        # 7. 政策/法规相关
        if any(keyword in content_lower for keyword in ["政策", "法规", "标准", "指南", "白皮书", "立法"]):
            return "政策动态"
        
        # 8. 通用模型相关（放在后面，避免误判）
        if any(keyword in content_lower for keyword in ["模型", "gpt", "claude", "llm", "大模型"]):
            return "模型发布/更新"
        
        # 9. 通用产品相关
        if any(keyword in content_lower for keyword in ["产品", "发布", "推出", "上线", "更新", "版本"]):
            return "产品发布/更新"
        
        # 10. 通用研究相关
        if any(keyword in content_lower for keyword in ["研究", "突破", "创新", "发现", "实验"]):
            return "论文研究"
        
        # 11. 通用行业相关
        if any(keyword in content_lower for keyword in ["行业", "产业", "生态", "合作伙伴", "合作"]):
            return "行业动态"
        
        return "其他"
    
    def generate_daily_brief(self) -> Dict[str, Any]:
        """生成每日AI简报（只使用真实数据源）"""
        print("📊 开始生成AI每日简报...")
        
        all_items = []
        real_items_count = 0
        
        # 获取真实数据
        if DATA_SOURCE_AVAILABLE:
            print("🔍 获取真实AI新闻数据...")
            real_news_result = self.get_real_ai_news()
            
            if real_news_result["success"]:
                real_items = real_news_result["items"]
                real_items_count = len(real_items)
                all_items.extend(real_items)
                print(f"✅ 成功获取 {real_items_count} 条真实新闻")
            else:
                print(f"⚠️ 获取真实数据失败: {real_news_result.get('error', '未知错误')}")
        
        # 生成报告
        report = self.generate_report(all_items, {}, real_items_count)
        
        # 保存报告
        filepath = None
        if self.generation_config.get("auto_save", True):
            filepath = self.save_report(report)
        
        return {
            "success": True,
            "total_items": len(all_items),
            "real_items": real_items_count,
            "report": report,
            "filepath": filepath
        }
    
    def generate_report(self, items: List[Dict[str, Any]], _categories: Dict[str, int],
                       _real_items: int) -> str:
        """生成简报报告（简化版：移除摘要、分类、数据来源）"""
        today = datetime.now().strftime("%Y-%m-%d")

        report_lines = [
            f"# {today} 简报",
            "",
            "## 📰 热点信息摘要",
            ""
        ]

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

        report_lines.extend([
            "",
            "---",
            f"*数据采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])

        return "\n".join(report_lines)
    
    def save_report(self, report: str) -> str:
        """保存报告到文件"""
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"简报_{today}.md"
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
                "📰 AI每日简报（真实数据版）",
                "",
                f"**数据来源**: 真实新闻渠道",
                f"**状态**: ✅ 已生成",
                f"**内容数量**: {result.get('total_items', 0)} 条",
                f"**新闻来源**: {result.get('real_items', 0)} 条",
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
        print(f"  新闻来源: {result.get('real_items', 0)} 条")
        
        
        # 显示文件路径
        filepath = result.get("filepath", "")
        if filepath:
            print(f"\n💾 保存位置: {filepath}")
        
        # 显示简报摘要
        print("\n📰 简报摘要:")
        # 直接从result生成摘要，避免重复生成简报
        summary_lines = [
            "📰 AI每日简报（真实数据版）",
            "",
            f"**数据来源**: 真实新闻渠道",
            f"**状态**: ✅ 已生成",
            f"**内容数量**: {result['total_items']} 条",
            f"**新闻来源**: {result['real_items']} 条",
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