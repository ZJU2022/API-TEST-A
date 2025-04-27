#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.models.test_result import TestStatus, TestCaseResult, ValidationResult, TestSuiteResult
from src.models.test_case import TestCase, TestCaseCollection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PostmanAdapter:
    """
    Adapter for converting structured test cases to Postman collections
    and handling Postman-related operations.
    """
    
    def __init__(self, newman_path: str = "newman", collection_output_dir: str = "postman_collections", api_environment: Optional[Dict[str, str]] = None):
        """
        Initialize the Postman adapter.
        
        Args:
            newman_path: Path to Newman CLI executable
            collection_output_dir: Directory to store generated Postman collections
            api_environment: Dictionary of environment variables for the API
        """
        self.newman_path = newman_path
        self.collection_output_dir = collection_output_dir
        self.api_environment = api_environment or {}
        
        # Create output directory if it doesn't exist
        os.makedirs(collection_output_dir, exist_ok=True)
        
        logger.info(f"Postman adapter initialized with Newman path: {newman_path}")
    
    def execute_test(self, test_case: Dict[str, Any]) -> TestCaseResult:
        """
        Execute a test case using Newman CLI.
        
        Args:
            test_case: The test case to execute
            
        Returns:
            TestCaseResult containing the test execution results
        """
        logger.info(f"Executing test case '{test_case['name']}' with Postman")
        
        try:
            # Convert test case to Postman collection
            collection = self._create_postman_collection(test_case)
            
            # Save collection to temporary file
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False, dir=self.collection_output_dir) as f:
                collection_path = f.name
                json.dump(collection, f)
            
            logger.info(f"Saved Postman collection to {collection_path}")
            
            # Execute Newman command
            result = self._run_newman(collection_path)
            
            # Convert Newman result to our test result format
            test_result = self._convert_newman_result(result, test_case)
            
            # Clean up temp file
            os.unlink(collection_path)
            
            return test_result
            
        except Exception as e:
            logger.error(f"Error executing test with Postman: {str(e)}")
            
            # Return an error result
            return TestCaseResult(
                test_name=test_case.get('name', 'Unknown test'),
                endpoint_path=test_case.get('path', 'Unknown path'),
                http_method=test_case.get('method', 'Unknown method'),
                status=TestStatus.ERROR,
                status_code=-1,
                response_time_ms=-1,
                request_data=test_case.get('request_data', {}),
                response_data={},
                error_message=f"Error executing test with Postman: {str(e)}"
            )
    
    def _create_postman_collection(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Convert test case to Postman collection format"""
        # Basic collection structure
        collection = {
            "info": {
                "name": f"Test: {test_case['name']}",
                "_postman_id": self._generate_uuid(),
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [
                {
                    "name": test_case['name'],
                    "request": {
                        "method": test_case['method'],
                        "header": [],
                        "url": {
                            "raw": self._build_raw_url(test_case),
                            "protocol": "http"
                        }
                    },
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "exec": self._generate_test_script(test_case),
                                "type": "text/javascript"
                            }
                        }
                    ]
                }
            ]
        }
        
        # Add headers
        for header_name, header_value in test_case.get('headers', {}).items():
            collection["item"][0]["request"]["header"].append({
                "key": header_name,
                "value": str(header_value),
                "type": "text"
            })
        
        # Add request body if present
        if test_case.get('request_data') and test_case['method'] in ['POST', 'PUT', 'PATCH']:
            collection["item"][0]["request"]["body"] = {
                "mode": "raw",
                "raw": json.dumps(test_case['request_data']),
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            }
        
        # Break down URL components
        url = collection["item"][0]["request"]["url"]
        
        # Base URL or host
        if test_case.get('base_url'):
            base_url = test_case['base_url'].rstrip('/')
            url_parts = base_url.split('://')
            if len(url_parts) > 1:
                url["protocol"] = url_parts[0]
                host_parts = url_parts[1].split('/')
                url["host"] = host_parts[0].split('.')
                if len(host_parts) > 1:
                    url["path"] = host_parts[1:]
            else:
                url["host"] = base_url.split('.')
        
        # Add path from test case
        path = test_case['path'].strip('/')
        if path:
            if "path" not in url:
                url["path"] = []
            url["path"].extend(path.split('/'))
        
        # Add query parameters
        if test_case.get('query_params'):
            url["query"] = []
            for key, value in test_case['query_params'].items():
                url["query"].append({
                    "key": key,
                    "value": str(value)
                })
        
        return collection
    
    def _build_raw_url(self, test_case: Dict[str, Any]) -> str:
        """Build a raw URL string for Postman"""
        base_url = test_case.get('base_url', '').rstrip('/')
        path = test_case['path']
        
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
        
        # Combine base URL and path
        url = base_url + path
        
        # Add query parameters if present
        if test_case.get('query_params'):
            query_string = '&'.join([f"{k}={v}" for k, v in test_case['query_params'].items()])
            url += f"?{query_string}"
        
        return url
    
    def _generate_test_script(self, test_case: Dict[str, Any]) -> List[str]:
        """Generate Postman test script based on validations"""
        script_lines = [
            "pm.test(\"Status code test\", function () {",
            f"    pm.response.to.have.status({test_case.get('expected_status', 200)});",
            "});"
        ]
        
        # Add custom validations
        for validation in test_case.get('validations', []):
            if validation.get('type') == 'json_path':
                field = validation.get('field')
                expected = validation.get('expected')
                
                # Handle different types of expected values
                if isinstance(expected, str):
                    expected_str = f"\"{expected}\""
                elif expected is None:
                    expected_str = "null"
                else:
                    expected_str = str(expected)
                
                script_lines.extend([
                    f"pm.test(\"Check {field}\", function () {{",
                    f"    var jsonData = pm.response.json();",
                    f"    pm.expect(jsonData.{field}).to.eql({expected_str});",
                    "});"
                ])
            
            elif validation.get('type') == 'error_message':
                contains = validation.get('contains')
                script_lines.extend([
                    f"pm.test(\"Error message contains '{contains}'\", function () {{",
                    f"    pm.expect(pm.response.text()).to.include(\"{contains}\");",
                    "});"
                ])
        
        return script_lines
    
    def _run_newman(self, collection_path: str) -> Dict[str, Any]:
        """Run Newman CLI command to execute the collection"""
        output_path = os.path.join(self.collection_output_dir, "newman_results.json")
        
        # Build the command
        cmd = [
            self.newman_path,
            "run", collection_path,
            "--reporters", "cli,json",
            "--reporter-json-export", output_path
        ]
        
        logger.info(f"Running Newman command: {' '.join(cmd)}")
        
        try:
            # Execute Newman
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Newman execution failed: {stderr}")
                raise Exception(f"Newman execution failed with code {process.returncode}: {stderr}")
            
            # Read the results file
            with open(output_path, 'r') as f:
                results = json.load(f)
            
            return results
            
        except Exception as e:
            logger.error(f"Error running Newman: {str(e)}")
            raise
    
    def _convert_newman_result(self, newman_result: Dict[str, Any], original_test_case: Dict[str, Any]) -> TestCaseResult:
        """Convert Newman results to our TestCaseResult format"""
        # Extract execution data
        execution = newman_result.get('run', {}).get('executions', [{}])[0]
        
        # Get response info
        response = execution.get('response', {})
        request = execution.get('request', {})
        
        # Determine test status
        newman_failures = execution.get('assertions', [])
        has_failures = any(not assertion.get('passed', False) for assertion in newman_failures)
        
        if has_failures:
            status = TestStatus.FAILURE
        else:
            status = TestStatus.SUCCESS
        
        # Extract response data
        try:
            response_data = json.loads(response.get('body', '{}'))
        except Exception:
            response_data = {"raw": response.get('body', '')}
        
        # Create test result
        test_result = TestCaseResult(
            test_name=original_test_case['name'],
            endpoint_path=original_test_case['path'],
            http_method=original_test_case['method'],
            status=status,
            status_code=response.get('code', 0),
            response_time_ms=execution.get('response', {}).get('responseTime', 0),
            request_data=original_test_case.get('request_data', {}),
            response_data=response_data
        )
        
        # Add validation results
        for assertion in newman_failures:
            validation = ValidationResult(
                field=assertion.get('assertion', "unknown"),
                is_valid=assertion.get('passed', False),
                expected=assertion.get('expected', ""),
                actual=assertion.get('actual', ""),
                message=assertion.get('error', {}).get('message', "Validation failed")
            )
            test_result.validations.append(validation)
        
        return test_result
    
    def _generate_uuid(self) -> str:
        """Generate a basic UUID for Postman collection ID"""
        return str(uuid.uuid4())

    def run_tests(self, test_cases: Dict[str, List[Dict[str, Any]]], base_url: Optional[str] = None) -> TestSuiteResult:
        """
        Run a suite of test cases using Postman/Newman
        
        Args:
            test_cases: Dictionary mapping endpoints to lists of test cases
            base_url: Base URL to use for requests
            
        Returns:
            TestSuiteResult object containing the results
        """
        logger.info(f"Running tests using Postman/Newman")
        
        # Create a Postman collection from the test cases
        collection = self._create_postman_collection(test_cases, base_url)
        
        # Create environment file with variables
        environment = self._create_environment_file()
        
        # Save collection to a file
        collection_path = os.path.join(self.collection_output_dir, f"collection_{self._get_timestamp()}.json")
        with open(collection_path, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
        # Save environment to a file if we have environment variables
        environment_path = None
        if environment:
            environment_path = os.path.join(self.collection_output_dir, f"environment_{self._get_timestamp()}.json")
            with open(environment_path, 'w', encoding='utf-8') as f:
                json.dump(environment, f, indent=2, ensure_ascii=False)
        
        # Generate result file path
        newman_result_path = os.path.join(self.collection_output_dir, f"newman_results_{self._get_timestamp()}.json")
        
        # Build Newman command
        command = [
            self.newman_path, 
            "run", 
            collection_path,
            "-r", "json,cli",
            "--reporter-json-export", newman_result_path,
            "--no-color"
        ]
        
        # Add environment file if it exists
        if environment_path:
            command.extend(["-e", environment_path])
        
        # Run Newman
        start_time = datetime.now()
        try:
            logger.info(f"Running Newman command: {' '.join(command)}")
            
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False  # Don't raise exception on non-zero exit
            )
            
            if process.returncode != 0:
                logger.warning(f"Newman exited with code {process.returncode}")
                logger.warning(f"Newman stderr: {process.stderr}")
            
            end_time = datetime.now()
            
            # Parse the results file
            if os.path.exists(newman_result_path):
                test_results = self._parse_newman_results(newman_result_path)
                
                # Create and return TestSuiteResult
                suite_result = TestSuiteResult(
                    name="Postman Test Suite",
                    start_time=start_time,
                    end_time=end_time,
                    test_results=test_results
                )
                
                return suite_result
            else:
                logger.error(f"Newman result file not found: {newman_result_path}")
                return TestSuiteResult(
                    name="Postman Test Suite (Failed)",
                    start_time=start_time,
                    end_time=end_time,
                    test_results=[]
                )
        
        except Exception as e:
            logger.error(f"Error running Newman: {str(e)}")
            end_time = datetime.now()
            
            return TestSuiteResult(
                name="Postman Test Suite (Error)",
                start_time=start_time,
                end_time=end_time,
                test_results=[]
            )
    
    def _create_postman_collection(self, test_cases: Dict[str, List[Dict[str, Any]]], base_url: Optional[str] = None) -> Dict[str, Any]:
        """Create a Postman collection from the test cases"""
        collection_id = str(uuid.uuid4())
        
        # Create collection structure
        collection = {
            "info": {
                "_postman_id": collection_id,
                "name": "API Test AI Generated Collection",
                "description": "Automatically generated test collection",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": []
        }
        
        # Add folder for each endpoint
        for endpoint, endpoint_tests in test_cases.items():
            endpoint_folder = {
                "name": endpoint,
                "item": []
            }
            
            # Add each test case as a request
            for test_case in endpoint_tests:
                request_item = self._create_postman_request(test_case, base_url)
                endpoint_folder["item"].append(request_item)
            
            collection["item"].append(endpoint_folder)
        
        return collection
    
    def _create_postman_request(self, test_case: Dict[str, Any], base_url: Optional[str] = None) -> Dict[str, Any]:
        """Create a Postman request item from a test case"""
        test_name = test_case.get("name", "Unnamed Test")
        method = test_case.get("method", "GET")
        path = test_case.get("path", "/")
        
        # Determine base URL
        url_base = test_case.get("base_url") or base_url or ""
        
        # Build URL
        url = f"{url_base.rstrip('/')}/{path.lstrip('/')}"
        
        # Create request object
        request = {
            "method": method,
            "header": [],
            "url": {
                "raw": url,
                "protocol": url.split("://")[0] if "://" in url else "",
                "host": url.split("://")[1].split("/")[0].split(".") if "://" in url else url.split("/")[0].split("."),
                "path": url.split("://")[1].split("/")[1:] if "://" in url and "/" in url.split("://")[1] else []
            }
        }
        
        # Add headers
        headers = test_case.get("headers", {})
        for header_name, header_value in headers.items():
            request["header"].append({
                "key": header_name,
                "value": header_value,
                "type": "text"
            })
        
        # Add query parameters
        query_params = test_case.get("query_params", {})
        if query_params:
            request["url"]["query"] = []
            
            for param_name, param_value in query_params.items():
                # Replace with environment variable if it's one of our common params
                if param_name in self.api_environment:
                    value = "{{" + param_name + "}}"
                else:
                    value = str(param_value)
                
                request["url"]["query"].append({
                    "key": param_name,
                    "value": value
                })
        
        # Add request body if needed
        request_data = test_case.get("request_data", {})
        if request_data and method in ["POST", "PUT", "PATCH"]:
            request["body"] = {
                "mode": "raw",
                "raw": json.dumps(request_data, ensure_ascii=False),
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            }
        
        # Create test script to validate response
        test_script = "pm.test(\"Status code test\", function() {\n"
        
        expected_status = test_case.get("expected_status", 200)
        test_script += f"    pm.response.to.have.status({expected_status});\n"
        
        # Add custom validations
        validations = test_case.get("validations", [])
        for validation in validations:
            validation_type = validation.get("type", "")
            
            if validation_type == "status_code":
                # Already handled above
                pass
            elif validation_type == "not_status_code":
                not_expected = validation.get("not_expected", 500)
                test_script += f"    pm.expect(pm.response.code).to.not.equal({not_expected});\n"
            elif validation_type == "json_path":
                path = validation.get("path", "")
                expected = validation.get("expected", "")
                test_script += f"    pm.expect(jsonPath.query(pm.response.json(), '{path}')[0]).to.eql({json.dumps(expected)});\n"
            elif validation_type == "error_message":
                contains = validation.get("contains", "")
                test_script += f"    pm.expect(pm.response.text()).to.include('{contains}');\n"
            elif validation_type == "response_time":
                max_ms = validation.get("max_ms", 1000)
                test_script += f"    pm.expect(pm.response.responseTime).to.be.below({max_ms});\n"
        
        test_script += "});"
        
        # Create the test item
        return {
            "name": test_name,
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": test_script.split("\n")
                    }
                }
            ],
            "request": request,
            "response": []
        }
    
    def _create_environment_file(self) -> Dict[str, Any]:
        """Create a Postman environment file from the environment variables"""
        if not self.api_environment:
            return {}
            
        environment = {
            "id": str(uuid.uuid4()),
            "name": "API-Test-AI Environment",
            "values": [],
            "_postman_variable_scope": "environment"
        }
        
        for key, value in self.api_environment.items():
            environment["values"].append({
                "key": key,
                "value": value,
                "enabled": True
            })
            
        return environment
    
    def _parse_newman_results(self, result_file_path: str) -> List[TestCaseResult]:
        """Parse Newman results from JSON file"""
        test_results = []
        
        try:
            with open(result_file_path, 'r', encoding='utf-8') as f:
                newman_results = json.load(f)
            
            # Get the run section
            run = newman_results.get("run", {})
            
            # Get all executions from all folders
            executions = []
            for item in run.get("executions", []):
                executions.append(item)
            
            # Create a TestCaseResult for each execution
            for execution in executions:
                item = execution.get("item", {})
                request = execution.get("request", {})
                response = execution.get("response", {})
                
                # Extract relevant information
                test_name = item.get("name", "Unnamed Test")
                method = request.get("method", "GET")
                url = request.get("url", {}).get("raw", "")
                path = "/" + "/".join(request.get("url", {}).get("path", []))
                
                # Get test script results
                assertions = execution.get("assertions", [])
                validations = []
                
                # Determine overall status
                status = TestStatus.SUCCESS
                error_message = None
                
                for assertion in assertions:
                    is_valid = assertion.get("skipped") != True
                    if not is_valid:
                        status = TestStatus.FAILURE
                        error_message = assertion.get("error", {}).get("message", "Assertion failed")
                    
                    validations.append(ValidationResult(
                        field=assertion.get("assertion", ""),
                        is_valid=is_valid,
                        expected="",
                        actual="",
                        message=assertion.get("error", {}).get("message", "")
                    ))
                
                # Create the TestCaseResult
                test_result = TestCaseResult(
                    test_name=test_name,
                    endpoint_path=path,
                    http_method=method,
                    status=status,
                    status_code=response.get("code", 0),
                    response_time_ms=response.get("responseTime", 0),
                    request_data=request.get("body", {}),
                    response_data=response.get("body", {}),
                    validations=validations,
                    error_message=error_message
                )
                
                test_results.append(test_result)
            
            return test_results
            
        except Exception as e:
            logger.error(f"Error parsing Newman results: {str(e)}")
            return []
    
    def _get_timestamp(self) -> str:
        """Get a timestamp string for file names"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def convert_collection_to_postman(self, collection: TestCaseCollection) -> Dict[str, Any]:
        """
        Convert a TestCaseCollection to Postman collection format
        
        Args:
            collection: The TestCaseCollection to convert
            
        Returns:
            Dictionary in Postman collection format
        """
        collection_id = str(uuid.uuid4())
        
        # Create collection structure
        postman_collection = {
            "info": {
                "_postman_id": collection_id,
                "name": collection.name,
                "description": collection.description,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": []
        }
        
        # Group test cases by endpoint
        endpoints = {}
        for test_case in collection.test_cases:
            endpoint_key = f"{test_case.method} {test_case.path}"
            if endpoint_key not in endpoints:
                endpoints[endpoint_key] = []
            endpoints[endpoint_key].append(test_case)
        
        # Create folders for each endpoint
        for endpoint_key, test_cases in endpoints.items():
            endpoint_folder = {
                "name": endpoint_key,
                "item": []
            }
            
            # Add test cases as requests
            for test_case in test_cases:
                request_item = self.create_postman_request(test_case)
                endpoint_folder["item"].append(request_item)
            
            postman_collection["item"].append(endpoint_folder)
        
        return postman_collection
    
    def create_postman_request(self, test_case: TestCase) -> Dict[str, Any]:
        """
        Create a Postman request item from a TestCase
        
        Args:
            test_case: The TestCase to convert
            
        Returns:
            Dictionary in Postman request format
        """
        # Extract interface name for Action parameter
        interface_name = test_case.path.split("/")[-1]
        
        # Create request object
        request = {
            "method": test_case.method,
            "header": [],
            "url": self.build_url_object(test_case.base_url, test_case.path)
        }
        
        # Add headers
        for header_name, header_value in test_case.headers.items():
            request["header"].append({
                "key": header_name,
                "value": str(header_value),
                "type": "text"
            })
        
        # Ensure Content-Type header exists
        content_type_exists = False
        for header in request["header"]:
            if header["key"].lower() == "content-type":
                header["value"] = "application/json"
                content_type_exists = True
                break
        
        if not content_type_exists:
            request["header"].append({
                "key": "Content-Type",
                "value": "application/json",
                "type": "text"
            })
        
        # Combine all parameters into request body (POST method)
        request_data = dict(test_case.request_data)
        
        # Add query parameters to request body
        for key, value in test_case.query_params.items():
            request_data[key] = value
        
        # Add Action parameter
        if interface_name:
            request_data["Action"] = interface_name
        
        # Add request body
        request["body"] = {
            "mode": "raw",
            "raw": json.dumps(request_data, ensure_ascii=False),
            "options": {
                "raw": {
                    "language": "json"
                }
            }
        }
        
        # Create test script for validations
        test_script = self.create_test_script(test_case)
        
        # Create the complete request item
        return {
            "name": test_case.name,
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": test_script.split("\n")
                    }
                }
            ],
            "request": request,
            "response": []
        }
    
    def build_url_object(self, base_url: Optional[str], path: str) -> Dict[str, Any]:
        """
        Build a Postman URL object
        
        Args:
            base_url: The base URL (can be None)
            path: The API path
            
        Returns:
            Dictionary in Postman URL format
        """
        url = f"{base_url.rstrip('/') if base_url else ''}/{path.lstrip('/')}"
        
        # Basic URL object
        url_object = {
            "raw": url
        }
        
        # Parse protocol
        if "://" in url:
            url_object["protocol"] = url.split("://")[0]
            host_and_path = url.split("://")[1]
        else:
            host_and_path = url
        
        # Parse host and path
        if "/" in host_and_path:
            host = host_and_path.split("/")[0]
            path_parts = host_and_path.split("/")[1:]
            url_object["host"] = host.split(".")
            if path_parts:
                url_object["path"] = path_parts
        else:
            url_object["host"] = host_and_path.split(".")
        
        return url_object
    
    def create_test_script(self, test_case: TestCase) -> str:
        """
        Create a Postman test script for validations
        
        Args:
            test_case: The TestCase with validations
            
        Returns:
            JavaScript test script as a string
        """
        # Start test script
        test_script = f"// Test script for {test_case.name}\n"
        test_script += "pm.test(\"Status code test\", function() {\n"
        test_script += f"    pm.response.to.have.status({test_case.expected_status});\n"
        test_script += "});\n\n"
        
        # Add validations
        for validation in test_case.validations:
            validation_type = validation.type.value if hasattr(validation.type, 'value') else validation.type
            
            if validation_type == "json_field":
                field = validation.field
                expected = validation.expected
                
                test_script += f"pm.test(\"{field} validation\", function() {{\n"
                test_script += f"    var jsonData = pm.response.json();\n"
                
                # Handle nested fields with dots
                if "." in field:
                    parts = field.split(".")
                    access_path = "jsonData"
                    for part in parts:
                        access_path += f"['{part}']"
                    test_script += f"    pm.expect({access_path}).to.eql({json.dumps(expected)});\n"
                else:
                    test_script += f"    pm.expect(jsonData['{field}']).to.eql({json.dumps(expected)});\n"
                
                test_script += "});\n\n"
                
            elif validation_type == "json_field_exists":
                field = validation.field
                
                test_script += f"pm.test(\"{field} exists\", function() {{\n"
                test_script += f"    var jsonData = pm.response.json();\n"
                
                # Handle nested fields with dots
                if "." in field:
                    parts = field.split(".")
                    access_path = "jsonData"
                    check_path = ""
                    for i, part in enumerate(parts):
                        access_path += f"['{part}']"
                        check_path += f"['{part}']"
                        if i < len(parts) - 1:
                            test_script += f"    pm.expect(jsonData{check_path}).to.be.an('object');\n"
                    
                    test_script += f"    pm.expect(jsonData{check_path}).to.exist;\n"
                else:
                    test_script += f"    pm.expect(jsonData['{field}']).to.exist;\n"
                
                test_script += "});\n\n"
                
            elif validation_type == "response_time":
                expected = validation.expected
                
                test_script += f"pm.test(\"Response time is acceptable\", function() {{\n"
                test_script += f"    pm.expect(pm.response.responseTime).to.be.below({expected});\n"
                test_script += "});\n\n"
                
            elif validation_type == "header":
                field = validation.field
                expected = validation.expected
                
                test_script += f"pm.test(\"Header {field} validation\", function() {{\n"
                test_script += f"    pm.response.to.have.header(\"{field}\");\n"
                if expected:
                    test_script += f"    pm.expect(pm.response.headers.get(\"{field}\")).to.eql(\"{expected}\");\n"
                test_script += "});\n\n"
        
        # Add generic response parsing test
        test_script += "pm.test(\"Response should be valid JSON\", function() {\n"
        test_script += "    pm.response.to.be.json;\n"
        test_script += "    var jsonData = pm.response.json();\n"
        test_script += "    pm.expect(jsonData).to.be.an('object');\n"
        test_script += "});\n"
        
        return test_script
    
    def save_collection_to_file(self, collection: Dict[str, Any], output_file: str) -> None:
        """
        Save a Postman collection to a file
        
        Args:
            collection: The Postman collection dictionary
            output_file: Path to the output file
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
    
    def convert_test_case_collection_to_postman_file(self, collection: TestCaseCollection, output_file: str) -> None:
        """
        Convert a TestCaseCollection to a Postman collection and save to file
        
        Args:
            collection: The TestCaseCollection to convert
            output_file: Path to the output file
        """
        postman_collection = self.convert_collection_to_postman(collection)
        self.save_collection_to_file(postman_collection, output_file)
    
    @staticmethod
    def load_collection_from_file(file_path: str) -> TestCaseCollection:
        """
        Load a TestCaseCollection from a JSON file
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            TestCaseCollection object
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return TestCaseCollection.from_dict(data)
