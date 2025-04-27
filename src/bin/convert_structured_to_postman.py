#!/usr/bin/env python3
import os
import sys
import argparse
import json

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.postman_adapter import PostmanAdapter
from src.models.test_case import TestCaseCollection
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """
    Command-line tool to convert structured test cases to Postman format
    """
    parser = argparse.ArgumentParser(description="Convert structured API test cases to Postman collection")
    
    parser.add_argument("-i", "--input", required=True,
                      help="Input structured test cases file path (e.g., reports/structured_test_cases.json)")
    
    parser.add_argument("-o", "--output",
                      help="Output Postman collection file path (default: <input_filename>_postman.json)")
    
    args = parser.parse_args()
    
    # Get input file
    input_file = args.input
    
    # Determine output file
    if args.output:
        output_file = args.output
    else:
        input_filename = os.path.splitext(os.path.basename(input_file))[0]
        output_dir = os.path.dirname(input_file)
        output_file = os.path.join(output_dir, f"{input_filename}_postman.json")
    
    try:
        logger.info(f"Starting conversion of structured test cases {input_file} to Postman collection format...")
        
        # Load test case collection
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        collection = TestCaseCollection.from_dict(data)
        
        # Convert to Postman format
        adapter = PostmanAdapter()
        adapter.convert_test_case_collection_to_postman_file(collection, output_file)
        
        logger.info(f"Conversion successful! Postman collection saved to: {output_file}")
        return 0
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 