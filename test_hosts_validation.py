#!/usr/bin/env python3
"""Test script for hosts configuration validation."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.hosts_config import validate_and_report_hosts, load_hosts_config, verify_hostname_resolution

def test_hosts_validation():
    """Test the hosts validation functionality."""
    
    config_file = Path("/home/snadboy/docker/docker-revp/config/hosts.yml")
    
    print("=" * 60)
    print("Testing Hosts Configuration Validation")
    print("=" * 60)
    
    # Test 1: Load and validate configuration
    print("\n1. Loading hosts configuration...")
    try:
        hosts_config = load_hosts_config(config_file)
        print(f"   ✓ Successfully loaded {len(hosts_config.hosts)} hosts")
        
        # Show configured hosts
        print("\n   Configured hosts:")
        for alias, host in hosts_config.hosts.items():
            print(f"     - {alias}: {host.hostname} (enabled: {host.enabled})")
    except Exception as e:
        print(f"   ✗ Failed to load configuration: {e}")
        return
    
    # Test 2: Check for duplicate hostnames
    print("\n2. Checking for duplicate hostnames...")
    hostnames = [h.hostname.lower() for h in hosts_config.hosts.values()]
    duplicates = [h for h in hostnames if hostnames.count(h) > 1]
    if duplicates:
        print(f"   ✗ Found duplicate hostnames: {set(duplicates)}")
    else:
        print("   ✓ No duplicate hostnames found")
    
    # Test 3: DNS resolution verification
    print("\n3. Verifying DNS resolution...")
    results = verify_hostname_resolution(hosts_config, check_dns=True)
    
    for alias, result in results.items():
        if result["dns_resolved"]:
            print(f"   ✓ {alias}: {result['hostname']} -> {result['ip_address']}")
        else:
            print(f"   ✗ {alias}: {result['hostname']} - DNS resolution failed")
            if result["errors"]:
                for error in result["errors"]:
                    print(f"      Error: {error}")
    
    # Test 4: Full validation report
    print("\n4. Running full validation report...")
    success, report = validate_and_report_hosts(config_file, check_dns=True)
    
    print("\n" + "=" * 60)
    print("Validation Summary:")
    print(f"  Status: {'✓ PASSED' if success else '✗ FAILED'}")
    print(f"  Total hosts: {report['total_hosts']}")
    print(f"  Enabled hosts: {report['enabled_hosts']}")
    print(f"  Errors: {len(report['errors'])}")
    print(f"  Warnings: {len(report['warnings'])}")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = test_hosts_validation()
    sys.exit(0 if success else 1)