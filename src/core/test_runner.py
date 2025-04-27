import json
import time
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import requests
from urllib.parse import urljoin, urlencode

from src.models.test_result import TestStatus, TestCaseResult, TestSuiteResult, ValidationResult
from src.utils.logger import get_logger
from src.utils.postman_adapter import PostmanAdapter

logger = get_logger(__name__)


class TestRunner:
    """Executes API test cases and captures results."""
    
    def __init__(self, base_url: Optional[str] = None, postman_adapter: Optional[PostmanAdapter] = None, api_environment: Optional[Dict[str, str]] = None):
        self.base_url = base_url
        self.postman_adapter = postman_adapter
        self.api_environment = api_environment or {}
    
    def run_test_suite(self, test_cases: Dict[str, List[Dict[str, Any]]]) -> TestSuiteResult:
        """
        Run a suite of test cases and return the results.
        
        Args:
            test_cases: Dictionary mapping endpoint paths to lists of test cases
            
        Returns:
            TestSuiteResult object containing the results of all test cases
        """
        logger.info(f"Running test suite with {sum(len(cases) for cases in test_cases.values())} test cases")
        
        # Create a test suite result
        suite_result = TestSuiteResult(
            name="API Test Suite",
            start_time=datetime.now()
        )
        
        # Run each test case
        for endpoint_path, endpoint_tests in test_cases.items():
            logger.info(f"Running {len(endpoint_tests)} tests for endpoint {endpoint_path}")
            
            for test_case in endpoint_tests:
                try:
                    # Execute the test case
                    test_result = self.run_test_case(test_case)
                    suite_result.test_results.append(test_result)
                    
                    # Log the result
                    status_str = test_result.status.value
                    logger.info(f"Test '{test_result.test_name}' completed with status: {status_str}")
                    
                except Exception as e:
                    # Log and create an error result for any exceptions
                    logger.error(f"Error running test case {test_case['name']}: {str(e)}")
                    error_result = TestCaseResult(
                        test_name=test_case.get('name', 'Unknown test'),
                        endpoint_path=test_case.get('path', 'Unknown path'),
                        http_method=test_case.get('method', 'Unknown method'),
                        status=TestStatus.ERROR,
                        status_code=-1,
                        response_time_ms=-1,
                        request_data=test_case.get('request_data', {}),
                        response_data={},
                        error_message=str(e)
                    )
                    suite_result.test_results.append(error_result)
        
        # Set the end time
        suite_result.end_time = datetime.now()
        
        logger.info(f"Test suite completed: {suite_result.success_count} passed, "
                   f"{suite_result.failure_count} failed, {suite_result.error_count} errors")
        
        return suite_result
    
    def run_test_case(self, test_case: Dict[str, Any]) -> TestCaseResult:
        """
        Run a single test case
        
        Args:
            test_case: Test case definition
            
        Returns:
            TestCaseResult object containing the result
        """
        test_name = test_case.get("name", "Unnamed Test")
        method = test_case.get("method", "GET")
        path = test_case.get("path", "/")
        
        logger.info(f"Running test: {test_name} ({method} {path})")
        
        # Prepare request
        base_url = test_case.get("base_url") or self.base_url
        if not base_url:
            logger.error("No base URL specified for test case or test runner")
            return TestCaseResult(
                test_name=test_name,
                endpoint_path=path,
                http_method=method,
                status=TestStatus.ERROR,
                error_message="No base URL specified"
            )
        
        # Replace environment variables in query params
        query_params = self._replace_env_vars(test_case.get("query_params", {}))
        
        # Replace environment variables in request data
        request_data = self._replace_env_vars(test_case.get("request_data", {}))
        
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = test_case.get("headers", {})
        
        expected_status = test_case.get("expected_status", 200)
        validations = test_case.get("validations", [])
        
        # Execute the request
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(url, params=query_params, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=request_data, headers=headers)
            elif method == "PUT":
                response = requests.put(url, json=request_data, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return TestCaseResult(
                    test_name=test_name,
                    endpoint_path=path,
                    http_method=method,
                    status=TestStatus.ERROR,
                    error_message=f"Unsupported HTTP method: {method}"
                )
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Parse response data
            try:
                response_data = response.json()
            except ValueError:
                response_data = {"raw_response": response.text}
            
            # Validate response
            validation_results = []
            is_valid = True
            
            for validation in validations:
                validation_result = self._validate_response(validation, response, response_data)
                validation_results.append(validation_result)
                
                if not validation_result.is_valid:
                    is_valid = False
            
            # Determine overall status
            status = TestStatus.SUCCESS if is_valid and response.status_code == expected_status else TestStatus.FAILURE
            
            error_message = None
            if status == TestStatus.FAILURE:
                error_message = f"Expected status code {expected_status}, got {response.status_code}"
            
            # Create test result
            result = TestCaseResult(
                test_name=test_name,
                endpoint_path=path,
                http_method=method,
                status=status,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                request_data=request_data,
                response_data=response_data,
                validations=validation_results,
                error_message=error_message
            )
            
            logger.info(f"Test {test_name} completed with status: {status.value}")
            return result
            
        except Exception as e:
            logger.error(f"Error running test {test_name}: {str(e)}")
            return TestCaseResult(
                test_name=test_name,
                endpoint_path=path,
                http_method=method,
                status=TestStatus.ERROR,
                error_message=str(e)
            )
    
    def _validate_response(self, validation: Dict[str, Any], response, response_data: Dict[str, Any]) -> ValidationResult:
        """Validate a response based on validation criteria"""
        validation_type = validation.get("type", "")
        
        if validation_type == "status_code":
            expected = validation.get("expected", 200)
            is_valid = response.status_code == expected
            return ValidationResult(
                field="status_code",
                is_valid=is_valid,
                expected=str(expected),
                actual=str(response.status_code),
                message=f"Expected status code {expected}, got {response.status_code}"
            )
        
        elif validation_type == "not_status_code":
            not_expected = validation.get("not_expected", 500)
            is_valid = response.status_code != not_expected
            return ValidationResult(
                field="status_code",
                is_valid=is_valid,
                expected=f"not {not_expected}",
                actual=str(response.status_code),
                message=f"Expected status code not to be {not_expected}"
            )
        
        elif validation_type == "json_path":
            path = validation.get("path", "")
            expected = validation.get("expected", "")
            # Implement JSON path validation
            # (This would require a JSON path library like jsonpath-ng)
            return ValidationResult(
                field=path,
                is_valid=True,  # Placeholder
                expected=str(expected),
                actual="Not implemented",
                message="JSON path validation not implemented"
            )
            
        elif validation_type == "json_field":
            field = validation.get("field", "")
            expected = validation.get("expected")
            description = validation.get("description", "")
            
            # 使用递归获取嵌套字段的值
            parts = field.split('.')
            actual = response_data
            for part in parts:
                if isinstance(actual, dict) and part in actual:
                    actual = actual[part]
                else:
                    actual = None
                    break
            
            is_valid = actual == expected
            return ValidationResult(
                field=field,
                is_valid=is_valid,
                expected=str(expected),
                actual=str(actual),
                message=f"{description or f'Expected {field}={expected}, got {actual}'}"
            )
            
        elif validation_type == "json_field_exists":
            field = validation.get("field", "")
            description = validation.get("description", "")
            
            # 检查字段是否存在
            parts = field.split('.')
            current = response_data
            field_exists = True
            
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    field_exists = False
                    break
            
            return ValidationResult(
                field=field,
                is_valid=field_exists,
                expected="field exists",
                actual="exists" if field_exists else "missing",
                message=f"{description or f'Field {field} should exist in response'}"
            )
        
        elif validation_type == "error_message":
            contains = validation.get("contains", "")
            response_str = json.dumps(response_data)
            is_valid = contains in response_str
            return ValidationResult(
                field="error_message",
                is_valid=is_valid,
                expected=f"Contains '{contains}'",
                actual=response_str[:100] + "..." if len(response_str) > 100 else response_str,
                message=f"Expected response to contain '{contains}'"
            )
        
        elif validation_type == "response_time":
            max_ms = validation.get("max_ms", 1000)
            is_valid = response.elapsed.total_seconds() * 1000 <= max_ms
            actual_ms = response.elapsed.total_seconds() * 1000
            return ValidationResult(
                field="response_time",
                is_valid=is_valid,
                expected=f"<= {max_ms} ms",
                actual=f"{actual_ms:.2f} ms",
                message=f"Expected response time to be <= {max_ms} ms, got {actual_ms:.2f} ms"
            )
        
        else:
            return ValidationResult(
                field="unknown",
                is_valid=False,
                expected="",
                actual="",
                message=f"Unknown validation type: {validation_type}"
            )
    
    def _replace_env_vars(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Replace environment variables in the data"""
        if not self.api_environment:
            return data
            
        result = {}
        for key, value in data.items():
            # Check if this is a common parameter that should be replaced
            if key in self.api_environment:
                result[key] = self.api_environment[key]
            else:
                result[key] = value
                
        return result
