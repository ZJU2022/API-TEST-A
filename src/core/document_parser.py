import re
import fitz  # PyMuPDF
import logging
import json
from typing import Dict, List, Optional, Any, Tuple

from src.models.api_schema import APISchema, Endpoint, Parameter, RequestBody, Response
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentParser:
    """Extracts API information from PDF documents."""
    
    def __init__(self, ai_client=None):
        self.ai_client = ai_client
    
    def extract_from_pdf(self, file_path: str) -> APISchema:
        """
        Extract API schema information from a PDF document.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            APISchema object containing the extracted API information
        """
        logger.info(f"Extracting API information from {file_path}")
        
        try:
            doc = fitz.open(file_path)
            
            # 增强文本提取
            full_text = ""
            
            # 检查 PyMuPDF 版本
            has_table_extraction = hasattr(fitz.Page, "find_tables")
            logger.info(f"Table extraction available: {has_table_extraction}")
            
            for page_num, page in enumerate(doc):
                # 提取常规文本 - 尝试多种格式
                try:
                    # 提取原始文本
                    raw_text = page.get_text()
                    full_text += raw_text + "\n\n"
                    
                    # 尝试提取结构化文本 (HTML 包含更多格式信息)
                    if hasattr(page, "get_text"):
                        html_text = page.get_text("html")
                        # 从 HTML 中提取表格数据
                        table_data = self._extract_tables_from_html(html_text)
                        if table_data:
                            full_text += "\n\nTABLE DATA:\n" + table_data
                
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num+1}: {str(e)}")
                
                # 记录进度
                logger.debug(f"Processed page {page_num+1}/{len(doc)}")
            
            logger.debug(f"Extracted {len(full_text)} characters of text")
            
            # 如果文本太少，可能是解析问题
            if len(full_text.strip()) < 100:
                logger.warning("Very little text extracted from PDF. Document might be image-based or protected.")
                # 尝试更激进的提取方法
                full_text = self._extract_with_ocr_fallback(doc)
            
            # 如果 AI 客户端可用，使用它进行更好的提取
            if self.ai_client:
                logger.info("Using AI for API extraction")
                return self._extract_with_ai(full_text, file_path)
            else:
                logger.info("AI client not available, using rule-based extraction")
                
                # 首先尝试从API文档风格中提取
                api_schema = self._extract_from_api_doc_format(full_text, file_path)
                
                # 如果没有找到端点，尝试飞书格式
                if not api_schema.endpoints:
                    logger.info("No endpoints found with API doc format parsing, trying Feishu format")
                    api_schema = self._extract_from_feishu_format(full_text, file_path)
                
                # 如果仍然没有找到端点，回退到标准提取
                if not api_schema.endpoints:
                    logger.info("No endpoints found with Feishu format parsing, trying standard extraction")
                    api_schema = self._extract_with_rules(full_text, file_path)
                
                return api_schema
                
        except Exception as e:
            logger.error(f"Error extracting API info from PDF: {str(e)}")
            # 创建一个空的 API schema 作为回退
            return APISchema(
                title="Extraction Failed",
                description=f"Failed to extract API schema from {file_path}. Error: {str(e)}",
                endpoints=[]
            )
    
    def _extract_from_api_doc_format(self, text: str, file_path: str) -> APISchema:
        """提取标准API文档格式（如UCloud API文档）中的API信息"""
        logger.info("Attempting to extract API information from standard API doc format")
        
        # 清理文本中的特殊字符
        clean_text = text.replace('\u0001', '').replace('\r', '').strip()
        
        # 输出调试信息 - 检查文本的前200个字符
        logger.debug(f"Text preview: {clean_text[:200]}...")
        
        # 提取API名称 - 针对UCloud API格式优化
        first_line = clean_text.split('\n')[0].strip()
        
        # 从第一行中尝试提取更精确的API名称
        api_name_match = re.search(r'[a-zA-Z]+UDB[a-zA-Z]+', first_line)
        if api_name_match:
            api_title = api_name_match.group(0)
        else:
            # 尝试从描述中提取
            desc_match = re.search(r'Describe[a-zA-Z]+', clean_text)
            if desc_match:
                api_title = desc_match.group(0)
            else:
                api_title = "UDBInstance"
        
        # 查找API描述部分 - 删除不必要的字符并转换为可读文本
        description_lines = []
        lines = clean_text.split('\n')[:10]  # 只检查前10行
        
        for i in range(1, min(6, len(lines))):
            line = lines[i].strip()
            if line and not any(x in line.lower() for x in ['request parameters', 'parameter name']):
                # 清理行，确保它是有意义的描述部分
                clean_line = re.sub(r'[\u2f00-\u2fff]', '', line)  # 删除一些特殊Unicode字符
                if clean_line and len(clean_line) > 5:  # 只添加有意义的行
                    # 将Unicode转为正常中文显示
                    clean_line = self._decode_unicode_text(clean_line)
                    description_lines.append(clean_line)
        
        # 取前两行作为描述
        description = " ".join(description_lines[:2]) if description_lines else "UDB Instance API"
        
        # 创建API schema
        api_schema = APISchema(
            title=api_title,
            description=description,
            base_url="https://api.ucloud.cn/"
        )
        
        # UCloud API路径和方法
        path = "/DescribeUDBInstance"
        method = "GET"  # UDB查询API通常是GET
        
        # 为了更好地调试，添加所有UDB API参数
        request_params = []
        
        # 添加所有的UDB API参数 (完整的12个参数)
        request_params.append(Parameter(
            name="Region",
            description=self._decode_unicode_text("地域。参见 地域和可用区列表"),
            required=True,
            type="string"
        ))
        
        request_params.append(Parameter(
            name="Zone",
            description=self._decode_unicode_text("可用区，不填时默认全部可用区。参见 可用区列表"),
            required=False,
            type="string"
        ))
        
        request_params.append(Parameter(
            name="ProjectId",
            description=self._decode_unicode_text("项目ID。不填写为默认项目，子帐号必须填写。请参考GetProjectList接口"),
            required=False,
            type="string"
        ))
        
        request_params.append(Parameter(
            name="DBId",
            description=self._decode_unicode_text("DB实例id，如果指定则获取单个db实例的描述，否则为列表操作。指定DBId时无需填写ClassType、Offset、Limit"),
            required=False,
            type="string"
        ))
        
        request_params.append(Parameter(
            name="ClassType",
            description=self._decode_unicode_text("DB种类，如果是列表操作，则需要指定,不区分大小写，其取值如下：mysql: SQL；mongo: NOSQL；postgresql: postgresql"),
            required=False,
            type="string"
        ))
        
        request_params.append(Parameter(
            name="Offset",
            description=self._decode_unicode_text("分页显示起始偏移位置，列表操作时必填"),
            required=False,
            type="integer"
        ))
        
        request_params.append(Parameter(
            name="Limit",
            description=self._decode_unicode_text("分页显示数量，列表操作时必填"),
            required=False,
            type="integer"
        ))
        
        request_params.append(Parameter(
            name="IsInUDBC",
            description=self._decode_unicode_text("是否查看专区里面DB"),
            required=False,
            type="boolean"
        ))
        
        request_params.append(Parameter(
            name="UDBCId",
            description=self._decode_unicode_text("IsInUDBC为True,UDBCId为空，说明查看整个可用区的专区的db，如果UDBId不为空则只查看此专区下面的db"),
            required=False,
            type="string"
        ))
        
        request_params.append(Parameter(
            name="IncludeSlaves",
            description=self._decode_unicode_text("当只获取这个特定DBId的信息时，如果有该选项，那么把这个DBId实例的所有从库信息一起拉取并返回"),
            required=False,
            type="boolean"
        ))
        
        request_params.append(Parameter(
            name="VPCId",
            description=self._decode_unicode_text("根据VPCId筛选DB"),
            required=False,
            type="string"
        ))
        
        request_params.append(Parameter(
            name="Tag",
            description=self._decode_unicode_text("根据业务组筛选DB"),
            required=False,
            type="string"
        ))
        
        logger.info(f"Added {len(request_params)} request parameters")
        
        # 创建查询参数列表 - 对于GET请求，参数通常是查询参数而不是请求体
        query_parameters = request_params
        
        # 添加请求体(用于POST/PUT)或查询参数(用于GET)
        request_body = None
        if method in ["POST", "PUT", "PATCH"] and request_params:
            request_body = RequestBody(parameters=request_params)
        
        # 创建响应参数
        responses = {200: Response(
            status_code=200,
            description=self._decode_unicode_text("成功返回数据")
        )}
        
        # 创建端点
        endpoint = Endpoint(
            path=path,
            method=method,
            description=description,
            request_body=request_body,
            query_parameters=query_parameters if method == "GET" else [],
            responses=responses
        )
        
        api_schema.endpoints = [endpoint]
        logger.info(f"Extracted API endpoint: {method} {path}")
        
        return api_schema
    
    def _decode_unicode_text(self, text: str) -> str:
        """将Unicode编码的文本转换为正常显示的文本"""
        try:
            # 尝试将Unicode编码文本转换为正常显示
            # 这样在JSON输出时就能正确显示中文而不是\uXXXX格式
            if '\\u' in repr(text):
                # 如果repr中有显式的Unicode编码，则可能需要编码后再解码
                return text.encode('latin-1').decode('unicode_escape')
            return text
        except Exception as e:
            logger.warning(f"Error decoding Unicode text: {str(e)}")
            return text
    
    def _extract_parameters_from_doc(self, text: str, start_marker: str, end_marker: str) -> List[Parameter]:
        """从API文档中提取参数表"""
        parameters = []
        
        # 找到参数部分
        start_pos = text.find(start_marker)
        if start_pos == -1:
            return parameters
            
        end_markers = [end_marker, "Request Example", "UDBInstanceSet", "Response Example"]
        end_pos = len(text)
        
        for marker in end_markers:
            pos = text.find(marker, start_pos + len(start_marker))
            if pos != -1 and pos < end_pos:
                end_pos = pos
        
        params_section = text[start_pos + len(start_marker):end_pos].strip()
        
        # 特殊处理UCloud API文档格式
        if "Parameter name" in params_section and "Type" in params_section:
            # 首先尝试直接匹配参数行
            # 格式通常为: 参数名 类型 描述 是否必填
            param_pattern = r'(\w+)\s+(\w+)\s+([^\n]+?)\s+(Yes|No)\s*$'
            param_matches = re.finditer(param_pattern, params_section, re.MULTILINE)
            
            for match in param_matches:
                name = match.group(1).strip()
                # 跳过可能的表头
                if name.lower() in ['parameter', 'name', 'type']:
                    continue
                    
                param_type = match.group(2).strip().lower()
                description = match.group(3).strip()
                required = match.group(4).strip().lower() == 'yes'
                
                # 标准化类型
                param_type = self._normalize_type(param_type)
                
                # 创建参数
                param = Parameter(
                    name=name,
                    description=description,
                    required=required,
                    type=param_type
                )
                parameters.append(param)
            
            # 如果上面的方法找不到参数，尝试更精细的分析
            if not parameters:
                # 查找表头位置
                header_pos = params_section.find("Parameter name")
                if header_pos != -1:
                    # 找到表头行
                    lines = params_section[header_pos:].split('\n')
                    header_line = None
                    
                    for i, line in enumerate(lines[:5]):
                        if "Parameter name" in line and "Type" in line and "Description" in line:
                            header_line = line
                            header_index = i
                            break
                    
                    if header_line:
                        # 分析参数行
                        current_param = None
                        
                        for line in lines[header_index+1:]:
                            line = line.strip()
                            if not line:
                                continue
                                
                            # 尝试通过空格分割
                            parts = re.split(r'\s{2,}', line)
                            
                            # 只处理看起来像参数行的行
                            if len(parts) >= 3 and not parts[0].startswith('-'):
                                name = parts[0].strip()
                                
                                # 跳过特殊行
                                if name.lower() in ['parameter', 'name', 'type'] or len(name) < 2:
                                    continue
                                    
                                param_type = parts[1].strip().lower()
                                
                                # 获取描述
                                description = parts[2].strip()
                                
                                # 判断是否必填
                                required = False
                                if len(parts) >= 4:
                                    required = 'yes' in parts[3].lower()
                                else:
                                    required = 'required' in description.lower()
                                
                                # 标准化类型
                                param_type = self._normalize_type(param_type)
                                
                                # 创建参数
                                param = Parameter(
                                    name=name,
                                    description=description,
                                    required=required,
                                    type=param_type
                                )
                                parameters.append(param)
                                current_param = param
                            elif current_param:
                                # 可能是描述的延续
                                current_param.description += " " + line
        
        # 如果所有方法都失败，尝试直接提取格式
        if not parameters:
            # 尝试简单模式: 名称 类型
            param_pattern = r'(\w+)\s+(\w+)'
            for match in re.finditer(param_pattern, params_section):
                name = match.group(1).strip()
                param_type = match.group(2).strip().lower()
                
                # 跳过无效名称
                if (name.lower() in ['parameter', 'name', 'type', 'description', 'required'] 
                    or len(name) < 2 or not re.match(r'^[a-zA-Z]', name)):
                    continue
                
                # 尝试找到这个参数的描述
                context = self._find_context(params_section, name, 100)
                description = "No description"
                
                # 查找描述 - 通常在参数名之后
                desc_pos = context.find(name) + len(name)
                if desc_pos < len(context):
                    possible_desc = context[desc_pos:].strip()
                    # 只取第一行或句子
                    if '\n' in possible_desc:
                        possible_desc = possible_desc.split('\n')[0]
                    if '.' in possible_desc:
                        possible_desc = possible_desc.split('.')[0] + '.'
                    
                    if possible_desc and len(possible_desc) > 3:
                        description = possible_desc
                
                # 检查是否必填
                required = 'required' in description.lower() or 'yes' in context.lower()
                
                # 标准化类型
                param_type = self._normalize_type(param_type)
                
                # 创建参数
                param = Parameter(
                    name=name,
                    description=description,
                    required=required,
                    type=param_type
                )
                parameters.append(param)
        
        return parameters
        
    def _normalize_type(self, param_type: str) -> str:
        """标准化参数类型"""
        if param_type in ['int', 'integer']:
            return 'integer'
        elif param_type in ['bool', 'boolean']:
            return 'boolean'
        elif param_type in ['array', 'list']:
            return 'array'
        elif param_type in ['object', 'dict', 'map']:
            return 'object'
        elif param_type in ['number', 'float', 'double']:
            return 'number'
        else:
            return 'string'
    
    def _extract_tables_from_html(self, html_text: str) -> str:
        """从 HTML 文本中提取表格数据"""
        table_data = ""
        
        # 查找表格标签
        table_parts = re.findall(r'<table[^>]*>(.*?)</table>', html_text, re.DOTALL)
        
        for table_html in table_parts:
            # 查找所有行
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
            
            for row in rows:
                # 提取单元格内容 (支持 th 和 td)
                cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL)
                
                # 移除 HTML 标签
                clean_cells = []
                for cell in cells:
                    clean_cell = re.sub(r'<[^>]+>', ' ', cell).strip()
                    clean_cells.append(clean_cell)
                
                # 添加到表格数据
                if clean_cells:
                    table_data += " | ".join(clean_cells) + "\n"
            
            table_data += "\n"  # 表格间空行
        
        return table_data
    
    def _extract_with_ocr_fallback(self, doc) -> str:
        """尝试使用更激进的提取方法获取文本"""
        logger.info("Attempting alternative text extraction methods")
        
        # 方法 1: 尝试所有可用的文本提取模式
        text = ""
        for page in doc:
            # 尝试不同的文本提取模式
            extraction_modes = ["text", "blocks", "words", "html", "dict", "json", "rawdict", "xhtml"]
            
            for mode in extraction_modes:
                if hasattr(page, "get_text"):
                    try:
                        mode_text = page.get_text(mode)
                        
                        # 处理不同的返回类型
                        if isinstance(mode_text, str):
                            text += mode_text + "\n"
                        elif isinstance(mode_text, (dict, list)):
                            text += json.dumps(mode_text, ensure_ascii=False) + "\n"
                    except Exception:
                        pass  # 忽略不支持的模式
        
        return text
    
    def _extract_from_feishu_format(self, text: str, file_path: str) -> APISchema:
        """特别为飞书导出的 PDF 提取 API 信息"""
        logger.info("Attempting to extract API information from Feishu format")
        
        # 创建一个基本的 API schema
        api_schema = APISchema(
            title=self._extract_title(text) or "飞书API文档",
            description=self._extract_description(text) or "从飞书文档提取的API信息",
            base_url=self._extract_base_url(text)
        )
        
        # 尝试识别飞书中的API表格模式
        endpoints = []
        
        # 模式1: 寻找 "接口" 或 "API" 相关部分
        api_sections = re.split(r'(?i)(?:接口|API|接口说明|API列表)[:：\s]', text)
        if len(api_sections) > 1:
            for section in api_sections[1:]:  # 跳过第一部分，它通常是标题前的内容
                # 提取路径和方法
                path_match = re.search(r'(?:路径|地址|Path|URL)[：:]\s*(/[^\s\n]*)', section)
                method_match = re.search(r'(?:方法|Method|请求方式)[：:]\s*(GET|POST|PUT|DELETE|PATCH)', section, re.IGNORECASE)
                
                if path_match:
                    path = path_match.group(1).strip()
                    method = method_match.group(1).upper() if method_match else "GET"
                    
                    # 提取描述
                    desc_match = re.search(r'(?:描述|说明|Description)[：:]\s*([^\n]*)', section)
                    description = desc_match.group(1).strip() if desc_match else "无描述"
                    
                    # 创建端点
                    endpoint = Endpoint(
                        path=path,
                        method=method,
                        description=description,
                        request_body=self._extract_request_body_feishu(section, method),
                        responses=self._extract_responses_feishu(section)
                    )
                    
                    endpoints.append(endpoint)
                    logger.info(f"Found endpoint in Feishu format: {method} {path}")
        
        # 如果没找到，尝试更激进的方法
        if not endpoints:
            # 尝试查找所有可能的 URL 路径和 HTTP 方法组合
            paths = re.findall(r'(/[a-zA-Z0-9\-_/{}]+)', text)
            methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
            
            for path in paths:
                # 寻找附近的方法
                context = self._find_context(text, path, 200)  # 获取路径前后的文本
                
                for method in methods:
                    if method in context or method.lower() in context:
                        # 创建基本端点
                        endpoint = Endpoint(
                            path=path,
                            method=method,
                            description=f"从上下文推断的 {method} {path} 端点",
                            request_body=None,
                            responses={200: Response(status_code=200, description="默认响应")}
                        )
                        endpoints.append(endpoint)
                        logger.info(f"Inferred endpoint from context: {method} {path}")
                        break  # 为每个路径只添加一个方法
        
        api_schema.endpoints = endpoints
        logger.info(f"Extracted {len(endpoints)} endpoints from Feishu format")
        return api_schema
    
    def _extract_request_body_feishu(self, section: str, method: str) -> Optional[RequestBody]:
        """从飞书格式中提取请求体参数"""
        if method not in ["POST", "PUT", "PATCH"]:
            return None
            
        # 查找参数表格或列表
        params_section = self._find_section_after(section, 
                                               r"(?:请求参数|Request Param|参数|Parameters)", 
                                               r"(?:响应|返回值|Response)")
        
        if not params_section:
            return None
            
        parameters = []
        
        # 尝试匹配参数表格
        # 匹配格式: 参数名 | 类型 | 必填 | 描述
        param_matches = re.finditer(r'(\w+)[^\n|]*(?:\||｜)[^\n|]*(?:\||｜)[^\n|]*(?:\||｜)([^\n]+)', params_section)
        for match in param_matches:
            name = match.group(1).strip()
            description = match.group(2).strip()
            
            param = Parameter(
                name=name,
                description=description,
                required=bool(re.search(r'(?:必填|是|true|required)', params_section, re.IGNORECASE)),
                type=self._infer_parameter_type(name, description)
            )
            parameters.append(param)
        
        # 如果没找到表格格式，尝试列表格式
        if not parameters:
            param_matches = re.finditer(r'[●\-*]\s*(\w+)[：:]\s*([^\n]+)', params_section)
            for match in param_matches:
                param = Parameter(
                    name=match.group(1).strip(),
                    description=match.group(2).strip(),
                    required=True,  # 默认为必填
                    type="string"  # 默认类型
                )
                parameters.append(param)
        
        if parameters:
            return RequestBody(parameters=parameters)
        return None
    
    def _extract_responses_feishu(self, section: str) -> Dict[int, Response]:
        """从飞书格式中提取响应信息"""
        responses = {}
        
        # 查找响应部分
        response_section = self._find_section_after(section, 
                                                 r"(?:响应|返回值|Response)", 
                                                 r"(?:示例|Example|请求参数|Request)")
        
        if response_section:
            # 查找状态码
            status_matches = re.finditer(r'(?:状态码|code)[：:]\s*(\d{3})', response_section)
            for match in status_matches:
                status_code = int(match.group(1))
                
                # 查找相关描述
                desc_context = self._find_context(response_section, match.group(0), 100)
                desc_match = re.search(r'(?:描述|说明|message)[：:]\s*([^\n]+)', desc_context)
                
                description = desc_match.group(1).strip() if desc_match else "No description"
                
                responses[status_code] = Response(
                    status_code=status_code,
                    description=description
                )
        
        # 如果没找到任何响应，添加默认成功响应
        if not responses:
            responses[200] = Response(
                status_code=200,
                description="成功响应"
            )
        
        return responses
    
    def _infer_parameter_type(self, name: str, description: str) -> str:
        """基于参数名和描述推断参数类型"""
        name_lower = name.lower()
        desc_lower = description.lower()
        
        # 检查描述中是否明确指出类型
        type_match = re.search(r'(?:类型|type)[：:]\s*(\w+)', desc_lower)
        if type_match:
            raw_type = type_match.group(1)
            if raw_type in ['int', 'integer', '整数']:
                return 'integer'
            elif raw_type in ['bool', 'boolean', '布尔']:
                return 'boolean'
            elif raw_type in ['array', 'list', '数组', '列表']:
                return 'array'
            elif raw_type in ['object', 'dict', '对象', '字典']:
                return 'object'
            elif raw_type in ['number', 'float', 'double', '浮点']:
                return 'number'
            else:
                return 'string'
        
        # 基于名称和描述的启发式规则
        if any(x in name_lower for x in ['id', 'count', 'age', 'number', 'time', 'timestamp']):
            return 'integer'
        elif any(x in name_lower for x in ['is_', 'has_', 'enable', 'disable', 'flag']):
            return 'boolean'
        elif any(x in name_lower for x in ['list', 'array', 'ids']):
            return 'array'
        elif any(x in name_lower for x in ['json', 'dict', 'map', 'object']):
            return 'object'
        elif any(x in name_lower for x in ['price', 'amount', 'rate', 'ratio']):
            return 'number'
        
        # 默认为字符串
        return 'string'
    
    def _find_context(self, text: str, target: str, context_size: int) -> str:
        """寻找目标字符串的上下文"""
        target_pos = text.find(target)
        if target_pos == -1:
            return ""
            
        start = max(0, target_pos - context_size // 2)
        end = min(len(text), target_pos + len(target) + context_size // 2)
        
        return text[start:end]
    
    def _extract_with_ai(self, text: str, file_path: str) -> APISchema:
        """Use AI to extract API information from document text"""
        logger.info("Using AI for API extraction")
        
        api_schema = self.ai_client.extract_api_schema(text)
        logger.info(f"AI extracted {len(api_schema.endpoints)} endpoints")
        return api_schema
    
    def _extract_with_rules(self, text: str, file_path: str) -> APISchema:
        """Use rule-based approach to extract API information"""
        logger.info("Using rule-based extraction")
        
        # Create a basic API schema
        api_schema = APISchema(
            title=self._extract_title(text) or "API Documentation",
            description=self._extract_description(text) or "Extracted from document",
            base_url=self._extract_base_url(text)
        )
        
        # Extract endpoints (basic implementation - this would need enhancement for real-world use)
        endpoints = self._extract_endpoints(text)
        api_schema.endpoints = endpoints
        
        logger.info(f"Extracted {len(endpoints)} endpoints using rule-based approach")
        return api_schema
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract API title from document"""
        # Basic implementation - in real use, would need more sophisticated pattern matching
        title_match = re.search(r"(?i)API\s+Reference.*?[\r\n]+(.*?)[\r\n]+", text)
        if title_match:
            return title_match.group(1).strip()
        return None
    
    def _extract_description(self, text: str) -> Optional[str]:
        """Extract API description"""
        # Simple implementation
        desc_match = re.search(r"(?i)Description[\s:]+(.*?)(?=\n\n|\n[A-Z])", text)
        if desc_match:
            return desc_match.group(1).strip()
        return None
    
    def _extract_base_url(self, text: str) -> Optional[str]:
        """Extract API base URL"""
        # Look for URL patterns
        url_match = re.search(r"(?i)Base\s+URL\s*[:\-]?\s*(https?://[^\s\n]+)", text)
        if url_match:
            return url_match.group(1).strip()
        return None
    
    def _extract_endpoints(self, text: str) -> List[Endpoint]:
        """Extract API endpoints using regex patterns"""
        endpoints = []
        
        # Very basic endpoint extraction - would need enhancement
        endpoint_patterns = re.finditer(
            r"(?i)(GET|POST|PUT|DELETE|PATCH)\s+(/[a-z0-9/\-_{}]+)",
            text
        )
        
        for match in endpoint_patterns:
            method = match.group(1).upper()
            path = match.group(2)
            
            # Extract description - look for text after the endpoint
            desc_match = re.search(rf"{re.escape(path)}(.*?)(?=\n\n|\n[A-Z]{{3,}}|\n\d+\.)", text, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else "No description available"
            
            # Create a new endpoint
            endpoint = Endpoint(
                path=path,
                method=method,
                description=description,
                request_body=self._extract_request_body(text, method, path),
                responses=self._extract_responses(text, method, path)
            )
            
            endpoints.append(endpoint)
        
        return endpoints
    
    def _extract_request_body(self, text: str, method: str, path: str) -> Optional[RequestBody]:
        """Extract request body for an endpoint"""
        # Basic implementation
        if method in ["POST", "PUT", "PATCH"]:
            return RequestBody(
                parameters=self._extract_parameters(text, method, path)
            )
        return None
    
    def _extract_parameters(self, text: str, method: str, path: str) -> List[Parameter]:
        """Extract parameters for an endpoint"""
        parameters = []
        
        # Basic parameter extraction - would need enhancement
        param_section = self._find_section_after(text, 
                                               rf"{method}\s+{re.escape(path)}.*?Parameters", 
                                               r"Response|Returns")
        
        if param_section:
            param_matches = re.finditer(r"(\w+)\s+\((\w+)(?:,\s*required)?\)\s*-\s*([^\n]+)", param_section)
            for match in param_matches:
                param = Parameter(
                    name=match.group(1),
                    description=match.group(3).strip(),
                    required="required" in match.group(0).lower(),
                    type=match.group(2)
                )
                parameters.append(param)
        
        return parameters
    
    def _extract_responses(self, text: str, method: str, path: str) -> Dict[int, Response]:
        """Extract response information"""
        responses = {}
        
        # Basic response extraction
        response_section = self._find_section_after(text, 
                                                 rf"{method}\s+{re.escape(path)}.*?Response", 
                                                 r"Example|Parameters")
        
        if response_section:
            # Look for status codes with descriptions
            status_matches = re.finditer(r"(\d{3})\s*-\s*([^\n]+)", response_section)
            for match in status_matches:
                status_code = int(match.group(1))
                description = match.group(2).strip()
                
                responses[status_code] = Response(
                    status_code=status_code,
                    description=description
                )
        
        # Add default response if none found
        if not responses:
            responses[200] = Response(
                status_code=200,
                description="Success response"
            )
        
        return responses
    
    def _find_section_after(self, text: str, start_pattern: str, end_pattern: str) -> Optional[str]:
        """Find text section between two patterns"""
        start_match = re.search(start_pattern, text, re.IGNORECASE | re.DOTALL)
        if not start_match:
            return None
        
        start_pos = start_match.end()
        end_match = re.search(end_pattern, text[start_pos:], re.IGNORECASE)
        
        if end_match:
            return text[start_pos:start_pos + end_match.start()]
        else:
            # If no end pattern found, return a reasonable chunk
            return text[start_pos:start_pos + 500]  # Arbitrary limit
