"""Hosts configuration management for Docker Reverse Proxy."""
import re
import yaml
import socket
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, field_validator, ValidationError, model_validator

# Note: Avoiding logger import here to prevent circular imports
# Will log from config.py instead


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
    
    @model_validator(mode='after')
    def validate_unique_hostnames(self):
        """Validate that all hostnames are unique and check for conflicts."""
        hostnames_seen: Dict[str, str] = {}  # hostname -> alias mapping
        errors = []
        
        for alias, host_config in self.hosts.items():
            hostname = host_config.hostname.lower()  # Case-insensitive comparison
            
            # Check for duplicate hostnames
            if hostname in hostnames_seen:
                errors.append(
                    f"Duplicate hostname '{host_config.hostname}' found for aliases "
                    f"'{alias}' and '{hostnames_seen[hostname]}'. Each host must have a unique hostname."
                )
            else:
                hostnames_seen[hostname] = alias
        
        # If there are any errors, raise them all at once
        if errors:
            raise ValueError("\n".join(errors))
        
        return self
    
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
        
        # Apply defaults to each host entry before validation
        defaults = data.get('defaults', {})
        if defaults:
            for host_alias, host_config in data['hosts'].items():
                # Apply defaults for missing fields
                for key, value in defaults.items():
                    if key not in host_config:
                        host_config[key] = value
        
        # Create and validate configuration
        hosts_config = HostsConfig(**data)
        
        # Note: Using print instead of logger to avoid circular imports
        print(f"INFO: Loaded {len(hosts_config.hosts)} hosts from {config_file}")
        return hosts_config
        
    except FileNotFoundError as e:
        print(f"ERROR: Hosts configuration file not found: {e}")
        raise
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML in hosts configuration: {e}")
        raise ValueError(f"Invalid YAML format in hosts configuration: {e}")
    except ValidationError as e:
        print(f"ERROR: Invalid hosts configuration: {e}")
        raise ValueError(f"Invalid hosts configuration: {e}")
    except Exception as e:
        print(f"ERROR: Error loading hosts configuration: {e}")
        raise


def validate_hosts_config(config_file: Path) -> bool:
    """Validate hosts configuration file without loading it."""
    try:
        load_hosts_config(config_file)
        return True
    except Exception as e:
        print(f"ERROR: Hosts configuration validation failed: {e}")
        return False


def verify_hostname_resolution(hosts_config: HostsConfig, check_dns: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Verify hostname resolution and connectivity for all configured hosts.
    
    Args:
        hosts_config: The loaded hosts configuration
        check_dns: Whether to perform DNS resolution checks
    
    Returns:
        Dictionary with verification results for each host
    """
    results = {}
    
    for alias, host_config in hosts_config.get_enabled_hosts().items():
        result = {
            "alias": alias,
            "hostname": host_config.hostname,
            "enabled": host_config.enabled,
            "dns_resolved": False,
            "ip_address": None,
            "errors": [],
            "warnings": []
        }
        
        # Check DNS resolution if requested
        if check_dns:
            try:
                # Attempt to resolve hostname
                ip_info = socket.getaddrinfo(host_config.hostname, host_config.port, 
                                            socket.AF_UNSPEC, socket.SOCK_STREAM)
                if ip_info:
                    # Get the first resolved IP address
                    result["ip_address"] = ip_info[0][4][0]
                    result["dns_resolved"] = True
                    print(f"INFO: Host '{alias}' ({host_config.hostname}) resolved to {result['ip_address']}")
                else:
                    result["errors"].append(f"Could not resolve hostname '{host_config.hostname}'")
                    print(f"ERROR: Failed to resolve hostname '{host_config.hostname}' for alias '{alias}'")
                    
            except socket.gaierror as e:
                result["errors"].append(f"DNS resolution failed: {e}")
                print(f"ERROR: DNS resolution failed for '{host_config.hostname}' (alias: {alias}): {e}")
            except Exception as e:
                result["errors"].append(f"Unexpected error during DNS resolution: {e}")
                print(f"ERROR: Unexpected error resolving '{host_config.hostname}' (alias: {alias}): {e}")
        
        results[alias] = result
    
    # Check for hosts resolving to the same IP address
    ip_to_hosts: Dict[str, List[str]] = {}
    for alias, result in results.items():
        if result["ip_address"]:
            ip = result["ip_address"]
            if ip not in ip_to_hosts:
                ip_to_hosts[ip] = []
            ip_to_hosts[ip].append(alias)
    
    # Add warnings for hosts resolving to the same IP
    for ip, aliases in ip_to_hosts.items():
        if len(aliases) > 1:
            warning = f"Multiple hosts resolve to the same IP {ip}: {', '.join(aliases)}"
            print(f"WARNING: {warning}")
            for alias in aliases:
                results[alias]["warnings"].append(warning)
    
    return results


def validate_and_report_hosts(config_file: Path, check_dns: bool = True) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate hosts configuration and provide detailed report.
    
    Args:
        config_file: Path to hosts.yml configuration file
        check_dns: Whether to perform DNS resolution checks
    
    Returns:
        Tuple of (success, report_dict) where report_dict contains validation results
    """
    report = {
        "config_file": str(config_file),
        "valid": False,
        "total_hosts": 0,
        "enabled_hosts": 0,
        "errors": [],
        "warnings": [],
        "hosts": {}
    }
    
    try:
        # Load and validate configuration
        hosts_config = load_hosts_config(config_file)
        report["valid"] = True
        report["total_hosts"] = len(hosts_config.hosts)
        report["enabled_hosts"] = len(hosts_config.get_enabled_hosts())
        
        # Check for duplicate hostnames (this will be caught by the validator)
        hostnames = [h.hostname.lower() for h in hosts_config.hosts.values()]
        if len(hostnames) != len(set(hostnames)):
            report["errors"].append("Duplicate hostnames detected in configuration")
        
        # Verify hostname resolution
        if check_dns:
            verification_results = verify_hostname_resolution(hosts_config, check_dns=True)
            report["hosts"] = verification_results
            
            # Aggregate errors and warnings
            for alias, result in verification_results.items():
                if result["errors"]:
                    report["errors"].extend([f"{alias}: {e}" for e in result["errors"]])
                if result["warnings"]:
                    report["warnings"].extend([f"{alias}: {w}" for w in result["warnings"]])
        
        # Print summary
        print(f"\n=== Hosts Configuration Validation Report ===")
        print(f"Configuration file: {config_file}")
        print(f"Total hosts: {report['total_hosts']}")
        print(f"Enabled hosts: {report['enabled_hosts']}")
        
        if report["errors"]:
            print(f"\nERRORS ({len(report['errors'])}):")
            for error in report["errors"]:
                print(f"  - {error}")
        
        if report["warnings"]:
            print(f"\nWARNINGS ({len(report['warnings'])}):")
            for warning in report["warnings"]:
                print(f"  - {warning}")
        
        if not report["errors"] and not report["warnings"]:
            print("\n✓ All hosts validated successfully")
        
        return (len(report["errors"]) == 0, report)
        
    except Exception as e:
        report["errors"].append(f"Failed to load configuration: {e}")
        print(f"ERROR: Failed to validate hosts configuration: {e}")
        return (False, report)