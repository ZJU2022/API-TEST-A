from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union


@dataclass
class Parameter:
    name: str
    description: str
    required: bool = True
    type: str = "string"
    example: Optional[Any] = None
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


@dataclass
class RequestBody:
    content_type: str = "application/json"
    parameters: List[Parameter] = field(default_factory=list)
    example: Optional[Dict[str, Any]] = None
    schema: Optional[Dict[str, Any]] = None


@dataclass
class Response:
    status_code: int
    description: str
    content_type: str = "application/json"
    schema: Optional[Dict[str, Any]] = None
    example: Optional[Dict[str, Any]] = None


@dataclass
class Endpoint:
    path: str
    method: str
    description: str
    request_body: Optional[RequestBody] = None
    query_parameters: List[Parameter] = field(default_factory=list)
    path_parameters: List[Parameter] = field(default_factory=list)
    header_parameters: List[Parameter] = field(default_factory=list)
    responses: Dict[int, Response] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class APISchema:
    title: str
    description: str
    base_url: Optional[str] = None
    endpoints: List[Endpoint] = field(default_factory=list)
    version: str = "1.0.0"
