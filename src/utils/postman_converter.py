#!/usr/bin/env python3
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

def convert_to_postman_collection(test_cases: Dict[str, Any]) -> Dict[str, Any]:
    """
    将测试用例转换为Postman集合格式
    
    Args:
        test_cases: 测试用例字典，键为端点路径，值为包含端点信息和测试用例列表的字典
        
    Returns:
        Postman集合格式的字典
    """
    collection_id = str(uuid.uuid4())
    
    # 创建集合结构
    collection = {
        "info": {
            "_postman_id": collection_id,
            "name": "API Test AI Generated Collection",
            "description": "Automatically generated test collection",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": []
    }
    
    # 为每个端点添加文件夹
    for endpoint_key, endpoint_data in test_cases.items():
        # 新格式检查
        if isinstance(endpoint_data, dict) and "endpoint" in endpoint_data and "test_cases" in endpoint_data:
            # 新格式：使用结构化数据
            endpoint_info = endpoint_data["endpoint"]
            endpoint_tests = endpoint_data["test_cases"]
            
            endpoint_path = endpoint_info.get("path", "")
            endpoint_method = endpoint_info.get("method", "POST")
            endpoint_description = endpoint_info.get("description", "")
            
            folder_name = endpoint_path
            if endpoint_description:
                folder_name = f"{endpoint_path} - {endpoint_description}"
            
            endpoint_folder = {
                "name": folder_name,
                "description": endpoint_description,
                "item": []
            }
            
            # 添加每个测试用例作为请求
            for test_case in endpoint_tests:
                # 确保所有请求都是POST方法
                request_method = "POST"
                
                # 处理新的测试用例格式
                request_item = create_postman_request_new_format(
                    test_case, 
                    endpoint_path, 
                    request_method
                )
                endpoint_folder["item"].append(request_item)
            
        else:
            # 旧格式：纯列表
            endpoint_folder = {
                "name": endpoint_key,
                "item": []
            }
            
            # 提取端点路径，用于处理旧格式
            endpoint_path = endpoint_key.split(" ")[-1] if " " in endpoint_key else endpoint_key
            endpoint_method = "POST"  # 强制使用POST方法
            
            # 添加每个测试用例作为请求
            for test_case in endpoint_data:
                # 提取接口名称，用于Action字段
                interface_name = endpoint_path.strip('/').split("/")[-1]
                test_case["action_name"] = interface_name
                
                # 确保所有请求都是POST方法
                test_case["method"] = "POST"
                test_case["path"] = endpoint_path
                
                request_item = create_postman_request_old_format(test_case)
                endpoint_folder["item"].append(request_item)
        
        collection["item"].append(endpoint_folder)
    
    return collection

def create_postman_request_new_format(test_case: Dict[str, Any], endpoint_path: str, method: str) -> Dict[str, Any]:
    """
    从新格式测试用例创建Postman请求项
    
    Args:
        test_case: 测试用例
        endpoint_path: 端点路径
        method: HTTP方法
        
    Returns:
        Postman请求项
    """
    test_name = test_case.get("name", "Unnamed Test")
    description = test_case.get("description", "")
    
    # 从测试用例中获取请求信息
    request_info = test_case.get("request", {})
    request_path = request_info.get("path", endpoint_path)
    request_method = request_info.get("method", method)
    request_headers = request_info.get("headers", {})
    request_body = request_info.get("body", {})
    
    # 从测试用例中获取期望的响应信息
    expected_info = test_case.get("expected", {})
    expected_status = expected_info.get("status", 200)
    expected_headers = expected_info.get("headers", {})
    expected_body = expected_info.get("body", {})
    
    # 构建URL（使用环境变量）
    url = "{{base_url}}" + request_path.lstrip('/')
    
    # 创建请求对象
    request = {
        "method": request_method,
        "header": [],
        "url": build_url_object(url, {})  # 不使用URL参数
    }
    
    # 添加头部
    for header_name, header_value in request_headers.items():
        request["header"].append({
            "key": header_name,
            "value": str(header_value),
            "type": "text"
        })
    
    # 确保Content-Type头部存在
    content_type_exists = False
    for header in request["header"]:
        if header["key"].lower() == "content-type":
            content_type_exists = True
            break
    
    if not content_type_exists:
        request["header"].append({
            "key": "Content-Type",
            "value": "application/json",
            "type": "text"
        })
    
    # 添加请求体
    request["body"] = {
        "mode": "raw",
        "raw": json.dumps(request_body, ensure_ascii=False, indent=2),
        "options": {
            "raw": {
                "language": "json"
            }
        }
    }
    
    # 创建测试脚本
    test_script = create_test_script_new_format(expected_status, expected_headers, expected_body)
    
    # 创建签名生成前置脚本
    pre_request_script = create_signature_script()
    
    # 创建完整的请求项
    return {
        "name": test_name,
        "description": description,
        "event": [
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": test_script.split("\n")
                }
            },
            {
                "listen": "prerequest",
                "script": {
                    "type": "text/javascript",
                    "exec": pre_request_script.split("\n")
                }
            }
        ],
        "request": request,
        "response": []
    }

def create_test_script_new_format(expected_status: int, expected_headers: Dict[str, Any], expected_body: Dict[str, Any]) -> str:
    """
    为新格式创建Postman测试脚本
    
    Args:
        expected_status: 期望的HTTP状态码
        expected_headers: 期望的响应头
        expected_body: 期望的响应体
        
    Returns:
        测试脚本代码
    """
    # 开始测试脚本
    test_script = "pm.test(\"Status code test\", function() {\n"
    
    # 状态码验证
    test_script += f"    pm.response.to.have.status({expected_status});\n"
    test_script += "});\n\n"
    
    # 响应时间验证
    test_script += "pm.test(\"Response time is acceptable\", function() {\n"
    test_script += "    pm.expect(pm.response.responseTime).to.be.below(5000);\n"
    test_script += "});\n\n"
    
    # 响应头验证
    if expected_headers:
        for header_name, header_value in expected_headers.items():
            test_script += f"pm.test(\"Header {header_name} is correct\", function() {{\n"
            test_script += f"    pm.response.to.have.header(\"{header_name}\");\n"
            if header_value:
                test_script += f"    pm.expect(pm.response.headers.get(\"{header_name}\")).to.include(\"{header_value}\");\n"
            test_script += "});\n\n"
    
    # 响应体验证
    if expected_body:
        test_script += "pm.test(\"Response body validation\", function() {\n"
        test_script += "    var jsonData = pm.response.json();\n"
        
        for key, value in expected_body.items():
            if isinstance(value, str):
                test_script += f"    pm.expect(jsonData).to.have.property(\"{key}\");\n"
                test_script += f"    pm.expect(jsonData[\"{key}\"]).to.equal(\"{value}\");\n"
            else:
                test_script += f"    pm.expect(jsonData).to.have.property(\"{key}\");\n"
                test_script += f"    pm.expect(jsonData[\"{key}\"]).to.equal({value});\n"
        
        test_script += "});\n\n"
    
    return test_script

def create_postman_request_old_format(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """
    从旧格式测试用例创建Postman请求项
    
    Args:
        test_case: 测试用例
        
    Returns:
        Postman请求项
    """
    test_name = test_case.get("name", "Unnamed Test")
    # 强制使用POST方法
    method = "POST"
    path = test_case.get("path", "/")
    
    # 确定基本URL
    url_base = test_case.get("base_url", "")
    
    # 构建URL
    url = f"{url_base.rstrip('/')}/{path.lstrip('/')}" if url_base else "{{base_url}}/" + path.lstrip('/')
    
    # 获取接口名称用于Action参数
    action_name = test_case.get("action_name", "")
    
    # 创建请求对象
    request = {
        "method": method,
        "header": [],
        "url": build_url_object(url, {})  # 不使用URL参数
    }
    
    # 添加头部
    headers = test_case.get("headers", {})
    for header_name, header_value in headers.items():
        request["header"].append({
            "key": header_name,
            "value": str(header_value),
            "type": "text"
        })
    
    # 确保Content-Type头部存在
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
    
    # 合并所有参数到请求体
    request_data = dict(test_case.get("request_data", {}))
    
    # 添加查询参数到请求体
    query_params = dict(test_case.get("query_params", {}))
    for key, value in query_params.items():
        request_data[key] = value
    
    # 添加Action参数到请求体
    if action_name:
        request_data["Action"] = action_name
    
    # 添加请求体
    request["body"] = {
        "mode": "raw",
        "raw": json.dumps(request_data, ensure_ascii=False, indent=2),
        "options": {
            "raw": {
                "language": "json"
            }
        }
    }
    
    # 创建测试脚本
    test_script = create_test_script_old_format(test_case)
    
    # 创建签名生成前置脚本
    pre_request_script = create_signature_script()
    
    # 创建完整的请求项
    return {
        "name": test_name,
        "event": [
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": test_script.split("\n")
                }
            },
            {
                "listen": "prerequest",
                "script": {
                    "type": "text/javascript",
                    "exec": pre_request_script.split("\n")
                }
            }
        ],
        "request": request,
        "response": []
    }

def build_url_object(url: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    构建Postman URL对象，不添加查询参数（所有参数都在Body中）
    
    Args:
        url: 原始URL字符串
        query_params: 查询参数字典（不使用）
        
    Returns:
        Postman URL对象
    """
    # 基本URL对象
    url_object = {
        "raw": url
    }
    
    # 处理环境变量
    if url.startswith("{{") and "}}" in url:
        var_end = url.find("}}") + 2
        host_var = url[2:var_end-2]
        
        url_object["host"] = [f"{{{{base_url}}}}"]
        
        # 处理路径部分
        remaining = url[var_end:].lstrip('/')
        if remaining:
            url_object["path"] = remaining.split('/')
        
        return url_object
    
    # 解析协议
    if "://" in url:
        url_object["protocol"] = url.split("://")[0]
        host_and_path = url.split("://")[1]
    else:
        host_and_path = url
    
    # 解析主机和路径
    if "/" in host_and_path:
        host = host_and_path.split("/")[0]
        path_parts = host_and_path.split("/")[1:]
        url_object["host"] = host.split(".")
        if path_parts:
            url_object["path"] = path_parts
    else:
        url_object["host"] = host_and_path.split(".")
    
    # 不添加查询参数，因为所有参数都在Body中
    
    return url_object

def create_test_script_old_format(test_case: Dict[str, Any]) -> str:
    """
    为旧格式创建Postman测试脚本
    
    Args:
        test_case: 测试用例
        
    Returns:
        测试脚本代码
    """
    # 开始测试脚本
    test_script = "pm.test(\"Status code test\", function() {\n"
    
    # 状态码验证
    expected_status = test_case.get("expected_status", 200)
    test_script += f"    pm.response.to.have.status({expected_status});\n"
    test_script += "});\n\n"
    
    # 响应时间验证
    test_script += "pm.test(\"Response time is acceptable\", function() {\n"
    test_script += "    pm.expect(pm.response.responseTime).to.be.below(5000);\n"
    test_script += "});\n\n"
    
    # 自定义验证
    validations = test_case.get("validations", [])
    
    for validation in validations:
        validation_type = validation.get("type", "")
        
        if validation_type == "json_field" or validation_type == "json_path":
            field = validation.get("field", validation.get("path", ""))
            value = validation.get("value", validation.get("expected_value", ""))
            
            if field:
                test_script += f"pm.test(\"Check field {field}\", function() {{\n"
                test_script += f"    var jsonData = pm.response.json();\n"
                
                if isinstance(value, str):
                    test_script += f"    pm.expect(jsonData.{field}).to.equal(\"{value}\");\n"
                else:
                    test_script += f"    pm.expect(jsonData.{field}).to.equal({value});\n"
                
                test_script += "});\n\n"
        
        elif validation_type == "response_time":
            max_ms = validation.get("max_ms", 1000)
            test_script += f"pm.test(\"Response time is within {max_ms}ms\", function() {{\n"
            test_script += f"    pm.expect(pm.response.responseTime).to.be.below({max_ms});\n"
            test_script += "});\n\n"
        
        elif validation_type == "content_type":
            content_type = validation.get("value", "application/json")
            test_script += f"pm.test(\"Content-Type is {content_type}\", function() {{\n"
            test_script += f"    pm.response.to.have.header(\"Content-Type\");\n"
            test_script += f"    pm.expect(pm.response.headers.get(\"Content-Type\")).to.include(\"{content_type}\");\n"
            test_script += "});\n\n"
        
        elif validation_type == "body_contains":
            text = validation.get("text", "")
            if text:
                test_script += f"pm.test(\"Body contains '{text}'\", function() {{\n"
                test_script += f"    pm.expect(pm.response.text()).to.include(\"{text}\");\n"
                test_script += "});\n\n"
        
        elif validation_type == "status_code":
            status = validation.get("value", 200)
            test_script += f"pm.test(\"Status code is {status}\", function() {{\n"
            test_script += f"    pm.response.to.have.status({status});\n"
            test_script += "});\n\n"
    
    return test_script

def create_signature_script() -> str:
    """
    创建用于生成请求签名的前置脚本
    
    Returns:
        包含签名生成逻辑的JavaScript代码
    """
    return """// 1. 替换请求体中的变量（如 {{Region}}）
const rawBody = pm.variables.replaceIn(pm.request.body.raw);
let obj;
try {
  obj = JSON.parse(rawBody);
  console.log("替换变量后的请求体:", JSON.stringify(obj, null, 2));
} catch (e) {
  console.error("解析 JSON 失败:", e.message);
  throw e;
}

// 2. 从变量中读取密钥（检查变量名是否一致！）
const publicKey = pm.variables.get('PublicKey');
const privateKey = pm.variables.get('PrivateKey');
console.log("PublicKey:", publicKey); // 调试输出
console.log("PrivateKey:", privateKey); // 调试输出 

// 3. 将 PublicKey 添加到请求体
obj.PublicKey = publicKey;

// 4. 对键排序并构建签名字符串
const keys = Object.keys(obj).sort();
let tmp = keys.map(key => `${key}${obj[key]}`).join('');
tmp += privateKey; // 追加 PrivateKey
console.log("签名字符串:", tmp); // 关键调试点！

// 5. 使用 CryptoJS 生成 SHA1（兼容 Postman 环境）
try {
  const signature = CryptoJS.SHA1(tmp).toString(CryptoJS.enc.Hex);
  obj.Signature = signature;
  console.log("生成的签名:", signature);
} catch (e) {
  console.error("加密失败:", e.message);
  throw e;
}

// 6. 更新请求体
pm.request.body.raw = JSON.stringify(obj);
console.log("最终请求体:", pm.request.body.raw);"""

def convert_test_cases_to_postman(input_file: str, output_file: str) -> None:
    """
    将测试用例JSON文件转换为Postman集合文件
    
    Args:
        input_file: 输入的测试用例JSON文件路径
        output_file: 输出的Postman集合文件路径
    """
    try:
        # 读取测试用例
        with open(input_file, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        
        # 转换为Postman集合
        collection = convert_to_postman_collection(test_cases)
        
        # 写入Postman集合文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
    except Exception as e:
        raise Exception(f"转换测试用例失败: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python postman_converter.py <测试用例文件> <输出文件>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    convert_test_cases_to_postman(input_file, output_file) 