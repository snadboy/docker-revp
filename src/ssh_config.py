"""SSH configuration generation for Docker hosts."""
import os
import stat
from pathlib import Path
from typing import List, Tuple

from .config import settings
from .logger import ssh_logger


class SSHConfigManager:
    """Manages SSH configuration for Docker hosts."""
    
    def __init__(self):
        self.ssh_dir = Path.home() / ".ssh"
        self.config_file = self.ssh_dir / "config"
        self.key_file = self.ssh_dir / "docker_monitor_key"
    
    def setup(self) -> None:
        """Set up SSH configuration and private key."""
        try:
            # Create SSH directory if it doesn't exist
            self.ssh_dir.mkdir(mode=0o700, exist_ok=True)
            
            # Write private key
            self._write_private_key()
            
            # Generate SSH config
            self._generate_ssh_config()
            
            ssh_logger.info("SSH configuration set up successfully")
            
        except Exception as e:
            ssh_logger.error(f"Failed to set up SSH configuration: {e}")
            raise
    
    def _write_private_key(self) -> None:
        """Handle SSH private key - either use mounted location directly or copy if needed."""
        mounted_key_path = Path(settings.ssh_private_key_path)
        
        # If the key is already in the right place, just ensure permissions
        if str(self.key_file) == str(mounted_key_path):
            ssh_logger.info(f"SSH private key already at {self.key_file}, checking permissions")
            if mounted_key_path.exists():
                # Just ensure permissions are correct
                try:
                    os.chmod(self.key_file, stat.S_IRUSR | stat.S_IWUSR)
                    ssh_logger.info("SSH private key permissions verified")
                except Exception as e:
                    ssh_logger.warning(f"Could not update key permissions: {e}")
            else:
                raise FileNotFoundError(f"SSH private key not found at {mounted_key_path}")
        else:
            # Copy from mounted location
            ssh_logger.info(f"Copying SSH private key from {mounted_key_path} to {self.key_file}")
            
            try:
                key_content = mounted_key_path.read_text()
                self.key_file.write_text(key_content)
                
                # Set strict permissions (600)
                os.chmod(self.key_file, stat.S_IRUSR | stat.S_IWUSR)
                
                ssh_logger.info("SSH private key copied successfully")
                
            except Exception as e:
                ssh_logger.error(f"Failed to copy SSH private key: {e}")
                raise
    
    def _generate_ssh_config(self) -> None:
        """Generate SSH config file for Docker hosts."""
        self._generate_ssh_config_from_hosts_yml()
    
    def _generate_ssh_config_from_hosts_yml(self) -> None:
        """Generate SSH config from hosts.yml configuration."""
        hosts_config = settings.load_hosts_config()
        enabled_hosts = hosts_config.get_enabled_hosts()
        
        if not enabled_hosts:
            ssh_logger.warning("No enabled hosts found in hosts.yml")
            return
        
        ssh_logger.info(f"Generating SSH config for {len(enabled_hosts)} hosts from hosts.yml")
        
        # Read existing config if it exists
        existing_config = self._read_existing_config()
        
        # Generate new config section
        config_lines = ["# BEGIN DOCKER MONITOR MANAGED HOSTS"]
        config_lines.append("# Generated from hosts.yml configuration")
        
        for alias, host_config in enabled_hosts.items():
            # Create SSH alias similar to legacy format for compatibility
            ssh_alias = f"docker-{host_config.hostname.replace('.', '-').replace(':', '-')}-{host_config.port}"
            
            config_lines.extend([
                f"Host {ssh_alias}",
                f"    HostName {host_config.hostname}",
                f"    User {host_config.user}",
                f"    Port {host_config.port}",
                f"    IdentityFile {host_config.key_file}",
                "    PasswordAuthentication no",
                "    StrictHostKeyChecking accept-new",
                "    ServerAliveInterval 60",
                "    ServerAliveCountMax 3",
                "    ControlMaster auto",
                "    ControlPath ~/.ssh/control-%r@%h:%p",
                "    ControlPersist 10m",
                f"    # {host_config.description}",
                ""
            ])
        
        config_lines.append("# END DOCKER MONITOR MANAGED HOSTS")
        
        # Write the final config
        self._write_ssh_config(existing_config, config_lines)
        
        ssh_logger.info(f"SSH config written successfully with {len(enabled_hosts)} hosts from hosts.yml")
    
    
    def _read_existing_config(self) -> str:
        """Read existing SSH config and remove our managed section."""
        existing_config = ""
        if self.config_file.exists():
            existing_config = self.config_file.read_text()
            
            # Remove our managed section if it exists
            start_marker = "# BEGIN DOCKER MONITOR MANAGED HOSTS"
            end_marker = "# END DOCKER MONITOR MANAGED HOSTS"
            
            if start_marker in existing_config and end_marker in existing_config:
                start_idx = existing_config.index(start_marker)
                end_idx = existing_config.index(end_marker) + len(end_marker)
                existing_config = existing_config[:start_idx] + existing_config[end_idx + 1:]
        
        return existing_config
    
    def _write_ssh_config(self, existing_config: str, config_lines: list) -> None:
        """Write SSH config with existing config and new managed section."""
        # Combine with existing config
        new_config = existing_config.rstrip() + "\n\n" + "\n".join(config_lines) + "\n"
        
        # Write config file
        self.config_file.write_text(new_config)
        
        # Set permissions (644)
        os.chmod(self.config_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    
    def get_docker_hosts(self) -> List[Tuple[str, str, int]]:
        """Get list of configured Docker hosts."""
        return settings.get_docker_hosts()
    
    def test_connections(self) -> dict:
        """Test SSH connections to all configured hosts."""
        results = {}
        hosts = self.get_docker_hosts()
        
        for alias, host, port in hosts:
            ssh_logger.info(f"Testing connection to {host}:{port}")
            
            # Generate the SSH alias that matches what's in the SSH config file
            # This should match the format used in _generate_ssh_config_from_hosts_yml
            ssh_alias = f"docker-{host.replace('.', '-').replace(':', '-')}-{port}"
            
            # Test with docker version command using the correct SSH alias
            cmd = f"docker -H ssh://{ssh_alias} version"
            exit_code = os.system(f"{cmd} >/dev/null 2>&1")
            
            success = exit_code == 0
            results[host] = {
                "alias": alias,
                "port": port,
                "connected": success,
                "ssh_alias": ssh_alias
            }
            
            if success:
                ssh_logger.info(f"Successfully connected to {host}:{port}")
            else:
                ssh_logger.error(f"Failed to connect to {host}:{port}")
        
        return results