#!/usr/bin/env python3
import argparse
import json
import os
import sys

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.env_file_generator import generate_environment_file
from src.utils.logger import get_logger

logger = get_logger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Generate environment file for API testing")
    
    # Output file
    parser.add_argument("-o", "--output", 
                       default="reports/environment.json",
                       help="Output path for environment file")
    
    # Base URL
    parser.add_argument("-u", "--url", 
                       default="https://api.ucloud.cn",
                       help="Base URL for API testing")
    
    # Environment name
    parser.add_argument("-n", "--name", 
                       default="API Test AI Environment",
                       help="Name of the environment")
    
    # Environment variables from file
    parser.add_argument("-f", "--file", 
                       help="Load environment variables from JSON file")
    
    # Environment variables
    parser.add_argument("-v", "--vars", 
                       action="append", 
                       help="Environment variables in format key=value")
    
    # Region
    parser.add_argument("--region", help="Region value")
    
    # Zone
    parser.add_argument("--zone", help="Zone value")
    
    # Project ID
    parser.add_argument("--project-id", dest="project_id", help="Project ID value")
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    
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
            
            logger.info(f"Loaded environment variables from {args.file}")
        except Exception as e:
            logger.error(f"Error loading environment variables from {args.file}: {str(e)}")
    
    # 2. Add command line variables
    if args.vars:
        for var_str in args.vars:
            if '=' in var_str:
                key, value = var_str.split('=', 1)
                env_vars[key] = value
                logger.info(f"Added environment variable from command line: {key}")
    
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
    
    print(f"Environment file generated: {output_path}")
    print("Example variables:")
    for key, value in env_vars.items():
        print(f"  - {key}: {value}")

if __name__ == "__main__":
    main() 