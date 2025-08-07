#!/usr/bin/env python3
"""Add a catch-all route for undefined domains to Caddy."""

import json
import requests

def add_catchall_route():
    """Add a catch-all route to handle undefined domains."""
    
    caddy_api_url = "http://localhost:2019"
    
    # Define the catch-all route configuration
    catchall_route = {
        "@id": "revp_catchall_route",
        "match": [{
            "host": ["*.snadboy.com"]
        }],
        "handle": [{
            "handler": "file_server",
            "root": "/var/www/error_pages",
            "index_names": ["404.html"],
            "status_code": 404
        }],
        "terminal": False  # Allow other routes to be checked first
    }
    
    try:
        # Get current routes
        response = requests.get(f"{caddy_api_url}/config/apps/http/servers/srv0/routes")
        if response.status_code == 200:
            routes = response.json() or []
            
            # Check if catch-all route already exists
            for i, route in enumerate(routes):
                if route.get("@id") == "revp_catchall_route":
                    print("Catch-all route already exists, updating...")
                    # Update existing route
                    response = requests.put(
                        f"{caddy_api_url}/config/apps/http/servers/srv0/routes/{i}",
                        json=catchall_route,
                        headers={"Content-Type": "application/json"}
                    )
                    if response.status_code in [200, 201]:
                        print("✓ Successfully updated catch-all route")
                    else:
                        print(f"✗ Failed to update catch-all route: {response.status_code} - {response.text}")
                    return
            
            # Add catch-all route at the end (lowest priority)
            response = requests.post(
                f"{caddy_api_url}/config/apps/http/servers/srv0/routes",
                json=catchall_route,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201]:
                print("✓ Successfully added catch-all route")
            else:
                print(f"✗ Failed to add catch-all route: {response.status_code} - {response.text}")
        
    except Exception as e:
        print(f"✗ Error adding catch-all route: {e}")

if __name__ == "__main__":
    add_catchall_route()