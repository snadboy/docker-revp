"""Data models for SSH Docker Client."""

import re
from typing import Dict, Optional

from pydantic import BaseModel, field_validator


class HostConfig(BaseModel):
    """Individual host configuration."""
    
    hostname: str
    user: str
    port: int = 22
    key_file: str
    description: str = ""
    enabled: bool = True
    
    @field_validator('hostname')
    def validate_hostname(cls, v: str) -> str:
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
            raise ValueError(f"Hostname '{v}' contains invalid characters")
        
        return v
    
    @field_validator('user')
    def validate_user(cls, v: str) -> str:
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
            raise ValueError(f"Username '{v}' contains invalid characters")
        
        return v
    
    @field_validator('port')
    def validate_port(cls, v: int) -> int:
        """Validate SSH port."""
        if not isinstance(v, int):
            raise ValueError("Port must be an integer")
        
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        
        return v
    
    @field_validator('key_file')
    def validate_key_file(cls, v: str) -> str:
        """Validate SSH key file path."""
        if not v or not isinstance(v, str):
            raise ValueError("Key file path must be a non-empty string")
        
        v = v.strip()
        
        # Basic path validation - allow both absolute and relative paths
        if not v:
            raise ValueError("Key file path cannot be empty")
        
        # Expand user home directory
        if v.startswith('~'):
            from pathlib import Path
            v = str(Path(v).expanduser())
        
        return v
    
    @field_validator('description')
    def validate_description(cls, v: Optional[str]) -> str:
        """Validate description."""
        if v is None:
            return ""
        
        if not isinstance(v, str):
            raise ValueError("Description must be a string")
        
        return v.strip()
    
    def get_ssh_alias(self) -> str:
        """Generate SSH config alias for this host."""
        # Create a safe alias for SSH config
        safe_hostname = self.hostname.replace('.', '-').replace(':', '-')
        return f"docker-{safe_hostname}-{self.port}"


class HostDefaults(BaseModel):
    """Default values for host configuration."""
    
    user: str = "root"
    port: int = 22
    key_file: str = "~/.ssh/id_rsa"
    enabled: bool = True
    
    @field_validator('user')
    def validate_user(cls, v: str) -> str:
        """Validate default SSH user format."""
        if not v or not isinstance(v, str):
            raise ValueError("Default user must be a non-empty string")
        
        v = v.strip()
        
        # Basic SSH username validation
        if len(v) > 32:
            raise ValueError("Default username must be 32 characters or less")
        
        username_regex = r'^[a-zA-Z0-9_\-]+$'
        if not re.match(username_regex, v):
            raise ValueError(f"Default username '{v}' contains invalid characters")
        
        return v
    
    @field_validator('port')
    def validate_port(cls, v: int) -> int:
        """Validate default SSH port."""
        if not isinstance(v, int):
            raise ValueError("Default port must be an integer")
        
        if not 1 <= v <= 65535:
            raise ValueError(f"Default port must be between 1 and 65535, got {v}")
        
        return v
    
    @field_validator('key_file')
    def validate_key_file(cls, v: str) -> str:
        """Validate default SSH key file path."""
        if not v or not isinstance(v, str):
            raise ValueError("Default key file path must be a non-empty string")
        
        v = v.strip()
        
        if not v:
            raise ValueError("Default key file path cannot be empty")
        
        # Expand user home directory
        if v.startswith('~'):
            from pathlib import Path
            v = str(Path(v).expanduser())
        
        return v


class DockerCommand(BaseModel):
    """Docker command execution details."""
    
    command: str
    host: Optional[str] = None
    timeout: Optional[int] = None
    
    @field_validator('command')
    def validate_command(cls, v: str) -> str:
        """Validate Docker command."""
        if not v or not isinstance(v, str):
            raise ValueError("Command must be a non-empty string")
        
        v = v.strip()
        
        if not v:
            raise ValueError("Command cannot be empty")
        
        return v
    
    @field_validator('timeout')
    def validate_timeout(cls, v: Optional[int]) -> Optional[int]:
        """Validate timeout value."""
        if v is None:
            return None
        
        if not isinstance(v, int):
            raise ValueError("Timeout must be an integer")
        
        if v <= 0:
            raise ValueError("Timeout must be positive")
        
        return v


class ContainerInfo(BaseModel):
    """Container information."""
    
    id: str
    name: str
    image: str
    status: str
    host: str
    labels: Dict[str, str] = {}
    ports: Dict[str, Optional[str]] = {}
    
    @property
    def short_id(self) -> str:
        """Get short container ID (first 12 characters)."""
        return self.id[:12] if len(self.id) > 12 else self.id