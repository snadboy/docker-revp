"""Configuration management for SSH Docker Client."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, field_validator, ValidationError

from .exceptions import ConfigurationError
from .models import HostConfig, HostDefaults


class HostsConfig(BaseModel):
    """Hosts configuration container."""
    
    hosts: Dict[str, HostConfig] = {}
    defaults: Optional[HostDefaults] = None
    
    @field_validator('hosts')
    def validate_hosts(cls, v: Dict[str, HostConfig]) -> Dict[str, HostConfig]:
        """Validate hosts dictionary."""
        if not isinstance(v, dict):
            raise ValueError("Hosts must be a dictionary")
        
        if not v:
            raise ValueError("At least one host must be configured")
        
        # Validate host aliases
        for alias in v.keys():
            if not isinstance(alias, str) or not alias:
                raise ValueError("Host alias must be a non-empty string")
            
            # Check for valid alias format
            alias_regex = r'^[a-zA-Z0-9_\-]+$'
            if not re.match(alias_regex, alias):
                raise ValueError(f"Host alias '{alias}' contains invalid characters")
        
        return v
    
    def get_host_config(self, alias: str) -> HostConfig:
        """Get host configuration with defaults applied."""
        if alias not in self.hosts:
            raise ValueError(f"Host '{alias}' not found in configuration")
        
        host = self.hosts[alias]
        
        # Apply defaults if they exist
        if self.defaults:
            # Create a new HostConfig with defaults applied where needed
            config_dict = host.model_dump()
            defaults_dict = self.defaults.model_dump()
            
            # Apply defaults only for fields that weren't explicitly set
            for field, default_value in defaults_dict.items():
                if field not in config_dict or config_dict[field] is None:
                    config_dict[field] = default_value
            
            return HostConfig(**config_dict)
        
        return host
    
    def get_enabled_hosts(self) -> Dict[str, HostConfig]:
        """Get only enabled hosts with defaults applied."""
        enabled_hosts = {}
        for alias, host in self.hosts.items():
            config = self.get_host_config(alias)
            if config.enabled:
                enabled_hosts[alias] = config
        return enabled_hosts
    
    def to_docker_hosts_format(self) -> List[Tuple[str, str, int]]:
        """Convert to legacy Docker hosts format for backward compatibility.
        
        Returns list of (alias, hostname, port) tuples.
        """
        hosts = []
        for alias, host_config in self.get_enabled_hosts().items():
            # Create SSH alias for the host
            ssh_alias = host_config.get_ssh_alias()
            hosts.append((ssh_alias, host_config.hostname, host_config.port))
        return hosts
    
    def get_host_by_hostname(self, hostname: str) -> Optional[Tuple[str, HostConfig]]:
        """Find host by hostname.
        
        Returns tuple of (alias, HostConfig) or None if not found.
        """
        for alias, host in self.hosts.items():
            if host.hostname == hostname:
                return (alias, self.get_host_config(alias))
        return None
    
    def validate_ssh_keys(self) -> List[str]:
        """Validate that all SSH key files exist.
        
        Returns list of missing key files.
        """
        missing_keys = []
        checked_keys = set()
        
        for alias, host in self.get_enabled_hosts().items():
            key_path = Path(host.key_file).expanduser()
            
            # Skip if we've already checked this key
            if str(key_path) in checked_keys:
                continue
            
            checked_keys.add(str(key_path))
            
            if not key_path.exists():
                missing_keys.append(f"{alias}: {host.key_file}")
        
        return missing_keys


def load_hosts_config(config_file: Path) -> HostsConfig:
    """Load hosts configuration from YAML file.
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        HostsConfig object
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    try:
        if not config_file.exists():
            raise ConfigurationError(f"Configuration file not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ConfigurationError("Configuration file is empty")
        
        # Validate the structure
        if not isinstance(data, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        if 'hosts' not in data:
            raise ConfigurationError("Configuration must contain 'hosts' section")
        
        # Apply defaults to each host entry before validation
        defaults = data.get('defaults', {})
        if defaults:
            for host_alias, host_config in data['hosts'].items():
                # Apply defaults for missing fields
                for key, value in defaults.items():
                    if key not in host_config:
                        host_config[key] = value
        
        # Create and validate configuration
        try:
            hosts_config = HostsConfig(**data)
        except ValidationError as e:
            raise ConfigurationError(f"Invalid configuration: {e}")
        
        return hosts_config
        
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML format: {e}")
    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(f"Error loading configuration: {e}")


def validate_hosts_config(config_file: Path) -> bool:
    """Validate hosts configuration file without loading it.
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        load_hosts_config(config_file)
        return True
    except Exception:
        return False


def create_example_config(output_file: Path) -> None:
    """Create an example configuration file.
    
    Args:
        output_file: Path where to write the example configuration
    """
    example_config = """# SSH Docker Client Configuration
# This file defines the remote Docker hosts to manage

# Global defaults for all hosts (optional)
defaults:
  user: deploy
  port: 22
  key_file: ~/.ssh/id_rsa
  enabled: true

# Host definitions
hosts:
  # Production server
  prod:
    hostname: prod.example.com
    description: "Production Docker host"
    
  # Staging server with custom settings
  staging:
    hostname: staging.example.com
    user: staging-user  # Override default user
    port: 2222         # Custom SSH port
    key_file: ~/.ssh/staging_key
    description: "Staging environment"
    
  # Development server (temporarily disabled)
  dev:
    hostname: dev.local
    enabled: false  # Disable this host
    description: "Local development"
    
  # Another production server
  prod2:
    hostname: prod2.example.com
    user: root  # Different user
    description: "Secondary production host"
"""
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(example_config)
    print(f"Example configuration written to: {output_file}")