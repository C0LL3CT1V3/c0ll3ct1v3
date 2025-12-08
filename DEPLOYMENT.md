# Deployment Guide: Exposing Your Domain on the Internet

This guide will walk you through exposing your Namecheap domain and serving your application on the internet.

## Prerequisites

1. **A domain registered on Namecheap** (you have this ✓)
2. **A VPS/Server with a public IP address** (DigitalOcean, AWS EC2, Linode, Vultr, etc.)
3. **SSH access to your server**
4. **Docker and Docker Compose installed on your server**

## Step 1: Get a VPS/Server

Choose a cloud provider and create a server:

### AWS EC2 (Free Tier Available! 🎉)

**AWS Free Tier (12 Months):**
- ✅ **750 hours/month** of EC2 t2.micro, t3.micro, t4g.micro, t3.small, t4g.small, c7i-flex.large, or m7i-flex.large instances
- ✅ **30 GB** of EBS General Purpose (SSD) storage
- ✅ **$100 in credits** for new accounts (valid for 6 months)
- ✅ Enough to run one small instance 24/7 for free!

**Recommended Instance for This Project:**
- **t3.micro** or **t4g.micro** (1 vCPU, 1 GB RAM) - Perfect for small applications
- **Ubuntu 22.04 LTS** or **Ubuntu 20.04 LTS**

**Cost After Free Tier:**
- ~$7-10/month for t3.micro (depending on region)

See [AWS Setup Guide](#aws-ec2-setup-guide) below for detailed instructions.

### Other Providers

- **DigitalOcean**: https://www.digitalocean.com/ ($6/month for basic droplet)
- **Linode**: https://www.linode.com/ ($5/month for Nanode)
- **Vultr**: https://www.vultr.com/ ($6/month for regular instance)

**Minimum Requirements:**
- 1-2 GB RAM
- 1 CPU core
- 20 GB storage
- Ubuntu 20.04 or 22.04 LTS

**Note your server's public IP address** - you'll need it for DNS configuration.

---

## Alternative: Hosting from Your Local Machine

⚠️ **Warning**: Hosting from your local machine is **not recommended** for production due to:
- Dynamic IP addresses (changes when you restart your router)
- Security risks (exposing your home network)
- Reliability issues (downtime when your machine/network is down)
- ISP restrictions (many block incoming connections on ports 80/443)

### If You Still Want to Host Locally:

#### 1. Find Your Public IP Address

Your public IP is what you need to put in the DNS record. Find it by:

```bash
# On Linux/Mac
curl ifconfig.me
# or
curl ipinfo.io/ip

# On Windows (PowerShell)
(Invoke-WebRequest -Uri "https://ifconfig.me").Content
```

Or visit: https://whatismyipaddress.com/

**This is the IP address you put in your Namecheap DNS A record.**

#### 2. Configure Router Port Forwarding

You need to forward ports 80 and 443 from your router to your local machine:

1. Find your router's admin panel (usually `192.168.1.1` or `192.168.0.1`)
2. Log in and find "Port Forwarding" or "Virtual Server" settings
3. Forward:
   - **Port 80** → Your local machine's IP (e.g., `192.168.1.100:80`)
   - **Port 443** → Your local machine's IP (e.g., `192.168.1.100:443`)

To find your local IP:
```bash
# Linux
ip addr show | grep "inet " | grep -v 127.0.0.1

# Mac
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
```

#### 3. Configure Firewall

Allow incoming connections on ports 80 and 443:

```bash
# Linux (UFW)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Linux (iptables)
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

#### 4. Dynamic DNS (Recommended for Local Hosting)

Since your public IP changes, use a Dynamic DNS service:

- **No-IP**: https://www.noip.com/ (Free)
- **DuckDNS**: https://www.duckdns.org/ (Free)
- **Namecheap Dynamic DNS**: If your domain is on Namecheap

Then point your domain to the dynamic DNS hostname instead of a static IP.

#### 5. Better Alternatives for Local Development

Instead of exposing your local machine, consider:

- **Cloudflare Tunnel** (Free): https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
  - No port forwarding needed
  - Free SSL certificates
  - Works behind NAT/firewall

- **ngrok** (Free tier available): https://ngrok.com/
  - Quick tunnel for testing
  - Free SSL
  - Not ideal for production

- **Tailscale** (Free for personal use): https://tailscale.com/
  - VPN solution
  - Secure access without port forwarding

**For production, a VPS is strongly recommended.**

## Step 2: Configure DNS on Namecheap

1. Log in to your Namecheap account
2. Go to **Domain List** → Select your domain → **Manage**
3. Go to the **Advanced DNS** tab
4. Add/Edit the following DNS records:

### For Root Domain (example.com):
- **Type**: A Record
- **Host**: @
- **Value**: `YOUR_SERVER_IP_ADDRESS`
- **TTL**: Automatic (or 300)

### For WWW Subdomain (www.example.com):
- **Type**: A Record
- **Host**: www
- **Value**: `YOUR_SERVER_IP_ADDRESS`
- **TTL**: Automatic (or 300)

**Important:** DNS propagation can take 24-48 hours, but usually happens within a few hours. You can check propagation status at https://www.whatsmydns.net/

## Step 3: Set Up Your Server

### 3.1 Initial Server Setup

SSH into your server:
```bash
ssh root@YOUR_SERVER_IP
```

Update the system:
```bash
apt update && apt upgrade -y
```

### 3.2 Install Docker and Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

### 3.3 Create a Non-Root User (Recommended)

```bash
# Create user
adduser deploy
usermod -aG docker deploy
usermod -aG sudo deploy

# Switch to new user
su - deploy
```

## Step 4: Deploy Your Application

### 4.1 Clone Your Repository

```bash
cd /opt
sudo git clone YOUR_REPOSITORY_URL c0ll3ct1v3
sudo chown -R deploy:deploy /opt/c0ll3ct1v3
cd /opt/c0ll3ct1v3
```

### 4.2 Set Up SSL Certificates

Run the SSL setup script (this will use Let's Encrypt):

```bash
cd /opt/c0ll3ct1v3
chmod +x infrastructure/scripts/setup-ssl.sh
./infrastructure/scripts/setup-ssl.sh YOUR_DOMAIN.com
```

This script will:
- Install Certbot
- Obtain SSL certificates from Let's Encrypt
- Set up auto-renewal
- Copy certificates to the correct location

### 4.3 Configure Environment Variables

Create a `.env` file for production:

```bash
cp .env.example .env  # If you have one, or create new
nano .env
```

Add your production settings:
```env
DATABASE_URL=postgresql://postgres:STRONG_PASSWORD_HERE@db:5432/collective
POSTGRES_PASSWORD=STRONG_PASSWORD_HERE
DOMAIN=yourdomain.com
```

### 4.4 Update Nginx Configuration

The nginx config will be automatically updated by the SSL setup script. If you need to manually update it, edit `infrastructure/nginx.prod.conf` and replace `server_name _;` with `server_name yourdomain.com www.yourdomain.com;`

### 4.5 Build and Start Services

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### 4.6 Verify Deployment

Check if services are running:
```bash
docker compose -f docker-compose.prod.yml ps
```

Check logs:
```bash
docker compose -f docker-compose.prod.yml logs -f
```

Visit your domain in a browser: `https://yourdomain.com`

## Step 5: Firewall Configuration

Make sure ports 80 and 443 are open:

```bash
# If using UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable

# If using iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
```

## Step 6: Set Up Auto-Deployment (Optional)

You can set up automatic deployments using the existing `deploy.sh` script:

```bash
# Make it executable
chmod +x infrastructure/scripts/deploy.sh

# Add to crontab for scheduled deployments, or use with CI/CD
```

## Troubleshooting

### DNS Not Resolving
- Wait 24-48 hours for full propagation
- Check DNS records are correct in Namecheap
- Verify with: `dig yourdomain.com` or `nslookup yourdomain.com`

### SSL Certificate Issues
- Ensure ports 80 and 443 are open
- Verify DNS is pointing to your server
- Check Certbot logs: `sudo certbot certificates`

### Application Not Loading
- Check Docker containers: `docker compose -f docker-compose.prod.yml ps`
- Check logs: `docker compose -f docker-compose.prod.yml logs`
- Verify nginx config: `docker exec -it <frontend-container> nginx -t`

### Database Connection Issues
- Verify database container is running
- Check DATABASE_URL in .env file
- Check database logs: `docker compose -f docker-compose.prod.yml logs db`

## Security Checklist

- [ ] Use strong passwords for database and services
- [ ] Keep server updated: `apt update && apt upgrade`
- [ ] Configure firewall (UFW or iptables)
- [ ] Set up SSH key authentication (disable password auth)
- [ ] Enable automatic security updates
- [ ] Regular backups (use `infrastructure/scripts/backup.sh`)
- [ ] Monitor logs regularly
- [ ] Use environment variables for secrets (never commit to git)

## Maintenance

### Update Application
```bash
cd /opt/c0ll3ct1v3
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### Renew SSL Certificates
SSL certificates auto-renew via Certbot. To manually renew:
```bash
sudo certbot renew
```

### Backup Database
```bash
./infrastructure/scripts/backup.sh
```

## AWS EC2 Setup Guide

### Creating Your AWS Account

1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Follow the signup process (requires credit card for verification, but won't be charged if you stay within free tier)
4. You'll receive **$100 in credits** and access to the **12-month free tier**

### Launching an EC2 Instance

1. **Log in to AWS Console**: https://console.aws.amazon.com/
2. **Navigate to EC2**: Search for "EC2" in the services menu
3. **Launch Instance**:
   - Click "Launch Instance"
   - **Name**: Give it a name (e.g., "c0ll3ct1v3-production")
   - **AMI**: Choose "Ubuntu Server 22.04 LTS" (free tier eligible)
   - **Instance Type**: Select **t3.micro** or **t4g.micro** (free tier eligible)
   - **Key Pair**: Create a new key pair or use existing
     - Name: `c0ll3ct1v3-key`
     - Key pair type: RSA
     - Private key file format: `.pem` (for Linux/Mac) or `.ppk` (for Windows)
     - **Download the key file** - you'll need it to SSH into your instance!
   - **Network Settings**: 
     - Click "Edit"
     - **Security Group**: Create new security group
     - **Allow SSH**: Port 22, Source: My IP (or 0.0.0.0/0 if you need access from anywhere)
     - **Allow HTTP**: Port 80, Source: 0.0.0.0/0
     - **Allow HTTPS**: Port 443, Source: 0.0.0.0/0
   - **Configure Storage**: 20 GB gp3 (free tier includes 30 GB)
   - **Launch Instance**

4. **Get Your Public IP**:
   - Wait for instance to start (Status: Running)
   - Note the **Public IPv4 address** - this is what you'll use in DNS!

### Connecting to Your EC2 Instance

**On Linux/Mac:**
```bash
# Set correct permissions on key file
chmod 400 ~/Downloads/c0ll3ct1v3-key.pem

# Connect (replace with your instance's public IP)
ssh -i ~/Downloads/c0ll3ct1v3-key.pem ubuntu@YOUR_PUBLIC_IP
```

**On Windows (using PowerShell or WSL):**
```bash
# Same as Linux/Mac if using WSL
# Or use PuTTY with the .ppk file
```

### Setting Up Elastic IP (Recommended)

EC2 instances get a new public IP when restarted. To get a static IP:

1. In EC2 Console, go to **Elastic IPs** (left sidebar)
2. Click **Allocate Elastic IP address**
3. Click **Allocate**
4. Select the Elastic IP, click **Actions** → **Associate Elastic IP address**
5. Select your instance and click **Associate**

**Use this Elastic IP in your DNS records** - it won't change!

### Important AWS Considerations

**Free Tier Limits:**
- 750 hours/month = enough for one instance running 24/7
- If you run 2 instances, you'll use 750 hours in ~15 days
- Monitor usage in AWS Billing Console

**Cost Monitoring:**
- Set up billing alerts: AWS Console → Billing → Preferences → Receive Billing Alerts
- Enable Cost Explorer to track spending
- Free tier applies for 12 months from account creation

**Security Best Practices:**
- Use Security Groups (firewall rules) - only open ports you need
- Consider using AWS Systems Manager Session Manager instead of SSH
- Enable CloudTrail for audit logging
- Regularly update your instance: `sudo apt update && sudo apt upgrade`

### AWS-Specific Firewall Configuration

AWS uses **Security Groups** instead of traditional firewalls. You should have already configured this during instance creation, but to modify:

1. EC2 Console → **Security Groups** (left sidebar)
2. Select your instance's security group
3. **Inbound Rules** → **Edit inbound rules**
4. Ensure you have:
   - SSH (22) from your IP
   - HTTP (80) from anywhere (0.0.0.0/0)
   - HTTPS (443) from anywhere (0.0.0.0/0)

### Stopping/Starting Your Instance

- **Stop**: Stops the instance (you don't pay for compute, but storage still costs)
- **Terminate**: Deletes the instance permanently (data is lost!)
- **Reboot**: Restarts without changing IP (if using Elastic IP)

**Note**: If you stop an instance without an Elastic IP, you'll get a new public IP when you start it again.

## Support

For issues or questions:
1. Check application logs: `docker compose -f docker-compose.prod.yml logs`
2. Check system logs: `journalctl -u docker`
3. Verify DNS: https://www.whatsmydns.net/
4. AWS Support: https://console.aws.amazon.com/support/ (Free tier includes basic support)

