#!/usr/bin/env python3
"""
测试数据源管理器
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_source_manager import DataSourceManager

def test_data_source_initialization():
    """测试数据源管理器初始化"""
    print("🧪 测试数据源管理器初始化...")
    try:
        manager = DataSourceManager()
        print("✅ 数据源管理器初始化成功")
        
        # 测试配置加载
        config = manager.config
        if config:
            print(f"✅ 配置加载成功，包含 {len(config.get('rss_sources', []))} 个RSS源")
        else:
            print("⚠️ 配置加载为空")
        
        return True
    except Exception as e:
        print(f"❌ 数据源管理器初始化失败: {e}")
        return False

def test_rss_sources():
    """测试RSS源获取"""
    print("\n🧪 测试RSS源获取...")
    try:
        manager = DataSourceManager()
        
        rss_sources = manager.config.get("rss_sources", [])
        enabled_sources = [s for s in rss_sources if s.get("enabled", False)]
        
        print(f"📊 共有 {len(rss_sources)} 个RSS源，其中 {len(enabled_sources)} 个已启用")
        
        # 测试第一个启用的RSS源
        for source in enabled_sources[:1]:  # 只测试第一个，避免过多网络请求
            name = source.get("name", "未知源")
            print(f"🔍 测试RSS源: {name}")
            
            items = manager.fetch_rss_source(source)
            print(f"  采集到 {len(items)} 条数据")
            
            if items:
                print(f"  第一条数据: {items[0].get('title', '无标题')[:50]}...")
                return True
            else:
                print(f"  ⚠️ 未采集到数据")
        
        return len(enabled_sources) > 0
    except Exception as e:
        print(f"❌ RSS源测试失败: {e}")
        return False

def test_ai_news_summary():
    """测试AI新闻摘要获取"""
    print("\n🧪 测试AI新闻摘要获取...")
    try:
        manager = DataSourceManager()
        summary = manager.get_ai_news_summary()
        
        if summary.get("success", False):
            items = summary.get("items", [])
            total = summary.get("total", 0)
            categories = summary.get("categories", {})
            
            print(f"✅ 成功获取新闻摘要")
            print(f"  总条目数: {total}")
            print(f"  分类统计: {categories}")
            
            # 显示前3条新闻
            for i, item in enumerate(items[:3], 1):
                print(f"  {i}. {item.get('title', '无标题')[:60]}...")
            
            return total > 0
        else:
            print(f"❌ 获取新闻摘要失败: {summary.get('error', '未知错误')}")
            return False
    except Exception as e:
        print(f"❌ AI新闻摘要测试失败: {e}")
        return False

def test_cache_disabled():
    """测试缓存是否已禁用"""
    print("\n🧪 测试缓存是否已禁用...")
    try:
        manager = DataSourceManager()
        cache_enabled = manager.config.get("fetch_config", {}).get("cache_enabled", True)
        
        if not cache_enabled:
            print("✅ 缓存已禁用，确保每次取最新数据")
            return True
        else:
            print("❌ 缓存未禁用")
            return False
    except Exception as e:
        print(f"❌ 缓存测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运行数据源管理器测试")
    print("=" * 50)
    
    test_results = []
    
    # 运行测试
    test_results.append(("数据源初始化", test_data_source_initialization()))
    test_results.append(("缓存禁用测试", test_cache_disabled()))
    test_results.append(("RSS源测试", test_rss_sources()))
    test_results.append(("AI新闻摘要测试", test_ai_news_summary()))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = 0
    total = 0
    
    for test_name, result in test_results:
        total += 1
        if result:
            passed += 1
            print(f"  ✅ {test_name}: 通过")
        else:
            print(f"  ❌ {test_name}: 失败")
    
    print(f"\n🎯 通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)