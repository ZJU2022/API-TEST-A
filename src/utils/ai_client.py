import json
import time
import os
import requests
from typing import Dict, List, Any, Optional

import openai
from dotenv import load_dotenv

from src.models.api_schema import APISchema, Endpoint, Parameter, RequestBody, Response
from src.models.test_result import TestSuiteResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()


class AIClient:
    """Client for AI services that provides API extraction, test generation, and recommendations."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", 
                 provider: str = "openai", endpoint: Optional[str] = None):
        """
        Initialize the AI client.
        
        Args:
            api_key: API key (defaults to environment var)
            model: The model to use
            provider: AI provider (openai or local_llm)
            endpoint: Custom API endpoint for local models
        """
        self.provider = provider
        self.model = model
        self.endpoint = endpoint
        
        # 根据不同提供商设置API密钥
        if provider == "openai":
            # Get API key from environment if not provided
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("No API key provided. Set OPENAI_API_KEY environment variable or pass api_key.")
            
            openai.api_key = self.api_key
        elif provider == "local_llm":
            # 本地模型可能不需要API密钥
            self.api_key = api_key
            # 设置默认端点
            if not self.endpoint:
                self.endpoint = "http://localhost:8080/v1"
            logger.info(f"Using local LLM at endpoint: {self.endpoint}")
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
        
        logger.info(f"AI client initialized with provider: {provider}, model: {model}")
    
    def extract_api_schema(self, document_text: str) -> APISchema:
        """
        Extract API schema from document text using AI.
        
        Args:
            document_text: The text content of the API documentation
            
        Returns:
            APISchema object containing the extracted information
        """
        logger.info("Extracting API schema using AI")
        
        # Create the prompt for extraction
        prompt = self._create_extraction_prompt(document_text)
        
        try:
            # Call the API based on provider
            if self.provider == "openai":
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an API documentation expert. Extract the API schema from the provided documentation."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,  # Low temperature for more deterministic output
                    max_tokens=4000
                )
                api_schema_json = response.choices[0].message.content
            elif self.provider == "local_llm":
                # 调用本地模型API
                response = requests.post(
                    f"{self.endpoint}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an API documentation expert. Extract the API schema from the provided documentation."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 4000
                    }
                )
                response.raise_for_status()
                api_schema_json = response.json()["choices"][0]["message"]["content"]
            
            # Try to extract JSON from the response if it's not pure JSON
            api_schema_json = self._extract_json(api_schema_json)
            
            # Convert to APISchema object
            api_schema = self._parse_api_schema(api_schema_json)
            
            logger.info(f"Successfully extracted API schema with {len(api_schema.endpoints)} endpoints")
            return api_schema
            
        except Exception as e:
            logger.error(f"Error extracting API schema: {str(e)}")
            # Return a minimal schema as fallback
            return APISchema(
                title="Extraction Failed",
                description="Failed to extract API schema. Check logs for details.",
                endpoints=[]
            )
    
    def generate_test_cases(self, endpoint: Endpoint) -> List[Dict[str, Any]]:
        """
        Generate test cases for an API endpoint using AI.
        
        Args:
            endpoint: The API endpoint to generate test cases for
            
        Returns:
            List of test case dictionaries
        """
        logger.info(f"Generating test cases for endpoint: {endpoint.path}")
        
        # Create the prompt for test case generation
        prompt = self._create_test_gen_prompt(endpoint)
        
        try:
            # Call the API based on provider
            if self.provider == "openai":
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an API testing expert. Generate test cases for the given API endpoint."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # Slightly higher temperature for creative test cases
                    max_tokens=4000
                )
                test_cases_json = response.choices[0].message.content
            elif self.provider == "local_llm":
                # 调用本地模型API
                response = requests.post(
                    f"{self.endpoint}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an API testing expert. Generate test cases for the given API endpoint."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 4000
                    }
                )
                response.raise_for_status()
                test_cases_json = response.json()["choices"][0]["message"]["content"]
            
            # Try to extract JSON from the response if it's not pure JSON
            test_cases_json = self._extract_json(test_cases_json)
            
            # Parse the JSON
            test_cases = json.loads(test_cases_json)
            
            logger.info(f"Successfully generated {len(test_cases)} test cases")
            return test_cases
            
        except Exception as e:
            logger.error(f"Error generating test cases: {str(e)}")
            # Return a basic test case as fallback
            return [{
                "name": f"Basic test for {endpoint.path}",
                "description": "Auto-generated basic test case",
                "method": endpoint.method,
                "path": endpoint.path,
                "headers": {},
                "query_params": {},
                "request_data": {},
                "expected_status": 200,
                "validations": [
                    {
                        "type": "status_code",
                        "value": 200
                    }
                ]
            }]
    
    def generate_recommendations(self, test_result: TestSuiteResult) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on test results using AI.
        
        Args:
            test_result: The test suite result to analyze
            
        Returns:
            List of recommendations
        """
        logger.info("Generating recommendations based on test results")
        
        # Create the prompt for recommendation generation
        prompt = self._create_recommendation_prompt(test_result)
        
        try:
            # Call the API based on provider
            if self.provider == "openai":
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an API design and testing expert. Generate actionable recommendations based on the test results."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,
                    max_tokens=2000
                )
                recommendations_json = response.choices[0].message.content
            elif self.provider == "local_llm":
                # 调用本地模型API
                response = requests.post(
                    f"{self.endpoint}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an API design and testing expert. Generate actionable recommendations based on the test results."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.4,
                        "max_tokens": 2000
                    }
                )
                response.raise_for_status()
                recommendations_json = response.json()["choices"][0]["message"]["content"]
            
            # Try to extract JSON from the response if it's not pure JSON
            recommendations_json = self._extract_json(recommendations_json)
            
            # Parse the JSON
            recommendations = json.loads(recommendations_json)
            
            logger.info(f"Successfully generated {len(recommendations)} recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            # Return basic recommendations as fallback
            return [{
                "endpoint": "general",
                "severity": "low",
                "issue": "AI recommendation generation failed",
                "description": "The system couldn't generate AI-powered recommendations",
                "recommendation": "Check the logs for details and try again"
            }]
    
    def _create_extraction_prompt(self, document_text: str) -> str:
        """Create a prompt for API schema extraction"""
        return f"""
Please extract the API schema from the following documentation text. 
The output should be a valid JSON object with the following structure:
{{
    "title": "API name",
    "description": "Description of the API",
    "endpoints": [
        {{
            "path": "/api/v1/resource",
            "method": "GET|POST|PUT|DELETE",
            "description": "Description of what this endpoint does",
            "parameters": [
                {{
                    "name": "param1",
                    "description": "Description of the parameter",
                    "required": true,
                    "type": "string|number|boolean|object|array"
                }}
            ],
            "request_body": {{
                "parameters": [
                    {{
                        "name": "body_param1",
                        "description": "Description of the body parameter",
                        "required": true,
                        "type": "string|number|boolean|object|array"
                    }}
                ]
            }},
            "responses": [
                {{
                    "status_code": 200,
                    "description": "Success response description",
                    "content_type": "application/json",
                    "schema": {{
                        "type": "object",
                        "properties": {{
                            "property1": {{
                                "type": "string|number|boolean|object|array",
                                "description": "Description of the property"
                            }}
                        }}
                    }}
                }}
            ]
        }}
    ]
}}

Documentation Text:
{document_text}

Return only the JSON object, with no additional explanation.
"""
    
    def _create_test_gen_prompt(self, endpoint: Endpoint) -> str:
        """Create a prompt for test case generation"""
        endpoint_json = json.dumps(endpoint.__dict__, default=lambda o: o.__dict__, indent=2)
        
        return f"""
Please generate comprehensive test cases for the following API endpoint:

{endpoint_json}

The output should be a valid JSON array of test cases with the following structure:
[
    {{
        "name": "Test case name",
        "description": "Description of the test case",
        "method": "{endpoint.method}",
        "path": "{endpoint.path}",
        "headers": {{
            "header1": "value1"
        }},
        "query_params": {{
            "param1": "value1"
        }},
        "request_data": {{
            "field1": "value1"
        }},
        "expected_status": 200,
        "validations": [
            {{
                "type": "status_code",
                "value": 200
            }},
            {{
                "type": "json_path",
                "path": "$.field1",
                "expected_value": "value1"
            }},
            {{
                "type": "response_time",
                "max_ms": 1000
            }}
        ]
    }}
]

Generate at least 3 test cases:
1. A positive test case (happy path)
2. A test case with invalid/missing parameters
3. A test case with an edge case

Return only the JSON array, with no additional explanation.
"""
    
    def _create_recommendation_prompt(self, test_result: TestSuiteResult) -> str:
        """Create a prompt for recommendation generation"""
        results_json = json.dumps(test_result.__dict__, default=lambda o: o.__dict__, indent=2)
        
        return f"""
Please analyze the following API test results and generate recommendations for improving the API:

{results_json}

The output should be a valid JSON array of recommendations with the following structure:
[
    {{
        "endpoint": "The endpoint path or 'general' for overall recommendations",
        "severity": "high|medium|low",
        "issue": "Brief issue description",
        "description": "Detailed description of the issue",
        "recommendation": "Actionable recommendation to address the issue"
    }}
]

Focus on:
1. Failed tests and their causes
2. Performance issues
3. Security concerns
4. Usability improvements
5. Documentation gaps

Return only the JSON array, with no additional explanation.
"""
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that might contain explanations around it"""
        try:
            # Try to parse directly first
            json.loads(text)
            return text
        except:
            # If that fails, try to find JSON blocks
            import re
            json_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
            if json_blocks:
                for block in json_blocks:
                    try:
                        json.loads(block)
                        return block
                    except:
                        continue
            
            # If still no valid JSON, try to find { ... } blocks
            matches = re.findall(r'({[\s\S]*})', text)
            if matches:
                for match in matches:
                    try:
                        json.loads(match)
                        return match
                    except:
                        continue
            
            # Give up and return the original text
            return text
    
    def _parse_api_schema(self, api_schema_json: str) -> APISchema:
        """Parse the API schema JSON into an APISchema object"""
        try:
            schema_dict = json.loads(api_schema_json)
            
            # Extract basic information
            title = schema_dict.get('title', 'Untitled API')
            description = schema_dict.get('description', '')
            
            # Extract endpoints
            endpoints = []
            for endpoint_dict in schema_dict.get('endpoints', []):
                # Extract parameters
                parameters = []
                for param_dict in endpoint_dict.get('parameters', []):
                    param = Parameter(
                        name=param_dict.get('name', ''),
                        description=param_dict.get('description', ''),
                        required=param_dict.get('required', False),
                        type=param_dict.get('type', 'string')
                    )
                    parameters.append(param)
                
                # Extract request body
                request_body = None
                if 'request_body' in endpoint_dict:
                    body_params = []
                    for param_dict in endpoint_dict['request_body'].get('parameters', []):
                        param = Parameter(
                            name=param_dict.get('name', ''),
                            description=param_dict.get('description', ''),
                            required=param_dict.get('required', False),
                            type=param_dict.get('type', 'string')
                        )
                        body_params.append(param)
                    
                    request_body = RequestBody(
                        parameters=body_params
                    )
                
                # Extract responses
                responses = []
                for resp_dict in endpoint_dict.get('responses', []):
                    response = Response(
                        status_code=resp_dict.get('status_code', 200),
                        description=resp_dict.get('description', ''),
                        content_type=resp_dict.get('content_type', 'application/json'),
                        schema=resp_dict.get('schema', {})
                    )
                    responses.append(response)
                
                # Create endpoint
                endpoint = Endpoint(
                    path=endpoint_dict.get('path', ''),
                    method=endpoint_dict.get('method', 'GET'),
                    description=endpoint_dict.get('description', ''),
                    parameters=parameters,
                    request_body=request_body,
                    responses=responses
                )
                endpoints.append(endpoint)
            
            # Create API schema
            return APISchema(
                title=title,
                description=description,
                endpoints=endpoints
            )
        
        except Exception as e:
            logger.error(f"Error parsing API schema: {str(e)}")
            # Return a minimal schema as fallback
            return APISchema(
                title="Parsing Failed",
                description="Failed to parse API schema. Check logs for details.",
                endpoints=[]
            )
