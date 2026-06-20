"""
Migration manager for SmartSync microservices.

Wraps Alembic commands and handles multi-service operations.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .config_loader import load_database_url
from .service_registry import get_repo_root


class MigrationResult:
    """Result of a migration operation."""
    
    def __init__(self, service_name: str, success: bool, output: str = "", 
                 error: str = "", duration: float = 0.0):
        self.service_name = service_name
        self.success = success
        self.output = output
        self.error = error
        self.duration = duration
        self.timestamp = datetime.now()
    
    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"<MigrationResult {self.service_name}: {status} ({self.duration:.1f}s)>"


class MigrationManager:
    """Manages Alembic migrations across multiple services."""
    
    def __init__(self):
        self.repo_root = get_repo_root()
    
    def run_alembic_command(
        self,
        service: Dict[str, str],
        operation: str,
        args: Optional[List[str]] = None
    ) -> MigrationResult:
        """
        Execute Alembic command for a single service.
        
        Args:
            service: Service metadata dict
            operation: Alembic command (upgrade, downgrade, revision, etc.)
            args: Additional command arguments
        
        Returns:
            MigrationResult with operation outcome
        """
        start_time = datetime.now()
        service_name = service['name']
        service_path = self.repo_root / service['path']
        
        # Validate service exists
        if not service_path.exists():
            return MigrationResult(
                service_name=service_name,
                success=False,
                error=f"Service directory not found: {service_path}",
                duration=0.0
            )
        
        alembic_path = service_path / 'alembic'
        if not alembic_path.exists():
            return MigrationResult(
                service_name=service_name,
                success=False,
                error=f"Alembic directory not found: {alembic_path}",
                duration=0.0
            )
        
        # Build command
        cmd = ['alembic', operation]
        if args:
            cmd.extend(args)
        
        # Set up environment
        env = os.environ.copy()
        
        # Set service-specific DATABASE_URL
        db_url = load_database_url(service['schema'])
        env[f"{service['env_prefix']}_DATABASE_URL"] = db_url
        
        # Execute command
        try:
            result = subprocess.run(
                cmd,
                cwd=service_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                return MigrationResult(
                    service_name=service_name,
                    success=True,
                    output=result.stdout,
                    duration=duration
                )
            else:
                return MigrationResult(
                    service_name=service_name,
                    success=False,
                    output=result.stdout,
                    error=result.stderr,
                    duration=duration
                )
        
        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds()
            return MigrationResult(
                service_name=service_name,
                success=False,
                error="Command timed out after 5 minutes",
                duration=duration
            )
        
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return MigrationResult(
                service_name=service_name,
                success=False,
                error=f"Unexpected error: {str(e)}",
                duration=duration
            )
    
    def run_multi_service_migration(
        self,
        services: List[Dict[str, str]],
        operation: str,
        args: Optional[List[str]] = None,
        stop_on_error: bool = True
    ) -> List[MigrationResult]:
        """
        Execute migration across multiple services.
        
        Args:
            services: List of service metadata dicts
            operation: Alembic command
            args: Additional command arguments
            stop_on_error: Stop if any service fails
        
        Returns:
            List of MigrationResult objects
        """
        results = []
        
        for i, service in enumerate(services, 1):
            print(f"[{i}/{len(services)}] {service['name']:25s} ", end='', flush=True)
            
            result = self.run_alembic_command(service, operation, args)
            results.append(result)
            
            if result.success:
                print(f"✓ SUCCESS ({result.duration:.1f}s)")
                if result.output and '--verbose' in (args or []):
                    print(f"        Output: {result.output.strip()}")
            else:
                print(f"✗ FAILED ({result.duration:.1f}s)")
                if result.error:
                    print(f"        Error: {result.error.strip()}")
                
                if stop_on_error:
                    print(f"\n⚠️  Stopped at {service['name']} due to error")
                    break
        
        return results
    
    def get_current_revision(self, service: Dict[str, str]) -> Optional[str]:
        """
        Get current migration revision for a service.
        
        Args:
            service: Service metadata dict
        
        Returns:
            Current revision ID or None if error
        """
        result = self.run_alembic_command(service, 'current', [])
        
        if result.success and result.output:
            # Parse output to extract revision ID
            lines = result.output.strip().split('\n')
            for line in lines:
                if line.strip() and not line.startswith('INFO'):
                    # Extract revision ID (first word)
                    parts = line.split()
                    if parts:
                        return parts[0]
        
        return None
    
    def get_pending_migrations(self, service: Dict[str, str]) -> List[str]:
        """
        Get list of pending migrations for a service.
        
        Args:
            service: Service metadata dict
        
        Returns:
            List of pending revision IDs
        """
        result = self.run_alembic_command(service, 'history', [])
        
        # This is a simplified implementation
        # A full implementation would parse history and compare with current
        return []
    
    def print_summary(self, results: List[MigrationResult]) -> None:
        """
        Print summary of migration results.
        
        Args:
            results: List of MigrationResult objects
        """
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)
        
        succeeded = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        total_time = sum(r.duration for r in results)
        
        print(f"Total services: {len(results)}")
        print(f"Succeeded:      {len(succeeded)}")
        print(f"Failed:         {len(failed)}")
        print(f"Total time:     {total_time:.1f}s")
        
        if failed:
            print("\nFailed services:")
            for result in failed:
                print(f"  • {result.service_name}")
                if result.error:
                    print(f"    {result.error.strip()}")
        
        print("=" * 60)


if __name__ == "__main__":
    # Test migration manager
    from service_registry import get_service_by_name
    
    manager = MigrationManager()
    
    # Test single service
    auth_service = get_service_by_name('auth-service')
    if auth_service:
        print("Testing migration manager with auth-service...")
        result = manager.run_alembic_command(auth_service, 'current', [])
        print(f"Result: {result}")
        if result.success:
            print(f"Output: {result.output}")
        else:
            print(f"Error: {result.error}")
