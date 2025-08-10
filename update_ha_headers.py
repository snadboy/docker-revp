#!/usr/bin/env python3
"""Update Home Assistant route with proper header forwarding."""

import json
import requests

def update_ha_route():
    """Update the Home Assistant route with proper headers for IP forwarding."""
    
    caddy_api_url = "http://localhost:2019"
    
    # Define the updated route configuration for Home Assistant
    ha_route = {
        "@id": "revp_static_route_ha_snadboy_com",
        "match": [{
            "host": ["ha.snadboy.com"]
        }],
        "handle": [{
            "handler": "subroute",
            "routes": [
                {
                    "match": [{"protocol": "http"}],
                    "handle": [{
                        "handler": "static_response",
                        "headers": {
                            "Location": ["https://{http.request.host}{http.request.uri}"]
                        },
                        "status_code": 308
                    }],
                    "terminal": True
                },
                {
                    "match": [{"protocol": "https"}],
                    "handle": [{
                        "handler": "reverse_proxy",
                        "headers": {
                            "request": {
                                "set": {
                                    "X-Forwarded-For": ["{http.request.header.X-Forwarded-For}, {http.request.remote.host}"],
                                    "X-Forwarded-Proto": ["{http.request.scheme}"],
                                    "X-Forwarded-Host": ["{http.request.host}"],
                                    "X-Real-IP": ["{http.request.remote.host}"],
                                    "Host": ["{http.request.host}"],
                                    "Connection": ["{http.request.header.Connection}"],
                                    "Upgrade": ["{http.request.header.Upgrade}"]
                                }
                            }
                        },
                        "upstreams": [{
                            "dial": "homeassistant:8123"
                        }]
                    }],
                    "terminal": True
                }
            ]
        }],
        "terminal": True
    }
    
    try:
        # Get current routes
        response = requests.get(f"{caddy_api_url}/config/apps/http/servers/srv0/routes")
        if response.status_code == 200:
            routes = response.json() or []
            
            # Find and remove existing HA route
            ha_index = None
            for i, route in enumerate(routes):
                if route.get("@id") == "revp_static_route_ha_snadboy_com":
                    ha_index = i
                    break
            
            if ha_index is not None:
                # Remove existing route
                del_response = requests.delete(
                    f"{caddy_api_url}/config/apps/http/servers/srv0/routes/{ha_index}"
                )
                if del_response.status_code in [200, 204]:
                    print(f"✓ Removed existing HA route at index {ha_index}")
                else:
                    print(f"✗ Failed to remove existing HA route: {del_response.status_code}")
            
            # Add updated route
            response = requests.post(
                f"{caddy_api_url}/config/apps/http/servers/srv0/routes",
                json=ha_route,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201]:
                print("✓ Successfully added updated HA route with proper headers")
                print("\nConfigured headers:")
                print("  - X-Forwarded-For: Client IP forwarding")
                print("  - X-Forwarded-Proto: Protocol forwarding (https)")
                print("  - X-Forwarded-Host: Host header forwarding")
                print("  - X-Real-IP: Real client IP")
                print("  - Host: Preserve host header")
                print("  - Connection/Upgrade: WebSocket support")
            else:
                print(f"✗ Failed to add HA route: {response.status_code} - {response.text}")
        
    except Exception as e:
        print(f"✗ Error updating HA route: {e}")

if __name__ == "__main__":
    update_ha_route()