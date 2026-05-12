# AI每日简报生成器

一个智能的AI领域简报生成工具，每日生成AI热点和趋势分析报告。支持从真实数据源获取AI新闻，并生成专业的Markdown格式简报。专为Claude Code和OpenClaw优化。

## ✨ 核心特性

### 智能数据源集成
- **真实数据采集**: 从多个AI新闻网站的RSS源和API获取真实新闻
- **智能分类系统**: 基于关键词自动分类（内部处理，不在报告中显示）
- **内容过滤**: 自动过滤广告和低质量内容
- **多语言支持**: 支持中英文AI新闻内容
- **缓存机制**: 内置缓存系统，避免重复请求

### 真实数据模式
- **纯真实数据**: 仅使用真实新闻数据，不生成内容
- **透明标注**: 清晰标注新闻来源和原文链接
- **可配置策略**: 支持多数据源和过滤规则

### 多平台兼容
- **Claude Code**: 原生支持，可直接集成使用
- **OpenClaw**: 完全兼容，提供专用API接口
- **标准Python**: 可作为独立Python包使用

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 基本使用
```bash
# 生成今日AI简报（自动显示摘要并保存报告）
python daily_brief.py
```

### Claude Code集成
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

### OpenClaw集成
```python
from daily_brief import EnhancedAIBrief

brief = EnhancedAIBrief()
result = brief.generate_daily_brief()

if result["success"]:
    # 在OpenClaw中显示结果
    print(f"📊 AI简报生成成功:")
    print(f"📰 内容数量: {result.get('total_items', 0)} 条")
    print(f"💾 保存到: {result.get('filepath', '未知')}")
    
    # 显示摘要
    print(brief.get_summary(result))
```

## ⚙️ 配置说明

### 主配置文件 (config.yaml)
```yaml
# 简报生成选项
generation:
  num_items: 5                    # 简报条目数
  auto_save: true                 # 是否自动保存
  format: "markdown"              # 输出格式
  
  # 增强版数据源配置
  use_real_data: true             # 是否使用真实数据
  min_real_items: 3               # 最少真实数据项数
  fallback_enabled: true          # 是否启用备用生成

# AI相关主题（用于备用生成）
topics:
  - "大语言模型进展"
  - "AI工具更新"
  - "开源项目发布"
  - "AI研究突破"
  - "行业应用案例"
  - "AI安全与伦理"
  - "AI硬件发展"
  - "AI政策动态"

# 公司列表
companies:
  - "OpenAI"
  - "Anthropic"
  - "Google"
  - "Meta"
  - "Microsoft"
  - "阿里云"
  - "腾讯"
  - "百度"
  - "字节跳动"
  - "华为"

# AI模型列表
models:
  - "GPT-4"
  - "Claude 3"
  - "Gemini"
  - "Llama 3"
  - "Mistral"
  - "Qwen"
  - "DeepSeek"
  - "Yi"
  - "Baichuan"
  - "通义千问"
```

### 数据源配置 (data_sources.yaml)
```yaml
# 数据源配置
fetch_config:
  cache_dir: "./cache"
  cache_ttl_minutes: 120
  request_timeout: 10
  max_concurrent: 3
  user_agent: "AI-Daily-Brief/2.0 (Enhanced)"

# RSS数据源配置
rss_sources:
  - name: "IT之家 AI新闻"
    url: "https://www.ithome.com/rss/"
    language: "zh"
    category: "industry"
    enabled: true
    priority: 1
    
  - name: "Apple机器学习研究"
    url: "https://machinelearning.apple.com/rss/research.xml"
    language: "en"
    category: "research"
    enabled: true
    priority: 2
    
  - name: "OpenAI官方博客"
    url: "https://openai.com/blog/rss/"
    language: "en"
    category: "product"
    enabled: true
    priority: 1

  - name: "TechCrunch AI"
    url: "https://techcrunch.com/category/artificial-intelligence/feed/"
    language: "en"
    category: "industry"
    enabled: true
    priority: 2

  - name: "MIT Technology Review AI"
    url: "https://www.technologyreview.com/topic/artificial-intelligence/feed/"
    language: "en"
    category: "research"
    enabled: true
    priority: 2

# API数据源配置
api_sources:
  - name: "GitHub Releases"
    type: "github"
    url: "https://api.github.com/repos/{owner}/{repo}/releases"
    enabled: true
    priority: 3
    params:
      owner: "openai"
      repo: "openai-python"

# 分类映射配置
category_mapping:
  model_update:
    keywords: ["gpt", "claude", "模型", "model", "参数", "参数规模"]
  product_update:
    keywords: ["工具", "产品", "应用", "platform", "应用", "plugin", "integration"]
  research_breakthrough:
    keywords: ["研究", "论文", "academic", "research", "paper", "arxiv", "学术"]
  industry_dynamics:
    keywords: ["行业", "融资", "ipo", "估值", "竞争", "industry", "funding", "market"]
  tips_and_insights:
    keywords: ["技巧", "观点", "tutorial", "insight", "guide", "best practice"]
```

## 📊 输出示例

### 程序运行输出
```
🚀 AI每日简报生成器启动
==================================================
✅ 数据源管理器初始化成功
📊 正在生成今日AI简报...
✅ 成功获取 X 条真实新闻
💾 简报已保存到: ./reports/今日AI简报_2026-05-12.md
✅ AI每日简报生成成功！
==================================================
📈 简报统计:
  总条目数: 5 条
  新闻来源: 5 条
  保存位置: ./reports/今日AI简报_2026-05-12.md
🎉 AI每日简报生成完成！
```

### 完整报告示例
```markdown
# 2026-05-12 简报

## 📰 今日热点新闻

### 1. 🔗 OpenAI发布GPT-4.5新版本
OpenAI宣布推出GPT-4.5的最新版本，性能提升显著。

*来源: TechCrunch AI*  [阅读原文](https://techcrunch.com/...)

### 2. 🔗 Google AI在医疗影像诊断取得突破
Google研究人员在医疗影像AI诊断领域取得新进展。

*来源: MIT Technology Review*  [阅读原文](https://www.technologyreview.com/...)

### 3. 🔗 Anthropic开源金融AI全栈模板
Anthropic发布了金融AI全栈模板，定义行业落地新标准。

*来源: 真实新闻*  [阅读原文](https://anthropic.com/...)

---
*生成时间：2026-05-12 13:05:00*
*注：所有内容均来自真实新闻渠道，不包含任何生成内容*
```

## 📁 项目结构

```
daily-ai-brief-skill/
├── daily_brief.py           # 主程序入口（增强版）
├── data_source_manager.py   # 数据源管理器
├── config.yaml              # 主配置文件
├── data_sources.yaml        # 数据源配置文件
├── requirements.txt         # 依赖列表
├── README.md               # 本文件
├── SKILL.md                # 技能说明文件
│
├── test/                   # 测试目录
│   ├── test_data_sources.py        # 数据源测试
│   ├── test_channel_sources.py     # 渠道测试
│   ├── demo_enhanced_features.py   # 功能演示
│   └── run_all_tests.py           # 完整测试套件
│
├── reports/                # 生成的简报文件目录
│   └── 今日AI简报_*.md     # 每日生成的简报
└── cache/                 # 数据缓存目录
```

## 🔧 增强版功能说明

### 真实数据源集成
项目集成了多个AI新闻数据源，包括：
- **RSS数据源**: IT之家AI新闻、Apple机器学习研究、OpenAI官方博客、TechCrunch AI、MIT Technology Review AI
- **API数据源**: GitHub Releases API
- **网页爬虫**: 支持从AI新闻网站获取内容

### 智能内容处理
- **自动分类**: 基于关键词自动分类（内部处理，不在报告中显示）
- **去重处理**: 自动去除重复新闻
- **时间过滤**: 只保留48小时内的最新新闻
- **内容过滤**: 智能过滤广告和低质量内容

### 缓存与性能优化
- **缓存机制**: 数据缓存120分钟，减少重复请求
- **并行处理**: 多数据源并行获取，提高效率
- **错误恢复**: 自动重试机制和备用方案

## 🕐 定时任务

### 每日自动运行
```bash
# 每天上午9点自动生成简报
0 9 * * * cd /path/to/daily-ai-brief-skill && python daily_brief.py

# 每天下午6点更新简报
0 18 * * * cd /path/to/daily-ai-brief-skill && python daily_brief.py
```

### Claude Code定时任务
在Claude Code中设置定时任务，每天自动生成并推送AI简报。

## 🧪 测试验证

### 运行完整测试
```bash
# 运行所有测试
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

## 🔍 故障排除

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

4. **生成内容较少**
   - 检查数据源配置是否启用
   - 调整内容过滤规则
   - 增加备用生成内容数量

### 调试模式
```bash
# 查看数据源状态
python -c "from data_source_manager import DataSourceManager; m = DataSourceManager(); print(m.get_ai_news_summary(max_items=3))"
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交改进建议和功能扩展！

### 贡献指南
1. Fork项目仓库
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

### 功能建议
- 添加新的数据源
- 改进分类算法
- 优化内容过滤
- 增强平台集成

---

**版本**: 2.0 (增强版)  
**最后更新**: 2026-05-12  
**状态**: ✅ 生产就绪  
**兼容性**: Claude Code ✅ OpenClaw ✅