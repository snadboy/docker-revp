# Installing Technitium DNS Server on Proxmox with Tailscale Split DNS

## Introduction

Technitium DNS Server is a powerful, open-source DNS server that provides an intuitive web interface and advanced features perfect for home labs and enterprise environments. In this guide, we'll set up Technitium on Proxmox to serve as an internal DNS server with DHCP integration, supporting A, CNAME, and automatic PTR records, while also configuring it as a split DNS solution for Tailscale networks.

**Version Note:** This guide is updated for **Technitium DNS Server v13.6**. The interface has been streamlined with most configuration now centralized in the Settings page. Menu locations may differ from older versions, but core functionality remains the same. When in doubt, check the Settings page (gear icon) as most options are there.

## Key Terminology

Before we begin, let's clarify some important naming conventions and networking concepts used throughout this guide:

**DNS Naming Conventions:**
- **Container Hostname** (`technitium-dns`): The name of the LXC container in Proxmox
- **Internal Domain** (`snadboy.internal`): Your private network's domain name - all internal devices will use this suffix
- **DNS Server Domain** (`ns.snadboy.internal`): The fully qualified domain name (FQDN) of your DNS server itself

**DNS Record Types:**
- **A Record**: Maps a hostname to an IP address (e.g., `server1.snadboy.internal` → `192.168.1.100`)
- **CNAME Record**: Creates an alias pointing to another hostname (e.g., `www` → `server1`)
- **PTR Record**: Reverse DNS - maps an IP address back to a hostname (e.g., `192.168.1.100` → `server1.snadboy.internal`)

**Networking Concepts:**
- **Split DNS**: Using different DNS servers for different domains (local vs. Tailscale)
- **0.0.0.0**: Special IP meaning "all network interfaces" - when a service listens on 0.0.0.0:53, it accepts connections from ANY network interface
- **Trailing Dot**: In DNS, `example.com.` with a dot means "this is the complete domain" (not a subdomain)
- **DNS Forwarders**: External DNS servers (like 8.8.8.8 or 1.1.1.1) that your DNS server queries when it doesn't know an answer locally
- **Recursive Resolution**: When a DNS server queries root servers directly to find answers (slower but more independent)
- **MagicDNS**: Tailscale's internal DNS service (100.100.100.100) that resolves Tailscale device names
- **--accept-dns=false**: Tailscale flag that prevents it from overriding system DNS (crucial for DNS servers!)

## Command Notation Guide

Throughout this guide, commands are clearly labeled to indicate where they should be executed:

- **[PROXMOX NODE]** - Commands run on the Proxmox host/node itself
- **[LXC CONTAINER]** - Commands run inside the Technitium container
- **[ANY CLIENT]** - Commands that can be run from any client machine
- **[WEB BROWSER]** - Actions performed in a web interface
- **[DHCP SERVER]** - Configuration on your DHCP server/router

Example:
```bash
# [PROXMOX NODE] This command runs on the Proxmox host
pct start 110

# [LXC CONTAINER] This command runs inside the container
apt update
```

## Prerequisites

- Proxmox VE 7.x or 8.x installed and running
- Basic understanding of DNS concepts
- Access to Proxmox web interface
- Access to DHCP server for configuring reservation
- Tailscale account (free tier works fine)
- **Note:** Container will need TUN/TAP support for Tailscale (covered in Part 4)

## Example Network Configuration

This guide uses the following example configuration (adjust for your network):

```yaml
Network Details:
  Subnet: 192.168.1.0/24
  Gateway: 192.168.1.1
  
DNS Server Configuration:
  Container Name: technitium-dns
  IP Address: 192.168.1.53 (via DHCP reservation)
  Tailscale IP: 100.x.x.x (obtained after Tailscale setup)
  
  Domains:
    Internal Domain: snadboy.internal (private, local only)
    Public Domain: snadboy.com (if you own one, resolved via Cloudflare)
    Tailscale Domain: tailnet-name.ts.net (your Tailscale network)
  
  DNS Zones to Create:
    Forward Zone: snadboy.internal
    Reverse Zone: 1.168.192.in-addr.arpa
    (Do NOT create zone for snadboy.com - let Cloudflare handle it)
  
  Upstream Forwarders (for external domains):
    Primary: 1.1.1.1 (Cloudflare - handles snadboy.com too)
    Secondary: 8.8.8.8 (Google - backup)
  
Example DNS Records:
  Forward Records (in snadboy.internal zone):
    ns.snadboy.internal → 192.168.1.53 (A record)
    server1.snadboy.internal → 192.168.1.100 (A record)
    nas.snadboy.internal → 192.168.1.101 (A record)
    www.snadboy.internal → server1.snadboy.internal (CNAME)
  
  Reverse Records (in 1.168.192.in-addr.arpa zone):
    192.168.1.53 → ns.snadboy.internal (PTR)
    192.168.1.100 → server1.snadboy.internal (PTR)
    192.168.1.101 → nas.snadboy.internal (PTR)
    
  Public Domain Resolution (handled by Cloudflare):
    www.snadboy.com → Your public web server IP
    mail.snadboy.com → Your public mail server IP
```

**Note:** You can customize these names for your environment:
- Replace `snadboy.internal` with your preferred domain (e.g., `home.local`, `smith.lan`, `lab.internal`)
- Replace `ns` with your preferred DNS server name (e.g., `dns`, `ns1`, `resolver`, `technitium`)
- Choose different forwarders based on your preference (Cloudflare, Google, Quad9, OpenDNS, etc.)
- **Reverse zone naming**: For different subnets:
  - 192.168.1.x → `1.168.192.in-addr.arpa`
  - 192.168.0.x → `0.168.192.in-addr.arpa`
  - 10.0.0.x → `0.0.10.in-addr.arpa`
  - 172.16.1.x → `1.16.172.in-addr.arpa`

## Part 1: Creating a Container in Proxmox

### Step 1: Download Container Template

1. Log into your Proxmox web interface
2. Navigate to your local storage → **CT Templates**
3. Click **Templates** and download **Ubuntu 22.04** or **Debian 12** template

### Step 2: Create LXC Container

1. Click **Create CT** in the top-right corner
2. Configure the container:
   ```
   General:
   - Node: Select your Proxmox node
   - CT ID: 110 (or next available)
   - Hostname: technitium-dns
     (This is the container's name in Proxmox)
   - Password: Set a secure password
   - Unprivileged container: ✓ (recommended)
   
   Template:
   - Storage: local
   - Template: Select Ubuntu-22.04 or Debian-12
   
   Root Disk:
   - Storage: local-lvm (or your preferred storage)
   - Disk size: 8 GB (minimum)
   
   CPU:
   - Cores: 2
   
   Memory:
   - Memory: 1024 MB
   - Swap: 512 MB
   
   Network:
   - Bridge: vmbr0
   - IPv4: DHCP
   - Note: Configure DHCP reservation for this container's MAC address
   
   DNS:
   - DNS domain: snadboy.internal
     (Your internal network domain - this will be used for all internal hosts)
   - DNS servers: 1.1.1.1,8.8.8.8
     (External DNS for the CONTAINER ITSELF during setup - NOT the same as forwarders)
     (These are used by the container OS, not by the Technitium service)
   ```

3. Review settings and click **Finish**

### Step 3: Start and Access Container

```bash
# [PROXMOX NODE] Start the container
pct start 110

# [PROXMOX NODE] Get the container's MAC address for DHCP reservation
pct config 110 | grep net0
# Note the MAC address (hwaddr=XX:XX:XX:XX:XX:XX)
```

### Step 4: Configure DHCP Reservation

Before proceeding, configure a DHCP reservation on your DHCP server:

1. **Access your DHCP server** (router or dedicated DHCP server)
2. **Create a DHCP reservation**:
   - MAC Address: Use the MAC from Step 3
   - IP Address: 192.168.1.53 (or your preferred DNS server IP)
   - Hostname: technitium-dns (optional, helps identify in DHCP lease list)
   - Description: "Technitium DNS - ns.snadboy.internal" (for documentation)
3. **Save and apply** the DHCP configuration
4. **Restart the container** to obtain the reserved IP:
   ```bash
   # [PROXMOX NODE] Reboot container to get DHCP reservation
   pct reboot 110
   
   # [PROXMOX NODE] Wait for container to restart, then enter it
   pct enter 110
   
   # [LXC CONTAINER] Verify IP assignment
   ip addr show eth0
   ```

**Optional: Set Static MAC Address**

To ensure the DHCP reservation always works, even if the container is recreated:

```bash
# [PROXMOX NODE] Set a specific MAC address for the container
pct set 110 -net0 name=eth0,bridge=vmbr0,hwaddr=DE:AD:BE:EF:00:53,ip=dhcp

# This ensures the MAC address remains constant
```

### Step 5: Continue with System Updates

```bash
# [PROXMOX NODE] Enter the container console if not already
pct enter 110

# [LXC CONTAINER] Update the system
apt update && apt upgrade -y
```

## Part 2: Installing Technitium DNS Server

**Note:** All commands in this section are executed **INSIDE the LXC container** unless otherwise specified.

### Step 1: Install Prerequisites

```bash
# [LXC CONTAINER] Install required packages
apt install curl wget gnupg apt-transport-https ca-certificates -y

# [LXC CONTAINER] Install .NET Runtime (required for Technitium)
wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

apt update
apt install aspnetcore-runtime-8.0 -y
```

### Step 2: Install Technitium DNS Server

```bash
# [LXC CONTAINER] Download and run the installer script
curl -sSL https://download.technitium.com/dns/install.sh | bash

# The installer will:
# - Download Technitium DNS Server
# - Create systemd service
# - Start the service automatically
```

### Step 3: Configure Firewall (if enabled)

```bash
# [LXC CONTAINER] If using ufw
ufw allow 53/tcp
ufw allow 53/udp
ufw allow 5380/tcp  # Web interface
ufw allow 67/udp    # DHCP if needed
ufw reload
```

## Part 3: Initial Technitium Configuration

**Note:** This entire section is performed in the **WEB BROWSER**. In v13.6, most configuration is centralized in the **Settings** page (gear icon). If you can't find a specific option, check all sections within Settings.

### Step 1: Access Web Interface

1. [WEB BROWSER] Open your browser and navigate to: `http://192.168.1.53:5380` (use your DHCP-reserved IP)
2. Create an admin account on first login
3. Note down your credentials securely

**Interface Overview (v13.6):**
- **Dashboard**: Real-time statistics and query logs
- **Zones**: Manage DNS zones and records (you'll create 2 zones here!)
- **Settings**: All server configuration options (most options are here)
- **Apps**: Optional applications (may not be visible by default)
- **About**: Version information and updates

### Step 2: Configure Basic Settings

1. [WEB BROWSER] Click **Settings** (gear icon in top menu)
   
   The Settings page has multiple collapsible sections. Look for:
   
   **Web Service Section:**
   - Web service port configuration (default 5380)
   - Enable/disable IPv6 for web service
   
   **DNS Server Section:**
   - DNS Server Domain: Enter `ns.snadboy.internal`
     *(This is how your DNS server identifies itself)*
   - DNS Server Local Endpoints: Should show `0.0.0.0:53` and/or `[::]:53`
     *(0.0.0.0 means listening on ALL network interfaces - this is correct!)*
     - `0.0.0.0:53` = IPv4 on all interfaces
     - `[::]:53` = IPv6 on all interfaces (if enabled)
     - This allows DNS queries from any network interface
   - Enable DNSSEC Validation: ✓ (recommended)
   - Enable DNS-over-UDP/TCP on port 53
   
   **Cache Section:**
   - Default cache values are usually fine
   - Increase if you have a large network
   
   **Proxy & Forwarders Section:**
   - This DNS Server Is A Forwarder: ✓ (recommended for faster resolution)
   - Configure upstream DNS servers (forwarders):
     - `1.1.1.1` (Cloudflare - fast, privacy-focused)
     - `8.8.8.8` (Google - reliable, widely used)
     - `9.9.9.9` (Quad9 - security-focused, blocks malware)
   
   *(Forwarders are external DNS servers that Technitium will query when it doesn't know an answer. Using forwarders is faster than recursive resolution but means trusting the upstream provider.)*
   
   **Alternative Options:**
   - Use "Root Hints Only" for full recursive resolution (slower but more private)
   - Use "System DNS" to use whatever the container is configured with
   
   **Blocking Section:**
   - Enable Blocking: Configure as needed
   
   **Important:** After making any changes in Settings:
   - Scroll to the bottom of the page
   - Click **Save** button
   - Some changes may require a service restart (you'll be prompted)

### Step 3: Configure Zones for Internal DNS

#### Understanding DNS Zones
- **Forward Zone** (`snadboy.internal`): Maps hostnames to IP addresses (hostname → IP)
- **Reverse Zone** (`1.168.192.in-addr.arpa`): Maps IP addresses to hostnames (IP → hostname)
- **Both zones are separate** - you must create each one individually
- **Both are needed** for a complete DNS setup!

**Important: Internal vs Public Domains**
- `snadboy.internal` = Your private/internal domain (resolved locally)
- `snadboy.com` = Your public domain (forwarded to Cloudflare for public IPs)
- These are completely separate - internal uses private IPs, public uses internet IPs

#### Part A: Create Forward Lookup Zone

1. [WEB BROWSER] Click on **Zones** in the top menu
2. Click **Add Zone** button (or Quick Add)
3. Create primary zone:
   ```
   Zone Name: snadboy.internal
   Type: Primary Zone
   ```
   *(This zone will handle all DNS queries for *.snadboy.internal)*
4. Click **Add** to create the zone

#### Part B: Create Reverse Lookup Zone (IMPORTANT!)

1. [WEB BROWSER] Still in **Zones**, click **Add Zone** again
2. Create the reverse zone:
   ```
   Zone Name: 1.168.192.in-addr.arpa
   Type: Primary Zone
   ```
   *(This is for the 192.168.1.x network - note the octets are reversed!)*
3. Click **Add** to create the zone

**Why create both zones?**
- Forward zone: Allows `nslookup server1.snadboy.internal` to work
- Reverse zone: Allows `nslookup 192.168.1.100` to work
- Some services (mail servers, SSH, etc.) require working reverse DNS
- **Without reverse zone**: Forward lookups work, but `nslookup 192.168.1.53` will fail
- **Best practice**: Always create both zones for a complete DNS setup

#### Part C: Add DNS Records to Forward Zone

1. [WEB BROWSER] Click on your `snadboy.internal` zone to open it
2. First, create a record for the DNS server itself:
   - Click **Add Record** button
   - Type: A
   - Name: `ns` (just "ns", not the full domain)
   - IPv4 Address: `192.168.1.53` (your DNS server's IP)
   - TTL: 3600 seconds (or leave default)
   - Click **Add Record**
   *(This creates ns.snadboy.internal → 192.168.1.53)*

3. Add your other hosts:
   - Click **Add Record**
   - Type: A
   - Name: `server1`
   - IPv4 Address: `192.168.1.100`
   - TTL: 3600 seconds
   - Click **Add Record**
   *(This creates server1.snadboy.internal → 192.168.1.100)*

4. Repeat for all internal hosts

**Important:** After adding records:
- Changes are usually instant
- If records don't resolve immediately, try:
  - Clear the cache (Dashboard → Clear Cache button if available)
  - Or wait for TTL to expire
  - Or restart the DNS service from Settings

#### Part D: Add CNAME Records (Optional Aliases)

1. [WEB BROWSER] In the `snadboy.internal` zone, click **Add Record**
   - Type: CNAME
   - Name: `www`
   - Domain Name: `server1.snadboy.internal.` (note the trailing dot)
   - TTL: 3600 seconds
   - Click **Add Record**
   *(CNAME creates an alias: www.snadboy.internal → server1.snadboy.internal)*

#### Part E: Add PTR Records to Reverse Zone

1. [WEB BROWSER] Go back to **Zones** and click on `1.168.192.in-addr.arpa` zone
2. Add PTR records for your hosts:
   - Click **Add Record**
   - Type: PTR
   - Name: `53` (last octet of IP for 192.168.1.53)
   - Domain Name: `ns.snadboy.internal.` (note trailing dot!)
   - Click **Add Record**
   
3. Add PTR for other hosts:
   - Click **Add Record**
   - Type: PTR
   - Name: `100` (for 192.168.1.100)
   - Domain Name: `server1.snadboy.internal.`
   - Click **Add Record**

**Understanding PTR record names:**
- For IP 192.168.1.53 → Use name "53"
- For IP 192.168.1.100 → Use name "100"
- The zone already handles the "192.168.1" part!

**Note about Automatic PTR:** 
- In v13.6, automatic PTR generation may not be available
- Some versions have an "Add reverse (PTR) record" checkbox when creating A records
- For now, manually create PTR records as shown above
- PTR records are important for mail servers and services that verify reverse DNS

---

### Summary: What You Should Have Created

After completing Step 3, you should have:

**Two Zones:**
1. ✅ `snadboy.internal` (forward zone)
2. ✅ `1.168.192.in-addr.arpa` (reverse zone)

**Records in Forward Zone (snadboy.internal):**
- ✅ A record: `ns` → `192.168.1.53`
- ✅ A record: `server1` → `192.168.1.100`
- ✅ CNAME: `www` → `server1.snadboy.internal.`
- ✅ (Add more A records for your other devices)

**Records in Reverse Zone (1.168.192.in-addr.arpa):**
- ✅ PTR: `53` → `ns.snadboy.internal.`
- ✅ PTR: `100` → `server1.snadboy.internal.`
- ✅ (Add PTR records for each A record you created)

---

## Part 4: Installing and Configuring Tailscale

**Important:** Tailscale requires TUN/TAP support which LXC containers don't have by default. We need to enable this first.

### Step 0: Enable TUN/TAP for the Container (REQUIRED!)

```bash
# [PROXMOX NODE] Stop the container
pct stop 110

# [PROXMOX NODE] Edit the container configuration
# Add these lines to /etc/pve/lxc/110.conf
echo "lxc.cgroup2.devices.allow: c 10:200 rwm" >> /etc/pve/lxc/110.conf
echo "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file" >> /etc/pve/lxc/110.conf

# [PROXMOX NODE] Start the container
pct start 110

# [PROXMOX NODE] Enter the container
pct enter 110

# [LXC CONTAINER] Verify TUN device exists
ls -la /dev/net/tun
# Should show: crw-rw-rw- 1 root root 10, 200 ...
```

**Alternative method if the above doesn't work:**

```bash
# [PROXMOX NODE] For Proxmox 7.x and 8.x, you might need:
echo "lxc.cap.drop:" >> /etc/pve/lxc/110.conf
echo "lxc.cgroup2.devices.allow: c 10:200 rwm" >> /etc/pve/lxc/110.conf
echo "lxc.mount.entry: /dev/net dev/net none bind,create=dir" >> /etc/pve/lxc/110.conf

# Then restart the container
pct stop 110 && pct start 110
```

### Step 1: Install Tailscale

```bash
# [LXC CONTAINER] Add Tailscale's package signing key and repository
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.tailscale-keyring.list | tee /etc/apt/sources.list.d/tailscale.list

# [LXC CONTAINER] Install Tailscale
apt update
apt install tailscale -y

# [LXC CONTAINER] Start the Tailscale daemon
systemctl start tailscaled
systemctl enable tailscaled

# [LXC CONTAINER] Verify the daemon is running
systemctl status tailscaled
# Should show "active (running)"

# [LXC CONTAINER] Now start Tailscale and authenticate
tailscale up --accept-routes --accept-dns=false

# Follow the link to authenticate with your Tailscale account
```

**Troubleshooting TUN/TAP issues:**

If you see errors like:
- `Module tun not found`
- `/dev/net/tun does not exist`
- `CreateTUN("tailscale0") failed`

This means the container doesn't have TUN/TAP access. Follow Step 0 above to fix it.

**For already running containers:**
1. Exit the container (`exit`)
2. Stop it from Proxmox node (`pct stop 110`)
3. Add the TUN/TAP configuration
4. Start and re-enter the container
5. Try Tailscale again

**Why `--accept-dns=false`?**

This flag is **critical** for our DNS server setup:

1. **Prevents DNS Conflicts**: By default, Tailscale overwrites the system's DNS settings to use MagicDNS (100.100.100.100). On a DNS server, this would create a circular dependency!

2. **Maintains Container DNS**: We need the container to keep using external DNS (1.1.1.1, 8.8.8.8) for its own operations, NOT Tailscale's DNS.

3. **Technitium Controls Split DNS**: We want Technitium to be the authoritative DNS server that decides when to forward to Tailscale's MagicDNS, not have Tailscale override everything.

4. **Avoids Bootstrap Issues**: If the DNS server container itself used Tailscale for DNS, it couldn't resolve external domains needed for updates, package installation, etc.

**Why `--accept-routes`?**

This flag allows the container to access other Tailscale subnets if you have them configured. It's optional but recommended for full Tailscale network access.

**What happens with this setup:**
- The Technitium container keeps using 1.1.1.1/8.8.8.8 for its own DNS needs
- Technitium serves as DNS for all Tailscale clients
- Technitium forwards Tailscale domains to MagicDNS when needed
- You get the best of both worlds: local DNS control + Tailscale's features

### Step 2: Configure Tailscale Settings

```bash
# [LXC CONTAINER] Get your Tailscale IP
tailscale ip -4
# Note this IP - you'll need it for configuring Tailscale admin console

# [LXC CONTAINER] Verify DNS wasn't changed
cat /etc/resolv.conf
# Should still show 1.1.1.1 or 8.8.8.8
# If it shows 100.100.100.100, Tailscale overwrote your DNS! 
# Run: tailscale down && tailscale up --accept-routes --accept-dns=false

# [LXC CONTAINER] Enable IP forwarding for split DNS
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding=1' >> /etc/sysctl.conf
sysctl -p
```

## Part 5: Configuring Split DNS for Tailscale

### Understanding the Split DNS Architecture

```
┌─────────────────────────────────────────────┐
│           Tailscale Network                 │
│                                             │
│  Tailscale Client                           │
│       ↓ (DNS Query)                         │
│  Technitium (100.x.x.x)                     │
│       ├→ *.snadboy.internal = Local Zone    │
│       ├→ *.tailnet.name = → MagicDNS        │ 
│       └→ *.com, etc = → 1.1.1.1/8.8.8.8     │
│                                             │
│  Technitium Container itself:               │
│       └→ Always uses 1.1.1.1/8.8.8.8        │
│          (because --accept-dns=false)       │
└─────────────────────────────────────────────┘
```

### Step 1: Create Tailscale Zone in Technitium

1. [WEB BROWSER - TECHNITIUM] Go to **Zones** → **Add Zone**
2. Create zone for Tailscale:
   ```
   Zone: tailnet.name (use your actual tailnet name)
   Type: Primary Zone
   ```

### Step 2: Add Conditional Forwarders

1. [WEB BROWSER - TECHNITIUM] Navigate to **Settings**
2. Look for **Proxy & Forwarders** or **Conditional Forwarders** section
3. Add conditional forwarder for Tailscale:
   - Network/Zone: `100.in-addr.arpa`
   - Forwarder: `100.100.100.100` (Tailscale's MagicDNS)
   - Protocol: UDP
   - Click **Save**

**Alternative Method - Using Conditional Forwarder Zones:**
1. [WEB BROWSER] Go to **Zones** → **Add Zone**
2. Create a Conditional Forwarder Zone:
   - Zone: `tailnet.name` (use your actual tailnet name)
   - Type: Conditional Forwarder Zone
   - Forwarder: `100.100.100.100`
   - Click **Add**

### Step 3: Configure Split DNS Rules

**Note:** In v13.6, the Apps menu may not be visible by default or advanced blocking might work differently:

**Option 1 - If Apps Menu is Available:**
1. [WEB BROWSER - TECHNITIUM] Click **Apps** in the top menu
2. Look for **Advanced Blocking** or similar apps
3. Install and configure split DNS rules

**Option 2 - Using Conditional Forwarder Zones (Recommended):**
This method works reliably in v13.6:

1. For Tailscale domains - already configured in Step 2 above
2. For local domains - they automatically resolve locally when you create the zone
3. The split DNS is effectively achieved through:
   - Local zone `snadboy.internal` → resolves locally
   - Conditional forwarder for `tailnet.name` → forwards to 100.100.100.100
   - Everything else → forwards to your configured upstream DNS

**Option 3 - Manual Configuration:**
If neither option above works, split DNS can be achieved by ensuring:
- Your `snadboy.internal` zone exists and contains your local records
- Conditional forwarders are set up for Tailscale domains
- Default forwarders handle everything else

### Step 4: Configure Tailscale to Use Local DNS

[WEB BROWSER - TAILSCALE ADMIN] In the Tailscale admin console:

1. Go to **DNS** settings
2. **Add Global Nameserver**: 
   - Add the Tailscale IP of your Technitium server (100.x.x.x)
   - Get this IP from the container with: `tailscale ip -4`
3. **Add Search Domains**:
   - `snadboy.internal` (for your local resources)
4. **Enable "Override local DNS"** for all clients

**What this achieves:**
- All Tailscale clients will use Technitium as their DNS server
- Technitium becomes the single source of truth for ALL DNS queries
- Both local network clients (via DHCP) and Tailscale clients use the same DNS server

**How the DNS flow works now:**

1. **Local network clients** (via DHCP) → Query Technitium at 192.168.1.53
2. **Tailscale clients** (via MagicDNS) → Query Technitium at 100.x.x.x
3. **Technitium resolves**:
   - `server1.snadboy.internal` → Local A record (192.168.1.100)
   - `www.snadboy.com` → Forward to Cloudflare → Public IP
   - `device.tailnet.name` → Forward to MagicDNS (100.100.100.100)
   - `google.com` → Forward to Cloudflare (1.1.1.1)

This creates a perfect split DNS setup where Technitium is in full control!

## Part 6: DHCP Integration

### Understanding Your DNS Architecture

**Your Goal:**
1. **Local Network**: DHCP hands out `192.168.1.53` (ns.snadboy.internal) as DNS server
2. **Tailscale Network**: Tailscale/MagicDNS configured to use the same Technitium server
3. **Split DNS Resolution**:
   - `*.snadboy.internal` → Resolved locally by Technitium
   - `*.snadboy.com` (your public domain) → Forwarded to Cloudflare (1.1.1.1)
   - `*.tailnet.name` → Forwarded to MagicDNS (100.100.100.100)
   - Everything else → Forwarded to Cloudflare/Google (1.1.1.1/8.8.8.8)

```yaml
DNS Flow:
  All Clients (Local + Tailscale):
    → Query ns.snadboy.internal (192.168.1.53 or 100.x.x.x)
    
  Technitium decides:
    snadboy.internal → Local zone (private IPs)
    snadboy.com → Cloudflare (public website)
    tailnet.name → MagicDNS (Tailscale devices)
    google.com → Cloudflare/Google (internet)
```

### Understanding DHCP Options

**Note:** Technitium v13.6+ includes a built-in DHCP server feature. You have two options:

**Option A - Use Existing DHCP Server (Recommended for beginners):**
- Keep your current router/DHCP server
- Just configure it to hand out Technitium as the DNS server

**Option B - Use Technitium's Built-in DHCP Server:**
- Disable DHCP on your router
- Configure DHCP in Technitium Settings → DHCP section
- More advanced but gives you unified management

### Step 1: Configure Your Existing DHCP Server (Option A)

[DHCP SERVER/ROUTER] On your DHCP server (router or dedicated server):

```
# Set DNS server option (use your DHCP-reserved IP for Technitium)
option domain-name-servers 192.168.1.53;

# Set domain name
option domain-name "snadboy.internal";

# Set search domain
option domain-search "snadboy.internal", "tailnet.name";
```

**What this achieves:**
- Every device on your local network gets `192.168.1.53` as their DNS server
- This is the same Technitium server that Tailscale clients will use
- All DNS queries go through one central point

**Note:** Since the Technitium server itself uses a DHCP reservation, ensure this reservation is configured before other clients start using it as their DNS server.

### Step 2: Configure Dynamic Updates (Optional)

If you want DHCP clients to automatically register in DNS:

1. [WEB BROWSER - TECHNITIUM] Navigate to **Settings**
2. Look for **TSIG** or **Security** settings
3. If TSIG is available:
   - Generate a new TSIG key for DHCP updates
   - Note the key name and secret
4. [DHCP SERVER] Configure your DHCP server to use this key for dynamic DNS updates

**Note:** Dynamic DNS updates require compatible DHCP server software (like ISC DHCP Server). Most consumer routers don't support this feature.

## Part 7: Testing and Verification

### Understanding DNS Resolution Flow

When a client queries your Technitium server:
1. **Local Zones First**: Checks if the query is for `snadboy.internal` (answered locally)
2. **Conditional Forwarders**: Checks if query matches special rules (e.g., Tailscale)
3. **Cache**: Checks if the answer is already cached from a previous query
4. **Forwarders**: If using forwarders, queries upstream servers (8.8.8.8, 1.1.1.1)
5. **Root Hints**: If not using forwarders, performs recursive resolution

### Test Using Technitium's Built-in Tools

1. [WEB BROWSER] In Technitium, use the **DNS Client** (if available):
   - Look for a DNS Client tab or testing tool
   - Test queries directly from the web interface

2. [WEB BROWSER] Check the **Dashboard**:
   - Verify queries are being received
   - Check cache hit ratio
   - Monitor for any errors

### Test Internal DNS Resolution

These tests can be run from either the Proxmox node or any client machine on your network:

```bash
# [ANY CLIENT or PROXMOX NODE] Test FORWARD zone (hostname → IP)
nslookup ns.snadboy.internal 192.168.1.53
nslookup server1.snadboy.internal 192.168.1.53
nslookup www.snadboy.internal 192.168.1.53

# [ANY CLIENT or PROXMOX NODE] Test REVERSE zone (IP → hostname)
nslookup 192.168.1.53 192.168.1.53
# Should return: ns.snadboy.internal

nslookup 192.168.1.100 192.168.1.53
# Should return: server1.snadboy.internal

# If reverse lookups fail, check:
# - Did you create the 1.168.192.in-addr.arpa zone?
# - Did you add PTR records to that zone?

# [ANY CLIENT or PROXMOX NODE] Test external resolution
nslookup google.com 192.168.1.53

# [ANY CLIENT or PROXMOX NODE] Alternative testing with dig
dig @192.168.1.53 ns.snadboy.internal
dig @192.168.1.53 -x 192.168.1.53  # Reverse lookup with dig
dig @192.168.1.53 google.com

# [LXC CONTAINER] Test that DNS is listening on all interfaces
netstat -tulpn | grep :53
# Should show 0.0.0.0:53 - this confirms it's listening on ALL interfaces
```

### Test Tailscale Split DNS

```bash
# [TAILSCALE-CONNECTED DEVICE] From a Tailscale-connected device
nslookup device.tailnet.name
nslookup server1.snadboy.internal

# Verify both Tailscale and local names resolve correctly
```

### Monitor DNS Queries

1. **[WEB BROWSER]** Click **Dashboard** to view real-time statistics:
   - Query rate graph
   - Cache utilization
   - Top clients
   - Top domains
   - Top blocked domains (if blocking enabled)

2. **Enable Query Logging** (for troubleshooting):
   - Settings → Logging section
   - Enable query logging temporarily
   - Return to Dashboard to see live query logs
   - **Important:** Disable logging after troubleshooting for better performance

3. **Check Zone Health:**
   - Click on **Zones**
   - Select your zone (e.g., `snadboy.internal`)
   - Verify all records are present and correct

## Part 8: Advanced Configuration

**Note:** Menu locations may vary in v13.6. Look for these features in the Settings page.

### Handling Your Public Domain (Optional)

If you own a public domain (like `snadboy.com`), you have several options:

**Option 1: Let Cloudflare Handle It (Recommended)**
- Don't create any zone for `snadboy.com` in Technitium
- Queries for `snadboy.com` will forward to Cloudflare (1.1.1.1)
- Cloudflare returns the public IPs for your website/services

**Option 2: Internal Override (Split-Horizon DNS)**
If you want `snadboy.com` to resolve to INTERNAL IPs when queried from inside:
1. Create a zone for `snadboy.com` in Technitium
2. Add A records with internal IPs
3. Now `www.snadboy.com` can resolve to 192.168.1.x internally
4. External clients still get public IPs from Cloudflare

**Option 3: Selective Override**
1. Don't create a zone for `snadboy.com`
2. But create specific records in `snadboy.internal`:
   - `vpn.snadboy.internal` → 192.168.1.50 (internal)
   - External users use `vpn.snadboy.com` → Public IP

### Enable DNS Security Features

1. **DNSSEC Validation**:
   - [WEB BROWSER] Settings → DNS Server section → Enable DNSSEC Validation ✓
   
2. **DNS-over-HTTPS (DoH) / DNS-over-TLS (DoT)**:
   - [WEB BROWSER] Settings → Look for **Optional Protocols** section
   - If available, you'll see options for:
     - DNS-over-HTTP
     - DNS-over-HTTPS (requires certificate)
     - DNS-over-TLS (requires certificate)
   - Enable desired protocols and configure ports
   - For HTTPS/TLS, you'll need to configure SSL certificates

3. **Rate Limiting & Security**:
   - [WEB BROWSER] Settings → look for **DDoS Protection** or similar
   - Configure options like:
     - Max requests per second per client
     - Block clients exceeding limits
     - Whitelist trusted IPs if needed

### Configure Blocking

1. [WEB BROWSER] Navigate to **Settings** → **Blocking** section
2. Configure blocking options:
   - Enable Blocking: ✓
   - Add block lists URLs (one per line):
     ```
     https://someonewhocares.org/hosts/zero/hosts
     https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
     https://big.oisd.nl/domainswild
     ```
   - Configure blocking type (NX Domain or custom IP)
   
**Using Apps (if available):**

The Apps menu might not be visible by default. To enable:
1. [WEB BROWSER] Check **Settings** for an option to enable Apps
2. Or check **About** → **Check for Updates** to ensure you have the latest version
3. If Apps menu appears:
   - Click **Apps** → **App Store**
   - Look for and install useful apps like:
     - Advanced Blocking
     - Query Reports
     - Split Horizon

### Configure DNS Forwarders

1. [WEB BROWSER] Settings → **Proxy & Forwarders** section
2. Configure how Technitium resolves external domains:

   **Option 1 - Use Forwarders (Recommended for most users):**
   - This Is A Forwarder: ✓
   - Add upstream DNS servers (one per line or use the add button):
     - `1.1.1.1` (Cloudflare - fastest)
     - `8.8.8.8` (Google - reliable)
     - `9.9.9.9` (Quad9 - blocks malware)
   
   **Option 2 - Root Hints (More private but slower):**
   - This Is A Forwarder: ✗
   - Use Root Hints Only: ✓
   - Technitium will recursively resolve all queries itself
   
   **What's the difference?**
   - **Forwarders**: Faster, relies on upstream providers, simpler
   - **Root Hints**: More private, slower initial queries, no dependency on third parties
   - Most home users should use forwarders for better performance

### Set Up Monitoring

```bash
# [LXC CONTAINER] Install monitoring agent (optional)
apt install prometheus-node-exporter -y
```

**Dashboard Monitoring in v13.6:**
1. [WEB BROWSER] Click **Dashboard** to view:
   - Total Queries
   - Queries Per Second
   - Top Clients
   - Top Domains
   - Top Blocked Domains
   - Recent Query Logs (if logging enabled)

2. [WEB BROWSER] For detailed stats, check:
   - Dashboard → Stats Graph (query trends over time)
   - Dashboard → Query Logs (if enabled in Settings)

## Maintenance and Best Practices

### DHCP Reservation Best Practices

1. **Document the reservation**:
   - Keep a record of the MAC address and reserved IP
   - Label the reservation clearly in your DHCP server (e.g., "Technitium DNS - ns.snadboy.internal")
   
2. **Set a long lease time** for the DNS server reservation:
   - Recommended: 7-30 days or permanent lease
   - Prevents IP changes during DHCP server restarts

3. **Monitor DHCP lease**:
   ```bash
   # [LXC CONTAINER] Check current IP assignment
   ip addr show eth0
   
   # [LXC CONTAINER] View DHCP lease information
   cat /var/lib/dhcp/dhclient.eth0.leases
   ```

### Regular Updates

```bash
# [LXC CONTAINER] Create update script
cat > /usr/local/bin/update-technitium.sh << 'EOF'
#!/bin/bash
systemctl stop dns.service
curl -sSL https://download.technitium.com/dns/install.sh | bash
systemctl start dns.service
EOF

chmod +x /usr/local/bin/update-technitium.sh
```

### Backup Configuration

```bash
# [LXC CONTAINER] Backup Technitium data
tar -czf /backup/technitium-$(date +%Y%m%d).tar.gz /etc/dns

# [LXC CONTAINER] Schedule regular backups
crontab -e
# Add: 0 2 * * * tar -czf /backup/technitium-$(date +\%Y\%m\%d).tar.gz /etc/dns
```

**Alternative: Backup from Proxmox Node**

```bash
# [PROXMOX NODE] Backup entire container
vzdump 110 --storage local --compress gzip --mode snapshot
```

### Performance Tuning

1. **Cache Settings**:
   - [WEB BROWSER] Settings → **Cache** section
   - Configure cache size based on your network (e.g., 10000-50000 entries)
   - Set Minimum/Maximum Record TTL as needed
   - Negative Cache: Configure how long to cache failed lookups

2. **Query Logging**:
   - [WEB BROWSER] Settings → **Logging** section (if available)
   - Enable/disable query logging
   - Configure log retention period
   - Note: Disable query logging for better performance unless troubleshooting

3. **Concurrent Requests**:
   - [WEB BROWSER] Settings → DNS Server section
   - Look for concurrent request limits
   - Adjust based on your network size

## Troubleshooting

### Technitium v13.6 Interface Issues

**Can't find a menu option:**
- Most configuration is in **Settings** (gear icon)
- Scroll through all sections in Settings
- Some features may require enabling in Settings first
- Check **About** for version and available updates

**DNS Server Local Endpoints shows 0.0.0.0:**
- This is **correct**! It means "listen on all interfaces"
- `0.0.0.0:53` = Accept DNS queries from any network interface
- You do NOT need to change this to your specific IP
- If you only want to listen on specific IPs, you can change it, but 0.0.0.0 is recommended

**Reverse DNS (PTR) lookups not working:**
- Did you create BOTH zones? You need:
  - Forward zone: `snadboy.internal`
  - Reverse zone: `1.168.192.in-addr.arpa`
- Check that PTR records exist in the reverse zone
- PTR record names should be just the last octet (e.g., "53" not "192.168.1.53")
- Domain names in PTR records need trailing dots

**Apps menu not visible:**
- Apps may need to be enabled in Settings
- Not all versions have Apps enabled by default
- Core functionality works without Apps

**Zone creation issues:**
- Ensure zone name doesn't include trailing dot when creating
- Use trailing dots in CNAME targets (e.g., `server1.snadboy.internal.`)
- Check zone type: Primary for local, Conditional Forwarder for external

### Common Issues and Solutions

**External domains not resolving:**
```bash
# [LXC CONTAINER] Test if forwarders are reachable
ping 1.1.1.1
ping 8.8.8.8

# [LXC CONTAINER] Test DNS resolution using forwarders directly
nslookup google.com 8.8.8.8

# [WEB BROWSER] Check Settings → Proxy & Forwarders
# Ensure "This Is A Forwarder" is checked
# Verify forwarder IPs are correct (1.1.1.1, 8.8.8.8)
```

**DNS not responding:**
```bash
# [LXC CONTAINER] Check service status
systemctl status dns.service

# [LXC CONTAINER] Check listening ports
netstat -tulpn | grep :53

# [LXC CONTAINER] Review logs
journalctl -u dns.service -n 50
```

**DHCP reservation not working:**
```bash
# [LXC CONTAINER] Check current IP
ip addr show eth0

# [LXC CONTAINER] Release and renew DHCP lease
dhclient -r eth0
dhclient eth0

# [LXC CONTAINER] Verify MAC address matches reservation
ip link show eth0 | grep ether

# [LXC CONTAINER] Check DHCP client logs
journalctl -u systemd-networkd -n 50
```

**IP address changed unexpectedly:**
- Verify DHCP reservation is still active on DHCP server
- Check for duplicate MAC addresses on network
- Ensure container MAC address hasn't changed after recreation
- Consider using static MAC in container config:
  ```bash
  # [PROXMOX NODE] Set static MAC address
  pct set 110 -net0 name=eth0,bridge=vmbr0,hwaddr=XX:XX:XX:XX:XX:XX
  ```

**Tailscale connectivity issues:**
```bash
# [LXC CONTAINER] Check Tailscale status
tailscale status

# [LXC CONTAINER] Verify routes
ip route show table 52

# [LXC CONTAINER] Test connectivity
tailscale ping <device-name>

# [LXC CONTAINER] Check DNS settings weren't overridden
cat /etc/resolv.conf
# Should show 1.1.1.1 or 8.8.8.8, NOT 100.100.100.100
# If it shows 100.100.100.100, you forgot --accept-dns=false

# [LXC CONTAINER] Fix if DNS was overridden
tailscale down
tailscale up --accept-routes --accept-dns=false
```

**Permission issues:**
```bash
# [LXC CONTAINER] Fix permissions
chown -R dns:dns /etc/dns
chmod 755 /etc/dns
```

**Container network issues:**
```bash
# [PROXMOX NODE] Check container network config
pct config 110 | grep net

# [PROXMOX NODE] Restart container networking
pct stop 110
pct start 110

# [PROXMOX NODE] Access container if network is broken
lxc-attach -n 110
```

## Conclusion

You now have a fully functional Technitium DNS Server that acts as the **single DNS authority** for both your local network and Tailscale network:

### What You've Achieved:

**1. Unified DNS Architecture:**
- Local network clients get `192.168.1.53` via DHCP
- Tailscale clients get `100.x.x.x` via MagicDNS configuration  
- Both point to the same Technitium server - single source of truth!

**2. Perfect Split DNS:**
- `*.snadboy.internal` → Resolved locally (private IPs like 192.168.1.x)
- `*.snadboy.com` → Forwarded to Cloudflare (returns public IPs)
- `*.tailnet.name` → Forwarded to MagicDNS (Tailscale device IPs)
- Everything else → Forwarded to Cloudflare/Google

**3. Clean Separation:**
- Internal resources use `.internal` (never exposed to internet)
- Public services use `.com` (accessible from anywhere)
- Tailscale devices use `.tailnet.name` (accessible via Tailscale)

**4. Robust Architecture:**
- Technitium container uses external DNS directly (`--accept-dns=false`)
- No circular dependencies
- DHCP reservation ensures consistent IP
- Both forward and reverse DNS zones configured

This setup provides enterprise-grade DNS management for your home lab, with clear separation between internal resources, public services, and Tailscale connectivity. The key to success is ensuring Technitium remains the authoritative DNS server by using `--accept-dns=false` when configuring Tailscale.

## Quick Reference - Technitium v13.6 Menu Locations

### Common Settings Locations
```yaml
Settings Page (Gear Icon):
  Web Service: Web interface configuration (port 5380)
  DNS Server: 
    - DNS Server Domain: ns.snadboy.internal
    - Local Endpoints: 0.0.0.0:53 (correct - means all interfaces)
    - DNSSEC validation settings
  Cache: Cache size and TTL settings
  Blocking: Enable/disable blocking features
  Proxy & Forwarders: 
    - Upstream DNS servers (8.8.8.8, 1.1.1.1, etc.)
    - Choose between forwarders or recursive resolution
  Logging: Query logging options
  TSIG: Transaction signatures for dynamic updates

Top Menu:
  Dashboard: Statistics and real-time monitoring
  Zones: Create and manage DNS zones
  Settings: All configuration options
  Apps: Optional applications (if enabled)
  About: Version and update information

Zone Management:
  Add Zone: Create Primary, Secondary, or Forwarder zones
    - Forward zone: yourdomain.internal
    - Reverse zone: 1.168.192.in-addr.arpa (for 192.168.1.x)
  Add Record: A, AAAA, CNAME, MX, TXT, PTR, etc.
  Quick Add: Simplified zone creation
```

## Quick Command Reference

### Container Management (Run on Proxmox Node)
```bash
pct start 110                    # Start container
pct stop 110                      # Stop container
pct enter 110                     # Enter container shell
pct config 110                    # View container config
vzdump 110 --storage local       # Backup container
```

### Service Management (Run Inside Container)
```bash
systemctl status dns.service      # Check Technitium status
systemctl restart dns.service     # Restart Technitium
tailscale status                  # Check Tailscale status
ip addr show eth0                 # Check IP address
```

### DNS Testing (Run from Any Client)
```bash
nslookup hostname.snadboy.internal 192.168.1.53    # Test DNS resolution
dig @192.168.1.53 hostname.snadboy.internal        # Alternative DNS test
nslookup ns.snadboy.internal 192.168.1.53          # Test DNS server's own record
```

## Additional Resources

- [Technitium DNS Server Documentation](https://technitium.com/dns/)
- [Technitium Blog - Feature Updates](https://blog.technitium.com/)
- [Technitium GitHub - Issues and Discussions](https://github.com/TechnitiumSoftware/DnsServer)
- [Tailscale Documentation](https://tailscale.com/kb/)
- [Proxmox VE Documentation](https://pve.proxmox.com/pve-docs/)

**Getting Help with v13.6:**
- Check the **About** section in Technitium for version-specific information
- The Technitium blog often has guides for new features
- GitHub Discussions has community solutions for common setups
- Most v13.x guides will work with minor menu location differences

---

*Last updated: August 2025 - Technitium v13.6*