# Let's Encrypt Recovery Instructions

## Current Status
- Let's Encrypt is currently experiencing an outage (as of July 21, 2025)
- Caddy is temporarily configured to use internal/self-signed certificates
- This causes browser certificate warnings but allows the sites to function

## To Restore Let's Encrypt Certificates

1. Check if Let's Encrypt is operational: https://letsencrypt.status.io/

2. Edit `/home/snadboy/docker/docker-revp/caddy/Caddyfile` and remove these lines:
   ```
   local_certs
   skip_install_trust
   ```

3. Restart Caddy:
   ```
   docker compose restart caddy
   ```

4. Monitor the logs to ensure certificates are obtained:
   ```
   docker compose logs -f caddy | grep -E "obtained|successfully"
   ```

## Notes
- HTTP/3 (QUIC) has been disabled due to ERR_QUIC_PROTOCOL_ERROR
- The email admin@snadboy.com is configured for certificate notifications
- All routing configurations remain intact and will work once proper certificates are obtained