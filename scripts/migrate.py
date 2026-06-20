#!/usr/bin/env python3
"""
SmartSync Database Migration Manager

Unified script for managing Alembic migrations across all microservices.

Usage:
    # Interactive mode
    python scripts/migrate.py
    
    # Direct commands
    python scripts/migrate.py --service auth --operation upgrade --args head
    python scripts/migrate.py --service all --operation current
    python scripts/migrate.py --service auth,platform --operation downgrade --args "-1"
    
    # Create new migration
    python scripts/migrate.py --service auth --operation revision --args "--autogenerate" "-m" "add_new_table"
"""
import argparse
import sys
from pathlib import Path

# Add scripts/utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.service_registry import (
    get_all_services,
    get_service_by_name,
    get_services_by_names,
    get_service_count
)
from utils.migration_manager import MigrationManager
from utils.config_loader import get_db_config


def print_banner():
    """Print application banner."""
    print("=" * 70)
    print("  SmartSync Database Migration Manager".center(70))
    print("=" * 70)
    print()


def interactive_mode():
    """Run in interactive mode with menu."""
    print_banner()
    
    # Show operation menu
    print("Select Operation:")
    operations = [
        ("upgrade", "Apply pending migrations"),
        ("downgrade", "Revert migrations"),
        ("revision", "Create new migration"),
        ("current", "Show current revision"),
        ("history", "Show migration history"),
        ("heads", "Show all head revisions"),
        ("show", "Show specific revision"),
        ("stamp", "Mark revision without executing"),
    ]
    
    for i, (cmd, desc) in enumerate(operations, 1):
        print(f"  {i}. {desc:40s} (alembic {cmd})")
    print(f"  {len(operations) + 1}. Exit")
    
    while True:
        try:
            choice = input(f"\nOperation [1-{len(operations) + 1}]: ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(operations):
                operation = operations[choice_num - 1][0]
                break
            elif choice_num == len(operations) + 1:
                print("Exiting...")
                sys.exit(0)
        except (ValueError, KeyError):
            pass
        print("Invalid choice. Try again.")
    
    print(f"\n{'=' * 70}")
    print(f"Operation: {operation}")
    print('=' * 70)
    
    # Show service selection
    print("\nSelect Service(s):")
    services = get_all_services()
    print(f"  0. All services ({len(services)})")
    for i, service in enumerate(services, 1):
        print(f"  {i:2d}. {service['name']:25s} ({service['schema']} schema)")
    
    while True:
        try:
            choice = input(f"\nService(s) [0-{len(services)}, comma-separated]: ").strip()
            
            if choice == '0':
                selected_services = services
                break
            elif ',' in choice:
                indices = [int(x.strip()) for x in choice.split(',')]
                selected_services = [services[i - 1] for i in indices if 1 <= i <= len(services)]
                if selected_services:
                    break
            else:
                idx = int(choice)
                if 1 <= idx <= len(services):
                    selected_services = [services[idx - 1]]
                    break
        except (ValueError, IndexError):
            pass
        print("Invalid choice. Try again.")
    
    # Get additional arguments based on operation
    args = []
    if operation == 'upgrade':
        print("\nUpgrade target:")
        print("  1. head (latest)")
        print("  2. +1 (next revision)")
        print("  3. Specific revision ID")
        target = input("Target [1-3]: ").strip()
        if target == '1':
            args = ['head']
        elif target == '2':
            args = ['+1']
        elif target == '3':
            rev = input("Revision ID: ").strip()
            if rev:
                args = [rev]
    
    elif operation == 'downgrade':
        print("\nDowngrade target:")
        print("  1. -1 (previous revision)")
        print("  2. base (remove all)")
        print("  3. Specific revision ID")
        target = input("Target [1-3]: ").strip()
        if target == '1':
            args = ['-1']
        elif target == '2':
            confirm = input("⚠️  This will remove ALL migrations. Confirm? [y/N]: ").strip()
            if confirm.lower() == 'y':
                args = ['base']
            else:
                print("Cancelled.")
                sys.exit(0)
        elif target == '3':
            rev = input("Revision ID: ").strip()
            if rev:
                args = [rev]
    
    elif operation == 'revision':
        message = input("\nMigration message: ").strip()
        if not message:
            print("Error: Migration message required")
            sys.exit(1)
        
        autogen = input("Auto-generate from models? [Y/n]: ").strip()
        if autogen.lower() != 'n':
            args = ['--autogenerate', '-m', message]
        else:
            args = ['-m', message]
    
    # Confirmation
    print(f"\n{'=' * 70}")
    print("Confirmation")
    print('=' * 70)
    print(f"Operation:  alembic {operation} {' '.join(args)}")
    print(f"Services:   {len(selected_services)} service(s)")
    for svc in selected_services:
        print(f"            • {svc['name']} ({svc['schema']} schema)")
    
    # Show database info
    try:
        db_config = get_db_config()
        db_info = f"{db_config['DB_USER']}@{db_config['DB_HOST']}:{db_config['DB_PORT']}/{db_config['DB_NAME']}"
        print(f"Database:   {db_info}")
    except Exception:
        print("Database:   (config not loaded)")
    
    confirm = input("\nProceed? [y/N]: ").strip()
    if confirm.lower() != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    # Execute migration
    print(f"\n{'=' * 70}")
    print(f"Executing: alembic {operation} {' '.join(args)}")
    print('=' * 70)
    print()
    
    manager = MigrationManager()
    results = manager.run_multi_service_migration(
        selected_services,
        operation,
        args,
        stop_on_error=True
    )
    
    manager.print_summary(results)
    
    # Exit with error code if any failed
    if any(not r.success for r in results):
        sys.exit(1)


def command_line_mode(args):
    """Run in command-line mode with arguments."""
    # Parse services
    if args.service.lower() == 'all':
        services = get_all_services()
    elif ',' in args.service:
        service_names = [s.strip() for s in args.service.split(',')]
        services = get_services_by_names(service_names)
        if not services:
            print(f"Error: No valid services found in: {args.service}")
            sys.exit(1)
    else:
        service = get_service_by_name(args.service)
        if not service:
            print(f"Error: Service not found: {args.service}")
            print(f"\nAvailable services:")
            for svc in get_all_services():
                print(f"  • {svc['name']}")
            sys.exit(1)
        services = [service]
    
    # Parse additional arguments
    cmd_args = args.args if args.args else []
    
    # Execute migration
    print(f"Executing: alembic {args.operation} {' '.join(cmd_args)}")
    print(f"Services: {len(services)}")
    print()
    
    manager = MigrationManager()
    results = manager.run_multi_service_migration(
        services,
        args.operation,
        cmd_args,
        stop_on_error=not args.continue_on_error
    )
    
    if not args.quiet:
        manager.print_summary(results)
    
    # Exit with error code if any failed
    if any(not r.success for r in results):
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='SmartSync Database Migration Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python scripts/migrate.py
  
  # Upgrade all services
  python scripts/migrate.py --service all --operation upgrade --args head
  
  # Upgrade specific service
  python scripts/migrate.py --service auth --operation upgrade --args head
  
  # Check current status
  python scripts/migrate.py --service all --operation current
  
  # Create new migration
  python scripts/migrate.py --service auth --operation revision \\
      --args "--autogenerate" "-m" "add_new_table"
  
  # Downgrade one step
  python scripts/migrate.py --service platform --operation downgrade --args "-1"
        """
    )
    
    parser.add_argument(
        '--service', '-s',
        help='Service name (or "all", or comma-separated list)'
    )
    parser.add_argument(
        '--operation', '-o',
        choices=['upgrade', 'downgrade', 'revision', 'current', 'history', 
                 'heads', 'show', 'stamp', 'merge'],
        help='Alembic operation to perform'
    )
    parser.add_argument(
        '--args', '-a',
        nargs='*',
        help='Additional arguments for Alembic command'
    )
    parser.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue even if a service fails'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress summary output'
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, run interactive mode
    if not args.service or not args.operation:
        interactive_mode()
    else:
        command_line_mode(args)


if __name__ == "__main__":
    main()
