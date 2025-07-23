"""Utility functions for SSH Docker Client."""

import json
from typing import Any, Dict, List, Optional


def parse_docker_ps_json(output: str) -> List[Dict[str, Any]]:
    """Parse JSON output from docker ps command.
    
    Args:
        output: Raw output from docker ps --format json
        
    Returns:
        List of container dictionaries
    """
    containers = []
    
    for line in output.strip().split('\n'):
        if not line:
            continue
        
        try:
            container = json.loads(line)
            containers.append(container)
        except json.JSONDecodeError:
            # Skip invalid lines
            continue
    
    return containers


def parse_docker_inspect(output: str) -> Optional[Dict[str, Any]]:
    """Parse docker inspect output.
    
    Args:
        output: Raw JSON output from docker inspect
        
    Returns:
        Container information dictionary or None
    """
    try:
        data = json.loads(output)
        if isinstance(data, list) and data:
            return data[0]
        return data
    except json.JSONDecodeError:
        return None


def parse_docker_events_json(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single Docker event JSON line.
    
    Args:
        line: Single line from docker events --format json
        
    Returns:
        Event dictionary or None if invalid
    """
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def parse_container_labels(labels_str: str) -> Dict[str, str]:
    """Parse container labels from comma-separated string.
    
    Args:
        labels_str: Comma-separated labels (key=value,key2=value2)
        
    Returns:
        Dictionary of labels
    """
    labels = {}
    
    if not labels_str:
        return labels
    
    for label in labels_str.split(','):
        if '=' in label:
            key, value = label.split('=', 1)
            labels[key.strip()] = value.strip()
    
    return labels


def format_container_ports(ports_str: str) -> List[str]:
    """Parse and format container ports string.
    
    Args:
        ports_str: Raw ports string from docker ps
        
    Returns:
        List of formatted port mappings
    """
    if not ports_str:
        return []
    
    ports = []
    for port_mapping in ports_str.split(','):
        port_mapping = port_mapping.strip()
        if port_mapping:
            ports.append(port_mapping)
    
    return ports


def safe_get_nested(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary values.
    
    Args:
        data: Dictionary to search
        *keys: Sequence of keys to traverse
        default: Default value if key not found
        
    Returns:
        Value at nested key path or default
    """
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def escape_shell_arg(arg: str) -> str:
    """Escape shell argument for safe execution.
    
    Args:
        arg: Argument to escape
        
    Returns:
        Escaped argument
    """
    # Simple escaping - for more complex cases, use shlex.quote
    return arg.replace("'", "'\"'\"'")


def parse_docker_version(output: str) -> Dict[str, str]:
    """Parse docker version output.
    
    Args:
        output: Raw output from docker version
        
    Returns:
        Dictionary with version information
    """
    version_info = {}
    current_section = None
    
    for line in output.split('\n'):
        line = line.strip()
        
        if not line:
            continue
        
        if line.endswith(':') and not ' ' in line:
            current_section = line[:-1].lower()
        elif ':' in line and current_section:
            key, value = line.split(':', 1)
            key = key.strip().lower().replace(' ', '_')
            value = value.strip()
            
            if current_section == 'client':
                version_info[f"client_{key}"] = value
            elif current_section == 'server':
                version_info[f"server_{key}"] = value
            else:
                version_info[key] = value
    
    return version_info