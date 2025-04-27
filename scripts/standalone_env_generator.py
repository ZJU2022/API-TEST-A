#!/usr/bin/env python3
"""
Standalone Environment File Generator for API Testing

This script generates Postman environment files for API testing.
It has no dependencies on the API Test AI project and can be used independently.
"""

import argparse
import json
import os
import uuid
from datetime import datetime

def generate_environment_file(
    output_path, 
    env_vars=None, 
    env_name="API Test AI Environment"
):
    """
    Generates an environment file for API testing.
    
    Args:
        output_path: Path where the environment file should be saved
        env_vars: Dictionary of environment variables to include
        env_name: Name of the environment
    
    Returns:
        Path to the generated environment file
    """
    # Use default values if no environment variables provided
    if not env_vars:
        env_vars = {
            "Region": "cn-bj2",
            "Zone": "cn-bj2-04",
            "ProjectId": "org-123456",
            "base_url": "https://api.ucloud.cn"
        }
    
    # Create environment file structure
    env_data = {
        "id": str(uuid.uuid4()),
        "name": env_name,
        "values": [
            {
                "key": key,
                "value": value,
                "type": "default",
                "enabled": True
            } for key, value in env_vars.items()
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_at": datetime.now().isoformat(),
        "_postman_exported_using": "API-Test-AI/1.0"
    }
    
    # Create directory if it doesn't exist and if there's a directory component
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    # Write environment file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(env_data, f, indent=2, ensure_ascii=False)
    
    print(f"环境文件已生成: {output_path}")
    return output_path

def load_environment_file(file_path):
    """
    Loads an environment file and returns its contents.
    
    Args:
        file_path: Path to the environment file
    
    Returns:
        Dictionary containing environment data
    """
    if not os.path.exists(file_path):
        print(f"错误: 环境文件未找到: {file_path}")
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            env_data = json.load(f)
        
        print(f"环境文件已加载: {file_path}")
        return env_data
    except Exception as e:
        print(f"加载环境文件时出错 {file_path}: {str(e)}")
        return {}

def extract_env_vars(env_data):
    """
    Extracts environment variables from an environment file data structure.
    
    Args:
        env_data: Environment file data
    
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    
    if not env_data or 'values' not in env_data:
        return env_vars
    
    for variable in env_data['values']:
        if 'key' in variable and 'value' in variable and variable.get('enabled', True):
            env_vars[variable['key']] = variable['value']
    
    return env_vars

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="为API测试生成环境文件")
    
    # Output file
    parser.add_argument("-o", "--output", 
                       default="reports/environment.json",
                       help="环境文件的输出路径")
    
    # Base URL
    parser.add_argument("-u", "--url", 
                       default="https://api.ucloud.cn",
                       help="API测试的基础URL")
    
    # Environment name
    parser.add_argument("-n", "--name", 
                       default="API Test AI Environment",
                       help="环境名称")
    
    # Environment variables from file
    parser.add_argument("-f", "--file", 
                       help="从JSON文件加载环境变量")
    
    # Environment variables
    parser.add_argument("-v", "--var", 
                       action="append", dest="vars",
                       help="环境变量，格式为key=value")
    
    # Region
    parser.add_argument("--region", help="区域值")
    
    # Zone
    parser.add_argument("--zone", help="可用区值")
    
    # Project ID
    parser.add_argument("--project-id", dest="project_id", help="项目ID值")
    
    # AI mode
    parser.add_argument("--ai", action="store_true", help="使用AI增强模式生成环境文件")
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Check if AI mode is enabled
    if args.ai:
        try:
            import sys
            import subprocess
            cmd = [sys.executable, "src/main.py", "env", "-u", args.url]
            if args.output != "reports/environment.json":
                cmd.extend(["-o", args.output])
            if args.name != "API Test AI Environment":
                cmd.extend(["-n", args.name])
            print("使用AI增强模式生成环境文件...")
            result = subprocess.run(cmd, check=True)
            return
        except Exception as e:
            print(f"AI模式启动失败: {str(e)}")
            print("使用标准模式继续...")
    
    # Collect environment variables
    env_vars = {}
    
    # 1. Load from file if provided
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                file_vars = json.load(f)
            
            # Handle different file formats
            if isinstance(file_vars, dict):
                # Simple key-value dictionary
                env_vars.update(file_vars)
            elif 'values' in file_vars:
                # Postman environment format
                for var in file_vars.get('values', []):
                    if 'key' in var and 'value' in var:
                        env_vars[var['key']] = var['value']
            
            print(f"已从{args.file}加载环境变量")
        except Exception as e:
            print(f"从{args.file}加载环境变量时出错: {str(e)}")
    
    # 2. Add command line variables
    if args.vars:
        for var_str in args.vars:
            if '=' in var_str:
                key, value = var_str.split('=', 1)
                env_vars[key] = value
                print(f"已添加命令行环境变量: {key}")
    
    # 3. Add specific variables if provided
    if args.url:
        env_vars['base_url'] = args.url
    
    if args.region:
        env_vars['Region'] = args.region
    
    if args.zone:
        env_vars['Zone'] = args.zone
    
    if args.project_id:
        env_vars['ProjectId'] = args.project_id
    
    # Generate the environment file
    output_path = generate_environment_file(
        output_path=args.output,
        env_vars=env_vars,
        env_name=args.name
    )
    
    print("环境变量:")
    for key, value in env_vars.items():
        print(f"  - {key}: {value}")

if __name__ == "__main__":
    main() 