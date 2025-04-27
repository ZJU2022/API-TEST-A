# Standalone Environment File Generator for API Testing

This script generates Postman environment files for API testing. It has no dependencies outside the Python standard library and can be used independently.

## Features

- Generate Postman/Newman compatible environment files
- Support for common API testing environment variables (Region, Zone, ProjectId, base URL)
- Load environment variables from existing files
- Specify variables via command line
- No external dependencies, just Python standard library

## Installation

1. Copy the `standalone_env_generator.py` script to your desired location
2. Make it executable (on Unix-like systems):
   ```bash
   chmod +x standalone_env_generator.py
   ```

## Usage

```
./standalone_env_generator.py [options]
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

## Examples

### Basic usage

```bash
./standalone_env_generator.py -o my_environment.json -u https://api.example.com
```

### Adding specific region, zone, and project ID

```bash
./standalone_env_generator.py -o region_env.json --region us-east-1 --zone us-east-1a --project-id project-123
```

### Adding custom variables

```bash
./standalone_env_generator.py -o custom_env.json -v ApiKey=12345abcde -v UserID=user123
```

### Loading variables from a file

```bash
./standalone_env_generator.py -o combined_env.json -f existing_env.json -v NewVar=newvalue
```

## Output Format

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
      "value": "us-east-1",
      "type": "default",
      "enabled": true
    }
  ],
  "_postman_variable_scope": "environment",
  "_postman_exported_at": "2023-04-25T10:00:00.000Z",
  "_postman_exported_using": "API-Test-AI/1.0"
}
```

## Default Environment Variables

If no environment variables are provided, the following defaults are used:

- `Region`: "cn-bj2"
- `Zone`: "cn-bj2-04"
- `ProjectId`: "org-123456"
- `base_url`: "https://api.ucloud.cn"

## License

This script is provided under the MIT License. 