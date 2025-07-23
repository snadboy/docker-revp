"""SSH configuration and connection management."""

import os
import stat
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import HostsConfig, load_hosts_config
from .exceptions import ConfigurationError, SSHConnectionError
from .models import HostConfig


class SSHManager:
    """Manages SSH configuration and connections for Docker hosts."""
    
    def __init__(self, ssh_dir: Optional[Path] = None):
        """Initialize SSH manager.
        
        Args:
            ssh_dir: SSH directory path (defaults to ~/.ssh)
        """
        self.ssh_dir = ssh_dir or Path.home() / ".ssh"
        self.config_file = self.ssh_dir / "config"
        self.hosts_config: Optional[HostsConfig] = None
        
        # SSH configuration options
        self.ssh_options = {
            "PasswordAuthentication": "no",
            "StrictHostKeyChecking": "accept-new",
            "ServerAliveInterval": "60",
            "ServerAliveCountMax": "3",
            "ControlMaster": "auto",
            "ControlPath": "~/.ssh/control-%r@%h:%p",
            "ControlPersist": "10m",
            "ConnectTimeout": "30",
        }
    
    def setup_from_config(self, config_file: Path) -> None:
        """Set up SSH configuration from hosts YAML file.
        
        Args:
            config_file: Path to hosts.yml configuration file
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        self.hosts_config = load_hosts_config(config_file)
        self._ensure_ssh_directory()
        self._generate_ssh_config()
        self._validate_ssh_keys()
    
    def add_host(self, alias: str, host_config: HostConfig) -> None:
        """Add a single host to SSH configuration.
        
        Args:
            alias: Host alias
            host_config: Host configuration
        """
        if not self.hosts_config:
            from .config import HostsConfig
            self.hosts_config = HostsConfig(hosts={})
        
        self.hosts_config.hosts[alias] = host_config
        self._generate_ssh_config()
    
    def _ensure_ssh_directory(self) -> None:
        """Ensure SSH directory exists with proper permissions."""
        self.ssh_dir.mkdir(mode=0o700, exist_ok=True)
        
        # Also create control socket directory
        control_dir = self.ssh_dir / "control"
        control_dir.mkdir(mode=0o700, exist_ok=True)
    
    def _validate_ssh_keys(self) -> None:
        """Validate SSH key files and permissions."""
        if not self.hosts_config:
            return
        
        missing_keys = self.hosts_config.validate_ssh_keys()
        if missing_keys:
            # Just warn, don't fail - keys might be created later
            print(f"Warning: SSH key files not found: {', '.join(missing_keys)}")
        
        # Check permissions on existing keys
        for alias, host in self.hosts_config.get_enabled_hosts().items():
            key_path = Path(host.key_file).expanduser()
            if key_path.exists():
                self._ensure_key_permissions(key_path)
    
    def _ensure_key_permissions(self, key_path: Path) -> None:
        """Ensure SSH key has proper permissions (600)."""
        try:
            current_mode = key_path.stat().st_mode
            if current_mode & 0o077:  # If any group/other permissions exist
                os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
                print(f"Fixed permissions for SSH key: {key_path}")
        except Exception as e:
            print(f"Warning: Could not update key permissions for {key_path}: {e}")
    
    def _generate_ssh_config(self) -> None:
        """Generate SSH config file for Docker hosts."""
        if not self.hosts_config:
            return
        
        enabled_hosts = self.hosts_config.get_enabled_hosts()
        if not enabled_hosts:
            print("Warning: No enabled hosts found in configuration")
            return
        
        print(f"Generating SSH config for {len(enabled_hosts)} hosts")
        
        # Read existing config if it exists
        existing_config = self._read_existing_config()
        
        # Generate new config section
        config_lines = ["# BEGIN SSH DOCKER CLIENT MANAGED HOSTS"]
        config_lines.append("# Generated from hosts configuration")
        config_lines.append("# DO NOT EDIT THIS SECTION MANUALLY")
        config_lines.append("")
        
        for alias, host_config in enabled_hosts.items():
            # Get SSH alias for this host
            ssh_alias = host_config.get_ssh_alias()
            
            config_lines.append(f"# {alias}: {host_config.description or 'No description'}")
            config_lines.append(f"Host {ssh_alias}")
            config_lines.append(f"    HostName {host_config.hostname}")
            config_lines.append(f"    User {host_config.user}")
            config_lines.append(f"    Port {host_config.port}")
            config_lines.append(f"    IdentityFile {host_config.key_file}")
            
            # Add SSH options
            for option, value in self.ssh_options.items():
                config_lines.append(f"    {option} {value}")
            
            config_lines.append("")
        
        config_lines.append("# END SSH DOCKER CLIENT MANAGED HOSTS")
        
        # Write the final config
        self._write_ssh_config(existing_config, config_lines)
        
        print(f"SSH config written successfully with {len(enabled_hosts)} hosts")
    
    def _read_existing_config(self) -> str:
        """Read existing SSH config and remove our managed section."""
        existing_config = ""
        if self.config_file.exists():
            existing_config = self.config_file.read_text()
            
            # Remove our managed section if it exists
            start_marker = "# BEGIN SSH DOCKER CLIENT MANAGED HOSTS"
            end_marker = "# END SSH DOCKER CLIENT MANAGED HOSTS"
            
            if start_marker in existing_config and end_marker in existing_config:
                start_idx = existing_config.index(start_marker)
                end_idx = existing_config.index(end_marker) + len(end_marker)
                existing_config = existing_config[:start_idx] + existing_config[end_idx + 1:]
        
        return existing_config.rstrip()
    
    def _write_ssh_config(self, existing_config: str, config_lines: List[str]) -> None:
        """Write SSH config with existing config and new managed section."""
        # Combine with existing config
        new_config = existing_config
        if new_config:
            new_config += "\n\n"
        new_config += "\n".join(config_lines) + "\n"
        
        # Write config file
        self.config_file.write_text(new_config)
        
        # Set permissions (644)
        os.chmod(self.config_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    
    def test_connections(self) -> Dict[str, Dict[str, any]]:
        """Test SSH connections to all configured hosts.
        
        Returns:
            Dictionary mapping hostname to connection status
        """
        if not self.hosts_config:
            return {}
        
        results = {}
        
        for alias, host_config in self.hosts_config.get_enabled_hosts().items():
            ssh_alias = host_config.get_ssh_alias()
            print(f"Testing connection to {host_config.hostname}:{host_config.port}")
            
            try:
                # Test with a simple command
                result = subprocess.run(
                    ["ssh", "-o", "BatchMode=yes", ssh_alias, "echo", "OK"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                success = result.returncode == 0 and result.stdout.strip() == "OK"
                
                results[host_config.hostname] = {
                    "alias": alias,
                    "ssh_alias": ssh_alias,
                    "port": host_config.port,
                    "connected": success,
                    "error": result.stderr if not success else None
                }
                
                if success:
                    print(f"✓ Successfully connected to {host_config.hostname}")
                else:
                    print(f"✗ Failed to connect to {host_config.hostname}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                results[host_config.hostname] = {
                    "alias": alias,
                    "ssh_alias": ssh_alias,
                    "port": host_config.port,
                    "connected": False,
                    "error": "Connection timeout"
                }
                print(f"✗ Connection timeout to {host_config.hostname}")
            except Exception as e:
                results[host_config.hostname] = {
                    "alias": alias,
                    "ssh_alias": ssh_alias,
                    "port": host_config.port,
                    "connected": False,
                    "error": str(e)
                }
                print(f"✗ Error connecting to {host_config.hostname}: {e}")
        
        return results
    
    def get_ssh_alias(self, host_alias: str) -> str:
        """Get SSH config alias for a host.
        
        Args:
            host_alias: Host alias from configuration
            
        Returns:
            SSH config alias to use with SSH commands
            
        Raises:
            ConfigurationError: If host not found
        """
        if not self.hosts_config:
            raise ConfigurationError("No hosts configuration loaded")
        
        if host_alias not in self.hosts_config.hosts:
            raise ConfigurationError(f"Host '{host_alias}' not found in configuration")
        
        host_config = self.hosts_config.get_host_config(host_alias)
        return host_config.get_ssh_alias()
    
    def get_docker_command(self, host_alias: str, docker_cmd: str) -> List[str]:
        """Build Docker command for remote execution.
        
        Args:
            host_alias: Host alias from configuration
            docker_cmd: Docker command to execute
            
        Returns:
            Full command list for subprocess execution
        """
        ssh_alias = self.get_ssh_alias(host_alias)
        
        # If docker_cmd already starts with 'docker', use it as-is
        if docker_cmd.strip().startswith('docker'):
            return ["ssh", ssh_alias, docker_cmd]
        else:
            # Otherwise, prepend 'docker'
            return ["ssh", ssh_alias, f"docker {docker_cmd}"]
    
    def execute_ssh_command(
        self, 
        host_alias: str, 
        command: str, 
        timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess:
        """Execute command over SSH.
        
        Args:
            host_alias: Host alias from configuration
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Completed process with result
            
        Raises:
            SSHConnectionError: If SSH connection fails
        """
        ssh_alias = self.get_ssh_alias(host_alias)
        
        try:
            result = subprocess.run(
                ["ssh", ssh_alias, command],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0 and "ssh:" in result.stderr:
                raise SSHConnectionError(f"SSH connection failed: {result.stderr}")
            
            return result
            
        except subprocess.TimeoutExpired as e:
            raise SSHConnectionError(f"Command timeout after {timeout} seconds")
        except Exception as e:
            raise SSHConnectionError(f"SSH execution failed: {e}")