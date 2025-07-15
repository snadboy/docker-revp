"""Configuration management for Docker Reverse Proxy."""
import os
from pathlib import Path
from typing import List, Tuple
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Docker hosts configuration
    docker_hosts: str = ""
    ssh_user: str = ""
    ssh_private_key: str = ""
    
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
    api_port: int = 8080
    api_host: str = "0.0.0.0"
    
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
    
    def validate(self) -> None:
        """Validate required settings."""
        errors = []
        
        if not self.docker_hosts:
            errors.append("DOCKER_HOSTS environment variable is required")
        else:
            # Validate DOCKER_HOSTS format by attempting to parse it
            try:
                self.parse_docker_hosts()
            except ValueError as e:
                errors.append(f"DOCKER_HOSTS validation failed: {e}")
        
        if not self.ssh_user:
            errors.append("SSH_USER environment variable is required")
        
        if not self.ssh_private_key:
            errors.append("SSH_PRIVATE_KEY environment variable is required")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(errors))


# Global settings instance
settings = Settings()