import json
import random
from typing import Dict, List, Any, Optional
import string
from datetime import datetime

from src.models.api_schema import APISchema, Endpoint, Parameter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TestCaseGenerator:
    """Generates test cases based on API schema information."""
    
    def __init__(self, ai_client=None):
        self.ai_client = ai_client
    
    def generate_test_cases(self, api_schema: APISchema) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate test cases for all endpoints in the API schema.
        
        Args:
            api_schema: The API schema to generate test cases for
            
        Returns:
            Dictionary mapping endpoint paths to lists of test cases
        """
        logger.info(f"Generating test cases for {len(api_schema.endpoints)} endpoints")
        
        test_cases = {}
        
        for endpoint in api_schema.endpoints:
            endpoint_key = f"{endpoint.method} {endpoint.path}"
            
            if self.ai_client:
                # Use AI to generate more sophisticated test cases
                endpoint_tests = self.ai_client.generate_test_cases(endpoint)
            else:
                # Use rule-based approach
                endpoint_tests = self._generate_tests_for_endpoint(endpoint, api_schema.base_url)
            
            test_cases[endpoint_key] = endpoint_tests
            logger.info(f"Generated {len(endpoint_tests)} test cases for {endpoint_key}")
        
        return test_cases
    
    def _generate_tests_for_endpoint(self, endpoint: Endpoint, base_url: Optional[str]) -> List[Dict[str, Any]]:
        """Generate test cases for a single endpoint using rule-based approach"""
        test_cases = []
        
        # 1. 正常路径测试 - 有效输入
        test_cases.append(self._create_happy_path_test(endpoint, base_url))
        
        # 2. 等价类测试
        # 2.1 全部必填参数测试
        test_cases.append(self._create_required_params_only_test(endpoint, base_url))
        
        # 2.2 部分选填参数测试
        test_cases.append(self._create_partial_optional_params_test(endpoint, base_url))
        
        # 2.3 所有参数测试（必填+选填）
        test_cases.append(self._create_all_params_test(endpoint, base_url))
        
        # 2.4 不同数据类型测试
        test_cases.append(self._create_data_type_test(endpoint, base_url, "number"))
        test_cases.append(self._create_data_type_test(endpoint, base_url, "string"))
        test_cases.append(self._create_data_type_test(endpoint, base_url, "boolean"))
        test_cases.append(self._create_data_type_test(endpoint, base_url, "array"))
        test_cases.append(self._create_data_type_test(endpoint, base_url, "object"))
        
        # 3. 边界值测试
        # 3.1 数值参数边界测试
        for param in self._get_all_parameters(endpoint):
            if param.type.lower() in ["integer", "number"]:
                test_cases.append(self._create_numeric_boundary_test(endpoint, param, base_url, "max"))
                test_cases.append(self._create_numeric_boundary_test(endpoint, param, base_url, "min"))
                test_cases.append(self._create_numeric_boundary_test(endpoint, param, base_url, "zero"))
                test_cases.append(self._create_numeric_boundary_test(endpoint, param, base_url, "negative"))
                test_cases.append(self._create_numeric_boundary_test(endpoint, param, base_url, "large"))
        
        # 3.2 字符串参数边界测试
        for param in self._get_all_parameters(endpoint):
            if param.type.lower() == "string":
                test_cases.append(self._create_string_boundary_test(endpoint, param, base_url, "empty"))
                test_cases.append(self._create_string_boundary_test(endpoint, param, base_url, "long"))
                test_cases.append(self._create_string_boundary_test(endpoint, param, base_url, "special"))
                test_cases.append(self._create_string_boundary_test(endpoint, param, base_url, "spaces"))
                test_cases.append(self._create_string_boundary_test(endpoint, param, base_url, "emoji"))
                test_cases.append(self._create_string_boundary_test(endpoint, param, base_url, "multilingual"))
        
        # 4. 异常测试
        # 4.1 缺失必填参数测试
        for param in self._get_all_parameters(endpoint):
            if param.required:
                test_cases.append(self._create_missing_param_test(endpoint, param, base_url))
        
        # 4.2 参数类型错误测试
        for param in self._get_all_parameters(endpoint):
            test_cases.append(self._create_invalid_type_test(endpoint, param, base_url))
        
        # 4.3 参数格式错误测试
        test_cases.append(self._create_invalid_format_test(endpoint, base_url, "date"))
        test_cases.append(self._create_invalid_format_test(endpoint, base_url, "json"))
        
        # 4.4 幂等性测试
        test_cases.append(self._create_idempotency_test(endpoint, base_url))
        
        # 5. 性能测试
        test_cases.append(self._create_performance_test(endpoint, base_url))
        
        # 6. 文档校验测试
        test_cases.append(self._create_doc_validation_test(endpoint, base_url))
        
        # 7. 组合测试
        test_cases.append(self._create_combination_test(endpoint, base_url))
        
        return test_cases
    
    def _get_all_parameters(self, endpoint: Endpoint) -> List[Parameter]:
        """获取端点的所有参数（请求体、查询和路径）"""
        all_params = []
        
        # 请求体参数
        if endpoint.request_body and endpoint.request_body.parameters:
            all_params.extend(endpoint.request_body.parameters)
        
        # 查询参数
        all_params.extend(endpoint.query_parameters)
        
        # 路径参数
        all_params.extend(endpoint.path_parameters)
        
        return all_params
    
    def _create_happy_path_test(self, endpoint: Endpoint, base_url: Optional[str]) -> Dict[str, Any]:
        """创建正常路径测试用例（有效输入）"""
        request_data = {}
        query_params = {}
        path_params = {}
        
        # 生成有效请求体（如果需要）
        if endpoint.request_body and endpoint.request_body.parameters:
            for param in endpoint.request_body.parameters:
                request_data[param.name] = self._generate_valid_value(param)
        
        # 生成有效查询参数
        for param in endpoint.query_parameters:
            query_params[param.name] = self._generate_valid_value(param)
        
        # 生成有效路径参数（替换路径中的 {param}）
        path = endpoint.path
        for param in endpoint.path_parameters:
            value = self._generate_valid_value(param)
            path_params[param.name] = value
            path = path.replace(f"{{{param.name}}}", str(value))
        
        # 创建UCloud API标准验证规则
        validations = [
            {"type": "status_code", "expected": 200},
            {"type": "json_field", "field": "RetCode", "expected": 0, "description": "UCloud API 成功响应代码必须为0"}
        ]
        
        # 添加响应字段验证，检查API文档中所需的Response Elements
        if endpoint.responses and "200" in endpoint.responses:
            response_desc = endpoint.responses["200"].description
            # 提取常见的响应字段名称
            common_fields = ["Action", "TotalCount", "DataSet"]
            for field in common_fields:
                if field in response_desc:
                    validations.append({
                        "type": "json_field_exists", 
                        "field": field, 
                        "description": f"检查响应中包含 {field} 字段"
                    })
        
        # 创建测试用例
        return {
            "name": f"正常请求测试 - {endpoint.path}",
            "description": f"测试所有参数均为有效值的情况 {endpoint.description}",
            "method": endpoint.method,
            "path": path,
            "base_url": base_url,
            "request_data": request_data,
            "query_params": query_params,
            "path_params": path_params,
            "headers": self._generate_headers(endpoint),
            "expected_status": 200,  # 假设正常路径状态码为 200
            "validations": validations
        }
    
    def _create_missing_param_test(self, endpoint: Endpoint, param: Parameter, base_url: Optional[str]) -> Dict[str, Any]:
        """创建缺少必需参数的测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 移除我们要测试的参数
        test_case["request_data"].pop(param.name, None)
        
        # 更新测试元数据
        test_case["name"] = f"缺少必需参数测试 - {param.name}"
        test_case["description"] = f"测试缺少必需参数 {param.name} 的情况"
        test_case["expected_status"] = 400  # 假设无效请求状态码为 400
        test_case["validations"] = [
            {"type": "status_code", "expected": 400},
            {"type": "error_message", "contains": param.name}  # 期望错误消息中包含缺少的参数名
        ]
        
        return test_case
    
    def _create_invalid_type_test(self, endpoint: Endpoint, param: Parameter, base_url: Optional[str]) -> Dict[str, Any]:
        """创建参数类型无效的测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 替换为无效类型
        test_case["request_data"][param.name] = self._generate_invalid_value(param)
        
        # 更新测试元数据
        test_case["name"] = f"参数类型无效测试 - {param.name}"
        test_case["description"] = f"测试参数 {param.name} 类型无效的情况"
        test_case["expected_status"] = 400  # 假设无效请求状态码为 400
        test_case["validations"] = [
            {"type": "status_code", "expected": 400},
            {"type": "error_message", "contains": param.name}  # 期望错误消息中包含参数名
        ]
        
        return test_case
    
    def _create_missing_query_param_test(self, endpoint: Endpoint, param: Parameter, base_url: Optional[str]) -> Dict[str, Any]:
        """创建缺少必需查询参数的测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 移除我们要测试的查询参数
        test_case["query_params"].pop(param.name, None)
        
        # 更新测试元数据
        test_case["name"] = f"缺少必需查询参数测试 - {param.name}"
        test_case["description"] = f"测试缺少必需查询参数 {param.name} 的情况"
        test_case["expected_status"] = 400  # 假设无效请求状态码为 400
        test_case["validations"] = [
            {"type": "status_code", "expected": 400},
            {"type": "error_message", "contains": param.name}  # 期望错误消息中包含缺少的参数名
        ]
        
        return test_case
    
    def _create_boundary_test(self, endpoint: Endpoint, base_url: Optional[str]) -> Dict[str, Any]:
        """创建边界条件测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 找到一个数字类型的参数
        number_param = None
        number_param_location = "body"
        
        if endpoint.request_body and endpoint.request_body.parameters:
            for param in endpoint.request_body.parameters:
                if param.type.lower() in ["integer", "number"]:
                    number_param = param
                    break
        
        if not number_param:
            for param in endpoint.query_parameters:
                if param.type.lower() in ["integer", "number"]:
                    number_param = param
                    number_param_location = "query"
                    break
        
        # 如果找到数字参数，设置为边界值
        if number_param:
            # 使用极大值
            boundary_value = 2147483647  # 32位整数最大值
            
            if number_param_location == "body":
                test_case["request_data"][number_param.name] = boundary_value
            else:
                test_case["query_params"][number_param.name] = boundary_value
            
            test_case["name"] = f"边界值测试 - {number_param.name} 最大值"
            test_case["description"] = f"测试参数 {number_param.name} 设置为边界最大值的情况"
        else:
            # 如果没有数字参数，则测试字符串长度
            string_param = None
            string_param_location = "body"
            
            if endpoint.request_body and endpoint.request_body.parameters:
                for param in endpoint.request_body.parameters:
                    if param.type.lower() == "string":
                        string_param = param
                        break
            
            if not string_param:
                for param in endpoint.query_parameters:
                    if param.type.lower() == "string":
                        string_param = param
                        string_param_location = "query"
                        break
            
            if string_param:
                # 使用长字符串
                long_string = "X" * 1000
                
                if string_param_location == "body":
                    test_case["request_data"][string_param.name] = long_string
                else:
                    test_case["query_params"][string_param.name] = long_string
                
                test_case["name"] = f"边界值测试 - {string_param.name} 长度极限"
                test_case["description"] = f"测试参数 {string_param.name} 长度达到极限的情况"
            else:
                test_case["name"] = "边界条件测试 - 通用"
                test_case["description"] = "测试API在处理边界条件时的表现"
        
        return test_case
    
    def _create_auth_test(self, endpoint: Endpoint, base_url: Optional[str]) -> Dict[str, Any]:
        """创建权限测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 删除或修改授权头
        headers = test_case["headers"]
        if "Authorization" in headers:
            headers.pop("Authorization")
        elif "X-Auth-Token" in headers:
            headers.pop("X-Auth-Token")
        else:
            # 如果没有明确的授权头，添加一个无效的
            headers["Authorization"] = "Invalid-Auth-Token"
        
        # 更新测试元数据
        test_case["name"] = "权限验证测试 - 无效授权"
        test_case["description"] = "测试使用无效授权时API的响应情况"
        test_case["expected_status"] = 401  # 假设未授权状态码为 401
        test_case["validations"] = [
            {"type": "status_code", "expected": 401},
            {"type": "error_message", "contains": "auth"}  # 期望错误消息中包含与授权相关的内容
        ]
        
        return test_case
    
    def _create_performance_test(self, endpoint: Endpoint, base_url: Optional[str]) -> Dict[str, Any]:
        """创建性能测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 更新测试元数据
        test_case["name"] = "性能测试 - 响应时间"
        test_case["description"] = "测试API在标准负载下的响应时间"
        test_case["expected_status"] = 200
        test_case["validations"] = [
            {"type": "status_code", "expected": 200},
            {"type": "response_time", "max_ms": 2000}  # 期望响应时间不超过2秒
        ]
        
        return test_case
    
    def _create_param_length_test(self, endpoint: Endpoint, param: Parameter, base_url: Optional[str]) -> Dict[str, Any]:
        """创建参数长度测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 如果是字符串类型参数，设置为空字符串
        if param.type.lower() == "string":
            test_case["request_data"][param.name] = ""
            
            # 更新测试元数据
            test_case["name"] = f"参数长度测试 - {param.name} 为空"
            test_case["description"] = f"测试参数 {param.name} 为空字符串的情况"
            
            # 如果是必需参数，期望失败，否则期望成功
            if param.required:
                test_case["expected_status"] = 400
                test_case["validations"] = [
                    {"type": "status_code", "expected": 400}
                ]
            else:
                test_case["expected_status"] = 200
                test_case["validations"] = [
                    {"type": "status_code", "expected": 200}
                ]
        else:
            # 如果不是字符串，使用默认值或最小值
            if param.type.lower() in ["integer", "number"]:
                test_case["request_data"][param.name] = 0
                
                # 更新测试元数据
                test_case["name"] = f"参数边界测试 - {param.name} 为零"
                test_case["description"] = f"测试参数 {param.name} 为零的情况"
            else:
                # 对于其他类型，不做特殊处理
                test_case["name"] = f"参数特殊值测试 - {param.name}"
                test_case["description"] = f"测试参数 {param.name} 使用特殊值的情况"
        
        return test_case
    
    def _create_fuzzy_query_param_test(self, endpoint: Endpoint, param: Parameter, base_url: Optional[str]) -> Dict[str, Any]:
        """创建查询参数模糊测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 根据参数类型，生成模糊测试值
        if param.type.lower() == "string":
            # 使用特殊字符
            test_case["query_params"][param.name] = "~!@#$%^&*()_+<>?:\"{}|[]\\;"
        elif param.type.lower() in ["integer", "number"]:
            # 使用非数字
            test_case["query_params"][param.name] = "not-a-number"
        elif param.type.lower() == "boolean":
            # 使用非布尔值
            test_case["query_params"][param.name] = "maybe"
        else:
            # 对于其他类型，使用随机字符串
            test_case["query_params"][param.name] = self._random_string(10)
        
        # 更新测试元数据
        test_case["name"] = f"查询参数模糊测试 - {param.name}"
        test_case["description"] = f"测试查询参数 {param.name} 使用模糊值的情况"
        
        # 对于模糊测试，期望API能够正确处理而不是崩溃
        test_case["expected_status"] = 400  # 假设返回400表示参数验证失败
        test_case["validations"] = [
            {"type": "not_status_code", "not_expected": 500}  # 不期望返回500错误
        ]
        
        return test_case
    
    def _create_combination_test(self, endpoint: Endpoint, base_url: Optional[str]) -> Dict[str, Any]:
        """创建组合测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 找到两个可以组合的参数
        params_to_combine = []
        
        # 首先检查请求体参数
        if endpoint.request_body and endpoint.request_body.parameters:
            for param in endpoint.request_body.parameters:
                if len(params_to_combine) < 2:
                    params_to_combine.append(("body", param))
        
        # 然后检查查询参数
        for param in endpoint.query_parameters:
            if len(params_to_combine) < 2:
                params_to_combine.append(("query", param))
        
        # 如果找到至少两个参数，进行组合测试
        if len(params_to_combine) >= 2:
            # 第一个参数使用有效值，第二个参数使用无效值
            location1, param1 = params_to_combine[0]
            location2, param2 = params_to_combine[1]
            
            if location1 == "body":
                test_case["request_data"][param1.name] = self._generate_valid_value(param1)
            else:
                test_case["query_params"][param1.name] = self._generate_valid_value(param1)
            
            if location2 == "body":
                test_case["request_data"][param2.name] = self._generate_invalid_value(param2)
            else:
                test_case["query_params"][param2.name] = self._generate_invalid_value(param2)
            
            # 更新测试元数据
            test_case["name"] = f"参数组合测试 - {param1.name} 有效 + {param2.name} 无效"
            test_case["description"] = f"测试参数 {param1.name} 为有效值，而 {param2.name} 为无效值的组合情况"
        else:
            # 如果没有足够的参数，简单修改测试名称
            test_case["name"] = "参数组合测试 - 通用"
            test_case["description"] = "测试API处理多个参数组合的情况"
        
        # 期望验证失败
        test_case["expected_status"] = 400
        test_case["validations"] = [
            {"type": "status_code", "expected": 400}
        ]
        
        return test_case
    
    def _create_required_params_only_test(self, endpoint: Endpoint, base_url: Optional[str]) -> Dict[str, Any]:
        """创建仅包含必填参数的测试用例"""
        request_data = {}
        query_params = {}
        path_params = {}
        
        # 只添加必填的请求体参数
        if endpoint.request_body and endpoint.request_body.parameters:
            for param in endpoint.request_body.parameters:
                if param.required:
                    request_data[param.name] = self._generate_valid_value(param)
        
        # 只添加必填的查询参数
        for param in endpoint.query_parameters:
            if param.required:
                query_params[param.name] = self._generate_valid_value(param)
        
        # 添加所有路径参数（路径参数总是必填的）
        path = endpoint.path
        for param in endpoint.path_parameters:
            value = self._generate_valid_value(param)
            path_params[param.name] = value
            path = path.replace(f"{{{param.name}}}", str(value))
        
        # 验证规则
        validations = [
            {"type": "status_code", "expected": 200},
            {"type": "json_field", "field": "RetCode", "expected": 0}
        ]
        
        # 创建测试用例
        return {
            "name": f"仅必填参数测试 - {endpoint.path}",
            "description": f"测试仅提供必填参数的情况",
            "method": endpoint.method,
            "path": path,
            "base_url": base_url,
            "request_data": request_data,
            "query_params": query_params,
            "path_params": path_params,
            "headers": self._generate_headers(endpoint),
            "expected_status": 200,
            "validations": validations
        }
    
    def _create_partial_optional_params_test(self, endpoint: Endpoint, base_url: Optional[str]) -> Dict[str, Any]:
        """创建包含部分选填参数的测试用例"""
        # 从仅必填参数测试开始
        test_case = self._create_required_params_only_test(endpoint, base_url)
        
        # 添加部分选填参数（约50%）
        optional_params = []
        
        # 收集所有选填参数
        if endpoint.request_body and endpoint.request_body.parameters:
            for param in endpoint.request_body.parameters:
                if not param.required:
                    optional_params.append(param)
        
        for param in endpoint.query_parameters:
            if not param.required:
                optional_params.append(param)
        
        # 随机选择大约一半的选填参数
        if optional_params:
            selected_count = max(1, len(optional_params) // 2)
            selected_params = random.sample(optional_params, selected_count)
            
            for param in selected_params:
                value = self._generate_valid_value(param)
                
                # 添加到请求体或查询参数
                if endpoint.request_body and param in endpoint.request_body.parameters:
                    test_case["request_data"][param.name] = value
                else:
                    test_case["query_params"][param.name] = value
        
        # 更新测试元数据
        test_case["name"] = f"部分选填参数测试 - {endpoint.path}"
        test_case["description"] = f"测试提供必填参数和部分选填参数的情况"
        
        return test_case
    
    def _create_all_params_test(self, endpoint: Endpoint, base_url: Optional[str]) -> Dict[str, Any]:
        """创建包含所有参数（必填和选填）的测试用例"""
        request_data = {}
        query_params = {}
        path_params = {}
        
        # 添加所有请求体参数
        if endpoint.request_body and endpoint.request_body.parameters:
            for param in endpoint.request_body.parameters:
                request_data[param.name] = self._generate_valid_value(param)
        
        # 添加所有查询参数
        for param in endpoint.query_parameters:
            query_params[param.name] = self._generate_valid_value(param)
        
        # 添加所有路径参数
        path = endpoint.path
        for param in endpoint.path_parameters:
            value = self._generate_valid_value(param)
            path_params[param.name] = value
            path = path.replace(f"{{{param.name}}}", str(value))
        
        # 验证规则
        validations = [
            {"type": "status_code", "expected": 200},
            {"type": "json_field", "field": "RetCode", "expected": 0}
        ]
        
        # 创建测试用例
        return {
            "name": f"所有参数测试 - {endpoint.path}",
            "description": f"测试提供所有参数（必填和选填）的情况",
            "method": endpoint.method,
            "path": path,
            "base_url": base_url,
            "request_data": request_data,
            "query_params": query_params,
            "path_params": path_params,
            "headers": self._generate_headers(endpoint),
            "expected_status": 200,
            "validations": validations
        }
    
    def _create_data_type_test(self, endpoint: Endpoint, base_url: Optional[str], data_type: str) -> Dict[str, Any]:
        """创建特定数据类型参数的测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 查找指定类型的参数
        target_params = []
        for param in self._get_all_parameters(endpoint):
            if param.type.lower() == data_type or (data_type == "number" and param.type.lower() == "integer"):
                target_params.append(param)
        
        # 如果没有找到该类型的参数，返回原始测试用例
        if not target_params:
            test_case["name"] = f"无{data_type}类型参数测试 - {endpoint.path}"
            test_case["description"] = f"API没有{data_type}类型参数，使用普通参数进行测试"
            return test_case
        
        # 随机选择一个目标参数进行特别处理
        target_param = random.choice(target_params)
        
        # 根据数据类型生成特殊值
        if data_type == "number" or data_type == "integer":
            value = 42  # 一个普通数字
        elif data_type == "string":
            value = "测试字符串Value_123"  # 包含中文、英文和数字
        elif data_type == "boolean":
            value = True
        elif data_type == "array":
            value = ["item1", "item2", "item3"]
        elif data_type == "object":
            value = {"key1": "value1", "key2": 2, "nested": {"inner": "value"}}
        else:
            value = self._generate_valid_value(target_param)
        
        # 更新参数值
        param_name = target_param.name
        if endpoint.request_body and param_name in test_case["request_data"]:
            test_case["request_data"][param_name] = value
        elif param_name in test_case["query_params"]:
            test_case["query_params"][param_name] = value
        
        # 更新测试元数据
        test_case["name"] = f"{data_type}类型参数测试 - {param_name}"
        test_case["description"] = f"测试{data_type}类型参数 {param_name} 的处理"
        
        return test_case
    
    def _generate_valid_value(self, param: Parameter) -> Any:
        """根据参数类型生成有效值"""
        # 对于常用的环境变量参数，使用环境变量占位符
        if param.name in ['Region', 'Zone', 'ProjectId']:
            return f"{{{{ {param.name} }}}}"
            
        # 使用示例（如果有）
        if param.example is not None:
            return param.example
        
        # 使用默认值（如果有）
        if param.default is not None:
            return param.default
            
        # 根据类型生成
        param_type = param.type.lower()
        
        if param_type == "string":
            return f"test_{param.name}_{self._random_string(5)}"
        elif param_type == "integer" or param_type == "number":
            return random.randint(1, 100)
        elif param_type == "boolean":
            return random.choice([True, False])
        elif param_type == "array":
            return [self._random_string(5) for _ in range(2)]
        elif param_type == "object":
            return {"key": self._random_string(5)}
        elif param_type == "date" or param_type == "datetime":
            return datetime.now().isoformat()
        else:
            return f"test_value_{param.name}"
    
    def _generate_invalid_value(self, param: Parameter) -> Any:
        """根据参数类型生成无效值"""
        param_type = param.type.lower()
        
        if param_type == "string":
            return random.randint(1, 100)  # 数字而非字符串
        elif param_type == "integer" or param_type == "number":
            return f"not_a_number_{self._random_string(3)}"  # 字符串而非数字
        elif param_type == "boolean":
            return "not_a_boolean"  # 字符串而非布尔值
        elif param_type == "array":
            return {"not": "an_array"}  # 对象而非数组
        elif param_type == "object":
            return "not_an_object"  # 字符串而非对象
        elif param_type == "date" or param_type == "datetime":
            return "not_a_date"  # 无效日期格式
        else:
            return None  # 对其他类型使用 null
    
    def _generate_headers(self, endpoint: Endpoint) -> Dict[str, str]:
        """根据端点生成请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 添加所需的头参数
        for param in endpoint.header_parameters:
            if param.required:
                headers[param.name] = self._generate_valid_value(param)
        
        return headers
    
    def _random_string(self, length: int) -> str:
        """生成指定长度的随机字符串"""
        return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
    
    def _create_numeric_boundary_test(self, endpoint: Endpoint, param: Parameter, base_url: Optional[str], boundary_type: str) -> Dict[str, Any]:
        """创建数值参数边界测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 根据边界类型生成边界值
        if boundary_type == "max":
            # 最大值+1
            value = 2147483648  # INT_MAX + 1
        elif boundary_type == "min":
            # 最小值-1
            value = -2147483649  # INT_MIN - 1
        elif boundary_type == "zero":
            # 零值
            value = 0
        elif boundary_type == "negative":
            # 负值
            value = -1
        elif boundary_type == "large":
            # 超大值
            value = 9223372036854775808  # LONG_MAX + 1
        else:
            # 默认边界测试
            value = 99999
        
        # 更新参数值
        param_name = param.name
        if endpoint.request_body and param.name in test_case["request_data"]:
            test_case["request_data"][param_name] = value
        elif param_name in test_case["query_params"]:
            test_case["query_params"][param_name] = value
        
        # 决定期望的响应
        should_accept = boundary_type in ["zero"]  # 通常零值应该被接受
        
        if should_accept:
            expected_status = 200
            validations = [
                {"type": "status_code", "expected": 200},
                {"type": "json_field", "field": "RetCode", "expected": 0}
            ]
        else:
            expected_status = 400
            validations = [
                {"type": "status_code", "expected": 400}
            ]
        
        # 更新测试元数据
        test_case["name"] = f"数值边界测试({boundary_type}) - {param_name}"
        test_case["description"] = f"测试数值参数 {param_name} 的{boundary_type}边界值"
        test_case["expected_status"] = expected_status
        test_case["validations"] = validations
        
        return test_case
    
    def _create_string_boundary_test(self, endpoint: Endpoint, param: Parameter, base_url: Optional[str], boundary_type: str) -> Dict[str, Any]:
        """创建字符串参数边界测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 根据边界类型生成边界值
        if boundary_type == "empty":
            # 空字符串
            value = ""
        elif boundary_type == "long":
            # 超长字符串
            value = "a" * 10000
        elif boundary_type == "special":
            # 特殊字符
            value = "!@#$%^&*()_+<>?:\"{}|~`-=[]\\;',./"
        elif boundary_type == "spaces":
            # 空格首尾
            value = "  带有空格的字符串  "
        elif boundary_type == "emoji":
            # Emoji字符
            value = "测试😀🚀💯🌟🔥"
        elif boundary_type == "multilingual":
            # 多语言字符
            value = "English 中文 日本語 Español Русский العربية"
        else:
            # 默认边界测试
            value = "DefaultBoundaryTest"
        
        # 更新参数值
        param_name = param.name
        if endpoint.request_body and param.name in test_case["request_data"]:
            test_case["request_data"][param_name] = value
        elif param_name in test_case["query_params"]:
            test_case["query_params"][param_name] = value
        
        # 决定期望的响应
        should_accept = boundary_type in ["spaces", "multilingual"]  # 通常空格和多语言应该被接受
        
        if should_accept:
            expected_status = 200
            validations = [
                {"type": "status_code", "expected": 200},
                {"type": "json_field", "field": "RetCode", "expected": 0}
            ]
        else:
            expected_status = 400
            validations = [
                {"type": "status_code", "expected": 400}
            ]
        
        # 更新测试元数据
        test_case["name"] = f"字符串边界测试({boundary_type}) - {param_name}"
        test_case["description"] = f"测试字符串参数 {param_name} 的{boundary_type}边界值"
        test_case["expected_status"] = expected_status
        test_case["validations"] = validations
        
        return test_case
    
    def _create_invalid_format_test(self, endpoint: Endpoint, base_url: Optional[str], format_type: str) -> Dict[str, Any]:
        """创建参数格式错误的测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        target_param = None
        
        # 寻找合适的参数
        if format_type == "date":
            # 寻找可能是日期类型的参数
            date_keywords = ["time", "date", "datetime", "timestamp", "begin", "end", "start", "expire"]
            for param in self._get_all_parameters(endpoint):
                if any(keyword in param.name.lower() for keyword in date_keywords):
                    target_param = param
                    break
        elif format_type == "json":
            # 寻找可能是JSON类型的参数
            json_keywords = ["json", "config", "params", "settings"]
            for param in self._get_all_parameters(endpoint):
                if any(keyword in param.name.lower() for keyword in json_keywords) or param.type.lower() == "object":
                    target_param = param
                    break
        
        # 如果找不到合适的参数，尝试使用任何参数
        if not target_param and endpoint.request_body and endpoint.request_body.parameters:
            target_param = endpoint.request_body.parameters[0]
        elif not target_param and endpoint.query_parameters:
            target_param = endpoint.query_parameters[0]
        
        # 如果仍然找不到参数，返回原始测试用例
        if not target_param:
            test_case["name"] = f"无法测试{format_type}格式错误 - {endpoint.path}"
            test_case["description"] = f"API没有适合测试{format_type}格式错误的参数"
            return test_case
        
        # 根据格式类型生成无效值
        if format_type == "date":
            value = "无效日期格式-2023/13/32"
        elif format_type == "json":
            value = "{这不是有效的JSON"
        else:
            value = "InvalidFormat"
        
        # 更新参数值
        param_name = target_param.name
        if endpoint.request_body and param_name in test_case["request_data"]:
            test_case["request_data"][param_name] = value
        elif param_name in test_case["query_params"]:
            test_case["query_params"][param_name] = value
        
        # 更新测试元数据
        test_case["name"] = f"{format_type}格式错误测试 - {param_name}"
        test_case["description"] = f"测试{format_type}格式错误的参数 {param_name}"
        test_case["expected_status"] = 400
        test_case["validations"] = [
            {"type": "status_code", "expected": 400}
        ]
        
        return test_case
    
    def _create_idempotency_test(self, endpoint: Endpoint, base_url: Optional[str]) -> Dict[str, Any]:
        """创建幂等性测试用例（重复提交相同请求）"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 幂等性测试的核心是重复发送完全相同的请求
        # 这在测试框架中通常需要特殊处理，我们这里只是标记它为幂等性测试
        
        # 更新测试元数据
        test_case["name"] = f"幂等性测试 - {endpoint.path}"
        test_case["description"] = f"测试重复提交相同请求的幂等性"
        test_case["repeat_count"] = 3  # 重复发送3次相同请求
        
        # 验证规则：所有重复请求都应返回相同的结果
        test_case["validations"] = [
            {"type": "status_code", "expected": 200},
            {"type": "json_field", "field": "RetCode", "expected": 0},
            {"type": "idempotency", "description": "所有重复请求应返回相同的结果"}
        ]
        
        return test_case
    
    def _create_doc_validation_test(self, endpoint: Endpoint, base_url: Optional[str]) -> Dict[str, Any]:
        """创建文档校验测试用例"""
        # 从有效请求开始
        test_case = self._create_happy_path_test(endpoint, base_url)
        
        # 更新测试元数据
        test_case["name"] = f"文档校验测试 - {endpoint.path}"
        test_case["description"] = f"验证接口文档与实现是否一致"
        
        # 为每个文档中描述的响应字段添加验证
        validations = [
            {"type": "status_code", "expected": 200},
            {"type": "json_field", "field": "RetCode", "expected": 0},
            {"type": "doc_validation", "description": "验证响应字段是否与文档一致"}
        ]
        
        # 检查API文档中所需的Response Elements
        if endpoint.responses and "200" in endpoint.responses:
            response_desc = endpoint.responses["200"].description
            response_schema = endpoint.responses["200"].schema
            
            if response_schema:
                for field_name, field_desc in response_schema.items():
                    validations.append({
                        "type": "json_field_exists", 
                        "field": field_name, 
                        "description": f"验证响应中包含文档定义的 {field_name} 字段"
                    })
        
        test_case["validations"] = validations
        
        return test_case
