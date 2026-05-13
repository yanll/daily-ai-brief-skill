## 项目介绍

AI Daily News Aggregator Skill for OpenClaw, Claude Code & Hermes Agent

## 项目结构框架

```
daily-ai-brief-skill/
├── src/                    # 源码目录
│   ├── test                # 测试脚本目录（生成的测试脚本必须放在此目录）
│   ├── datasources         # 信息数据源（各个信息渠道的采集模模块代码文件）
│   ├── main.py             # 运行入口
├── requirements.txt        # 依赖列表
├── SKILL.md                # 技能描述
├── README.md               # 项目描述
└── reports                 # 报告文件存放目录（生成的日报结果必须放在此目录）
```

## 任务步骤

### Step1:

- 理解项目结构和目标
- 设计信息抓取抽象方法和框架，包含配置读取、数据抓取、内容解析、结果组装等抽象方案

### Step2:

- 读取[data_sources.yaml](src/data_sources.yaml)，根据不同的信息渠道，生成不同的抓取模块，单独存放文件
- 不同抓取模块根据采集方式不同，例如RSS、API、网页等有不同的解析方案
- 生成数据采集代码，使用多线程并发执行各个采集模块
- 需要支持网页、RSS、API等多种方式，可以使用Playwright、Requests、Selenium、Fake-useragent等依赖，不限制三方组件的使用，结果是第一要务
- 最终将main.py作为项目运行入口触发工具执行

### Step3:

生成MD文件，用于支持此项目作为标准的Skill发布到ClawHub

## 工作铁律

- 每个渠道必须写测试脚本验证结果，若验证失败仔细检查并修复
- 