# Quick AWS EC2 Setup Guide

## AWS Free Tier Summary

✅ **What's Free (12 months):**
- **750 hours/month** of EC2 compute (enough for 1 instance 24/7)
- **30 GB** of storage
- **$100 in credits** (valid 6 months)
- Perfect for hosting your application!

✅ **What You'll Pay After Free Tier:**
- ~$7-10/month for t3.micro instance
- ~$2/month for 20 GB storage
- **Total: ~$9-12/month** (very affordable!)

## Step-by-Step Setup

### 1. Create AWS Account
- Go to https://aws.amazon.com/
- Click "Create an AWS Account"
- Complete signup (credit card required for verification, but won't be charged if you stay within free tier)

### 2. Launch EC2 Instance

1. **Go to EC2 Console**: https://console.aws.amazon.com/ec2/
2. **Click "Launch Instance"**
3. **Configure Instance**:
   ```
   Name: c0ll3ct1v3-production
   AMI: Ubuntu Server 22.04 LTS (Free tier eligible)
   Instance Type: t3.micro (Free tier eligible)
   ```
4. **Create Key Pair**:
   - Click "Create new key pair"
   - Name: `c0ll3ct1v3-key`
   - Key pair type: RSA
   - Private key file format: `.pem`
   - **Download and save the .pem file securely!**
5. **Network Settings**:
   - Click "Edit"
   - Security group name: `c0ll3ct1v3-sg`
   - **Add rules**:
     - SSH (22) - Source: My IP
     - HTTP (80) - Source: 0.0.0.0/0
     - HTTPS (443) - Source: 0.0.0.0/0
6. **Storage**: 20 GB gp3 (free tier includes 30 GB)
7. **Launch Instance**

### 3. Get Your Public IP

1. Wait for instance status to be "Running" (green checkmark)
2. Note the **Public IPv4 address** (e.g., `54.123.45.67`)
3. **This is what you'll put in your Namecheap DNS A record!**

### 4. Set Up Elastic IP (Recommended)

To prevent IP changes when you restart the instance:

1. EC2 Console → **Elastic IPs** (left sidebar)
2. **Allocate Elastic IP address** → **Allocate**
3. Select the Elastic IP → **Actions** → **Associate Elastic IP address**
4. Select your instance → **Associate**
5. **Use this Elastic IP in DNS** (it's static!)

### 5. Connect to Your Instance

**Linux/Mac:**
```bash
# Set permissions
chmod 400 ~/Downloads/c0ll3ct1v3-key.pem

# Connect (replace with your IP)
ssh -i ~/Downloads/c0ll3ct1v3-key.pem ubuntu@YOUR_PUBLIC_IP
```

**Windows (WSL or Git Bash):**
```bash
# Same as Linux/Mac
chmod 400 ~/Downloads/c0ll3ct1v3-key.pem
ssh -i ~/Downloads/c0ll3ct1v3-key.pem ubuntu@YOUR_PUBLIC_IP
```

**Windows (PuTTY):**
- Convert .pem to .ppk using PuTTYgen
- Use PuTTY with the .ppk file

### 6. Set Up Your Server

Once connected, follow the main deployment guide starting from **Step 3: Set Up Your Server**.

Quick start:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Add your user to docker group (if not using root)
sudo usermod -aG docker $USER
# Log out and back in for this to take effect
```

### 7. Configure DNS

In Namecheap:
- **Type**: A Record
- **Host**: @
- **Value**: Your Elastic IP (or Public IP if you didn't set up Elastic IP)
- **TTL**: Automatic

## Cost Monitoring

**Set Up Billing Alerts:**
1. AWS Console → **Billing** → **Preferences**
2. Enable "Receive Billing Alerts"
3. Go to **CloudWatch** → **Alarms** → **Billing**
4. Create alarm for estimated charges (e.g., alert at $5)

**Monitor Usage:**
- AWS Console → **Billing Dashboard**
- Check "Free Tier" tab to see remaining free tier usage

## Important Notes

⚠️ **Free Tier Limits:**
- 750 hours/month = 1 instance running 24/7
- If you launch 2 instances, you'll use up free hours faster
- Storage: 30 GB free, then ~$0.10/GB/month

⚠️ **What Costs Money:**
- Running more than 1 instance simultaneously
- Storage over 30 GB
- Data transfer out (first 1 GB/month free, then ~$0.09/GB)
- Elastic IP (free if attached to running instance, $0.005/hour if unattached)

✅ **Best Practices:**
- Use Elastic IP so your IP doesn't change
- Set up billing alerts
- Stop instance when not in use (saves compute costs, storage still costs)
- Use the same region for all resources (reduces data transfer costs)

## Troubleshooting

**Can't connect via SSH:**
- Check Security Group allows SSH from your IP
- Verify key file permissions: `chmod 400 key.pem`
- Make sure you're using `ubuntu` user (not `root` or `ec2-user`)

**Instance not accessible:**
- Check Security Groups allow HTTP (80) and HTTPS (443)
- Verify instance is running
- Check instance status checks are passing

**Unexpected charges:**
- Check Billing Dashboard
- Review CloudWatch billing alarms
- Verify you're using free tier eligible instance types

## Next Steps

After your instance is set up:
1. Follow the main [DEPLOYMENT.md](./DEPLOYMENT.md) guide
2. Set up SSL certificates
3. Deploy your application
4. Configure your domain

## Resources

- **AWS Free Tier Details**: https://aws.amazon.com/free/
- **EC2 Pricing**: https://aws.amazon.com/ec2/pricing/
- **AWS Documentation**: https://docs.aws.amazon.com/ec2/
- **AWS Support**: Free tier includes basic support via forums


