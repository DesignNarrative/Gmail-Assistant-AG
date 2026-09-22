# InboxIQ — AWS Production Deployment & Google Verification Guide

This guide details the exact, step-by-step process for deploying **InboxIQ** as a live, multi-user **Public Commercial SaaS on AWS Lightsail** with 24/7 uptime, automated SSL, nightly backups, and passing Google OAuth App Verification.

---

## Architecture Overview

```
                          [Users Anywhere in the World]
                                       │
                                       ▼ (HTTPS 443)
                         [AWS Lightsail Static IP]
                                       │
               ┌───────────────────────┴───────────────────────┐
               │         InboxIQ Gateway (Nginx Reverse Proxy)  │
               └───────────┬───────────────────────┬───────────┘
                           │                       │
                (Static / Frontend)        (API Reverse Proxy /api/)
                           │                       │
                           ▼                       ▼
                  [React 18 Production]    [FastAPI Backend (Uvicorn)]
                                                   │
                                       ┌───────────┴───────────┐
                                       │                       │
                                       ▼                       ▼
                            [PostgreSQL 16 + pgvector]   [Redis 7 Cache]
                                       │                       │
                                       └───────────┬───────────┘
                                                   │
                                                   ▼
                                       [Celery Workers (OCR/RAG)]
```

---

## Step 1: Create Your AWS Lightsail Instance

1. Log into your [AWS Management Console](https://console.aws.amazon.com/lightsail).
2. Select your preferred region (e.g. `us-east-1` (N. Virginia), `ap-south-1` (Mumbai), or `eu-central-1` (Frankfurt)).
3. Click **Create instance**:
   - **Platform**: `Linux/Unix`
   - **Blueprint**: Choose `OS Only` $\rightarrow$ **Ubuntu 24.04 LTS**
   - **Instance Plan**: **$40 / month (8 GB RAM, 2 vCPUs, 160 GB SSD, 5 TB Transfer)**
     *(This 8 GB tier guarantees smooth multi-user PDF OCR and pgvector search without out-of-memory crashes).*
   - **Instance Name**: `inboxiq-production`
4. Click **Create instance**. It will be ready in ~60 seconds.

---

## Step 2: Attach a Static IP & Open Firewall Ports

1. In Lightsail, go to the **Networking** tab.
2. Click **Create Static IP**:
   - Attach it to `inboxiq-production`.
   - Name it `inboxiq-static-ip`.
   - Note the assigned Public IP address (e.g., `54.x.x.x`).
3. Scroll down to **IPv4 Firewall**:
   - Port 22 (SSH) $\rightarrow$ Default open
   - Click **Add rule** $\rightarrow$ **HTTP (TCP Port 80)**
   - Click **Add rule** $\rightarrow$ **HTTPS (TCP Port 443)**
   - Click **Save**.

---

## Step 3: Configure Your Domain & DNS

1. In your domain provider (Cloudflare, GoDaddy, Namecheap, or Route 53):
2. Add an **`A` Record**:
   - **Host / Name**: `app` (or `@` for root domain)
   - **Points to**: `<YOUR_AWS_STATIC_IP>`
   - **TTL**: Auto / 300s
3. Verify DNS is pointing to your server:
   ```bash
   ping app.yourdomain.com
   ```

---

## Step 4: Run the One-Click AWS Server Setup

1. Connect to your Lightsail instance via SSH (using Lightsail's browser terminal or your terminal):
   ```bash
   ssh -i your-key.pem ubuntu@<YOUR_AWS_STATIC_IP>
   ```
2. Download and run the setup script:
   ```bash
   curl -sSL https://raw.githubusercontent.com/your-repo/deploy/aws_setup.sh | bash
   # Or upload deploy/aws_setup.sh and run:
   chmod +x aws_setup.sh && ./aws_setup.sh
   ```
   *This automatically configures Docker, 4GB swap space, UFW firewall, folder permissions, and nightly backup cron.*

---

## Step 5: Transfer Application Code & Configure `.env`

1. Copy the project files to `/opt/inboxiq` on the server:
   ```bash
   git clone <YOUR_GIT_REPO_URL> /opt/inboxiq
   # Or rsync from your local machine:
   # rsync -avz --exclude 'venv' --exclude 'node_modules' . ubuntu@<IP>:/opt/inboxiq/
   ```

2. Generate production secrets:
   ```bash
   python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
   python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_hex(32))"
   python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_hex(16))"
   python3 -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_hex(16))"
   ```

3. Create `/opt/inboxiq/.env` with production values:
   ```ini
   APP_NAME="InboxIQ"
   APP_VERSION="1.0.0"
   DEBUG=false

   # Generated Secrets
   SECRET_KEY=<PASTE_GENERATED_SECRET_KEY>
   ENCRYPTION_KEY=<PASTE_GENERATED_ENCRYPTION_KEY>
   POSTGRES_PASSWORD=<PASTE_GENERATED_POSTGRES_PASSWORD>
   REDIS_PASSWORD=<PASTE_GENERATED_REDIS_PASSWORD>

   # Domain & URLs
   FRONTEND_URL="https://app.yourdomain.com"
   ALLOWED_ORIGINS="https://app.yourdomain.com"
   GOOGLE_REDIRECT_URI="https://app.yourdomain.com/api/v1/oauth/callback"

   # Google OAuth Credentials
   GOOGLE_CLIENT_ID="<YOUR_GOOGLE_CLIENT_ID>"
   GOOGLE_CLIENT_SECRET="<YOUR_GOOGLE_CLIENT_SECRET>"

   # AI Inference APIs
   GROQ_API_KEY="<YOUR_GROQ_API_KEY>"
   GROQ_MODEL="openai/gpt-oss-120b"
   GEMINI_API_KEY="<YOUR_GEMINI_API_KEY>"
   GEMINI_MODEL="gemini-3.5-flash"
   ```

---

## Step 6: Build & Launch with Docker Compose

1. Build the frontend for production:
   ```bash
   cd /opt/inboxiq/frontend
   npm install
   npm run build
   ```

2. Start all production containers:
   ```bash
   cd /opt/inboxiq
   docker compose -f docker-compose.prod.yml up -d --build
   ```

3. Verify containers are running healthy:
   ```bash
   docker ps
   curl -I http://localhost/health
   ```

---

## Step 7: Issue Free Automated SSL (HTTPS)

1. Issue the Let's Encrypt certificate:
   ```bash
   sudo certbot certonly --webroot -w /opt/inboxiq/frontend/dist -d app.yourdomain.com
   ```
2. Link the certificates into Nginx:
   ```bash
   mkdir -p /opt/inboxiq/docker/nginx/certs
   sudo cp /etc/letsencrypt/live/app.yourdomain.com/fullchain.pem /opt/inboxiq/docker/nginx/certs/cert.pem
   sudo cp /etc/letsencrypt/live/app.yourdomain.com/privkey.pem /opt/inboxiq/docker/nginx/certs/key.pem
   docker compose -f docker-compose.prod.yml restart gateway
   ```
3. Visit `https://app.yourdomain.com` in your browser. You will see the live, secure InboxIQ interface!

---

## Step 8: Google OAuth App Verification Checklist

Because InboxIQ requests `gmail.readonly` (a Restricted Scope), Google requires verification before opening to any public Gmail user. Follow these exact steps to pass verification on your first submission:

### 1. OAuth Consent Screen Configuration
In [Google Cloud Console](https://console.cloud.google.com/apis/credentials/consent):
* **User Type**: `External`
* **App Name**: `InboxIQ`
* **User support email**: Your support email (e.g. `support@yourdomain.com`)
* **App logo**: Upload InboxIQ logo
* **Application home page**: `https://app.yourdomain.com`
* **Application Privacy Policy link**: `https://app.yourdomain.com/privacy`
* **Application Terms of Service link**: `https://app.yourdomain.com/terms`
* **Authorized domains**: `yourdomain.com`

### 2. Scopes Requested
Add only the minimal required scope:
* `https://www.googleapis.com/auth/gmail.readonly`

### 3. Record the 2-Minute YouTube Demo Video
Google strictly requires a video demonstration. Upload an **Unlisted** YouTube video showing:
1. The user navigating to `https://app.yourdomain.com`.
2. Logging in and clicking **"Connect Gmail"**.
3. **CRITICAL**: The browser URL bar must be clearly visible, showing the full OAuth URL with your `client_id=...`.
4. The Google consent screen asking for read-only access.
5. Granting consent and redirecting back to the InboxIQ Dashboard.
6. A quick demonstration of searching an email and asking the AI Chat a question grounded in the synced email.

### 4. Limited Use Compliance Explanation
When Google asks for your justification, paste this exact text:
> *"InboxIQ is an executive search and retrieval assistant. We request `gmail.readonly` solely to index email correspondence and document attachments specifically labeled or selected by the user, enabling natural language semantic search and document retrieval. Customer data is processed strictly in isolated tenant containers, is never sold or transferred, and is never used to train generalized artificial intelligence models, adhering strictly to Google's Limited Use requirements."*

### 5. CASA Tier 2 Security Assessment
* After submitting, Google will invite you to complete a Cloud Application Security Assessment (CASA).
* Use the **free automated CASA scan portal** (via the AppDefense Alliance).
* It scans your domain `https://app.yourdomain.com` for OWASP top 10 vulnerabilities (SSL grade, security headers, CORS), which our hardened Nginx configuration is already configured to pass.

---

## Step 9: Disaster Recovery & Automated Maintenance

Your server is configured to run fully hands-off:
* **Nightly Database Backups**: Runs at 2:00 AM every night, saving compressed `.sql.gz` archives with a 14-day rolling retention policy.
* **Storage Pruner**: Daily unlinked file sweep with a 24-hour safety buffer.
* **Log Rotation**: Capped at 50 MB with UTF-8 support.
* **Auto-Recovery**: If AWS reboots or migrates the instance, all 5 Docker containers restart automatically in under 15 seconds.
