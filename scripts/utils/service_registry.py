"""
Service registry for SmartSync microservices.

Auto-discovers all services and their Alembic configurations.
"""
from pathlib import Path
from typing import List, Dict, Optional


# Service definitions: name, schema, description
SERVICES = [
    {
        "name": "auth-service",
        "schema": "auth",
        "path": "auth-service",
        "env_prefix": "AUTH",
        "description": "Authentication & RBAC Service"
    },
    {
        "name": "platform-service",
        "schema": "platform",
        "path": "platform-service",
        "env_prefix": "PLATFORM",
        "description": "Platform Management Service (Tenants, Schools, Subscriptions)"
    },
    {
        "name": "academic-service",
        "schema": "academic",
        "path": "academic-service",
        "env_prefix": "ACADEMIC",
        "description": "Academic Management Service (Classes, Subjects, Grades)"
    },
    {
        "name": "administration-service",
        "schema": "administration",
        "path": "administration-service",
        "env_prefix": "ADMINISTRATION",
        "description": "School Administration Service"
    },
    {
        "name": "management-service",
        "schema": "management",
        "path": "management-service",
        "env_prefix": "MANAGEMENT",
        "description": "General Management Service"
    },
    {
        "name": "finance-service",
        "schema": "finance",
        "path": "finance-service",
        "env_prefix": "FINANCE",
        "description": "Finance & Billing Service"
    },
    {
        "name": "hr-service",
        "schema": "hr",
        "path": "hr-service",
        "env_prefix": "HR",
        "description": "Human Resources Service"
    },
    {
        "name": "hostel-service",
        "schema": "hostel",
        "path": "hostel-service",
        "env_prefix": "HOSTEL",
        "description": "Hostel Management Service"
    },
    {
        "name": "transport-service",
        "schema": "transport",
        "path": "transport-service",
        "env_prefix": "TRANSPORT",
        "description": "Transport Management Service"
    },
    {
        "name": "notification-service",
        "schema": "notification",
        "path": "notification-service",
        "env_prefix": "NOTIFICATION",
        "description": "Notification & Messaging Service"
    },
    {
        "name": "library-service",
        "schema": "library",
        "path": "library-service",
        "env_prefix": "LIBRARY",
        "description": "Library Management Service"
    },
    {
        "name": "security-service",
        "schema": "security",
        "path": "security-service",
        "env_prefix": "SECURITY",
        "description": "Security & Access Control Service"
    },
    {
        "name": "communication-service",
        "schema": "communication",
        "path": "communication-service",
        "env_prefix": "COMMUNICATION",
        "description": "Communication Service (Chat, Announcements)"
    },
    {
        "name": "lms-service",
        "schema": "lms",
        "path": "lms-service",
        "env_prefix": "LMS",
        "description": "Learning Management System"
    },
    {
        "name": "analytics-service",
        "schema": "analytics",
        "path": "analytics-service",
        "env_prefix": "ANALYTICS",
        "description": "Analytics & Reporting Service"
    },
    {
        "name": "media-service",
        "schema": "media",
        "path": "media-service",
        "env_prefix": "MEDIA",
        "description": "Media & File Storage Service"
    },
]


def get_repo_root() -> Path:
    """Get repository root directory."""
    return Path(__file__).parent.parent.parent


def get_all_services() -> List[Dict[str, str]]:
    """
    Get list of all registered services.
    
    Returns:
        List of service metadata dictionaries
    """
    return SERVICES.copy()


def get_service_by_name(name: str) -> Optional[Dict[str, str]]:
    """
    Get service metadata by name.
    
    Args:
        name: Service name (e.g., 'auth-service' or 'auth')
    
    Returns:
        Service metadata dict or None if not found
    """
    # Normalize name
    if not name.endswith('-service'):
        name = f"{name}-service"
    
    for service in SERVICES:
        if service['name'] == name or service['schema'] == name.replace('-service', ''):
            return service.copy()
    
    return None


def get_services_by_names(names: List[str]) -> List[Dict[str, str]]:
    """
    Get multiple services by names.
    
    Args:
        names: List of service names
    
    Returns:
        List of service metadata dicts
    """
    services = []
    for name in names:
        service = get_service_by_name(name)
        if service:
            services.append(service)
    return services


def validate_service_exists(service_name: str) -> bool:
    """
    Check if service exists in filesystem.
    
    Args:
        service_name: Service name
    
    Returns:
        True if service directory and alembic folder exist
    """
    service = get_service_by_name(service_name)
    if not service:
        return False
    
    repo_root = get_repo_root()
    service_path = repo_root / service['path']
    alembic_path = service_path / 'alembic'
    
    return service_path.exists() and alembic_path.exists()


def discover_services() -> List[Dict[str, str]]:
    """
    Auto-discover services by scanning directory structure.
    
    Returns:
        List of discovered service metadata
    """
    repo_root = get_repo_root()
    discovered = []
    
    for item in repo_root.iterdir():
        if item.is_dir() and item.name.endswith('-service'):
            alembic_path = item / 'alembic'
            if alembic_path.exists():
                # Check if service is in registry
                service = get_service_by_name(item.name)
                if service:
                    discovered.append(service)
    
    return discovered


def get_service_count() -> int:
    """Get total number of registered services."""
    return len(SERVICES)


if __name__ == "__main__":
    # Test service registry
    print("SmartSync Service Registry")
    print("=" * 60)
    print(f"\nTotal services: {get_service_count()}")
    print("\nRegistered Services:")
    for i, service in enumerate(get_all_services(), 1):
        exists = "✓" if validate_service_exists(service['name']) else "✗"
        print(f"  {i:2d}. {exists} {service['name']:25s} ({service['schema']} schema)")
    
    print("\nDiscovering services from filesystem...")
    discovered = discover_services()
    print(f"Found {len(discovered)} services with Alembic configured")
