#!/usr/bin/env python3
"""Command-line interface for SSH Docker Client."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from .client import SSHDockerClient
from .config import create_example_config
from .exceptions import SSHDockerError


def test_connections(client: SSHDockerClient) -> None:
    """Test connections to all configured hosts."""
    print("Testing SSH connections...")
    results = client.test_connections()
    
    for host, status in results.items():
        if status['connected']:
            print(f"✓ {host}:{status['port']} - Connected")
        else:
            error = status.get('error', 'Unknown error')
            print(f"✗ {host}:{status['port']} - Failed: {error}")


def list_containers(client: SSHDockerClient, host: Optional[str] = None, all_containers: bool = False) -> None:
    """List containers on specified host or all hosts."""
    try:
        containers = client.list_containers_sync(host=host, all_containers=all_containers)
        
        if not containers:
            print("No containers found")
            return
        
        # Group by host
        by_host = {}
        for container in containers:
            container_host = container['host']
            if container_host not in by_host:
                by_host[container_host] = []
            by_host[container_host].append(container)
        
        # Display containers
        for container_host, host_containers in by_host.items():
            print(f"\n{container_host}:")
            for container in host_containers:
                status = "🟢" if container['State'] == 'running' else "🔴"
                print(f"  {status} {container['Names']} - {container['Image']} ({container['Status']})")
                
    except SSHDockerError as e:
        print(f"Error listing containers: {e}", file=sys.stderr)
        sys.exit(1)


def execute_command(client: SSHDockerClient, host: str, command: str) -> None:
    """Execute Docker command on specified host."""
    try:
        result = client.execute_sync(command, host=host)
        print(result)
    except SSHDockerError as e:
        print(f"Error executing command: {e}", file=sys.stderr)
        sys.exit(1)


def inspect_container(client: SSHDockerClient, host: str, container_id: str) -> None:
    """Inspect a container on specified host."""
    try:
        details = client.inspect_container_sync(host, container_id)
        if details:
            print(json.dumps(details, indent=2))
        else:
            print(f"Container {container_id} not found on {host}")
            sys.exit(1)
    except SSHDockerError as e:
        print(f"Error inspecting container: {e}", file=sys.stderr)
        sys.exit(1)


async def monitor_events(client: SSHDockerClient, host: str) -> None:
    """Monitor Docker events on specified host."""
    print(f"Monitoring Docker events on {host}... (Press Ctrl+C to stop)")
    
    try:
        async for event in client.docker_events(host, filters={"type": "container"}):
            action = event.get('Action', 'unknown')
            actor = event.get('Actor', {})
            container_name = actor.get('Attributes', {}).get('name', 'unknown')
            timestamp = event.get('time', 'unknown')
            
            print(f"[{timestamp}] {action}: {container_name}")
            
    except KeyboardInterrupt:
        print("\nStopped monitoring events")
    except SSHDockerError as e:
        print(f"Error monitoring events: {e}", file=sys.stderr)
        sys.exit(1)


def create_config(config_file: Path) -> None:
    """Create example configuration file."""
    if config_file.exists():
        response = input(f"{config_file} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted")
            return
    
    create_example_config(config_file)
    print(f"Created example configuration: {config_file}")
    print("Please edit the file with your actual host details")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SSH Docker Client - Manage Docker over SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ssh-docker-client test                    # Test all connections
  ssh-docker-client ls                      # List containers on all hosts
  ssh-docker-client ls --host prod          # List containers on specific host
  ssh-docker-client exec prod "version"     # Execute Docker command
  ssh-docker-client inspect prod abc123     # Inspect container
  ssh-docker-client events prod             # Monitor events
  ssh-docker-client config                  # Create example config
        """
    )
    
    parser.add_argument(
        '-c', '--config', 
        type=Path, 
        default=Path('hosts.yml'),
        help='Configuration file path (default: hosts.yml)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Test command
    subparsers.add_parser('test', help='Test SSH connections to all hosts')
    
    # List command
    ls_parser = subparsers.add_parser('ls', help='List containers')
    ls_parser.add_argument('--host', help='Specific host to list containers from')
    ls_parser.add_argument('-a', '--all', action='store_true', help='Show all containers (including stopped)')
    
    # Execute command
    exec_parser = subparsers.add_parser('exec', help='Execute Docker command')
    exec_parser.add_argument('host', help='Host to execute command on')
    exec_parser.add_argument('command', help='Docker command to execute')
    
    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect container')
    inspect_parser.add_argument('host', help='Host where container is located')
    inspect_parser.add_argument('container', help='Container ID or name')
    
    # Events command
    events_parser = subparsers.add_parser('events', help='Monitor Docker events')
    events_parser.add_argument('host', help='Host to monitor events from')
    
    # Config command
    subparsers.add_parser('config', help='Create example configuration file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Handle config command separately (doesn't need client)
    if args.command == 'config':
        create_config(args.config)
        return
    
    # Check if config file exists
    if not args.config.exists():
        print(f"Configuration file not found: {args.config}")
        print("Create one with: ssh-docker-client config")
        sys.exit(1)
    
    # Create client
    try:
        client = SSHDockerClient.from_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Handle commands
    if args.command == 'test':
        test_connections(client)
    elif args.command == 'ls':
        list_containers(client, host=args.host, all_containers=args.all)
    elif args.command == 'exec':
        execute_command(client, args.host, args.command)
    elif args.command == 'inspect':
        inspect_container(client, args.host, args.container)
    elif args.command == 'events':
        asyncio.run(monitor_events(client, args.host))


if __name__ == '__main__':
    main()