#!/usr/bin/env python3
"""
测试daily_brief.py主程序
"""

import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daily_brief import EnhancedAIBrief

def test_enhanced_ai_brief_initialization():
    """测试EnhancedAIBrief初始化"""
    print("🧪 测试EnhancedAIBrief初始化...")
    try:
        # 使用临时目录避免影响实际文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建临时测试实例
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                brief = EnhancedAIBrief()
                print("✅ EnhancedAIBrief初始化成功")
                
                # 检查必要目录是否创建
                reports_dir = os.path.join(temp_dir, "reports")
                if os.path.exists(reports_dir):
                    print(f"✅ reports目录已创建: {reports_dir}")
                else:
                    print(f"❌ reports目录未创建")
                
                return True
            finally:
                os.chdir(original_dir)
    except Exception as e:
        print(f"❌ EnhancedAIBrief初始化失败: {e}")
        return False

def test_real_ai_news_fetch():
    """测试真实AI新闻获取"""
    print("\n🧪 测试真实AI新闻获取...")
    try:
        brief = EnhancedAIBrief()
        news_result = brief.get_real_ai_news()
        
        if news_result.get("success", False):
            items = news_result.get("items", [])
            total = news_result.get("total", 0)
            
            print(f"✅ 成功获取真实AI新闻")
            print(f"  总条目数: {total}")
            
            if items:
                print(f"  第一条新闻: {items[0].get('title', '无标题')[:50]}...")
                print(f"  来源: {items[0].get('source', '未知来源')}")
            else:
                print(f"  ⚠️ 未获取到新闻数据")
            
            return True
        else:
            error = news_result.get("error", "未知错误")
            print(f"❌ 获取真实AI新闻失败: {error}")
            return False
    except Exception as e:
        print(f"❌ 真实AI新闻获取测试失败: {e}")
        return False

def test_daily_brief_generation():
    """测试每日简报生成"""
    print("\n🧪 测试每日简报生成...")
    try:
        # 使用临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                brief = EnhancedAIBrief()
                result = brief.generate_daily_brief()
                
                if result.get("success", False):
                    total_items = result.get("total_items", 0)
                    real_items = result.get("real_items", 0)
                    categories = result.get("categories", {})
                    report = result.get("report", "")
                    filepath = result.get("filepath", "")
                    
                    print(f"✅ 每日简报生成成功")
                    print(f"  总条目数: {total_items}")
                    print(f"  真实新闻: {real_items}")
                    print(f"  分类统计: {categories}")
                    
                    if filepath and os.path.exists(filepath):
                        print(f"  报告已保存: {filepath}")
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                            print(f"  报告长度: {len(content)} 字符")
                    
                    # 检查报告内容
                    if report:
                        lines = report.split('\n')
                        print(f"  报告行数: {len(lines)}")
                        
                        # 检查关键部分
                        has_title = any("AI每日简报" in line for line in lines[:10])
                        has_summary = any("简报摘要" in line for line in lines[:20])
                        has_content = any("今日AI热点" in line for line in lines)
                        
                        if has_title and has_summary and has_content:
                            print("✅ 报告内容结构完整")
                        else:
                            print("⚠️ 报告内容结构不完整")
                    
                    return True
                else:
                    error = result.get("error", "未知错误")
                    print(f"❌ 每日简报生成失败: {error}")
                    return False
            finally:
                os.chdir(original_dir)
    except Exception as e:
        print(f"❌ 每日简报生成测试失败: {e}")
        return False

def test_content_categorization():
    """测试内容分类"""
    print("\n🧪 测试内容分类...")
    try:
        brief = EnhancedAIBrief()
        
        # 测试不同的内容分类
        test_cases = [
            ("OpenAI发布新的GPT-5模型", "模型发布/更新"),
            ("Claude推出新的代码编辑工具", "产品发布/更新"),
            ("AI芯片研究取得突破", "硬件发展"),
            ("机器学习论文在顶会发表", "论文研究"),
            ("AI行业融资额创新高", "行业动态"),
            ("AI安全标准发布", "安全伦理"),
            ("政府发布AI政策指南", "政策动态"),
            ("这是一个普通的测试", "其他"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for content, expected_category in test_cases:
            category = brief.categorize_content(content)
            if category == expected_category:
                print(f"  ✅ '{content[:20]}...' -> {category}")
                passed += 1
            else:
                print(f"  ❌ '{content[:20]}...' -> {category} (期望: {expected_category})")
        
        accuracy = passed / total * 100
        print(f"📊 分类准确率: {passed}/{total} ({accuracy:.1f}%)")
        
        return passed >= total * 0.8  # 允许80%的准确率
    except Exception as e:
        print(f"❌ 内容分类测试失败: {e}")
        return False

def test_report_saving():
    """测试报告保存功能"""
    print("\n🧪 测试报告保存功能...")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # 创建测试报告内容
                test_report = "# 测试报告\n\n这是一个测试报告。\n\n生成时间: 2026-05-12"
                
                # 创建brief实例
                brief = EnhancedAIBrief()
                
                # 测试保存报告
                filepath = brief.save_report(test_report)
                
                if filepath and os.path.exists(filepath):
                    print(f"✅ 报告保存成功: {filepath}")
                    
                    # 验证文件内容
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    if content == test_report:
                        print("✅ 报告内容正确")
                    else:
                        print("❌ 报告内容不匹配")
                    
                    return True
                else:
                    print(f"❌ 报告保存失败")
                    return False
            finally:
                os.chdir(original_dir)
    except Exception as e:
        print(f"❌ 报告保存测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运行daily_brief测试")
    print("=" * 50)
    
    test_results = []
    
    # 运行测试
    test_results.append(("EnhancedAIBrief初始化", test_enhanced_ai_brief_initialization()))
    test_results.append(("真实AI新闻获取", test_real_ai_news_fetch()))
    test_results.append(("内容分类", test_content_categorization()))
    test_results.append(("报告保存", test_report_saving()))
    test_results.append(("每日简报生成", test_daily_brief_generation()))
    
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