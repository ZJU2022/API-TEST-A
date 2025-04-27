#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import platform
import time
import json
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

def run_command(command, cwd=None):
    """运行命令并返回输出"""
    try:
        process = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        print(f"错误输出: {e.stderr}")
        sys.exit(1)

def generate_test_cases(api_doc_path, output_dir=None, base_url="https://api.ucloud.cn"):
    """生成POST测试用例"""
    cmd = [sys.executable, "scripts/generate_post_testcases.py", "-f", api_doc_path, "-u", base_url]
    if output_dir:
        cmd.extend(["-o", os.path.join(output_dir, "test_cases.json")])
    
    cmd_str = " ".join(cmd)
    print(f"生成POST测试用例: {cmd_str}")
    output = run_command(cmd_str, cwd=project_root)
    print(output)
    
    # 返回生成的测试用例文件路径
    if output_dir:
        test_cases_path = os.path.join(output_dir, "test_cases.json")
    else:
        test_cases_path = os.path.join(project_root, "reports", "test_cases.json")
    
    if os.path.exists(test_cases_path):
        print(f"测试用例生成成功: {test_cases_path}")
        return test_cases_path
    else:
        print("无法找到生成的测试用例文件")
        sys.exit(1)

def convert_to_postman(test_cases_path, output_file=None):
    """转换测试用例为Postman格式"""
    if not output_file:
        output_file = os.path.splitext(test_cases_path)[0] + "_postman.json"
    
    cmd = [sys.executable, "src/bin/convert_to_postman.py", "-i", test_cases_path, "-o", output_file]
    cmd_str = " ".join(cmd)
    print(f"转换为Postman格式: {cmd_str}")
    output = run_command(cmd_str, cwd=project_root)
    print(output)
    
    if os.path.exists(output_file):
        print(f"Postman集合文件生成成功: {output_file}")
        return output_file
    else:
        print("无法找到生成的Postman集合文件")
        sys.exit(1)

def open_postman(postman_file):
    """打开Postman并显示如何导入文件的说明"""
    print("\n=== 正在打开Postman ===")
    
    system = platform.system()
    
    # 尝试打开Postman
    try:
        if system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", "Postman"])
        elif system == "Windows":
            # 尝试常见的Windows安装路径
            postman_paths = [
                os.path.join(os.environ.get('LOCALAPPDATA', ''), "Postman", "Postman.exe"),
                os.path.join(os.environ.get('PROGRAMFILES', ''), "Postman", "Postman.exe"),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), "Postman", "Postman.exe")
            ]
            
            for path in postman_paths:
                if os.path.exists(path):
                    subprocess.Popen([path])
                    break
            else:
                print("无法找到Postman安装位置，请手动打开Postman")
        elif system == "Linux":
            subprocess.Popen(["postman"])
        else:
            print(f"未知操作系统: {system}，请手动打开Postman")
    except Exception as e:
        print(f"打开Postman时出错: {e}")
        print("请手动打开Postman")
    
    # 显示导入说明
    print("\n=== 导入Postman集合的步骤 ===")
    print("1. 在Postman中点击左上角的「Import」按钮")
    print("2. 选择「File」选项卡，然后点击「Upload Files」")
    print(f"3. 选择此文件: {os.path.abspath(postman_file)}")
    print("4. 点击「Import」按钮完成导入")
    print("\n集合导入后，您可以在左侧的Collections面板中找到导入的测试集合。")

def create_environment_file(postman_file, env_vars=None):
    """为Postman创建环境变量文件"""
    if not env_vars:
        env_vars = {}
        
    # 确保基本环境变量存在，如果用户没有提供则使用默认值
    default_vars = {
        "Region": "cn-bj2",
        "Zone": "cn-bj2-02",
        "ProjectId": "50400554",
        "PublicKey": "0",
        "PrivateKey": "0",
        "base_url": "https://api.ucloud.cn"
    }
    
    # 将默认值与用户提供的值合并，用户提供的值优先
    for key, value in default_vars.items():
        if key not in env_vars:
            env_vars[key] = value
    
    # 创建环境变量文件
    env_file = os.path.splitext(postman_file)[0] + "_environment.json"
    
    env_data = {
        "id": "auto-generated-env",
        "name": "API Test AI Environment",
        "values": [
            {
                "key": key,
                "value": value,
                "type": "default",
                "enabled": True
            } for key, value in env_vars.items()
        ],
        "_postman_variable_scope": "environment"
    }
    
    with open(env_file, 'w', encoding='utf-8') as f:
        json.dump(env_data, f, indent=2, ensure_ascii=False)
    
    print(f"环境变量文件创建成功: {env_file}")
    return env_file

def main():
    parser = argparse.ArgumentParser(description="自动化API测试流程（强制POST请求）")
    parser.add_argument("-f", "--file", required=True, help="API文档或架构文件路径")
    parser.add_argument("-o", "--output", help="输出目录")
    parser.add_argument("-u", "--url", default="https://api.ucloud.cn", help="测试的API基本URL")
    parser.add_argument("-e", "--env", help="环境变量文件路径")
    
    args = parser.parse_args()
    
    print("=== 自动化API测试工作流开始（强制POST请求）===")
    
    # 1. 生成测试用例
    test_cases_path = generate_test_cases(args.file, args.output, args.url)
    
    # 2. 转换为Postman格式
    postman_file = convert_to_postman(test_cases_path)
    
    # 3. 创建环境变量文件
    if args.url:
        env_vars = {"base_url": args.url}
        env_file = create_environment_file(postman_file, env_vars)
    else:
        env_file = create_environment_file(postman_file)
    
    # 4. 打开Postman
    open_postman(postman_file)
    
    print("\n=== 在Postman中导入环境说明 ===")
    print("1. 在Postman中点击右上角的眼睛图标(Environment)")
    print("2. 点击「Import」按钮")
    print(f"3. 选择此环境文件: {os.path.abspath(env_file)}")
    print("4. 导入后，从下拉菜单中选择环境「API Test AI Environment」")
    
    print("\n=== 自动化工作流完成 ===")
    print("请按照上述步骤在Postman中导入集合和环境文件，然后运行测试。")

if __name__ == "__main__":
    main() 