#!/usr/bin/env python3
import os
import sys
import json
import argparse
import random
import string
import datetime
import re
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

def generate_random_string(length=10):
    """生成随机字符串"""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def parse_markdown_api_doc(md_file_path):
    """
    解析Markdown格式的API文档，提取API信息和参数
    
    Args:
        md_file_path: Markdown文件路径
        
    Returns:
        解析后的API信息字典，包含路径、描述和参数列表
    """
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取API名称和描述
        first_line = content.strip().split('\n')[0]
        api_title_match = re.search(r'(.+)-(\w+)', first_line)
        
        api_description = ""
        api_name = ""
        api_path = ""
        
        if api_title_match:
            api_description = api_title_match.group(1).strip()
            api_name = api_title_match.group(2).strip()
            api_path = "/" + api_name
            print(f"找到API: 名称={api_name}, 路径={api_path}, 描述={api_description}")
        else:
            print("无法从Markdown文件中提取API名称和路径，将使用默认值")
            api_name = "DescribeUDBInstance"
            api_path = "/DescribeUDBInstance"
            api_description = "获取UDB实例信息"
        
        # 查找Request Parameters部分
        request_params_section = re.search(r'# Request Parameters(.*?)(?:# |$)', content, re.DOTALL)
        parameters = []
        
        if request_params_section:
            params_content = request_params_section.group(1)
            
            # 使用正则表达式解析Markdown表格
            param_rows = re.findall(r'\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|', params_content)
            
            if len(param_rows) > 1:  # 确保表头之后有数据行
                # 跳过表头行和分隔行
                for row in param_rows[2:]:
                    if len(row) >= 4:
                        param_name = row[0].strip()
                        param_type = row[1].strip().lower()
                        description = row[2].strip()
                        required = "yes" in row[3].strip().lower()
                        
                        if param_name and param_type and not param_name.startswith('---'):
                            parameters.append({
                                "name": param_name,
                                "type": param_type,
                                "description": description,
                                "required": required
                            })
                            print(f"解析到参数: {param_name}, 类型: {param_type}, 必填: {required}")
        
        # 确保至少有一些参数
        if not parameters:
            print("警告：未找到任何参数，将使用基本参数")
            parameters = [
                {"name": "Action", "type": "string", "required": True, "description": f"API名称，固定值为{api_name}"},
                {"name": "Region", "type": "string", "required": True, "description": "地域"},
                {"name": "Zone", "type": "string", "required": False, "description": "可用区"},
                {"name": "ProjectId", "type": "string", "required": False, "description": "项目ID"}
            ]
        else:
            # 确保Action参数存在
            has_action = any(param["name"] == "Action" for param in parameters)
            if not has_action:
                parameters.append({
                    "name": "Action",
                    "type": "string",
                    "required": True,
                    "description": f"API名称，固定值为{api_name}"
                })
        
        # 查找Response Elements部分
        response_section = re.search(r'# Response Elements(.*?)(?:# |$)', content, re.DOTALL)
        response_params = []
        
        if response_section:
            response_content = response_section.group(1)
            
            # 使用正则表达式解析Markdown表格
            resp_rows = re.findall(r'\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|', response_content)
            
            if len(resp_rows) > 1:  # 确保表头之后有数据行
                # 跳过表头行和分隔行
                for row in resp_rows[2:]:
                    if len(row) >= 4:
                        param_name = row[0].strip()
                        param_type = row[1].strip().lower()
                        description = row[2].strip()
                        required = "yes" in row[3].strip().lower()
                        
                        if param_name and param_type and not param_name.startswith('---'):
                            response_params.append({
                                "name": param_name,
                                "type": param_type,
                                "description": description,
                                "required": required
                            })
                            print(f"解析到响应参数: {param_name}, 类型: {param_type}, 必填: {required}")
        
        # 打印找到的所有参数
        print(f"总共解析到请求参数 {len(parameters)} 个")
        print(f"总共解析到响应参数 {len(response_params)} 个")
            
        return {
            "path": api_path,
            "name": api_name,
            "description": api_description,
            "parameters": parameters,
            "responses": response_params
        }
    except Exception as e:
        print(f"解析Markdown文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def generate_post_testcases(api_file, output_file, base_url):
    """
    生成POST测试用例
    
    Args:
        api_file: API描述文件路径（JSON、PDF或Markdown）
        output_file: 输出的测试用例文件路径
        base_url: API的基础URL
    """
    print(f"从 {api_file} 生成POST测试用例...")
    
    endpoints = []
    
    # 检查文件扩展名
    _, ext = os.path.splitext(api_file)
    
    if ext.lower() == '.md':
        # 处理Markdown文件
        api_info = parse_markdown_api_doc(api_file)
        if api_info and api_info["path"]:
            endpoints = [{
                "path": api_info["path"],
                "method": "POST",
                "name": api_info["name"],
                "description": api_info["description"],
                "parameters": api_info["parameters"],
                "responses": api_info.get("responses", [])
            }]
    elif ext.lower() == '.json':
        # 处理JSON文件
        try:
            with open(api_file, 'r', encoding='utf-8') as f:
                api_data = json.load(f)
                
            if "endpoints" in api_data:
                endpoints = api_data.get("endpoints", [])
        except Exception as e:
            print(f"读取JSON文件时出错: {str(e)}")
    else:
        # 不支持的文件类型，使用默认测试端点
        print(f"不支持的文件类型: {ext}，使用默认测试端点")
        endpoints = [{
            "path": "/api/test",
            "method": "POST",
            "description": "Default test endpoint"
        }]
    
    # 生成测试用例
    test_cases = {}
    
    for endpoint in endpoints:
        path = endpoint.get("path", "").strip()
        method = "POST"  # 强制使用POST
        api_name = endpoint.get("name", "")
        description = endpoint.get("description", "")
        parameters = endpoint.get("parameters", [])
        responses = endpoint.get("responses", [])
        endpoint_key = f"{method} {path}"
        
        # 提取名称（通常是路径的最后一段或API名称）
        name = api_name if api_name else path.strip('/').split('/')[-1]
        
        # 创建一个有组织的测试用例集合，按类别分组
        endpoint_test_cases = {
            "等价类测试": [],
            "边界值测试": [],
            "异常测试": [],
            "特殊测试": []
        }
        
        # 1. 等价类测试
        print(f"生成 {api_name} 的等价类测试...")
        
        # 1.1 正常请求测试（所有参数有效值）
        normal_test = create_normal_test(path, method, description, parameters, name)
        endpoint_test_cases["等价类测试"].append(normal_test)
        
        # 1.2 仅必填参数测试
        required_only_test = create_required_only_test(path, method, description, parameters, name)
        endpoint_test_cases["等价类测试"].append(required_only_test)
        
        # 1.3 部分选填参数测试
        partial_optional_test = create_normal_test(path, method, description, parameters, name)
        partial_optional_test["name"] = f"{name}_部分选填参数测试"
        partial_optional_test["description"] = "测试部分选填参数"
        endpoint_test_cases["等价类测试"].append(partial_optional_test)
        
        # 1.4 所有参数测试
        all_params_test = create_normal_test(path, method, description, parameters, name)
        all_params_test["name"] = f"{name}_所有参数测试"
        all_params_test["description"] = "使用所有参数测试API"
        
        # 确保所有非必填参数也被添加
        for param in parameters:
            param_name = param.get("name", "")
            param_type = param.get("type", "").lower()
            required = param.get("required", False)
            
            if not required and param_name not in all_params_test["request"]["body"]:
                if param_name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
                    continue
                    
                if param_type == "string":
                    all_params_test["request"]["body"][param_name] = f"test_{param_name}_{generate_random_string(5)}"
                elif param_type in ["number", "integer", "int"]:
                    all_params_test["request"]["body"][param_name] = random.randint(1, 100)
                elif param_type in ["boolean", "bool"]:
                    all_params_test["request"]["body"][param_name] = random.choice([True, False])
                elif param_type == "array":
                    all_params_test["request"]["body"][param_name] = [f"item_{i}" for i in range(1, 4)]
                else:
                    all_params_test["request"]["body"][param_name] = f"default_value_for_{param_name}"
        
        endpoint_test_cases["等价类测试"].append(all_params_test)
        
        # 1.5 不同数据类型测试
        for param in parameters:
            param_name = param.get("name", "")
            param_type = param.get("type", "").lower()
            if param_name not in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
                if param_type in ["number", "integer", "int"]:
                    number_type_test = create_data_type_test(path, method, description, parameters, param, "number", name)
                    endpoint_test_cases["等价类测试"].append(number_type_test)
                elif param_type == "string":
                    string_type_test = create_data_type_test(path, method, description, parameters, param, "string", name)
                    endpoint_test_cases["等价类测试"].append(string_type_test)
                elif param_type in ["boolean", "bool"]:
                    boolean_type_test = create_data_type_test(path, method, description, parameters, param, "boolean", name)
                    endpoint_test_cases["等价类测试"].append(boolean_type_test)
                elif param_type == "array":
                    array_type_test = create_data_type_test(path, method, description, parameters, param, "array", name)
                    endpoint_test_cases["等价类测试"].append(array_type_test)
        
        # 2. 边界值测试
        print(f"生成 {api_name} 的边界值测试...")
        
        for param in parameters:
            param_type = param.get("type", "").lower()
            param_name = param.get("name", "")
            
            if param_name not in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
                if param_type in ["number", "integer", "int"]:
                    # 2.1 数值型边界测试
                    max_test = create_boundary_test(path, method, description, parameters, param, "max", name)
                    endpoint_test_cases["边界值测试"].append(max_test)
                    
                    max_plus_one_test = create_boundary_test(path, method, description, parameters, param, "max_plus_one", name)
                    endpoint_test_cases["边界值测试"].append(max_plus_one_test)
                    
                    min_test = create_boundary_test(path, method, description, parameters, param, "min", name)
                    endpoint_test_cases["边界值测试"].append(min_test)
                    
                    min_minus_one_test = create_boundary_test(path, method, description, parameters, param, "min_minus_one", name)
                    endpoint_test_cases["边界值测试"].append(min_minus_one_test)
                    
                    zero_test = create_boundary_test(path, method, description, parameters, param, "zero", name)
                    endpoint_test_cases["边界值测试"].append(zero_test)
                    
                    negative_test = create_boundary_test(path, method, description, parameters, param, "negative", name)
                    endpoint_test_cases["边界值测试"].append(negative_test)
                    
                    large_test = create_boundary_test(path, method, description, parameters, param, "large", name)
                    endpoint_test_cases["边界值测试"].append(large_test)
                    
                elif param_type == "string":
                    # 2.2 字符串边界测试
                    empty_test = create_boundary_test(path, method, description, parameters, param, "empty", name)
                    endpoint_test_cases["边界值测试"].append(empty_test)
                    
                    long_test = create_boundary_test(path, method, description, parameters, param, "long", name)
                    endpoint_test_cases["边界值测试"].append(long_test)
                    
                    special_test = create_boundary_test(path, method, description, parameters, param, "special", name)
                    endpoint_test_cases["边界值测试"].append(special_test)
                    
                    spaces_test = create_boundary_test(path, method, description, parameters, param, "spaces", name)
                    endpoint_test_cases["边界值测试"].append(spaces_test)
                    
                    emoji_test = create_boundary_test(path, method, description, parameters, param, "emoji", name)
                    endpoint_test_cases["边界值测试"].append(emoji_test)
                    
                    multilingual_test = create_boundary_test(path, method, description, parameters, param, "multilingual", name)
                    endpoint_test_cases["边界值测试"].append(multilingual_test)
        
        # 3. 异常测试
        print(f"生成 {api_name} 的异常测试...")
        
        # 3.1 缺失必填参数测试
        for param in parameters:
            if param.get("required", False):
                missing_param_test = create_missing_param_test(path, method, description, parameters, param, name)
                endpoint_test_cases["异常测试"].append(missing_param_test)
        
        # 3.2 无效数据类型测试（对每个参数）
        for param in parameters:
            if param.get("name", "") not in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey", "Action"]:
                invalid_type_test = create_invalid_type_test(path, method, description, parameters, param, name)
                endpoint_test_cases["异常测试"].append(invalid_type_test)
        
        # 3.3 格式错误测试（针对特定格式如Email、URL等）
        email_format_test = create_format_error_test(path, method, description, parameters, "email", name)
        endpoint_test_cases["异常测试"].append(email_format_test)
        
        url_format_test = create_format_error_test(path, method, description, parameters, "url", name)
        endpoint_test_cases["异常测试"].append(url_format_test)
        
        date_format_test = create_format_error_test(path, method, description, parameters, "date", name)
        endpoint_test_cases["异常测试"].append(date_format_test)
        
        json_format_test = create_format_error_test(path, method, description, parameters, "json", name)
        endpoint_test_cases["异常测试"].append(json_format_test)
        
        # 4. 特殊测试
        print(f"生成 {api_name} 的特殊测试...")
        
        # 4.1 幂等性测试（对于支持幂等性的API）
        idempotent_test = create_idempotency_test(path, method, description, parameters, name)
        endpoint_test_cases["特殊测试"].append(idempotent_test)
        
        # 4.2 性能测试
        performance_test = create_performance_test(path, method, description, parameters, name)
        endpoint_test_cases["特殊测试"].append(performance_test)
        
        # 4.3 安全测试
        security_test = create_security_test(path, method, description, parameters, name)
        endpoint_test_cases["特殊测试"].append(security_test)
        
        # 4.4 文档验证测试（检查响应是否符合文档）
        doc_validation_test = create_doc_validation_test(path, method, description, parameters, responses, name)
        endpoint_test_cases["特殊测试"].append(doc_validation_test)
        
        # 将所有测试用例扁平化为列表
        flat_test_cases = []
        for category, tests in endpoint_test_cases.items():
            for test in tests:
                # 添加测试类别到测试用例
                test["category"] = category
                flat_test_cases.append(test)
        
        test_cases[endpoint_key] = {
            "endpoint": {
                "path": path,
                "method": method,
                "description": description
            },
            "test_cases": flat_test_cases
        }
        
        print(f"为 API {name} 生成了 {len(flat_test_cases)} 个测试用例")
    
    # 保存到输出文件
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_cases, f, indent=2, ensure_ascii=False)
        print(f"测试用例已保存到: {output_file}")
        print(f"总共生成了 {sum(len(data['test_cases']) for data in test_cases.values())} 个测试用例")
    except Exception as e:
        print(f"保存测试用例时出错: {str(e)}")
    
    return test_cases

def create_normal_test(path, method, description, parameters, api_name=""):
    """创建正常路径测试用例"""
    test_case = {
        "name": f"{api_name}_正常路径测试" if api_name else "正常路径测试",
        "description": f"使用所有必填参数和常见可选参数测试API的正常功能",
        "request": {
            "path": path,
            "method": method,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                # 添加通用必填参数
                "Region": "{{Region}}",
                "Zone": "{{Zone}}",
                "ProjectId": "{{ProjectId}}",
                "PublicKey": "{{PublicKey}}",
                "PrivateKey": "{{PrivateKey}}"
            }
        },
        "expected": {
            "status": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                "RetCode": 0
            }
        }
    }
    
    # 添加所有必填参数和部分可选参数
    for param in parameters:
        name = param.get("name", "")
        param_type = param.get("type", "string")
        required = param.get("required", False)
        
        # 跳过已经添加的通用参数
        if name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
            continue
            
        if required or random.random() > 0.5:  # 随机选择一些可选参数
            if name.lower() == "action":
                test_case["request"]["body"][name] = api_name
            elif param_type == "string":
                test_case["request"]["body"][name] = f"test_{name}_{generate_random_string(5)}"
            elif param_type == "number" or param_type == "integer" or param_type == "int":
                test_case["request"]["body"][name] = random.randint(1, 100)
            elif param_type == "boolean" or param_type == "bool":
                test_case["request"]["body"][name] = random.choice([True, False])
            elif param_type == "array":
                test_case["request"]["body"][name] = [f"item_{i}" for i in range(1, 4)]
            else:
                test_case["request"]["body"][name] = f"default_value_for_{name}"
    
    return test_case

def create_required_only_test(path, method, description, parameters, api_name=""):
    """仅使用必填参数的测试用例"""
    test_case = {
        "name": f"{api_name}_仅必填参数测试" if api_name else "仅必填参数测试",
        "description": "仅使用必填参数测试API",
        "request": {
            "path": path,
            "method": method,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                # 添加通用必填参数
                "Region": "{{Region}}",
                "Zone": "{{Zone}}",
                "ProjectId": "{{ProjectId}}",
                "PublicKey": "{{PublicKey}}",
                "PrivateKey": "{{PrivateKey}}"
            }
        },
        "expected": {
            "status": 200,
            "body": {
                "RetCode": 0
            }
        }
    }
    
    # 仅添加必填参数
    for param in parameters:
        name = param.get("name", "")
        param_type = param.get("type", "string")
        required = param.get("required", False)
        
        # 跳过已经添加的通用参数
        if name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
            continue
            
        if required:
            if name.lower() == "action":
                test_case["request"]["body"][name] = api_name
            elif param_type == "string":
                test_case["request"]["body"][name] = f"test_{name}"
            elif param_type == "number" or param_type == "integer" or param_type == "int":
                test_case["request"]["body"][name] = 1
            elif param_type == "boolean" or param_type == "bool":
                test_case["request"]["body"][name] = True
            elif param_type == "array":
                test_case["request"]["body"][name] = ["item_1"]
            else:
                test_case["request"]["body"][name] = f"default_value_for_{name}"
    
    return test_case

def create_partial_optional_test(path, method, description, parameters, api_name=""):
    """创建提供必填参数和部分选填参数的测试用例"""
    request_data = {}
    optional_params = [p for p in parameters if not p.get("required", False)]
    
    # 添加所有必填参数
    for param in parameters:
        param_name = param.get("name", "")
        param_type = param.get("type", "string")
        required = param.get("required", False)
        
        if required:
            if param_name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
                request_data[param_name] = f"{{{{{param_name}}}}}"
            else:
                if param_type == "string":
                    request_data[param_name] = f"test_{param_name}_{generate_random_string(5)}"
                elif param_type == "integer" or param_type == "number" or param_type == "int":
                    request_data[param_name] = random.randint(1, 100)
                elif param_type == "boolean" or param_type == "bool":
                    request_data[param_name] = random.choice([True, False])
                elif param_type == "array":
                    request_data[param_name] = [f"item_{generate_random_string(3)}" for _ in range(2)]
    
    # 添加部分选填参数（随机选择一半）
    selected_optional = random.sample(optional_params, max(1, len(optional_params) // 2)) if optional_params else []
    
    for param in selected_optional:
        param_name = param.get("name", "")
        param_type = param.get("type", "string")
        
        if param_name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
            request_data[param_name] = f"{{{{{param_name}}}}}"
        else:
            if param_type == "string":
                request_data[param_name] = f"test_{param_name}_{generate_random_string(5)}"
            elif param_type == "integer" or param_type == "number" or param_type == "int":
                request_data[param_name] = random.randint(1, 100)
            elif param_type == "boolean" or param_type == "bool":
                request_data[param_name] = random.choice([True, False])
            elif param_type == "array":
                request_data[param_name] = [f"item_{generate_random_string(3)}" for _ in range(2)]
    
    # 添加Action参数（UCloud API 要求）
    action = path.strip('/').split('/')[-1]
    request_data["Action"] = action
    
    return {
        "name": f"{api_name}_部分选填参数测试" if api_name else "部分选填参数测试",
        "description": f"测试提供必填参数和部分选填参数的情况",
        "method": method,
        "path": path,
        "headers": {
            "Content-Type": "application/json"
        },
        "request_data": request_data,
        "expected_status": 200,
        "validations": [
            {
                "type": "status_code",
                "value": 200
            },
            {
                "type": "json_field",
                "field": "RetCode",
                "value": 0
            }
        ]
    }

def create_all_params_test(path, method, description, parameters, api_name=""):
    """创建提供所有参数（必填和选填）的测试用例"""
    request_data = {}
    
    # 添加所有参数
    for param in parameters:
        param_name = param.get("name", "")
        param_type = param.get("type", "string")
        
        if param_name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
            request_data[param_name] = f"{{{{{param_name}}}}}"
        else:
            if param_type == "string":
                request_data[param_name] = f"test_{param_name}_{generate_random_string(5)}"
            elif param_type == "integer" or param_type == "number" or param_type == "int":
                request_data[param_name] = random.randint(1, 100)
            elif param_type == "boolean" or param_type == "bool":
                request_data[param_name] = random.choice([True, False])
            elif param_type == "array":
                request_data[param_name] = [f"item_{generate_random_string(3)}" for _ in range(2)]
    
    # 添加Action参数（UCloud API 要求）
    action = path.strip('/').split('/')[-1]
    request_data["Action"] = action
    
    return {
        "name": f"{api_name}_所有参数测试" if api_name else "所有参数测试",
        "description": f"测试提供所有参数（必填和选填）的情况",
        "method": method,
        "path": path,
        "headers": {
            "Content-Type": "application/json"
        },
        "request_data": request_data,
        "expected_status": 200,
        "validations": [
            {
                "type": "status_code",
                "value": 200
            },
            {
                "type": "json_field",
                "field": "RetCode",
                "value": 0
            }
        ]
    }

def create_data_type_test(path, method, description, parameters, target_param, data_type, api_name=""):
    """创建针对特定数据类型参数的测试用例"""
    test_case = {
        "name": f"{api_name}_{target_param.get('name', '')}_{data_type}_类型测试",
        "description": f"测试{data_type}类型参数 {target_param.get('name', '')} 的处理",
        "request": {
            "path": path,
            "method": method,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                # 添加通用必填参数
                "Region": "{{Region}}",
                "Zone": "{{Zone}}",
                "ProjectId": "{{ProjectId}}",
                "PublicKey": "{{PublicKey}}",
                "PrivateKey": "{{PrivateKey}}"
            }
        },
        "expected": {
            "status": 200,
            "body": {
                "RetCode": 0
            }
        }
    }
    
    # 添加必填参数
    for param in parameters:
        name = param.get("name", "")
        param_type = param.get("type", "string")
        required = param.get("required", False)
        
        # 跳过已经添加的通用参数和目标参数
        if name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"] or name == target_param.get("name", ""):
            continue
            
        if required:
            if name.lower() == "action":
                test_case["request"]["body"][name] = api_name
            elif param_type == "string":
                test_case["request"]["body"][name] = f"test_{name}"
            elif param_type == "number" or param_type == "integer" or param_type == "int":
                test_case["request"]["body"][name] = 1
            elif param_type == "boolean" or param_type == "bool":
                test_case["request"]["body"][name] = True
            elif param_type == "array":
                test_case["request"]["body"][name] = ["item_1"]
            else:
                test_case["request"]["body"][name] = f"default_value_for_{name}"
    
    # 特别处理目标参数
    target_name = target_param.get("name", "")
    
    # 根据测试的数据类型，设置相应的值
    if data_type == "number":
        test_case["request"]["body"][target_name] = 42
    elif data_type == "string":
        test_case["request"]["body"][target_name] = f"测试字符串Value_123"
    elif data_type == "boolean":
        test_case["request"]["body"][target_name] = True
    elif data_type == "array":
        test_case["request"]["body"][target_name] = ["item1", "item2", "item3"]
    elif data_type == "object":
        test_case["request"]["body"][target_name] = {"key1": "value1", "key2": "value2"}
    
    # 如果是Action参数，确保值为API名称
    if target_name.lower() == "action" and api_name:
        test_case["request"]["body"][target_name] = api_name
    
    return test_case

def create_boundary_test(path, method, description, parameters, target_param, boundary_type, api_name=""):
    """创建边界值测试用例"""
    test_case = {
        "name": f"{api_name}_{target_param.get('name', '')}_{boundary_type}_边界值测试",
        "description": f"测试参数 {target_param.get('name', '')} 的{boundary_type}边界值",
        "request": {
            "path": path,
            "method": method,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                # 添加通用必填参数
                "Region": "{{Region}}",
                "Zone": "{{Zone}}",
                "ProjectId": "{{ProjectId}}",
                "PublicKey": "{{PublicKey}}",
                "PrivateKey": "{{PrivateKey}}"
            }
        },
        "expected": {
            "status": 200,
            "body": {
                "RetCode": 0
            }
        }
    }
    
    # 添加必填参数
    for param in parameters:
        name = param.get("name", "")
        param_type = param.get("type", "string")
        required = param.get("required", False)
        
        # 跳过已经添加的通用参数和目标参数
        if name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"] or name == target_param.get("name", ""):
            continue
            
        if required:
            if name.lower() == "action":
                test_case["request"]["body"][name] = api_name
            elif param_type == "string":
                test_case["request"]["body"][name] = f"test_{name}"
            elif param_type == "number" or param_type == "integer" or param_type == "int":
                test_case["request"]["body"][name] = 1
            elif param_type == "boolean" or param_type == "bool":
                test_case["request"]["body"][name] = True
            elif param_type == "array":
                test_case["request"]["body"][name] = ["item_1"]
            else:
                test_case["request"]["body"][name] = f"default_value_for_{name}"
    
    # 特别处理目标参数
    target_name = target_param.get("name", "")
    target_type = target_param.get("type", "").lower()
    
    # 根据边界类型和参数类型，设置相应的值
    if target_type in ["number", "integer", "int"]:
        if boundary_type == "max":
            test_case["request"]["body"][target_name] = 2147483647  # INT_MAX
            test_case["description"] = f"测试参数 {target_name} 的最大值(INT_MAX)"
        elif boundary_type == "max_plus_one":
            test_case["request"]["body"][target_name] = 2147483648  # INT_MAX + 1
            test_case["description"] = f"测试参数 {target_name} 的最大值+1(INT_MAX+1)"
            test_case["expected"]["status"] = 400
            test_case["expected"]["body"]["RetCode"] = {"$ne": 0}
        elif boundary_type == "min":
            test_case["request"]["body"][target_name] = -2147483648  # INT_MIN
            test_case["description"] = f"测试参数 {target_name} 的最小值(INT_MIN)"
        elif boundary_type == "min_minus_one":
            test_case["request"]["body"][target_name] = -2147483649  # INT_MIN - 1
            test_case["description"] = f"测试参数 {target_name} 的最小值-1(INT_MIN-1)"
            test_case["expected"]["status"] = 400
            test_case["expected"]["body"]["RetCode"] = {"$ne": 0}
        elif boundary_type == "zero":
            test_case["request"]["body"][target_name] = 0
            test_case["description"] = f"测试参数 {target_name} 的零值(0)"
        elif boundary_type == "negative":
            test_case["request"]["body"][target_name] = -1
            test_case["description"] = f"测试参数 {target_name} 的负值(-1)"
        elif boundary_type == "large":
            test_case["request"]["body"][target_name] = 9999999999
            test_case["description"] = f"测试参数 {target_name} 的超大值(9999999999)"
            test_case["expected"]["status"] = 400
            test_case["expected"]["body"]["RetCode"] = {"$ne": 0}
    elif target_type == "string":
        if boundary_type == "empty":
            test_case["request"]["body"][target_name] = ""
            test_case["description"] = f"测试参数 {target_name} 的空字符串"
        elif boundary_type == "long":
            test_case["request"]["body"][target_name] = "a" * 1000
            test_case["description"] = f"测试参数 {target_name} 的超长字符串(1000字符)"
            test_case["expected"]["status"] = 400
            test_case["expected"]["body"]["RetCode"] = {"$ne": 0}
        elif boundary_type == "special":
            test_case["request"]["body"][target_name] = "!@#$%^&*()_+-=[]{}|;':\",./<>?\\"
            test_case["description"] = f"测试参数 {target_name} 的特殊字符"
        elif boundary_type == "spaces":
            test_case["request"]["body"][target_name] = "   空格前后   "
            test_case["description"] = f"测试参数 {target_name} 的空格前后"
        elif boundary_type == "emoji":
            test_case["request"]["body"][target_name] = "测试Emoji😀👍🎉"
            test_case["description"] = f"测试参数 {target_name} 的Emoji字符"
        elif boundary_type == "multilingual":
            test_case["request"]["body"][target_name] = "English中文日本語한국어"
            test_case["description"] = f"测试参数 {target_name} 的多语言字符"
    
    # 如果是Action参数，确保值为API名称
    if target_name.lower() == "action" and api_name:
        test_case["request"]["body"][target_name] = api_name
    
    return test_case

def create_missing_param_test(path, method, description, parameters, target_param, api_name=""):
    """创建缺失必需参数的测试用例"""
    test_case = {
        "name": f"{api_name}_{target_param.get('name', '')}_缺失测试",
        "description": f"测试缺少必需参数 {target_param.get('name', '')} 的情况",
        "request": {
            "path": path,
            "method": method,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                # 添加通用必填参数
                "Region": "{{Region}}",
                "Zone": "{{Zone}}",
                "ProjectId": "{{ProjectId}}",
                "PublicKey": "{{PublicKey}}",
                "PrivateKey": "{{PrivateKey}}"
            }
        },
        "expected": {
            "status": 400,
            "body": {
                "RetCode": {"$ne": 0}
            }
        }
    }
    
    target_name = target_param.get("name", "")
    
    # 如果目标参数是通用参数之一，从请求中移除它
    if target_name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
        del test_case["request"]["body"][target_name]
    
    # 添加除目标参数外的所有必填参数
    for param in parameters:
        name = param.get("name", "")
        param_type = param.get("type", "string")
        required = param.get("required", False)
        
        # 跳过已经添加的通用参数和目标参数
        if name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"] or name == target_name:
            continue
            
        if required:
            if name.lower() == "action":
                test_case["request"]["body"][name] = api_name
            elif param_type == "string":
                test_case["request"]["body"][name] = f"test_{name}"
            elif param_type == "number" or param_type == "integer" or param_type == "int":
                test_case["request"]["body"][name] = 1
            elif param_type == "boolean" or param_type == "bool":
                test_case["request"]["body"][name] = True
            elif param_type == "array":
                test_case["request"]["body"][name] = ["item_1"]
            else:
                test_case["request"]["body"][name] = f"default_value_for_{name}"
    
    return test_case

def create_invalid_type_test(path, method, description, parameters, target_param, api_name=""):
    """创建参数类型错误的测试用例"""
    test_case = {
        "name": f"{api_name}_{target_param.get('name', '')}_类型错误测试",
        "description": f"测试参数 {target_param.get('name', '')} 类型错误的情况",
        "request": {
            "path": path,
            "method": method,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                # 添加通用必填参数
                "Region": "{{Region}}",
                "Zone": "{{Zone}}",
                "ProjectId": "{{ProjectId}}",
                "PublicKey": "{{PublicKey}}",
                "PrivateKey": "{{PrivateKey}}"
            }
        },
        "expected": {
            "status": 400,
            "body": {
                "RetCode": {"$ne": 0}
            }
        }
    }
    
    # 添加所有必填参数
    for param in parameters:
        name = param.get("name", "")
        param_type = param.get("type", "string")
        required = param.get("required", False)
        
        # 跳过已经添加的通用参数和目标参数
        if name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"] or name == target_param.get("name", ""):
            continue
            
        if required:
            if name.lower() == "action":
                test_case["request"]["body"][name] = api_name
            elif param_type == "string":
                test_case["request"]["body"][name] = f"test_{name}"
            elif param_type == "number" or param_type == "integer" or param_type == "int":
                test_case["request"]["body"][name] = 1
            elif param_type == "boolean" or param_type == "bool":
                test_case["request"]["body"][name] = True
            elif param_type == "array":
                test_case["request"]["body"][name] = ["item_1"]
            else:
                test_case["request"]["body"][name] = f"default_value_for_{name}"
    
    # 特别处理目标参数，设置错误的类型
    target_name = target_param.get("name", "")
    target_type = target_param.get("type", "").lower()
    
    # 故意设置错误的类型
    if target_type == "string":
        test_case["request"]["body"][target_name] = 12345
    elif target_type in ["number", "integer", "int"]:
        test_case["request"]["body"][target_name] = "这不是数字"
    elif target_type in ["boolean", "bool"]:
        test_case["request"]["body"][target_name] = "不是布尔值"
    elif target_type == "array":
        test_case["request"]["body"][target_name] = "不是数组"
    
    # 如果目标参数是Action，我们不应该改变它
    if target_name.lower() == "action" and api_name:
        test_case["request"]["body"][target_name] = api_name
        # 尝试使用其他方式测试Action参数的错误类型
        test_case["request"]["body"]["InvalidActionParam"] = "InvalidActionValue"
    
    return test_case

def create_format_error_test(path, method, description, parameters, format_type, api_name=""):
    """创建参数格式错误的测试用例"""
    test_case = {
        "name": f"{api_name}_{format_type}_格式错误测试",
        "description": f"测试{format_type}格式参数错误的情况",
        "request": {
            "path": path,
            "method": method,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                # 添加通用必填参数
                "Region": "{{Region}}",
                "Zone": "{{Zone}}",
                "ProjectId": "{{ProjectId}}",
                "PublicKey": "{{PublicKey}}",
                "PrivateKey": "{{PrivateKey}}"
            }
        },
        "expected": {
            "status": 400,
            "body": {
                "RetCode": {"$ne": 0}
            }
        }
    }
    
    # 添加必填参数
    for param in parameters:
        name = param.get("name", "")
        param_type = param.get("type", "string")
        required = param.get("required", False)
        
        # 跳过已经添加的通用参数
        if name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
            continue
            
        if required:
            if name.lower() == "action":
                test_case["request"]["body"][name] = api_name
            elif param_type == "string":
                test_case["request"]["body"][name] = f"test_{name}"
            elif param_type == "number" or param_type == "integer" or param_type == "int":
                test_case["request"]["body"][name] = 1
            elif param_type == "boolean" or param_type == "bool":
                test_case["request"]["body"][name] = True
            elif param_type == "array":
                test_case["request"]["body"][name] = ["item_1"]
            else:
                test_case["request"]["body"][name] = f"default_value_for_{name}"
    
    # 根据格式类型，插入一个格式错误的参数
    if format_type == "email":
        test_case["request"]["body"]["Email"] = "无效的邮箱格式"
    elif format_type == "url":
        test_case["request"]["body"]["URL"] = "无效的URL格式"
    elif format_type == "date":
        test_case["request"]["body"]["StartTime"] = "无效的日期格式"
    elif format_type == "json":
        test_case["request"]["body"]["ConfigJson"] = "{ 这不是有效的JSON }"
    
    return test_case

def create_idempotency_test(path, method, description, parameters, api_name=""):
    """创建幂等性测试用例"""
    # 使用正常请求测试用例作为基础
    test_case = create_normal_test(path, method, description, parameters, api_name)
    
    # 修改测试用例名称和描述
    test_case["name"] = f"{api_name}_幂等性测试" if api_name else "幂等性测试"
    test_case["description"] = "测试多次发送相同请求是否产生相同结果 (重复提交相同的请求应产生一样的结果)"
    
    # 添加幂等性标识，如果API支持的话
    test_case["request"]["body"]["ClientToken"] = "{{$randomUUID}}"
    
    return test_case

def create_performance_test(path, method, description, parameters, api_name=""):
    """创建性能测试用例"""
    # 使用正常请求测试用例作为基础
    test_case = create_normal_test(path, method, description, parameters, api_name)
    
    # 修改测试用例名称和描述
    test_case["name"] = f"{api_name}_性能测试" if api_name else "性能测试"
    test_case["description"] = "测试API响应时间是否在可接受范围内 (响应时间应小于2秒)"
    
    # 对于新格式的测试用例，更新预期响应信息
    test_case["expected"]["max_response_time"] = 2000  # 2秒
    
    return test_case

def create_doc_validation_test(path, method, description, parameters, responses, api_name=""):
    """创建文档校验测试用例"""
    # 使用正常请求测试用例作为基础
    test_case = create_normal_test(path, method, description, parameters, api_name)
    
    # 修改测试用例名称和描述
    test_case["name"] = f"{api_name}_文档校验测试" if api_name else "文档校验测试"
    test_case["description"] = "验证API响应是否符合文档描述 (检查响应字段是否与文档一致)"
    
    # 为新格式的测试用例，添加文档中定义的响应字段
    for response_param in responses:
        name = response_param.get("name", "")
        if name:
            if name not in test_case["expected"]["body"]:
                test_case["expected"]["body"][name] = True  # 只验证字段存在，不验证具体值
    
    return test_case

def create_security_test(path, method, description, parameters, api_name=""):
    """创建安全测试用例"""
    test_case = {
        "name": f"{api_name}_安全测试" if api_name else "安全测试",
        "description": "测试API对于SQL注入和XSS攻击的防御能力",
        "request": {
            "path": path,
            "method": method,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                # 添加通用必填参数
                "Region": "{{Region}}",
                "Zone": "{{Zone}}",
                "ProjectId": "{{ProjectId}}",
                "PublicKey": "{{PublicKey}}",
                "PrivateKey": "{{PrivateKey}}"
            }
        },
        "expected": {
            "status": 200,
            "body": {
                "RetCode": {"$ne": 0}  # 期望非0错误码
            }
        }
    }
    
    # 添加必填参数
    for param in parameters:
        name = param.get("name", "")
        param_type = param.get("type", "string")
        required = param.get("required", False)
        
        # 跳过已经添加的通用参数
        if name in ["Region", "Zone", "ProjectId", "PublicKey", "PrivateKey"]:
            continue
            
        if required:
            if name.lower() == "action":
                test_case["request"]["body"][name] = api_name
            elif param_type == "string":
                test_case["request"]["body"][name] = "' OR 1=1; -- <script>alert('XSS')</script>"
            elif param_type == "number" or param_type == "integer" or param_type == "int":
                test_case["request"]["body"][name] = 1
            elif param_type == "boolean" or param_type == "bool":
                test_case["request"]["body"][name] = True
            elif param_type == "array":
                test_case["request"]["body"][name] = ["' OR 1=1; --", "<script>alert('XSS')</script>"]
            else:
                test_case["request"]["body"][name] = "' OR 1=1; -- <script>alert('XSS')</script>"
    
    return test_case

def main():
    parser = argparse.ArgumentParser(description="生成POST测试用例")
    parser.add_argument("-f", "--file", required=True, help="API描述文件路径")
    parser.add_argument("-o", "--output", default="reports/test_cases.json", help="输出文件路径")
    parser.add_argument("-u", "--url", default="https://api.ucloud.cn", help="API基础URL")

    args = parser.parse_args()
    
    generate_post_testcases(args.file, args.output, args.url)

if __name__ == "__main__":
    main() 