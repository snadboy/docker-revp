# Network Request Tracing Implementation Proposal

## Overview
Implement comprehensive network request tracing tools for the infrastructure that uses Tailscale MagicDNS, split DNS via PiHole, and Caddy reverse proxy.

## Implementation Plan

### 1. Create a DNS Resolution Tracer Script
- Trace DNS queries through Tailscale MagicDNS and split DNS
- Show resolution path from client → Tailscale → PiHole → final IP
- Identify which DNS server answered the query
- Support for both MagicDNS names and split DNS domains

### 2. Implement Caddy Request Tracing
- Add debug logging configuration to capture request flow
- Set up trace headers that follow requests through the proxy
- Create a log parser to visualize request paths
- Track timing information for each proxy hop

### 3. Build an End-to-End Network Trace Tool
- Generate unique trace IDs for requests
- Follow requests from DNS resolution through Caddy to backend services
- Correlate logs across all components (DNS, Tailscale, Caddy, Backend)
- Provide timing information for each hop
- Support for both CLI and web-based visualization

### 4. Set up Monitoring Dashboards
- Use GoAccess for real-time Caddy log analysis
- Custom scripts to correlate DNS queries with proxy requests
- Network flow visualization showing the complete request path
- Integration with existing RevP dashboard

## Technical Details

### DNS Tracing Methods
```bash
# Trace DNS resolution on the client
dig +trace app.snadboy.com

# Check Tailscale DNS resolution
tailscale status --json | jq '.MagicDNSSuffix'
tailscale dns status

# Query specific DNS servers
dig @100.100.100.100 app.snadboy.com  # Tailscale MagicDNS
dig @<pihole-ip> app.snadboy.com      # PiHole directly
```

### Caddy Debug Configuration
```json
{
  "logging": {
    "logs": {
      "default": {
        "level": "DEBUG",
        "encoder": {
          "format": "json"
        }
      }
    }
  }
}
```

### Trace Headers Implementation
```
reverse_proxy {
    header_up X-Trace-ID {header.X-Trace-ID}
    header_down X-Trace-ID {header.X-Trace-ID}
}
```

## Benefits
- Full visibility into request flow through the infrastructure
- Easy debugging of DNS resolution issues
- Performance monitoring and bottleneck identification
- Better understanding of Tailscale routing paths
- Correlation of issues across multiple layers