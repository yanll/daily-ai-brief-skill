#!/usr/bin/env python3
"""
验证项目完整性
"""
import sys
import os
import importlib

def test_imports():
    """测试所有模块导入"""
    modules = [
        'modules.config',
        'modules.base_fetcher',
        'modules.rss_fetcher',
        'modules.reddit_fetcher',
        'modules.x_fetcher',
        'modules.web_scraper',
        'modules.api_fetcher',
        'modules.fetcher_factory',
        'modules.orchestrator',
        'modules.hotness_evaluator',
        'modules.report_generator',
    ]

    print("测试模块导入...")
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except Exception as e:
            print(f"❌ {module}: {e}")
            return False
    return True

def test_config():
    """测试配置加载"""
    print("\n测试配置加载...")
    try:
        from modules.config import ConfigLoader
        loader = ConfigLoader()
        config = loader.load()
        print(f"✅ 配置加载成功")
        print(f"   RSS源数量: {len(config.get('rss_sources', []))}")
        print(f"   Reddit源数量: {len(config.get('reddit_sources', []))}")
        print(f"   X/Twitter源数量: {len(config.get('x_sources', []))}")
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

def test_factory():
    """测试工厂创建"""
    print("\n测试抓取器工厂...")
    try:
        from modules.config import ConfigLoader
        from modules.fetcher_factory import FetcherFactory

        loader = ConfigLoader()
        config = loader.load()
        factory = FetcherFactory()
        fetchers = factory.create_fetchers_from_config(config)

        print(f"✅ 创建了 {len(fetchers)} 个抓取器")

        # 统计类型
        type_count = {}
        for fetcher in fetchers:
            cls_name = fetcher.__class__.__name__
            type_count[cls_name] = type_count.get(cls_name, 0) + 1

        for cls_name, count in type_count.items():
            print(f"   {cls_name}: {count}")

        return True
    except Exception as e:
        print(f"❌ 工厂测试失败: {e}")
        return False

def main():
    """主验证函数"""
    print("=" * 60)
    print("AI Daily Brief Skill - 项目完整性验证")
    print("=" * 60)

    all_passed = True

    # 添加src目录到路径
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

    # 运行测试
    all_passed &= test_imports()
    all_passed &= test_config()
    all_passed &= test_factory()

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有验证通过！项目结构完整。")
    else:
        print("❌ 验证失败！请检查上述错误。")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())