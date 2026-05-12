# AI每日简报技能

## 概述
一个智能的AI领域简报生成技能，专为Claude Code和OpenClaw优化。每日生成AI热点和趋势分析报告，支持从真实数据源获取AI新闻，并生成专业的Markdown格式简报。

## 核心功能

### 真实数据源集成
- **RSS数据源**: 从多个AI新闻网站获取真实新闻
- **API数据源**: 支持GitHub Releases等API
- **智能分类**: 基于关键词自动分类（内部处理，不在报告中显示）
- **内容过滤**: 自动过滤广告和低质量内容

### 真实数据模式
- **纯真实数据**: 仅使用真实新闻数据，不生成内容
- **透明标注**: 清晰标注新闻来源和原文链接
- **可配置策略**: 支持多数据源和过滤规则

### 平台优化
- **Claude Code原生支持**: 无缝集成到Claude Code工作流
- **OpenClaw兼容**: 提供专用API接口和输出格式
- **标准Python包**: 可作为独立Python模块使用

## 使用方法

### 基本使用
```bash
# 生成AI每日简报（自动显示摘要并保存报告）
python daily_brief.py
```

### Python API
```python
from daily_brief import EnhancedAIBrief

# 创建实例
brief = EnhancedAIBrief()

# 生成简报
result = brief.generate_daily_brief()

# 获取摘要
print(brief.get_summary(result))

# 获取完整报告
if result["success"]:
    print(brief.get_formatted_report(result))
```

### Claude Code集成示例
```python
# 在Claude Code中直接调用
from daily_brief import EnhancedAIBrief

brief = EnhancedAIBrief()
result = brief.generate_daily_brief()

if result["success"]:
    print("🎯 AI每日简报生成成功！")
    print(f"📊 统计信息:")
    print(f"  总条目数: {result.get('total_items', 0)} 条")
    print(f"  新闻来源: {result.get('real_items', 0)} 条")
    print(f"  保存位置: {result.get('filepath', '未知')}")
    
    # 显示简报摘要
    print(brief.get_summary(result))
```

### OpenClaw集成示例
```python
# 在OpenClaw中集成
from daily_brief import EnhancedAIBrief
import datetime

def generate_ai_daily_brief():
    """生成AI每日简报"""
    brief = EnhancedAIBrief()
    result = brief.generate_daily_brief()
    
    if result["success"]:
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "summary": "📰 AI每日简报生成成功",
                "total_items": result.get('total_items', 0),
                "real_items": result.get('real_items', 0),
                "generated_items": result.get('generated_items', 0),
                "categories": result.get("categories", {}),
                "filepath": result.get('filepath', '未知'),
                "report_preview": brief.get_summary(result)[:200] + "..." if len(brief.get_summary(result)) > 200 else brief.get_summary(result)
            }
        }
    else:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "message": result.get("error", "未知错误"),
            "details": str(result)
        }

# 调用函数
brief_result = generate_ai_daily_brief()
if brief_result["status"] == "success":
    print("✅ AI简报生成成功")
    print(brief_result["data"]["summary"])
```

## 技术特性

### 数据源架构设计
- **模块化设计**: 可扩展的数据源管理器架构
- **多源支持**: RSS、API、网页爬虫等多种数据源类型
- **缓存机制**: 内置智能缓存系统，减少重复请求
- **错误处理**: 完善的错误处理和重试机制

### 智能内容处理系统
- **自动分类系统**: 基于关键词的智能分类（内部处理，不在报告中显示）
  - 模型发布/更新: GPT、Claude、模型、参数等关键词
  - 产品发布/更新: 工具、平台、开源、版本等关键词
  - 行业动态: IPO、估值、融资、竞争等关键词
  - 论文研究: 研究、论文、学术、框架等关键词
  - 技巧与观点: 技巧、观点、教程、交互等关键词

- **内容过滤系统**:
  - 广告内容自动识别和过滤
  - 低质量内容筛选
  - 可配置的过滤规则

### 性能优化
- **缓存管理**: 数据缓存120分钟，减少网络请求
- **并行处理**: 多数据源并行获取，提高效率
- **错误恢复**: 自动重试机制和备用方案

## 项目结构

```
daily-ai-brief-skill/
├── daily_brief.py           # 主程序（增强版）
├── data_source_manager.py   # 数据源管理器
├── config.yaml              # 主配置文件
├── data_sources.yaml        # 数据源配置文件
├── requirements.txt         # 依赖列表
├── SKILL.md                # 本文件
├── README.md               # 详细文档
│
├── test/                   # 测试目录
│   ├── test_data_sources.py        # 数据源测试
│   ├── test_channel_sources.py     # 渠道测试
│   ├── demo_enhanced_features.py   # 功能演示
│   └── run_all_tests.py           # 完整测试套件
│
├── reports/                # 生成的简报文件
└── cache/                 # 数据缓存目录
```

## 配置说明

### 快速配置示例
在Claude Code或OpenClaw中快速使用：

```python
# 最小化配置示例
from daily_brief import EnhancedAIBrief

# 使用默认配置
brief = EnhancedAIBrief()

# 或使用自定义配置
brief = EnhancedAIBrief(
    config_path="my_config.yaml",
    data_source_config="my_data_sources.yaml"
)

# 生成简报
result = brief.generate_daily_brief()
```

### 配置参数
- **num_items**: 简报条目数（默认：5）
- **use_real_data**: 是否使用真实数据（默认：true）
- **min_real_items**: 最少真实数据项数（默认：3）
- **fallback_enabled**: 是否启用备用生成（默认：true）

## 输出格式

### Claude Code友好格式
```
🎯 AI每日简报生成成功！
📊 统计信息:
  总条目数: 8 条
  新闻来源: 8 条
  保存位置: ./reports/今日AI简报_2026-05-12.md

📰 今日热点新闻:
1. 🤖 OpenAI发布GPT-4.5新版本
2. 🔬 Google AI在医疗影像诊断取得突破
3. 🛠️ Anthropic开源金融AI全栈模板
```

### OpenClaw友好格式
```json
{
  "status": "success",
  "timestamp": "2026-05-12 14:30:00",
  "data": {
    "total_items": 8,
    "real_items": 8,
    "filepath": "./reports/今日AI简报_2026-05-12.md",
    "summary": "📰 AI每日简报生成成功"
  }
}
```

## 定时任务集成

### Claude Code定时任务
```bash
# 每天上午9点自动生成简报
0 9 * * * cd /path/to/daily-ai-brief-skill && python daily_brief.py

# 每天下午6点更新简报
0 18 * * * cd /path/to/daily-ai-brief-skill && python daily_brief.py
```

### OpenClaw定时任务
在OpenClaw中设置定时任务调用简报生成API。

## 测试验证

### 运行测试
```bash
# 运行完整测试套件
python test/run_all_tests.py

# 运行单元测试
python test/test_data_sources.py

# 运行功能演示
python test/demo_enhanced_features.py
```

### 测试覆盖率
- ✅ 数据源管理测试
- ✅ 分类系统测试
- ✅ 内容过滤测试
- ✅ 集成功能测试
- ✅ 平台兼容测试

## 故障排除

### 常见问题
1. **依赖安装失败**
   ```bash
   pip install --upgrade pip
   pip install PyYAML feedparser requests beautifulsoup4 lxml
   ```

2. **数据源获取失败**
   ```bash
   # 检查网络连接
   curl https://www.ithome.com/rss/
   ```

3. **配置文件错误**
   - 检查YAML格式是否正确
   - 确保文件编码为UTF-8
   - 验证配置文件路径

### 调试模式
```bash
# 查看数据源状态
python -c "from data_source_manager import DataSourceManager; m = DataSourceManager(); print(m.get_ai_news_summary(max_items=3))"
```

## 扩展开发

### 添加新的数据源
1. 在 `data_sources.yaml` 中添加新的数据源配置
2. 测试数据获取功能
3. 更新分类关键词映射

### 自定义分类规则
编辑 `data_sources.yaml` 中的 `category_mapping` 部分，添加自定义关键词映射。

### 集成到其他系统
```python
# 示例：将AI简报集成到工作流系统
def integrate_ai_brief_to_workflow():
    from daily_brief import EnhancedAIBrief
    
    brief = EnhancedAIBrief()
    result = brief.generate_daily_brief()
    
    if result["success"]:
        # 发送到工作流系统
        send_to_workflow_system({
            "type": "ai_daily_brief",
            "content": result,
            "timestamp": datetime.now().isoformat()
        })
        return True
    return False
```

## 许可证
MIT License

## 技术支持
- 问题反馈：检查日志文件
- 功能建议：编辑配置文件
- 定制开发：扩展数据源管理器

---

**技能名称**: AI每日简报  
**版本**: 2.0 (增强版)  
**最后更新**: 2026-05-12  
**状态**: ✅ 生产就绪  
**兼容性**: Claude Code ✅ OpenClaw ✅  
**推荐用途**: 每日AI趋势跟踪、团队技术分享、个人学习参考