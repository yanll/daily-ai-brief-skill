#!/usr/bin/env python3
"""
运行所有测试
"""

import sys
import os
import subprocess

def run_test(test_file):
    """运行单个测试文件"""
    print(f"\n🔍 运行测试: {test_file}")
    print("=" * 50)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        # 打印输出
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print(f"⚠️ 错误输出:\n{result.stderr}")
        
        if result.returncode == 0:
            print(f"✅ {test_file} 测试通过")
            return True
        else:
            print(f"❌ {test_file} 测试失败 (返回码: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_file} 测试超时")
        return False
    except Exception as e:
        print(f"❌ {test_file} 测试异常: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运行所有测试")
    print("=" * 60)
    
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_files = [
        "test_data_source_manager.py",
        "test_daily_brief.py"
    ]
    
    test_results = []
    
    for test_file in test_files:
        test_path = os.path.join(test_dir, test_file)
        if os.path.exists(test_path):
            success = run_test(test_path)
            test_results.append((test_file, success))
        else:
            print(f"⚠️ 测试文件不存在: {test_path}")
            test_results.append((test_file, False))
    
    # 显示测试结果汇总
    print("\n" + "=" * 60)
    print("📊 所有测试结果汇总:")
    print("=" * 60)
    
    passed = 0
    total = 0
    
    for test_file, success in test_results:
        total += 1
        if success:
            passed += 1
            print(f"  ✅ {test_file}: 通过")
        else:
            print(f"  ❌ {test_file}: 失败")
    
    print("=" * 60)
    print(f"🎯 总体通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️ {total - passed} 个测试失败")
    
    return passed == total

def run_continuous_testing(iterations=3):
    """连续运行测试多次，模拟反复运行直到成功"""
    print("🔄 开始连续测试模式")
    print("=" * 60)
    
    successful_runs = 0
    total_runs = 0
    
    for i in range(iterations):
        print(f"\n🔄 第 {i+1}/{iterations} 次运行")
        print("-" * 40)
        
        success = run_all_tests()
        total_runs += 1
        
        if success:
            successful_runs += 1
            print(f"✅ 第 {i+1} 次运行成功")
        else:
            print(f"❌ 第 {i+1} 次运行失败")
        
        # 如果不是最后一次，等待一下再继续
        if i < iterations - 1:
            print("\n⏳ 等待5秒后继续...")
            import time
            time.sleep(5)
    
    print("\n" + "=" * 60)
    print(f"📈 连续测试结果: {successful_runs}/{total_runs} 次成功")
    
    if successful_runs == total_runs:
        print("🎉 所有连续测试都成功！")
    else:
        print(f"⚠️ 有 {total_runs - successful_runs} 次运行失败")
    
    return successful_runs == total_runs

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        success = run_continuous_testing(iterations=3)
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)