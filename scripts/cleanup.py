#!/usr/bin/env python3
import os
import shutil
import glob
import argparse
from pathlib import Path


def cleanup_files():
    """
    Clean up temporary files generated during API testing process.
    This includes intermediate JSON files, logs, and other temporary artifacts.
    """
    print("开始清理临时文件...")
    
    # Get the project root directory
    root_dir = Path(__file__).parent.parent.absolute()
    
    # Files and directories to clean
    cleanup_targets = [
        # Temporary JSON files
        os.path.join(root_dir, "reports", "test_cases_*.json"),
        os.path.join(root_dir, "reports", "*.html"),
        os.path.join(root_dir, "reports", "*.pdf"),
        # Log files
        os.path.join(root_dir, "logs", "*.log"),
        # Extracted API schemas
        os.path.join(root_dir, "extracted_schemas", "*.json"),
        # Temporary environment files
        os.path.join(root_dir, "*.json"),
    ]
    
    # Create directories if they don't exist
    for directory in ["reports", "logs", "extracted_schemas"]:
        os.makedirs(os.path.join(root_dir, directory), exist_ok=True)
    
    # Count of deleted files
    deleted_count = 0
    
    # Clean up files
    for target in cleanup_targets:
        for file_path in glob.glob(target):
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"已删除: {os.path.relpath(file_path, root_dir)}")
                    deleted_count += 1
            except Exception as e:
                print(f"删除文件 {file_path} 时出错: {str(e)}")
    
    print(f"清理完成! 共删除 {deleted_count} 个临时文件。")
    
    return deleted_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="清理API测试过程中生成的临时文件")
    args = parser.parse_args()
    
    cleanup_files() 