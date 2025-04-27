from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class TestCaseType(Enum):
    # Happy path test cases
    HAPPY_PATH = "happy_path"
    REQUIRED_PARAMS_ONLY = "required_params_only"
    PARTIAL_OPTIONAL_PARAMS = "partial_optional_params"
    ALL_PARAMS = "all_params"
    
    # Data type specific tests
    DATA_TYPE_NUMBER = "data_type_number"
    DATA_TYPE_STRING = "data_type_string"
    DATA_TYPE_BOOLEAN = "data_type_boolean"
    DATA_TYPE_ARRAY = "data_type_array"
    DATA_TYPE_OBJECT = "data_type_object"
    
    # Missing parameter tests
    MISSING_PARAM = "missing_param"
    
    # Invalid type tests
    INVALID_TYPE_NUMBER = "invalid_type_number"
    INVALID_TYPE_STRING = "invalid_type_string"
    INVALID_TYPE_BOOLEAN = "invalid_type_boolean"
    INVALID_TYPE_ARRAY = "invalid_type_array"
    INVALID_TYPE_OBJECT = "invalid_type_object"
    
    # Boundary value tests for numeric parameters
    NUMERIC_BOUNDARY_MAX = "numeric_boundary_max"
    NUMERIC_BOUNDARY_MIN = "numeric_boundary_min"
    NUMERIC_BOUNDARY_ZERO = "numeric_boundary_zero"
    NUMERIC_BOUNDARY_NEGATIVE = "numeric_boundary_negative"
    NUMERIC_BOUNDARY_DECIMAL = "numeric_boundary_decimal"
    NUMERIC_BOUNDARY_LARGE = "numeric_boundary_large"
    
    # Boundary value tests for string parameters
    STRING_BOUNDARY_EMPTY = "string_boundary_empty"
    STRING_BOUNDARY_LONG = "string_boundary_long"
    STRING_BOUNDARY_SPECIAL_CHARS = "string_boundary_special_chars"
    STRING_BOUNDARY_SPACES = "string_boundary_spaces"
    STRING_BOUNDARY_EMOJI = "string_boundary_emoji"
    STRING_BOUNDARY_MULTILINGUAL = "string_boundary_multilingual"
    STRING_BOUNDARY_NUMERIC = "string_boundary_numeric"
    
    # Format error tests
    INVALID_FORMAT_DATE = "invalid_format_date"
    INVALID_FORMAT_EMAIL = "invalid_format_email"
    INVALID_FORMAT_URL = "invalid_format_url"
    INVALID_FORMAT_JSON = "invalid_format_json"
    INVALID_FORMAT_PHONE = "invalid_format_phone"
    
    # Combination tests
    COMBINATION = "combination"
    
    # Special case tests
    IDEMPOTENCY = "idempotency"
    PERFORMANCE = "performance"
    CACHE = "cache"
    SECURITY = "security"
    
    # Documentation validation tests
    DOC_VALIDATION = "doc_validation"
    OPENAPI_SPEC = "openapi_spec"


class ValidationType(Enum):
    STATUS_CODE = "status_code"
    JSON_FIELD = "json_field"  
    JSON_FIELD_EXISTS = "json_field_exists"
    RESPONSE_TIME = "response_time"
    JSON_SCHEMA = "json_schema"
    HEADER = "header"
    CONTENT_TYPE = "content_type"


@dataclass
class Validation:
    """Represents a validation to perform on the API response"""
    type: ValidationType
    field: Optional[str] = None
    expected: Optional[Any] = None
    description: Optional[str] = None


@dataclass
class TestCase:
    """Represents an API test case"""
    name: str
    description: str
    method: str
    path: str
    test_type: TestCaseType
    
    # Request data
    request_data: Dict[str, Any] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    path_params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Expected results
    expected_status: int = 200
    validations: List[Validation] = field(default_factory=list)
    
    # Test metadata
    base_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the test case to a dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "method": self.method,
            "path": self.path,
            "test_type": self.test_type.value,
            "request_data": self.request_data,
            "query_params": self.query_params,
            "path_params": self.path_params,
            "headers": self.headers,
            "expected_status": self.expected_status,
            "validations": [
                {
                    "type": v.type.value,
                    "field": v.field,
                    "expected": v.expected,
                    "description": v.description
                } for v in self.validations
            ],
            "base_url": self.base_url,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create a TestCase from a dictionary representation"""
        # Process validations
        validations = []
        for v in data.get("validations", []):
            validations.append(Validation(
                type=ValidationType(v.get("type")),
                field=v.get("field"),
                expected=v.get("expected"),
                description=v.get("description")
            ))
        
        # Return the test case
        return cls(
            name=data.get("name", "Unnamed Test"),
            description=data.get("description", ""),
            method=data.get("method", "GET"),
            path=data.get("path", "/"),
            test_type=TestCaseType(data.get("test_type", "happy_path")),
            request_data=data.get("request_data", {}),
            query_params=data.get("query_params", {}),
            path_params=data.get("path_params", {}),
            headers=data.get("headers", {}),
            expected_status=data.get("expected_status", 200),
            validations=validations,
            base_url=data.get("base_url"),
            tags=data.get("tags", [])
        )


@dataclass
class TestCaseCollection:
    """Collection of test cases for an API"""
    name: str
    description: str
    test_cases: List[TestCase] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the test case collection to a dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "test_cases": [tc.to_dict() for tc in self.test_cases]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCaseCollection':
        """Create a TestCaseCollection from a dictionary representation"""
        test_cases = [TestCase.from_dict(tc) for tc in data.get("test_cases", [])]
        
        return cls(
            name=data.get("name", "Unnamed Collection"),
            description=data.get("description", ""),
            test_cases=test_cases
        ) 