#!/usr/bin/env python3
import os
import sys
import argparse

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.postman_converter import convert_test_cases_to_postman
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """
    转换测试用例为Postman集合的命令行工具
    """
    parser = argparse.ArgumentParser(description="将API Test AI测试用例转换为Postman集合")
    
    parser.add_argument("-i", "--input", required=True,
                      help="输入测试用例文件路径（如：reports/test_cases.json）")
    
    parser.add_argument("-o", "--output",
                      help="输出Postman集合文件路径（默认：<input_filename>_postman.json）")
    
    args = parser.parse_args()
    
    # 获取输入文件
    input_file = args.input
    
    # 确定输出文件
    if args.output:
        output_file = args.output
    else:
        input_filename = os.path.splitext(os.path.basename(input_file))[0]
        output_dir = os.path.dirname(input_file)
        output_file = os.path.join(output_dir, f"{input_filename}_postman.json")
    
    try:
        logger.info(f"开始转换测试用例 {input_file} 为Postman集合格式...")
        convert_test_cases_to_postman(input_file, output_file)
        logger.info(f"转换成功！Postman集合已保存到: {output_file}")
        return 0
    except Exception as e:
        logger.error(f"转换失败: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 