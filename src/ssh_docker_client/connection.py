"""Connection management for SSH Docker Client."""

import asyncio
import json
from typing import Dict, Optional, Any, AsyncIterator
from pathlib import Path

from .exceptions import SSHConnectionError, DockerCommandError, HostNotFoundError
from .config import HostsConfig
from .ssh_manager import SSHManager
from .utils import parse_docker_events_json


class ConnectionPool:
    """Manages SSH connections to Docker hosts."""
    
    def __init__(self, hosts_config: HostsConfig, ssh_manager: SSHManager):
        """Initialize connection pool.
        
        Args:
            hosts_config: Hosts configuration
            ssh_manager: SSH configuration manager
        """
        self.hosts_config = hosts_config
        self.ssh_manager = ssh_manager
        self._connections: Dict[str, Any] = {}
        self._event_streams: Dict[str, asyncio.subprocess.Process] = {}
    
    async def execute_docker_command(
        self,
        host_alias: str,
        command: str,
        timeout: Optional[int] = None
    ) -> str:
        """Execute Docker command on remote host.
        
        Args:
            host_alias: Host alias from configuration
            command: Docker command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Command output
            
        Raises:
            HostNotFoundError: If host not found
            SSHConnectionError: If connection fails
            DockerCommandError: If Docker command fails
        """
        if host_alias not in self.hosts_config.hosts:
            raise HostNotFoundError(f"Host '{host_alias}' not found in configuration")
        
        ssh_alias = self.ssh_manager.get_ssh_alias(host_alias)
        
        # Build command
        if not command.strip().startswith('docker'):
            command = f"docker {command}"
        
        try:
            # Execute command
            process = await asyncio.create_subprocess_exec(
                "ssh", ssh_alias, command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise DockerCommandError(f"Command timeout after {timeout} seconds")
            
            # Check result
            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                
                # Check for SSH connection errors
                if "ssh:" in error_msg.lower() or "connection" in error_msg.lower():
                    raise SSHConnectionError(f"SSH connection failed: {error_msg}")
                
                # Docker command error
                raise DockerCommandError(f"Docker command failed: {error_msg}")
            
            return stdout.decode().strip()
            
        except Exception as e:
            if isinstance(e, (SSHConnectionError, DockerCommandError, HostNotFoundError)):
                raise
            raise SSHConnectionError(f"Failed to execute command: {e}")
    
    async def stream_docker_events(
        self,
        host_alias: str,
        filters: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream Docker events from a host.
        
        Args:
            host_alias: Host alias from configuration
            filters: Optional Docker event filters
            
        Yields:
            Docker event dictionaries
        """
        if host_alias not in self.hosts_config.hosts:
            raise HostNotFoundError(f"Host '{host_alias}' not found in configuration")
        
        # Stop existing event stream if any
        await self.stop_event_stream(host_alias)
        
        ssh_alias = self.ssh_manager.get_ssh_alias(host_alias)
        
        # Build docker events command
        cmd = ["ssh", ssh_alias, "docker", "events", "--format", "{{json .}}"]
        
        # Add filters
        if filters:
            for key, value in filters.items():
                cmd.extend(["--filter", f"{key}={value}"])
        
        try:
            # Start event stream
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self._event_streams[host_alias] = process
            
            # Stream events
            while True:
                line = await process.stdout.readline()
                
                if not line:
                    # Stream ended
                    break
                
                # Parse event
                event = parse_docker_events_json(line.decode())
                if event:
                    yield event
            
            # Check if process ended with error
            if process.returncode and process.returncode != 0:
                stderr = await process.stderr.read()
                raise DockerCommandError(f"Event stream error: {stderr.decode()}")
                
        except asyncio.CancelledError:
            # Clean shutdown
            await self.stop_event_stream(host_alias)
            raise
        except Exception as e:
            await self.stop_event_stream(host_alias)
            if isinstance(e, (SSHConnectionError, DockerCommandError)):
                raise
            raise SSHConnectionError(f"Failed to stream events: {e}")
    
    async def stop_event_stream(self, host_alias: str) -> None:
        """Stop event stream for a host.
        
        Args:
            host_alias: Host alias from configuration
        """
        if host_alias in self._event_streams:
            process = self._event_streams[host_alias]
            
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            finally:
                del self._event_streams[host_alias]
    
    async def close(self) -> None:
        """Close all connections and streams."""
        # Stop all event streams
        hosts = list(self._event_streams.keys())
        for host in hosts:
            await self.stop_event_stream(host)
    
    def execute_docker_command_sync(
        self,
        host_alias: str,
        command: str,
        timeout: Optional[int] = None
    ) -> str:
        """Synchronous version of execute_docker_command.
        
        Args:
            host_alias: Host alias from configuration
            command: Docker command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Command output
        """
        # Use subprocess directly for sync execution
        result = self.ssh_manager.execute_ssh_command(
            host_alias,
            command if command.startswith('docker') else f"docker {command}",
            timeout=timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            
            # Check for SSH connection errors
            if "ssh:" in error_msg.lower() or "connection" in error_msg.lower():
                raise SSHConnectionError(f"SSH connection failed: {error_msg}")
            
            # Docker command error
            raise DockerCommandError(f"Docker command failed: {error_msg}")
        
        return result.stdout.strip()