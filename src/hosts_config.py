"""Hosts configuration management for Docker Reverse Proxy."""
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, field_validator, ValidationError

from .logger import api_logger


class HostConfig(BaseModel):
    """Individual host configuration."""
    hostname: str
    user: str
    port: int = 22
    key_file: str
    description: str = ""
    enabled: bool = True
    
    @field_validator('hostname')
    def validate_hostname(cls, v):
        """Validate hostname format."""
        if not v or not isinstance(v, str):
            raise ValueError("Hostname must be a non-empty string")
        
        v = v.strip()
        
        # Basic hostname validation
        if len(v) > 253:
            raise ValueError("Hostname must be 253 characters or less")
        
        # Check for valid hostname format
        hostname_regex = r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$'
        if not re.match(hostname_regex, v):
            raise ValueError("Hostname contains invalid characters")
        
        return v
    
    @field_validator('user')
    def validate_user(cls, v):
        """Validate SSH user format."""
        if not v or not isinstance(v, str):
            raise ValueError("User must be a non-empty string")
        
        v = v.strip()
        
        # Basic SSH username validation
        if len(v) > 32:
            raise ValueError("Username must be 32 characters or less")
        
        # Check for valid username format (no special characters except underscore and hyphen)
        username_regex = r'^[a-zA-Z0-9_\-]+$'
        if not re.match(username_regex, v):
            raise ValueError("Username contains invalid characters")
        
        return v
    
    @field_validator('port')
    def validate_port(cls, v):
        """Validate SSH port."""
        if not isinstance(v, int):
            raise ValueError("Port must be an integer")
        
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        
        return v
    
    @field_validator('key_file')
    def validate_key_file(cls, v):
        """Validate SSH key file path."""
        if not v or not isinstance(v, str):
            raise ValueError("Key file path must be a non-empty string")
        
        v = v.strip()
        
        # Basic path validation
        if not v.startswith('/'):
            raise ValueError("Key file path must be absolute")
        
        return v
    
    @field_validator('description')
    def validate_description(cls, v):
        """Validate description."""
        if v is None:
            return ""
        
        if not isinstance(v, str):
            raise ValueError("Description must be a string")
        
        return v.strip()


class HostDefaults(BaseModel):
    """Default values for host configuration."""
    user: str = "revp"
    port: int = 22
    key_file: str = "/root/.ssh/id_revp"
    enabled: bool = True
    
    @field_validator('user')
    def validate_user(cls, v):
        """Validate default SSH user format."""
        if not v or not isinstance(v, str):
            raise ValueError("Default user must be a non-empty string")
        
        v = v.strip()
        
        # Basic SSH username validation
        if len(v) > 32:
            raise ValueError("Default username must be 32 characters or less")
        
        username_regex = r'^[a-zA-Z0-9_\-]+$'
        if not re.match(username_regex, v):
            raise ValueError("Default username contains invalid characters")
        
        return v
    
    @field_validator('port')
    def validate_port(cls, v):
        """Validate default SSH port."""
        if not isinstance(v, int):
            raise ValueError("Default port must be an integer")
        
        if not 1 <= v <= 65535:
            raise ValueError("Default port must be between 1 and 65535")
        
        return v
    
    @field_validator('key_file')
    def validate_key_file(cls, v):
        """Validate default SSH key file path."""
        if not v or not isinstance(v, str):
            raise ValueError("Default key file path must be a non-empty string")
        
        v = v.strip()
        
        if not v.startswith('/'):
            raise ValueError("Default key file path must be absolute")
        
        return v


class HostsConfig(BaseModel):
    """Hosts configuration container."""
    hosts: Dict[str, HostConfig] = {}
    defaults: Optional[HostDefaults] = None
    
    @field_validator('hosts')
    def validate_hosts(cls, v):
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
            # (This is a simplified approach - in practice you might want more sophisticated merging)
            for field, default_value in defaults_dict.items():
                if field in config_dict and field != 'enabled':  # Don't apply enabled default if explicitly set
                    continue
                if field not in config_dict or config_dict[field] == getattr(HostConfig.model_fields[field], 'default', None):
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
        """Convert to legacy DOCKER_HOSTS format for backward compatibility."""
        hosts = []
        for alias, host_config in self.get_enabled_hosts().items():
            # Create a safe alias for SSH config (similar to legacy format)
            safe_alias = f"docker-{host_config.hostname.replace('.', '-').replace(':', '-')}-{host_config.port}"
            hosts.append((safe_alias, host_config.hostname, host_config.port))
        return hosts


def load_hosts_config(config_file: Path) -> HostsConfig:
    """Load hosts configuration from YAML file."""
    try:
        if not config_file.exists():
            raise FileNotFoundError(f"Hosts configuration file not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError("Hosts configuration file is empty")
        
        # Validate the structure
        if not isinstance(data, dict):
            raise ValueError("Hosts configuration must be a dictionary")
        
        if 'hosts' not in data:
            raise ValueError("Hosts configuration must contain 'hosts' section")
        
        # Create and validate configuration
        hosts_config = HostsConfig(**data)
        
        api_logger.info(f"Loaded {len(hosts_config.hosts)} hosts from {config_file}")
        return hosts_config
        
    except FileNotFoundError as e:
        api_logger.error(f"Hosts configuration file not found: {e}")
        raise
    except yaml.YAMLError as e:
        api_logger.error(f"Invalid YAML in hosts configuration: {e}")
        raise ValueError(f"Invalid YAML format in hosts configuration: {e}")
    except ValidationError as e:
        api_logger.error(f"Invalid hosts configuration: {e}")
        raise ValueError(f"Invalid hosts configuration: {e}")
    except Exception as e:
        api_logger.error(f"Error loading hosts configuration: {e}")
        raise


def validate_hosts_config(config_file: Path) -> bool:
    """Validate hosts configuration file without loading it."""
    try:
        load_hosts_config(config_file)
        return True
    except Exception as e:
        api_logger.error(f"Hosts configuration validation failed: {e}")
        return False