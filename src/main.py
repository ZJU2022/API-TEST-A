#!/usr/bin/env python3
import argparse
import os
import sys
import yaml
import logging
from typing import Dict, Any, Optional

from src.core.document_parser import DocumentParser
from src.core.testcase_generator import TestCaseGenerator
from src.core.test_runner import TestRunner
from src.core.report_generator import ReportGenerator
from src.utils.ai_client import AIClient
from src.utils.postman_adapter import PostmanAdapter
from src.utils.logger import get_logger
from src.models.api_schema import APISchema, Endpoint
from src.utils.env_file_generator import generate_environment_file

logger = get_logger(__name__)


def load_config(config_path: str = "src/config/settings.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {str(e)}")
        return {}


def create_ai_client(config: Dict[str, Any]) -> Optional[AIClient]:
    """Create and configure an AI client if settings allow"""
    ai_config = config.get('ai', {})
    provider = ai_config.get('provider', 'openai')
    
    if provider == 'openai':
        # Check if API key is set in environment or config
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            api_key = ai_config.get('api_key')
        
        if not api_key:
            logger.warning("No OpenAI API key found. AI features will be disabled.")
            logger.warning("请设置OPENAI_API_KEY环境变量或在配置文件中设置api_key来启用AI功能。")
            logger.warning("AI功能能生成更全面的测试用例，强烈推荐使用！")
            logger.warning("可以通过 export OPENAI_API_KEY=your_key 设置环境变量")
            return None
        
        model = ai_config.get('model', 'gpt-3.5-turbo')
        logger.info(f"使用AI模型 {model} 创建测试用例")
        return AIClient(api_key=api_key, model=model, provider=provider)
        
    elif provider == 'local_llm':
        # 本地大模型配置
        model = ai_config.get('model', 'llama3')
        endpoint = ai_config.get('endpoint', 'http://localhost:8080/v1')
        api_key = ai_config.get('api_key')  # 可能为空
        
        logger.info(f"使用本地大模型 {model} 创建测试用例")
        return AIClient(api_key=api_key, model=model, provider=provider, endpoint=endpoint)
    
    else:
        logger.error(f"不支持的AI提供商: {provider}")
        return None


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="API Test AI - Automated API Testing")
    
    # Main command options
    parser.add_argument("command", choices=["run", "extract", "generate", "test", "report", "env"],
                        help="Command to execute")
    
    # Input file argument
    parser.add_argument("-f", "--file", help="Path to API documentation file (PDF)")
    
    # Output directory
    parser.add_argument("-o", "--output", help="Output directory for reports")
    
    # Base URL for testing
    parser.add_argument("-u", "--url", help="Base URL for API testing")
    
    # Config file
    parser.add_argument("-c", "--config", default="src/config/settings.yaml",
                        help="Path to configuration file")
    
    # Use Postman
    parser.add_argument("--postman", action="store_true", help="Use Postman for test execution")
    
    # Export to Postman collection
    parser.add_argument("--export-postman", action="store_true", 
                        help="Export test cases to Postman collection format")
    
    # Environment variables (for env command)
    parser.add_argument("--env-var", action="append", dest="vars",
                        help="Environment variables in format key=value (for env command)")
    
    # Environment name (for env command)
    parser.add_argument("-n", "--name", default="API Test AI Environment",
                        help="Name of the environment (for env command)")
    
    # Verbose output
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    return parser.parse_args()


# 新增函数：将 APISchema 对象转换为可序列化的字典
def api_schema_to_dict(api_schema: APISchema) -> Dict[str, Any]:
    """Convert an APISchema object to a dictionary for JSON serialization"""
    schema_dict = {
        "title": api_schema.title,
        "description": api_schema.description,
        "version": api_schema.version
    }
    
    # 添加 base_url 如果存在
    if api_schema.base_url:
        schema_dict["base_url"] = api_schema.base_url
    
    # 转换所有端点
    endpoints = []
    for endpoint in api_schema.endpoints:
        # 使用现有方法转换单个端点
        if hasattr(AIClient, '_endpoint_to_dict'):
            endpoint_dict = AIClient._endpoint_to_dict(AIClient, endpoint)
            endpoints.append(endpoint_dict)
    
    schema_dict["endpoints"] = endpoints
    return schema_dict


def run_extract_command(args, config, ai_client):
    """Run the extract command to parse a document"""
    if not args.file:
        logger.error("No input file specified. Use -f/--file to specify a document.")
        return 1
    
    logger.info(f"Extracting API information from {args.file}")
    
    # Create document parser
    document_parser = DocumentParser(ai_client=ai_client)
    
    try:
        # Extract API schema
        api_schema = document_parser.extract_from_pdf(args.file)
        
        # Output information about extracted endpoints
        logger.info(f"Extracted {len(api_schema.endpoints)} endpoints:")
        for endpoint in api_schema.endpoints:
            logger.info(f"  {endpoint.method} {endpoint.path}")
        
        # Save the schema to a JSON file
        import json
        output_dir = args.output or config.get('report', {}).get('output_dir', 'reports')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "api_schema.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            # 使用新的序列化函数
            schema_dict = api_schema_to_dict(api_schema)
            # 确保中文字符显示正确，而不是Unicode转义序列
            json.dump(schema_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"API schema saved to {output_path}")
        return 0
        
    except Exception as e:
        logger.error(f"Error extracting API information: {str(e)}")
        return 1


def run_generate_command(args, config, ai_client):
    """Run the generate command to create test cases"""
    if not args.file:
        logger.error("No input file specified. Use -f/--file to specify a schema or document.")
        return 1
    
    logger.info(f"Generating test cases from {args.file}")
    
    try:
        # Load schema or extract from document
        api_schema = None
        if args.file.endswith('.json'):
            # Load from JSON
            import json
            with open(args.file, 'r', encoding='utf-8') as f:
                schema_dict = json.load(f)
            
            # Convert dict to APISchema object
            from src.utils.ai_client import AIClient
            api_schema = AIClient._parse_api_schema(AIClient, json.dumps(schema_dict, ensure_ascii=False))
        else:
            # Extract from document
            document_parser = DocumentParser(ai_client=ai_client)
            api_schema = document_parser.extract_from_pdf(args.file)
        
        # Generate test cases
        testcase_generator = TestCaseGenerator(ai_client=ai_client)
        test_cases = testcase_generator.generate_test_cases(api_schema)
        
        # Save test cases to file
        import json
        output_dir = args.output or config.get('report', {}).get('output_dir', 'reports')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "test_cases.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(test_cases, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Generated test cases for {len(test_cases)} endpoints")
        logger.info(f"Test cases saved to {output_path}")
        return 0
        
    except Exception as e:
        logger.error(f"Error generating test cases: {str(e)}")
        return 1


def run_test_command(args, config, ai_client):
    """Run the test command to execute tests"""
    if not args.file:
        logger.error("No input file specified. Use -f/--file to specify test cases.")
        return 1
    
    logger.info(f"Running tests from {args.file}")
    
    try:
        # Load test cases
        import json
        with open(args.file, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        
        # Set up test runner
        base_url = args.url or config.get('testing', {}).get('base_url')
        
        # Check if we should export to Postman
        export_postman = args.export_postman or args.postman or config.get('testing', {}).get('use_postman', False)
        
        # Export test cases to Postman collection if requested
        if export_postman:
            try:
                from src.utils.postman_converter import convert_test_cases_to_postman
                output_dir = args.output or config.get('report', {}).get('output_dir', 'reports')
                input_filename = os.path.splitext(os.path.basename(args.file))[0]
                postman_file = os.path.join(output_dir, f"{input_filename}_postman.json")
                convert_test_cases_to_postman(args.file, postman_file)
                logger.info(f"Exported test cases to Postman collection: {postman_file}")
            except Exception as e:
                logger.warning(f"Failed to export Postman collection: {str(e)}")
        
        # Create Postman adapter if needed
        postman_adapter = None
        use_postman = args.postman or config.get('testing', {}).get('use_postman', False)
        
        if use_postman:
            postman_config = config.get('postman', {})
            newman_path = postman_config.get('newman_path', 'newman')
            collection_dir = postman_config.get('collection_dir', 'postman_collections')
            
            postman_adapter = PostmanAdapter(
                newman_path=newman_path,
                collection_output_dir=collection_dir
            )
        
        # Get API environment variables
        api_environment = config.get('api_environment', {})
        
        # Create test runner
        test_runner = TestRunner(
            base_url=base_url,
            postman_adapter=postman_adapter,
            api_environment=api_environment
        )
        
        # Run tests
        test_suite_result = test_runner.run_test_suite(test_cases)
        
        # Generate report
        report_config = config.get('report', {})
        output_dir = args.output or report_config.get('output_dir', 'reports')
        
        report_generator = ReportGenerator(
            output_dir=output_dir,
            ai_client=ai_client
        )
        
        report = report_generator.generate_report(test_suite_result)
        
        # Generate HTML report if configured
        if report_config.get('generate_html', True):
            html_path = report_generator.generate_html_report(report)
            logger.info(f"HTML report saved to {html_path}")
        
        logger.info(f"Testing completed: {test_suite_result.success_count} passed, "
                   f"{test_suite_result.failure_count} failed, {test_suite_result.error_count} errors")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        return 1


def run_report_command(args, config, ai_client):
    """Run the report command to generate reports from previous test results"""
    if not args.file:
        logger.error("No input file specified. Use -f/--file to specify test results.")
        return 1
    
    logger.info(f"Generating report from {args.file}")
    
    try:
        # Load test results
        import json
        with open(args.file, 'r') as f:
            results_dict = json.load(f)
        
        # Convert dict to TestSuiteResult object
        from src.models.test_result import TestSuiteResult, TestCaseResult, TestStatus, ValidationResult
        from datetime import datetime
        
        # Create test case results
        test_results = []
        for result_dict in results_dict.get('test_results', []):
            # Convert string status to enum
            status_str = result_dict.get('status', 'error')
            status = TestStatus.ERROR
            if status_str == 'success':
                status = TestStatus.SUCCESS
            elif status_str == 'failure':
                status = TestStatus.FAILURE
            elif status_str == 'skipped':
                status = TestStatus.SKIPPED
            
            # Create validation results
            validations = []
            for v_dict in result_dict.get('validations', []):
                validation = ValidationResult(
                    field=v_dict.get('field', ''),
                    is_valid=v_dict.get('is_valid', False),
                    expected=v_dict.get('expected', ''),
                    actual=v_dict.get('actual', ''),
                    message=v_dict.get('message', '')
                )
                validations.append(validation)
            
            # Create test case result
            test_result = TestCaseResult(
                test_name=result_dict.get('test_name', 'Unknown'),
                endpoint_path=result_dict.get('endpoint_path', '/'),
                http_method=result_dict.get('http_method', 'GET'),
                status=status,
                status_code=result_dict.get('status_code', 0),
                response_time_ms=result_dict.get('response_time_ms', 0),
                request_data=result_dict.get('request_data', {}),
                response_data=result_dict.get('response_data', {}),
                validations=validations,
                error_message=result_dict.get('error_message')
            )
            test_results.append(test_result)
        
        # Create test suite result
        test_suite_result = TestSuiteResult(
            name=results_dict.get('name', 'API Test Suite'),
            start_time=datetime.fromisoformat(results_dict.get('start_time', datetime.now().isoformat())),
            test_results=test_results
        )
        
        if 'end_time' in results_dict:
            test_suite_result.end_time = datetime.fromisoformat(results_dict['end_time'])
        else:
            test_suite_result.end_time = datetime.now()
        
        # Generate report
        report_config = config.get('report', {})
        output_dir = args.output or report_config.get('output_dir', 'reports')
        
        report_generator = ReportGenerator(
            output_dir=output_dir,
            ai_client=ai_client
        )
        
        report = report_generator.generate_report(test_suite_result)
        
        # Generate HTML report if configured
        if report_config.get('generate_html', True):
            html_path = report_generator.generate_html_report(report)
            logger.info(f"HTML report saved to {html_path}")
        
        logger.info(f"Report generated successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return 1


def run_env_command(args, config, ai_client):
    """Generate an environment file for API testing"""
    # Determine output path
    output_dir = args.output or config.get('report', {}).get('output_dir', 'reports')
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "environment.json")
    
    # Get environment variables
    env_vars = {}
    
    # 1. Start with config values
    env_vars.update(config.get('api_environment', {}))
    
    # 2. Add base URL if provided
    if args.url:
        env_vars['base_url'] = args.url
    
    # 3. Add variables from command line
    if args.vars:
        for var_str in args.vars:
            if '=' in var_str:
                key, value = var_str.split('=', 1)
                env_vars[key] = value
    
    # Generate the environment file
    output_path = generate_environment_file(
        output_path=output_path,
        env_vars=env_vars,
        env_name=args.name
    )
    
    logger.info(f"Environment file generated: {output_path}")
    return 0


def run_full_workflow(args, config, ai_client):
    """Run the full workflow: extract, generate, test, report"""
    if not args.file:
        logger.error("No input file specified. Use -f/--file to specify a document.")
        return 1
    
    logger.info(f"Running full workflow on {args.file}")
    
    try:
        # 1. Extract API schema
        document_parser = DocumentParser(ai_client=ai_client)
        api_schema = document_parser.extract_from_pdf(args.file)
        logger.info(f"Extracted {len(api_schema.endpoints)} endpoints")
        
        # 2. Generate test cases
        testcase_generator = TestCaseGenerator(ai_client=ai_client)
        test_cases = testcase_generator.generate_test_cases(api_schema)
        logger.info(f"Generated test cases for {len(test_cases)} endpoints")
        
        # 3. Run tests
        base_url = args.url or config.get('testing', {}).get('base_url')
        
        # Create Postman adapter if needed
        postman_adapter = None
        use_postman = args.postman or config.get('testing', {}).get('use_postman', False)
        
        if use_postman:
            postman_config = config.get('postman', {})
            newman_path = postman_config.get('newman_path', 'newman')
            collection_dir = postman_config.get('collection_dir', 'postman_collections')
            
            postman_adapter = PostmanAdapter(
                newman_path=newman_path,
                collection_output_dir=collection_dir
            )
        
        # Get API environment variables
        api_environment = config.get('api_environment', {})
        
        # Create test runner
        test_runner = TestRunner(
            base_url=base_url,
            postman_adapter=postman_adapter,
            api_environment=api_environment
        )
        
        # Run tests
        test_suite_result = test_runner.run_test_suite(test_cases)
        
        # 4. Generate report
        report_config = config.get('report', {})
        output_dir = args.output or report_config.get('output_dir', 'reports')
        
        report_generator = ReportGenerator(
            output_dir=output_dir,
            ai_client=ai_client
        )
        
        report = report_generator.generate_report(test_suite_result)
        
        # Generate HTML report if configured
        if report_config.get('generate_html', True):
            html_path = report_generator.generate_html_report(report)
            logger.info(f"HTML report saved to {html_path}")
        
        logger.info(f"Full workflow completed successfully: {test_suite_result.success_count} passed, "
                   f"{test_suite_result.failure_count} failed, {test_suite_result.error_count} errors")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in workflow: {str(e)}")
        return 1


def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config(args.config)
    
    # Create AI client
    ai_client = create_ai_client(config)
    
    # Execute the requested command
    if args.command == "extract":
        return run_extract_command(args, config, ai_client)
    elif args.command == "generate":
        return run_generate_command(args, config, ai_client)
    elif args.command == "test":
        return run_test_command(args, config, ai_client)
    elif args.command == "report":
        return run_report_command(args, config, ai_client)
    elif args.command == "env":
        return run_env_command(args, config, ai_client)
    elif args.command == "run":
        return run_full_workflow(args, config, ai_client)


if __name__ == "__main__":
    sys.exit(main())
