#!/usr/bin/env python3
"""
PhD-Scout 测试运行脚本

使用方式:
    python run_tests.py           # 运行所有测试
    python run_tests.py -v        # 详细输出
    python run_tests.py --help    # 查看帮助
"""

import subprocess
import sys
import os

def main():
    """运行测试"""
    # 确保在项目根目录
    if not os.path.exists("main.py"):
        print("错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 构建 pytest 命令
    cmd = ["pytest", "tests/"]
    
    # 添加命令行参数
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    else:
        cmd.append("-v")  # 默认详细输出
    
    print(f"运行命令: {' '.join(cmd)}")
    print("=" * 50)
    
    # 运行测试
    try:
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print("错误: 未找到 pytest。请先安装: pip install pytest")
        sys.exit(1)

if __name__ == "__main__":
    main()