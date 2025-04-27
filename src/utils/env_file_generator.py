import json
import os
import uuid
from typing import Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)

def generate_environment_file(
    output_path: str, 
    env_vars: Optional[Dict[str, str]] = None, 
    env_name: str = "API Test AI Environment"
) -> str:
    """
    Generates an environment file for API testing.
    
    Args:
        output_path: Path where the environment file should be saved
        env_vars: Dictionary of environment variables to include
        env_name: Name of the environment
    
    Returns:
        Path to the generated environment file
    """
    # Use default values if no environment variables provided
    if not env_vars:
        env_vars = {
            "Region": "cn-bj2",
            "Zone": "cn-bj2-04",
            "ProjectId": "org-123456",
            "base_url": "https://api.ucloud.cn"
        }
    
    # Create environment file structure
    env_data = {
        "id": str(uuid.uuid4()),
        "name": env_name,
        "values": [
            {
                "key": key,
                "value": value,
                "type": "default",
                "enabled": True
            } for key, value in env_vars.items()
        ],
        "_postman_variable_scope": "environment"
    }
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write environment file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(env_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Environment file generated: {output_path}")
    return output_path

def load_environment_file(file_path: str) -> Dict[str, Any]:
    """
    Loads an environment file and returns its contents.
    
    Args:
        file_path: Path to the environment file
    
    Returns:
        Dictionary containing environment data
    """
    if not os.path.exists(file_path):
        logger.error(f"Environment file not found: {file_path}")
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            env_data = json.load(f)
        
        logger.info(f"Environment file loaded: {file_path}")
        return env_data
    except Exception as e:
        logger.error(f"Error loading environment file {file_path}: {str(e)}")
        return {}

def extract_env_vars(env_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extracts environment variables from an environment file data structure.
    
    Args:
        env_data: Environment file data
    
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    
    if not env_data or 'values' not in env_data:
        return env_vars
    
    for variable in env_data['values']:
        if 'key' in variable and 'value' in variable and variable.get('enabled', True):
            env_vars[variable['key']] = variable['value']
    
    return env_vars 