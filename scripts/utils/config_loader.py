"""
Configuration loader for SmartSync database migrations.

Loads database credentials from etc/config/config.yaml or environment variables.
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Optional


def get_repo_root() -> Path:
    """Get repository root directory."""
    return Path(__file__).parent.parent.parent


def load_config_yaml() -> Dict[str, str]:
    """
    Load database configuration from etc/config/config.yaml.
    
    Returns:
        Dict with DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    """
    config_path = get_repo_root() / "etc" / "config" / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            "Please create etc/config/config.yaml with database credentials."
        )
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Extract from nested structure (Kubernetes ConfigMap format)
    try:
        app_config_str = config['data']['app-config.yaml']
        app_config = yaml.safe_load(app_config_str)
        
        return {
            'DB_HOST': app_config.get('DB_HOST', 'localhost'),
            'DB_PORT': app_config.get('DB_PORT', '5432'),
            'DB_NAME': app_config.get('DB_NAME', 'postgres'),
            'DB_USER': app_config.get('DB_USER', 'smartsync'),
            'DB_PASSWORD': app_config.get('DB_PASSWORD', 'smartsync'),
        }
    except (KeyError, TypeError):
        # Fallback for direct YAML format
        return {
            'DB_HOST': config.get('DB_HOST', 'localhost'),
            'DB_PORT': config.get('DB_PORT', '5432'),
            'DB_NAME': config.get('DB_NAME', 'postgres'),
            'DB_USER': config.get('DB_USER', 'smartsync'),
            'DB_PASSWORD': config.get('DB_PASSWORD', 'smartsync'),
        }


def load_database_url(service_name: Optional[str] = None) -> str:
    """
    Generate PostgreSQL database URL.
    
    Priority:
    1. Environment variable {SERVICE}_DATABASE_URL
    2. Environment variable DATABASE_URL
    3. Shared config from etc/config/config.yaml
    4. Fallback to localhost
    
    Args:
        service_name: Service name (e.g., 'auth', 'platform'). If provided,
                     checks {SERVICE}_DATABASE_URL env var first.
    
    Returns:
        PostgreSQL connection URL (sync format for Alembic)
    """
    # Priority 1: Service-specific env var
    if service_name:
        env_var_name = f"{service_name.upper()}_DATABASE_URL"
        url = os.getenv(env_var_name)
        if url:
            return url.replace("+asyncpg", "")
    
    # Priority 2: Generic DATABASE_URL env var
    url = os.getenv("DATABASE_URL")
    if url:
        return url.replace("+asyncpg", "")
    
    # Priority 3: Load from config.yaml
    try:
        config = load_config_yaml()
        
        # Override from individual env vars if set
        db_host = os.getenv("DB_HOST", config['DB_HOST'])
        db_port = os.getenv("DB_PORT", config['DB_PORT'])
        db_name = os.getenv("DB_NAME", config['DB_NAME'])
        db_user = os.getenv("DB_USER", config['DB_USER'])
        db_password = os.getenv("DB_PASSWORD", config['DB_PASSWORD'])
        
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    except FileNotFoundError:
        # Priority 4: Fallback for local development
        return "postgresql://smartsync:smartsync@localhost:5432/smartsync_dev"


def get_db_config() -> Dict[str, str]:
    """
    Get database configuration as dictionary.
    
    Returns:
        Dict with connection parameters and full DATABASE_URL
    """
    try:
        config = load_config_yaml()
        config['DATABASE_URL'] = load_database_url()
        return config
    except FileNotFoundError:
        return {
            'DB_HOST': 'localhost',
            'DB_PORT': '5432',
            'DB_NAME': 'smartsync_dev',
            'DB_USER': 'smartsync',
            'DB_PASSWORD': 'smartsync',
            'DATABASE_URL': 'postgresql://smartsync:smartsync@localhost:5432/smartsync_dev'
        }


if __name__ == "__main__":
    # Test config loading
    print("Testing config loader...")
    print("\nDatabase Config:")
    config = get_db_config()
    for key, value in config.items():
        if key == 'DB_PASSWORD':
            print(f"  {key}: {'*' * len(value)}")
        else:
            print(f"  {key}: {value}")
