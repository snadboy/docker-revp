"""Configuration management for Docker Reverse Proxy."""
import os
from pathlib import Path
from typing import List, Tuple, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings

from .hosts_config import HostsConfig, load_hosts_config


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Docker hosts configuration
    docker_hosts: str = ""
    ssh_user: str = ""
    ssh_private_key_path: str = "/home/app/.ssh/docker_monitor_key"
    
    # Caddy configuration
    caddy_api_url: str = "http://caddy:2019"
    
    # Monitoring configuration
    reconcile_interval: int = 300  # seconds
    
    # Logging configuration
    log_level: str = "INFO"
    log_max_size: int = 10  # MB
    log_backup_count: int = 5
    log_file_path: str = "/var/log/docker-revp/monitor.log"
    
    # API configuration
    api_bind: str = "0.0.0.0:8080"
    
    # Static routes configuration
    static_routes_file: str = "/app/config/static-routes.yml"
    
    # Hosts configuration
    hosts_config_file: str = "/app/config/hosts.yml"
    
    @field_validator('api_bind')
    def validate_api_bind(cls, v):
        """Validate API bind format is HOST:PORT."""
        if ':' not in v:
            raise ValueError(f"API_BIND must be in HOST:PORT format, got: {v}")
        
        parts = v.split(':')
        if len(parts) != 2:
            raise ValueError(f"API_BIND must be in HOST:PORT format, got: {v}")
        
        try:
            port = int(parts[1])
            if not 1 <= port <= 65535:
                raise ValueError(f"Port must be between 1 and 65535, got: {port}")
        except ValueError:
            raise ValueError(f"Invalid port number in API_BIND: {parts[1]}")
        
        return v
    
    # Version configuration
    app_version: str = "unknown"
    build_date: str = "unknown"
    git_commit: str = "unknown"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_version_info()
        self._hosts_config: Optional[HostsConfig] = None
    
    def _load_version_info(self) -> None:
        """Load version information from environment or VERSION file."""
        # Try environment variables first (set by Docker)
        self.app_version = os.getenv("APP_VERSION", self.app_version)
        self.build_date = os.getenv("BUILD_DATE", self.build_date)
        self.git_commit = os.getenv("GIT_COMMIT", self.git_commit)
        
        # If still unknown, try to read from VERSION file
        if self.app_version == "unknown":
            try:
                version_file = Path(__file__).parent.parent / "VERSION"
                if version_file.exists():
                    self.app_version = version_file.read_text().strip()
            except Exception:
                pass
    
    def load_hosts_config(self) -> HostsConfig:
        """Load hosts configuration from hosts.yml file."""
        if self._hosts_config is not None:
            return self._hosts_config
        
        hosts_file = Path(self.hosts_config_file)
        
        try:
            self._hosts_config = load_hosts_config(hosts_file)
            return self._hosts_config
        except Exception as e:
            # Log warning but don't fail - fall back to DOCKER_HOSTS
            from .logger import api_logger
            api_logger.warning(f"Could not load hosts.yml configuration: {e}")
            api_logger.info("Falling back to DOCKER_HOSTS environment variable")
            return None
    
    def get_hosts_config(self) -> Optional[HostsConfig]:
        """Get cached hosts configuration."""
        return self._hosts_config
    
    def has_hosts_config(self) -> bool:
        """Check if hosts.yml configuration is available and loaded."""
        if self._hosts_config is not None:
            return True
        
        # Try to load it
        config = self.load_hosts_config()
        return config is not None
    
    def parse_docker_hosts(self) -> List[Tuple[str, str, int]]:
        """Parse DOCKER_HOSTS into list of (alias, host, port) tuples."""
        if not self.docker_hosts:
            return []
        
        hosts = []
        for host_spec in self.docker_hosts.split():
            # Validate against invalid formats
            if any(scheme in host_spec.lower() for scheme in ['unix://', 'tcp://', 'http://', 'https://']):
                raise ValueError(f"Invalid DOCKER_HOST format '{host_spec}': protocol schemes not supported. Use hostname or hostname:port format.")
            
            if '/' in host_spec and not host_spec.replace(':', '').replace('.', '').replace('-', '').isalnum():
                raise ValueError(f"Invalid DOCKER_HOST format '{host_spec}': paths not supported. Use hostname or hostname:port format.")
            
            if ':' in host_spec:
                host, port_str = host_spec.rsplit(':', 1)
                try:
                    port = int(port_str)
                    if port < 1 or port > 65535:
                        raise ValueError(f"Invalid port {port} in '{host_spec}': port must be between 1 and 65535")
                except ValueError as e:
                    if "port must be between" in str(e):
                        raise e
                    # If port is not a number, treat the whole thing as hostname
                    host = host_spec
                    port = 22
            else:
                host = host_spec
                port = 22
            
            # Basic hostname validation
            if not host or len(host) > 253:
                raise ValueError(f"Invalid hostname '{host}': must be 1-253 characters")
            
            # Create a safe alias for SSH config
            alias = f"docker-{host.replace('.', '-').replace(':', '-')}-{port}"
            hosts.append((alias, host, port))
        
        return hosts
    
    def get_docker_hosts(self) -> List[Tuple[str, str, int]]:
        """Get Docker hosts from either hosts.yml or DOCKER_HOSTS environment variable.
        
        Returns list of (alias, hostname, port) tuples.
        Prioritizes hosts.yml if available, falls back to DOCKER_HOSTS.
        """
        # Try to use hosts.yml first
        if self.has_hosts_config():
            hosts_config = self.get_hosts_config()
            if hosts_config:
                return hosts_config.to_docker_hosts_format()
        
        # Fall back to legacy DOCKER_HOSTS
        return self.parse_docker_hosts()
    
    def validate(self) -> None:
        """Validate required settings."""
        errors = []
        
        # Check for either hosts.yml or DOCKER_HOSTS configuration
        has_hosts_yml = self.has_hosts_config()
        has_docker_hosts = bool(self.docker_hosts)
        
        if not has_hosts_yml and not has_docker_hosts:
            errors.append("Either hosts.yml configuration file or DOCKER_HOSTS environment variable is required")
        
        # Validate hosts.yml if present
        if has_hosts_yml:
            try:
                hosts_config = self.get_hosts_config()
                if not hosts_config or not hosts_config.get_enabled_hosts():
                    errors.append("No enabled hosts found in hosts.yml configuration")
            except Exception as e:
                errors.append(f"hosts.yml validation failed: {e}")
        
        # Validate DOCKER_HOSTS if present (and hosts.yml not available)
        elif has_docker_hosts:
            try:
                docker_hosts = self.parse_docker_hosts()
                if not docker_hosts:
                    errors.append("No valid hosts found in DOCKER_HOSTS")
            except ValueError as e:
                errors.append(f"DOCKER_HOSTS validation failed: {e}")
            
            # For legacy DOCKER_HOSTS, we still need SSH_USER
            if not self.ssh_user:
                errors.append("SSH_USER environment variable is required when using DOCKER_HOSTS")
            
            # Check SSH key for legacy configuration
            if not Path(self.ssh_private_key_path).exists():
                errors.append(f"SSH private key file not found at {self.ssh_private_key_path}")
        
        # For hosts.yml configuration, SSH settings are per-host, so we don't validate global SSH settings
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(errors))


# Global settings instance
settings = Settings()