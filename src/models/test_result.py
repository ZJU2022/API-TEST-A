from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class TestStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    field: str
    is_valid: bool
    expected: Any
    actual: Any
    message: str


@dataclass
class TestCaseResult:
    test_name: str
    endpoint_path: str
    http_method: str
    status: TestStatus
    status_code: int
    response_time_ms: float
    request_data: Dict[str, Any]
    response_data: Dict[str, Any]
    validations: List[ValidationResult] = field(default_factory=list)
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TestSuiteResult:
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    test_results: List[TestCaseResult] = field(default_factory=list)
    
    @property
    def success_count(self) -> int:
        return sum(1 for result in self.test_results if result.status == TestStatus.SUCCESS)
    
    @property
    def failure_count(self) -> int:
        return sum(1 for result in self.test_results if result.status == TestStatus.FAILURE)
    
    @property
    def error_count(self) -> int:
        return sum(1 for result in self.test_results if result.status == TestStatus.ERROR)
    
    @property
    def skipped_count(self) -> int:
        return sum(1 for result in self.test_results if result.status == TestStatus.SKIPPED)
    
    @property
    def total_count(self) -> int:
        return len(self.test_results)
    
    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count
