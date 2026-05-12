#!/usr/bin/env python3
"""
反复运行daily_brief.py直到成功采集到足够数据
不要偷懒，不要怪网络问题，不要失败就放弃，结果为导向
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime

class RetryRunner:
    """重试运行器"""
    
    def __init__(self, min_items=10, max_retries=10, retry_delay=5):
        self.min_items = min_items  # 最少需要采集到的条目数
        self.max_retries = max_retries  # 最大重试次数
        self.retry_delay = retry_delay  # 重试延迟（秒）
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.results = []
    
    def clean_cache_before_run(self):
        """运行前清理缓存"""
        print("🧹 运行前清理缓存...")
        try:
            # 清理缓存目录
            cache_dir = os.path.join(self.base_dir, "cache")
            if os.path.exists(cache_dir):
                import shutil
                shutil.rmtree(cache_dir)
                print(f"  ✅ 已清理缓存目录: {cache_dir}")
            
            # 清理pycache
            pycache_dir = os.path.join(self.base_dir, "__pycache__")
            if os.path.exists(pycache_dir):
                import shutil
                shutil.rmtree(pycache_dir)
                print(f"  ✅ 已清理pycache目录")
            
            # 清理历史报告（保留最新几个）
            reports_dir = os.path.join(self.base_dir, "reports")
            if os.path.exists(reports_dir):
                report_files = []
                for f in os.listdir(reports_dir):
                    if f.endswith('.md'):
                        filepath = os.path.join(reports_dir, f)
                        report_files.append((filepath, os.path.getmtime(filepath)))
                
                # 按修改时间排序，保留最新的3个文件
                report_files.sort(key=lambda x: x[1], reverse=True)
                for i, (filepath, _) in enumerate(report_files):
                    if i >= 3:  # 保留最新的3个文件
                        os.remove(filepath)
                        print(f"  🗑️ 已删除旧报告: {os.path.basename(filepath)}")
            
        except Exception as e:
            print(f"  ⚠️ 缓存清理失败: {e}")
    
    def run_daily_brief(self):
        """运行daily_brief.py"""
        print("🚀 运行daily_brief.py...")
        
        try:
            result = subprocess.run(
                [sys.executable, "daily_brief.py"],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300  # 5分钟超时
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "timestamp": datetime.now().isoformat()
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "运行超时（超过5分钟）",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def extract_item_count(self, stdout):
        """从输出中提取采集到的条目数"""
        import re
        
        # 尝试从输出中提取条目数
        patterns = [
            r"总条目数:\s*(\d+)\s*条",
            r"内容数量:\s*(\d+)\s*条",
            r"总计采集到\s*(\d+)\s*条唯一数据",
            r"成功获取\s*(\d+)\s*条真实新闻",
            r"total_items.*?(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, stdout)
            if match:
                try:
                    return int(match.group(1))
                except:
                    continue
        
        # 如果无法提取，尝试从报告文件中获取
        reports_dir = os.path.join(self.base_dir, "reports")
        if os.path.exists(reports_dir):
            # 找到最新的报告文件
            report_files = []
            for f in os.listdir(reports_dir):
                if f.endswith('.md'):
                    filepath = os.path.join(reports_dir, f)
                    report_files.append((filepath, os.path.getmtime(filepath)))
            
            if report_files:
                report_files.sort(key=lambda x: x[1], reverse=True)
                latest_report = report_files[0][0]
                
                try:
                    with open(latest_report, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 从报告内容中提取
                    match = re.search(r"总条目数.*?(\d+)\s*条", content)
                    if match:
                        return int(match.group(1))
                except:
                    pass
        
        return 0
    
    def analyze_output(self, result):
        """分析输出结果"""
        if not result["success"]:
            print(f"❌ 运行失败")
            if "error" in result:
                print(f"   错误: {result['error']}")
            return False, 0
        
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        
        # 检查是否有错误信息
        has_errors = False
        error_keywords = ["失败", "错误", "error", "exception", "traceback", "❌", "⚠️"]
        
        for keyword in error_keywords:
            if keyword.lower() in stdout.lower() or (stderr and keyword.lower() in stderr.lower()):
                has_errors = True
                break
        
        # 提取采集到的条目数
        item_count = self.extract_item_count(stdout)
        
        # 检查是否成功
        success_keywords = ["成功", "已生成", "已完成", "✅", "🎉"]
        has_success = any(keyword in stdout for keyword in success_keywords)
        
        if has_errors and not has_success:
            print(f"⚠️ 运行完成但有错误，采集到 {item_count} 条数据")
            return False, item_count
        elif item_count > 0:
            print(f"✅ 运行成功，采集到 {item_count} 条数据")
            return True, item_count
        else:
            print(f"📭 运行完成但未采集到数据")
            return False, 0
    
    def run_with_retry(self):
        """带重试的运行"""
        print(f"🔄 开始反复运行daily_brief.py")
        print(f"   目标: 至少采集到 {self.min_items} 条数据")
        print(f"   最大重试次数: {self.max_retries}")
        print(f"   重试延迟: {self.retry_delay} 秒")
        print("=" * 60)
        
        best_result = None
        best_item_count = 0
        
        for attempt in range(1, self.max_retries + 1):
            print(f"\n🔄 第 {attempt}/{self.max_retries} 次尝试")
            print("-" * 40)
            
            # 运行前清理缓存
            self.clean_cache_before_run()
            
            # 运行daily_brief
            result = self.run_daily_brief()
            success, item_count = self.analyze_output(result)
            
            # 记录结果
            run_info = {
                "attempt": attempt,
                "success": success,
                "item_count": item_count,
                "timestamp": datetime.now().isoformat(),
                "best_so_far": item_count > best_item_count
            }
            self.results.append(run_info)
            
            # 更新最佳结果
            if item_count > best_item_count:
                best_item_count = item_count
                best_result = run_info
                print(f"🎯 更新最佳记录: {item_count} 条数据")
            
            # 检查是否达到目标
            if item_count >= self.min_items:
                print(f"\n🎉 达到目标！采集到 {item_count} 条数据（目标: {self.min_items}）")
                print(f"✅ 在第 {attempt} 次尝试中成功")
                return True, item_count, attempt
            
            # 如果未达到目标且不是最后一次尝试，等待后继续
            if attempt < self.max_retries:
                print(f"\n⏳ 未达到目标，等待 {self.retry_delay} 秒后重试...")
                time.sleep(self.retry_delay)
            else:
                print(f"\n⏰ 已达到最大重试次数 ({self.max_retries})")
        
        # 所有尝试都结束后
        print(f"\n📊 所有尝试完成")
        print(f"   最佳结果: {best_item_count} 条数据")
        print(f"   目标要求: {self.min_items} 条数据")
        
        if best_item_count > 0:
            print(f"⚠️ 未达到目标，但采集到 {best_item_count} 条数据")
            return False, best_item_count, self.max_retries
        else:
            print("❌ 所有尝试均未采集到数据")
            return False, 0, self.max_retries
    
    def generate_report(self, overall_success, best_item_count, attempts):
        """生成运行报告"""
        print("\n" + "=" * 60)
        print("📋 运行报告")
        print("=" * 60)
        
        if overall_success:
            print(f"✅ 任务成功完成！")
            print(f"   采集到数据: {best_item_count} 条")
            print(f"   尝试次数: {attempts} 次")
        else:
            print(f"⚠️ 任务未完全成功")
            print(f"   最佳采集数据: {best_item_count} 条")
            print(f"   尝试次数: {attempts} 次")
        
        print(f"\n📈 详细运行记录:")
        for i, result in enumerate(self.results, 1):
            status = "✅" if result["success"] else "❌"
            best_mark = " 🎯" if result["best_so_far"] else ""
            print(f"   尝试 {i}: {status} {result['item_count']} 条数据{best_mark}")
        
        # 保存报告到文件
        report_dir = os.path.join(self.base_dir, "reports")
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, f"重试运行报告_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("重试运行报告\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"任务状态: {'成功' if overall_success else '未完全成功'}\n")
            f.write(f"采集数据: {best_item_count} 条\n")
            f.write(f"尝试次数: {attempts} 次\n")
            f.write(f"目标要求: {self.min_items} 条\n\n")
            
            f.write("详细运行记录:\n")
            for i, result in enumerate(self.results, 1):
                status = "成功" if result["success"] else "失败"
                f.write(f"  尝试 {i}: {status}, {result['item_count']} 条数据")
                if result["best_so_far"]:
                    f.write(" (最佳记录)")
                f.write(f", 时间: {result['timestamp']}\n")
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        return report_file

def main():
    """主函数"""
    print("🔄 AI新闻采集重试运行器")
    print("=" * 60)
    print("原则: 不偷懒，不怪网络问题，不失败就放弃，结果为导向")
    print("=" * 60)
    
    # 配置参数
    min_items = 15  # 最少需要15条数据
    max_retries = 5  # 最多重试5次
    retry_delay = 10  # 重试延迟10秒
    
    runner = RetryRunner(
        min_items=min_items,
        max_retries=max_retries,
        retry_delay=retry_delay
    )
    
    # 运行带重试的任务
    overall_success, best_item_count, attempts = runner.run_with_retry()
    
    # 生成报告
    runner.generate_report(overall_success, best_item_count, attempts)
    
    # 返回退出码
    if overall_success:
        print("\n🎉 任务成功完成！")
        sys.exit(0)
    else:
        print("\n⚠️ 任务未完全成功，请检查问题")
        sys.exit(1)

if __name__ == "__main__":
    main()