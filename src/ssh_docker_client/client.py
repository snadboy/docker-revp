"""Main client interface for SSH Docker Client."""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, AsyncIterator, AsyncContextManager
from contextlib import asynccontextmanager

from .config import HostsConfig, load_hosts_config
from .connection import ConnectionPool
from .exceptions import ConfigurationError, HostNotFoundError, DockerCommandError
from .models import ContainerInfo
from .ssh_manager import SSHManager
from .utils import parse_docker_ps_json, parse_docker_inspect


class SSHDockerClient:
    """Client for managing Docker over SSH on remote hosts."""
    
    def __init__(
        self,
        config_file: Optional[Path] = None,
        hosts_config: Optional[HostsConfig] = None,
        ssh_dir: Optional[Path] = None
    ):
        """Initialize SSH Docker client.
        
        Args:
            config_file: Path to hosts.yml configuration file
            hosts_config: Pre-loaded hosts configuration
            ssh_dir: SSH directory path (defaults to ~/.ssh)
            
        Raises:
            ConfigurationError: If no configuration provided
        """
        if config_file:
            self.hosts_config = load_hosts_config(config_file)
        elif hosts_config:
            self.hosts_config = hosts_config
        else:
            raise ConfigurationError("Either config_file or hosts_config must be provided")
        
        self.ssh_manager = SSHManager(ssh_dir=ssh_dir)
        self.connection_pool = ConnectionPool(self.hosts_config, self.ssh_manager)
        self._setup_complete = False
    
    @classmethod
    def from_config(cls, config_file: Union[str, Path], **kwargs) -> 'SSHDockerClient':
        """Create client from configuration file.
        
        Args:
            config_file: Path to hosts.yml configuration file
            **kwargs: Additional arguments for client initialization
            
        Returns:
            SSHDockerClient instance
        """
        return cls(config_file=Path(config_file), **kwargs)
    
    def setup_ssh(self) -> None:
        """Set up SSH configuration for all hosts."""
        if self._setup_complete:
            return
        
        # Pass the hosts config to SSH manager
        self.ssh_manager.hosts_config = self.hosts_config
        self.ssh_manager._ensure_ssh_directory()
        self.ssh_manager._generate_ssh_config()
        self.ssh_manager._validate_ssh_keys()
        
        self._setup_complete = True
    
    async def __aenter__(self) -> 'SSHDockerClient':
        """Async context manager entry."""
        self.setup_ssh()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def close(self) -> None:
        """Close all connections."""
        await self.connection_pool.close()
    
    # Async methods
    
    async def list_containers(
        self, 
        host: Optional[str] = None,
        all_containers: bool = False
    ) -> List[Dict[str, Any]]:
        """List Docker containers.
        
        Args:
            host: Optional host alias (None for all hosts)
            all_containers: Include stopped containers
            
        Returns:
            List of container dictionaries
        """
        self.setup_ssh()
        
        # Build docker ps command
        cmd = "ps --format '{{json .}}'"
        if all_containers:
            cmd += " -a"
        
        containers = []
        
        # Get containers from specified host or all hosts
        hosts_to_check = [host] if host else list(self.hosts_config.get_enabled_hosts().keys())
        
        for host_alias in hosts_to_check:
            try:
                output = await self.connection_pool.execute_docker_command(
                    host_alias, 
                    cmd
                )
                
                host_containers = parse_docker_ps_json(output)
                
                # Add host information
                for container in host_containers:
                    container['host'] = host_alias
                    container['host_info'] = self.hosts_config.get_host_config(host_alias).model_dump()
                
                containers.extend(host_containers)
                
            except Exception as e:
                print(f"Error listing containers on {host_alias}: {e}")
                continue
        
        return containers
    
    async def inspect_container(
        self,
        host: str,
        container_id: str
    ) -> Optional[Dict[str, Any]]:
        """Inspect a Docker container.
        
        Args:
            host: Host alias
            container_id: Container ID or name
            
        Returns:
            Container details or None if not found
        """
        self.setup_ssh()
        
        try:
            output = await self.connection_pool.execute_docker_command(
                host,
                f"inspect {container_id}"
            )
            
            return parse_docker_inspect(output)
            
        except DockerCommandError as e:
            if "No such object" in str(e):
                return None
            raise
    
    async def execute(
        self,
        command: str,
        host: str,
        timeout: Optional[int] = None
    ) -> str:
        """Execute arbitrary Docker command.
        
        Args:
            command: Docker command to execute
            host: Host alias
            timeout: Command timeout in seconds
            
        Returns:
            Command output
        """
        self.setup_ssh()
        
        return await self.connection_pool.execute_docker_command(
            host,
            command,
            timeout=timeout
        )
    
    async def docker_events(
        self,
        host: str,
        filters: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream Docker events from a host.
        
        Args:
            host: Host alias
            filters: Optional event filters
            
        Yields:
            Docker event dictionaries
        """
        self.setup_ssh()
        
        async for event in self.connection_pool.stream_docker_events(host, filters):
            yield event
    
    # Sync methods
    
    def list_containers_sync(
        self,
        host: Optional[str] = None,
        all_containers: bool = False
    ) -> List[Dict[str, Any]]:
        """Synchronous version of list_containers."""
        self.setup_ssh()
        
        # Build docker ps command
        cmd = "ps --format '{{json .}}'"
        if all_containers:
            cmd += " -a"
        
        containers = []
        
        # Get containers from specified host or all hosts
        hosts_to_check = [host] if host else list(self.hosts_config.get_enabled_hosts().keys())
        
        for host_alias in hosts_to_check:
            try:
                output = self.connection_pool.execute_docker_command_sync(
                    host_alias,
                    cmd
                )
                
                host_containers = parse_docker_ps_json(output)
                
                # Add host information
                for container in host_containers:
                    container['host'] = host_alias
                    container['host_info'] = self.hosts_config.get_host_config(host_alias).model_dump()
                
                containers.extend(host_containers)
                
            except Exception as e:
                print(f"Error listing containers on {host_alias}: {e}")
                continue
        
        return containers
    
    def inspect_container_sync(
        self,
        host: str,
        container_id: str
    ) -> Optional[Dict[str, Any]]:
        """Synchronous version of inspect_container."""
        self.setup_ssh()
        
        try:
            output = self.connection_pool.execute_docker_command_sync(
                host,
                f"inspect {container_id}"
            )
            
            return parse_docker_inspect(output)
            
        except DockerCommandError as e:
            if "No such object" in str(e):
                return None
            raise
    
    def execute_sync(
        self,
        command: str,
        host: str,
        timeout: Optional[int] = None
    ) -> str:
        """Synchronous version of execute."""
        self.setup_ssh()
        
        return self.connection_pool.execute_docker_command_sync(
            host,
            command,
            timeout=timeout
        )
    
    # Utility methods
    
    def test_connections(self) -> Dict[str, Dict[str, Any]]:
        """Test SSH connections to all hosts.
        
        Returns:
            Connection status for each host
        """
        self.setup_ssh()
        return self.ssh_manager.test_connections()
    
    def get_hosts(self) -> Dict[str, Any]:
        """Get all configured hosts.
        
        Returns:
            Dictionary of host configurations
        """
        return {
            alias: config.model_dump()
            for alias, config in self.hosts_config.get_enabled_hosts().items()
        }
    
    def add_host(self, alias: str, **kwargs) -> None:
        """Add a new host to configuration.
        
        Args:
            alias: Host alias
            **kwargs: Host configuration parameters
        """
        from .models import HostConfig
        
        host_config = HostConfig(**kwargs)
        self.hosts_config.hosts[alias] = host_config
        
        # Regenerate SSH config
        self.ssh_manager.add_host(alias, host_config)