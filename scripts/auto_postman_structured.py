#!/usr/bin/env python3
import os
import sys
import argparse
import json
import subprocess
from pathlib import Path

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.utils.logger import get_logger
from src.utils.postman_converter import convert_test_cases_to_postman
from src.utils.env_file_generator import generate_environment_file

logger = get_logger(__name__)

def main():
    """运行结构化测试用例生成器并自动打开Postman"""
    parser = argparse.ArgumentParser(description="生成结构化测试用例并打开Postman")
    parser.add_argument("-f", "--file", required=True, help="API文档文件路径")
    parser.add_argument("-u", "--url", required=True, help="API基础URL")
    parser.add_argument("-o", "--output", help="输出目录", default="reports")
    parser.add_argument("--nopostman", action="store_true", help="不自动打开Postman")
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 运行结构化测试用例生成器
    logger.info(f"正在从 {args.file} 生成结构化测试用例...")
    try:
        # 调用测试用例生成脚本
        cmd = [
            sys.executable, 
            os.path.join(current_dir, "generate_structured_testcases.py"),
            "-f", args.file,
            "-u", args.url
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(result.stdout)
        
        # 获取生成的测试用例文件路径
        test_cases_file = os.path.join(project_root, "reports", "structured_test_cases.json")
        
        if os.path.exists(test_cases_file):
            logger.info(f"成功生成测试用例: {test_cases_file}")
            
            # 读取测试用例数据
            with open(test_cases_file, 'r', encoding='utf-8') as f:
                test_case_data = json.load(f)
            
            # 将测试用例转换为Postman集合
            postman_file = os.path.join(project_root, args.output, "structured_test_cases_postman.json")
            
            # 检查格式：如果是包含test_cases字段的字典，则提取其中的测试用例列表
            if isinstance(test_case_data, dict) and "test_cases" in test_case_data:
                test_cases = test_case_data["test_cases"]
                
                # 创建临时文件存储test_cases列表
                temp_file = os.path.join(project_root, args.output, "temp_test_cases.json")
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(test_cases, f, indent=2, ensure_ascii=False)
                
                # 使用临时文件作为输入来转换
                convert_test_cases_to_postman(temp_file, postman_file)
                
                # 删除临时文件
                try:
                    os.remove(temp_file)
                except:
                    pass
            else:
                # 旧格式，直接转换
                convert_test_cases_to_postman(test_cases_file, postman_file)
            
            logger.info(f"成功生成Postman集合: {postman_file}")
            
            # 生成环境文件
            env_file = os.path.join(project_root, args.output, "postman_environment.json")
            env_vars = {
                "Region": "cn-bj2",
                "Zone": "cn-bj2-04",
                "ProjectId": "org-123456",
                "base_url": args.url
            }
            generate_environment_file(
                output_path=env_file,
                env_vars=env_vars,
                env_name="API Test AI Environment"
            )
            logger.info(f"成功生成Postman环境文件: {env_file}")
            
            # 自动打开Postman
            if not args.nopostman:
                logger.info("正在打开Postman...")
                try:
                    # 尝试打开Postman (支持macOS和Windows)
                    if sys.platform == "darwin":  # macOS
                        subprocess.run(["open", "-a", "Postman", postman_file])
                    elif sys.platform == "win32":  # Windows
                        os.startfile(postman_file)
                    else:  # Linux or other
                        subprocess.run(["xdg-open", postman_file])
                    logger.info("已成功打开Postman")
                except Exception as e:
                    logger.error(f"无法自动打开Postman: {str(e)}")
                    logger.info(f"请手动导入Postman集合: {postman_file}")
        else:
            logger.error(f"未找到生成的测试用例文件: {test_cases_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"测试用例生成失败: {e.stderr}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 