# Environment Generator

The API Test AI tool includes a utility for generating environment files that can be used with Postman or the API testing framework.

## Using the Environment Generator

There are three ways to generate environment files:

### 1. Using the main.py script

```
python -m src.main env [options]
```

Options:
- `-o, --output`: Output directory for the environment file (default: reports)
- `-u, --url`: Base URL for API testing
- `-n, --name`: Name of the environment (default: "API Test AI Environment")
- `--env-var`: Environment variables in format key=value. Can be specified multiple times.
- `-c, --config`: Path to configuration file (default: src/config/settings.yaml)

Example:
```
python -m src.main env -u https://api.example.com --env-var Region=eu-west-1 --env-var ProjectId=project-123
```

### 2. Using the project's script

```
./scripts/generate_env_file.py [options]
```

Options:
- `-o, --output`: Output path for environment file (default: reports/environment.json)
- `-u, --url`: Base URL for API testing (default: https://api.ucloud.cn)
- `-n, --name`: Name of the environment (default: "API Test AI Environment")
- `-f, --file`: Load environment variables from JSON file
- `-v, --vars`: Environment variables in format key=value. Can be specified multiple times.
- `--region`: Region value
- `--zone`: Zone value
- `--project-id`: Project ID value

Example:
```
./scripts/generate_env_file.py -u https://api.example.com --region eu-west-1 --project-id project-123
```

### 3. Using the standalone script

This script doesn't depend on the project structure and can be copied and used independently.

```
./scripts/standalone_env_generator.py [options]
```

Options:
- `-o, --output`: Output path for environment file (default: environment.json)
- `-u, --url`: Base URL for API testing (default: https://api.ucloud.cn)
- `-n, --name`: Name of the environment (default: "API Test AI Environment")
- `-f, --file`: Load environment variables from JSON file
- `-v, --var`: Environment variables in format key=value. Can be specified multiple times.
- `--region`: Region value
- `--zone`: Zone value
- `--project-id`: Project ID value

Example:
```
./scripts/standalone_env_generator.py -o my_environment.json -u https://api.example.com --region us-east-1
```

## Environment File Format

The generated environment file follows the Postman environment format:

```json
{
  "id": "auto-generated-uuid",
  "name": "API Test AI Environment",
  "values": [
    {
      "key": "base_url",
      "value": "https://api.example.com",
      "type": "default",
      "enabled": true
    },
    {
      "key": "Region",
      "value": "eu-west-1",
      "type": "default",
      "enabled": true
    },
    {
      "key": "ProjectId",
      "value": "project-123",
      "type": "default",
      "enabled": true
    }
  ],
  "_postman_variable_scope": "environment"
}
```

## Default Environment Variables

If no environment variables are provided, the following defaults are used:

- `Region`: "cn-bj2"
- `Zone`: "cn-bj2-04"
- `ProjectId`: "org-123456"
- `base_url`: "https://api.ucloud.cn"

You can override these defaults by:
1. Modifying the `api_environment` section in the config file (for the main script)
2. Providing values via command line arguments
3. Loading values from a JSON file 