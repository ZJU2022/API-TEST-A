# API-Test-AI

API-Test-AI 是一个自动化 API 测试工具，能够根据 API 文档（Markdown格式）生成测试用例并执行测试。本工具可以解析 Markdown 格式的 API 文档，提取 API 结构信息，生成全面的测试用例，并执行测试生成报告。

## 特性

- **API Markdown文档解析**：从 Markdown 文档中提取 API 结构信息
- **全面的测试用例生成**：
  - 有效路径测试（正常参数）
  - 边界值测试（数值和字符串参数）
  - 缺失必填参数测试
  - 无效数据类型测试
  - 性能测试
  - 文档验证测试
- **灵活的测试执行**：
  - 使用 Python requests 直接执行
  - 与 Postman 集成，用于可视化检查和执行
- **AI 增强**：
  - 使用 AI 改进 API 结构提取
  - 生成更智能的测试用例
  - 支持 OpenAI 和本地 LLM 模型

## 快速开始

### 环境准备

确保你已安装以下依赖：
- Python 3.10+
- Postman (用于可视化和执行测试)
- 大语言模型访问（OpenAI API Key或本地大模型，用于AI增强测试用例生成）

### 使用指南

#### 命令一：从 API 文档生成测试用例（无需AI）

从 API 文档自动生成测试用例并执行，无需AI辅助：

```bash
# 在项目根目录执行
python3.10 scripts/auto_postman_post.py -f docs/api_document.md -u https://api.ucloud.cn
python3.10 scripts/auto_postman_post.py -f docs/test.md -u https://api.ucloud.cn
```

此命令将解析 Markdown 格式的 API 文档并生成相应的POST测试用例，参数放在请求体(Body)中而不是URL参数中，然后转换为 Postman 格式并自动打开 Postman。

**特点：**
- 所有生成的请求都是POST方法
- 所有参数都放在请求体中，而不是URL参数
- 不依赖AI功能，使用内部文档解析逻辑
- 请确保docs目录中有api_document.md文件，或提供其他Markdown格式API文档路径

如果需要使用结构化测试用例生成器，提供更全面的测试场景覆盖，可以使用：

```bash
# 在项目根目录执行
python3.10 scripts/auto_postman_structured.py -f docs/api_document.md -u https://api.ucloud.cn
```

结构化测试用例生成器提供以下优势：
- 使用结构化的TestCase数据模型
- 更全面的测试场景覆盖：
  - 等价类测试（必填/选填参数组合）
  - 边界值测试（数值型和字符串型参数）
  - 异常测试（缺失必填参数、错误类型）
  - 特殊场景（幂等性、性能测试）

#### 命令二：使用 AI 生成测试用例并执行

使用AI技术生成测试用例并自动打开 Postman：

```bash
# 设置OpenAI API密钥
export OPENAI_API_KEY=您的密钥

# 在项目根目录执行
python3.10 src/main.py run -f docs/api_document.md -u https://api.ucloud.cn --postman
```

此命令将使用 AI 技术从 Markdown 文档中提取 API 信息，生成测试用例，执行测试，并在 Postman 中打开结果供查看。

**注意**: 
1. 使用此命令前，请设置 AI 模型（可选择OpenAI或本地模型）
2. 确保 docs/api_document.md 文件存在，或者使用其他API文档路径。如果没有Markdown文档，可以使用以下方式创建简单API描述文件：
```bash
# 在项目根目录执行
mkdir -p docs
echo '{"title": "测试API", "description": "简单测试API", "endpoints": [{"path": "/test", "method": "GET", "description": "测试接口"}]}' > docs/simple_api.json
python3.10 src/main.py run -f docs/simple_api.json -u https://api.ucloud.cn --postman
```

## 环境配置

### AI 模型配置

默认使用 `gpt-3.5-turbo` 模型。可以通过编辑 `src/config/settings.yaml` 文件配置:

#### OpenAI模型:
```yaml
ai:
  provider: openai
  model: gpt-3.5-turbo  # 可选: gpt-3.5-turbo, gpt-4 (需要访问权限)
  # api_key: YOUR_KEY   # 建议通过环境变量设置
```

#### 本地大模型:
```yaml
ai:
  provider: local_llm
  model: llama3      # 使用本地运行的模型
  endpoint: http://localhost:8080/v1  # 本地API端点
  api_key: not-needed  # 本地模型通常不需要密钥
```

### API 测试环境配置

为了配置 API 测试环境变量（如基础 URL、区域等），可以使用环境变量生成器：

```bash
# 在项目根目录执行
python3.10 scripts/standalone_env_generator.py --url https://api.ucloud.cn --name "测试环境" --output my_environment.json --var api_key=YOUR_API_KEY --var user_id=YOUR_USER_ID
```

此命令生成 Postman 环境文件，设置以下环境变量：
- `base_url`: API 测试的基础URL
- `api_key`: API服务的访问密钥（非 OpenAI 密钥）
- `user_id`: API服务的用户ID

默认情况下，环境文件还会包含以下变量：
- `Region`: "cn-bj2"
- `Zone`: "cn-bj2-04"
- `ProjectId`: "org-123456"

### OpenAI API 密钥配置

OpenAI 模型需要 API 密钥，有两种方式配置：

1. 设置环境变量 (推荐)：
```bash
export OPENAI_API_KEY=您的密钥
```

2. 在配置文件中设置(`src/config/settings.yaml`)：
```yaml
ai:
  provider: openai
  model: gpt-3.5-turbo
  api_key: 您的OpenAI_API密钥
```

**注意**: API测试环境变量中的`api_key`用于被测试API的认证，与OpenAI API密钥不同。

## 清理生成的临时文件

删除执行过程中生成的所有临时文件：

```bash
# 在项目根目录执行
python3.10 scripts/cleanup.py
```

此命令将清理测试过程中生成的所有临时文件，包括测试用例 JSON 文件、报告文件、日志文件等。

## 更多信息

有关详细的使用说明和高级配置选项，请参考项目文档或联系项目维护者。