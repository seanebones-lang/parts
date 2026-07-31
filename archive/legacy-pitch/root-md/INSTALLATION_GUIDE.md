# Installation Guide - AI-Powered Multi-Location Dealership Parts Management System

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Prerequisites and Requirements](#prerequisites-and-requirements)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Database Configuration](#database-configuration)
5. [Application Deployment](#application-deployment)
6. [Integration Configuration](#integration-configuration)
7. [Monitoring and Observability](#monitoring-and-observability)
8. [Security Configuration](#security-configuration)
9. [Testing and Validation](#testing-and-validation)
10. [Troubleshooting Guide](#troubleshooting-guide)

## System Architecture Overview

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT INTERFACE LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│  Next.js Frontend (React 18)     │  Mobile/Web Browsers        │
│  - Dashboard Interface            │  - Staff Management UI      │
│  - Real-time Analytics           │  - Customer Portals         │
│  - Admin Controls                │                             │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTPS/WSS
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API GATEWAY LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Backend (Python 3.12+)  │  Load Balancer (Nginx)      │
│  - REST API Endpoints             │  - SSL Termination          │
│  - WebSocket Connections          │  - Rate Limiting            │
│  - Authentication & Authorization │  - Request Routing          │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI AGENT ORCHESTRATION LAYER                │
├─────────────────────────────────────────────────────────────────┤
│  LangGraph Supervisor Agent                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │Email        │ │Customer     │ │Parts        │ │Inventory    ││
│  │Classifier   │ │Service      │ │Lookup       │ │Manager      ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │Pricing &    │ │Payment      │ │Shipping     │ │Supplier     ││
│  │Invoice      │ │Agent        │ │Coordinator  │ │Sourcing     ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │Follow-up    │ │Supervisor   │ │Notification │               │
│  │Agent        │ │Agent        │ │Agent        │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICE INTEGRATIONS               │
├─────────────────────────────────────────────────────────────────┤
│  AI/LLM Services        │  Payment Processing  │  Shipping APIs  │
│  - Claude 3.5 Sonnet    │  - Stripe API        │  - UPS API      │
│  - GPT-4 (Fallback)     │  - Payment Links     │  - FedEx API    │
│  - LangSmith Monitoring │  - Webhooks          │  - USPS API     │
│                         │                      │  - DHL API      │
├─────────────────────────────────────────────────────────────────┤
│  Email Services         │  Parts Sourcing      │  Analytics      │
│  - IMAP/SMTP            │  - Rock Auto         │  - Sentry       │
│  - Gmail API            │  - AutoZone          │  - LangSmith    │
│  - Outlook API          │  - O'Reilly's        │  - Custom Logs  │
│                         │  - NAPA              │                 │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA PERSISTENCE LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL 16 (Primary Database)                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │Core Data    │ │Vector Store │ │Audit Logs   │ │Configuration││
│  │- Customers  │ │- Parts      │ │- Agent      │ │- Settings   ││
│  │- Orders     │ │- Embeddings │ │- Actions    │ │- Locations  ││
│  │- Inventory  │ │- Similarity │ │- Errors     │ │- Users      ││
│  │- Invoices   │ │- Search     │ │- Performance│ │- Permissions││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  Redis (Caching & Job Queue)                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │Session      │ │Task Queue   │ │Real-time    │               │
│  │Cache        │ │- Email      │ │Data Cache   │               │
│  │- User Auth  │ │- Orders     │ │- Inventory  │               │
│  │- API Keys   │ │- Follow-ups │ │- Analytics  │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Email Input   │    │   Web Request   │    │   Mobile App    │
│   (IMAP/SMTP)   │    │   (HTTPS)       │    │   (API Calls)   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API GATEWAY                                 │
│  - Request Authentication & Authorization                       │
│  - Rate Limiting & Load Balancing                              │
│  - Request Routing & Validation                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI AGENT ORCHESTRATION                      │
│                                                                 │
│  ┌─────────────────┐                                           │
│  │  Supervisor     │ ◄── Orchestrates all agent interactions   │
│  │  Agent          │                                           │
│  └─────────┬───────┘                                           │
│            │                                                   │
│            ▼                                                   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Email Classifier│ │ Customer Service│ │ Parts Lookup    │   │
│  │ - Route emails  │ │ - Answer queries│ │ - Search parts  │   │
│  │ - Extract info  │ │ - Provide info  │ │ - Check stock   │   │
│  └─────────┬───────┘ └─────────┬───────┘ └─────────┬───────┘   │
│            │                   │                   │           │
│            ▼                   ▼                   ▼           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Inventory Mgr   │ │ Pricing/Invoice │ │ Payment Agent   │   │
│  │ - Track stock   │ │ - Generate docs │ │ - Process pay   │   │
│  │ - Reorder alert │ │ - Calculate tax │ │ - Send reminders│   │
│  └─────────┬───────┘ └─────────┬───────┘ └─────────┬───────┘   │
│            │                   │                   │           │
│            ▼                   ▼                   ▼           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Shipping Coord  │ │ Supplier Source │ │ Follow-up Agent │   │
│  │ - Arrange ship  │ │ - Find parts    │ │ - Send reminders│   │
│  │ - Track orders  │ │ - Compare price │ │ - Check status  │   │
│  └─────────┬───────┘ └─────────┬───────┘ └─────────┬───────┘   │
└────────────┼───────────────────┼───────────────────┼───────────┘
             │                   │                   │
             ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                       │
│                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │ AI Services │ │ Payment     │ │ Shipping    │ │ Email       ││
│  │ - Claude    │ │ - Stripe    │ │ - UPS/FedEx │ │ - SMTP/IMAP ││
│  │ - GPT-4     │ │ - Webhooks  │ │ - USPS/DHL  │ │ - APIs      ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
│                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ Parts       │ │ Analytics   │ │ Monitoring  │               │
│  │ Sourcing    │ │ - Sentry    │ │ - LangSmith │               │
│  │ - Rock Auto │ │ - Custom    │ │ - Health    │               │
│  │ - AutoZone  │ │ - Metrics   │ │ - Logs      │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
             │                   │                   │
             ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA PERSISTENCE                            │
│                                                                 │
│  ┌─────────────────┐ ┌─────────────────┐                       │
│  │ PostgreSQL 16   │ │ Redis Cache     │                       │
│  │ - Core Data     │ │ - Session Data  │                       │
│  │ - Vector Store  │ │ - Task Queue    │                       │
│  │ - Audit Logs    │ │ - Real-time     │                       │
│  │ - Configuration │ │ - Cache         │                       │
│  └─────────────────┘ └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites and Requirements

### System Requirements

#### Server Infrastructure

**Minimum Requirements**:
- CPU: 8 cores (Intel Xeon or AMD EPYC)
- RAM: 32 GB
- Storage: 500 GB SSD (NVMe preferred)
- Network: 1 Gbps connection
- Operating System: Ubuntu 22.04 LTS or CentOS 8+

**Recommended Requirements**:
- CPU: 16 cores (Intel Xeon or AMD EPYC)
- RAM: 64 GB
- Storage: 1 TB SSD (NVMe)
- Network: 10 Gbps connection
- Operating System: Ubuntu 22.04 LTS

#### Software Dependencies

**System Packages**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y curl wget git python3.12 python3.12-venv python3.12-dev
sudo apt install -y postgresql-16 postgresql-client-16 postgresql-contrib-16
sudo apt install -y redis-server nginx certbot
sudo apt install -y docker.io docker-compose-plugin
sudo apt install -y build-essential libpq-dev

# CentOS/RHEL
sudo yum update
sudo yum install -y curl wget git python3.12 python3.12-devel
sudo yum install -y postgresql16-server postgresql16
sudo yum install -y redis nginx certbot
sudo yum install -y docker docker-compose
sudo yum groupinstall -y "Development Tools"
```

**Python Dependencies**:
```bash
# Python 3.12+ required
python3.12 --version  # Should show 3.12.0 or higher

# Install pip and virtual environment tools
sudo apt install -y python3.12-venv python3.12-pip
```

#### External Service Requirements

**Required API Keys and Accounts**:
- Anthropic API Key (Claude 3.5 Sonnet)
- OpenAI API Key (GPT-4 fallback)
- Stripe API Keys (Live and Test)
- Email provider credentials (SMTP/IMAP)
- Shipping carrier API keys (UPS, FedEx, USPS, DHL)
- Domain name with SSL certificate capability

### Network Requirements

#### Port Configuration

**Inbound Ports**:
- 80 (HTTP) - Redirects to HTTPS
- 443 (HTTPS) - Main application access
- 22 (SSH) - Server administration

**Outbound Ports**:
- 5432 (PostgreSQL) - Database connections
- 6379 (Redis) - Cache connections
- 25, 587, 993, 995 (Email) - SMTP/IMAP
- 443 (HTTPS) - External API calls

#### Firewall Configuration

```bash
# UFW (Ubuntu Firewall)
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 5432/tcp   # PostgreSQL (internal only)
sudo ufw deny 6379/tcp   # Redis (internal only)
```

## Infrastructure Setup

### 1. Server Provisioning

#### Cloud Provider Setup (AWS Example)

```bash
# Create EC2 instance
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.xlarge \
  --key-name your-key-pair \
  --security-group-ids sg-12345678 \
  --subnet-id subnet-12345678 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=dealership-ai-system}]'
```

#### Physical Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Set hostname
sudo hostnamectl set-hostname dealership-ai-system

# Configure timezone
sudo timedatectl set-timezone America/New_York

# Create application user
sudo useradd -m -s /bin/bash dealership
sudo usermod -aG docker dealership
sudo usermod -aG sudo dealership
```

### 2. Docker Installation and Configuration

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 3. Nginx Installation and Configuration

```bash
# Install Nginx
sudo apt install -y nginx

# Create application configuration
sudo tee /etc/nginx/sites-available/dealership-ai << EOF
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Authorization, Content-Type";
        
        if (\$request_method = 'OPTIONS') {
            return 204;
        }
    }
    
    # WebSocket support
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/dealership-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. SSL Certificate Installation

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

## Database Configuration

### 1. PostgreSQL Installation and Setup

```bash
# Install PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-client-16 postgresql-contrib-16

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE dealership_ai;
CREATE USER dealership_user WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE dealership_ai TO dealership_user;
ALTER USER dealership_user CREATEDB;
EOF

# Install pgvector extension
sudo -u postgres psql -d dealership_ai << EOF
CREATE EXTENSION IF NOT EXISTS vector;
EOF
```

### 2. Database Schema Deployment

```bash
# Navigate to project directory
cd /opt/dealership-ai

# Install Python dependencies
python3.12 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Run database migrations
cd backend
alembic upgrade head

# Seed initial data
python -c "
from app.core.database import get_db
from app.models.location import Location
from sqlalchemy.orm import Session

db = next(get_db())

# Create initial locations
locations = [
    {'name': 'Downtown Location', 'address': '123 Main St, Downtown', 'phone': '+1-555-0101'},
    {'name': 'Northside Location', 'address': '456 North Ave, Northside', 'phone': '+1-555-0102'},
    {'name': 'Southside Location', 'address': '789 South St, Southside', 'phone': '+1-555-0103'},
    {'name': 'Eastside Location', 'address': '321 East Blvd, Eastside', 'phone': '+1-555-0104'},
    {'name': 'Westside Location', 'address': '654 West Rd, Westside', 'phone': '+1-555-0105'},
    {'name': 'Central Location', 'address': '987 Central Ave, Central', 'phone': '+1-555-0106'},
    {'name': 'Airport Location', 'address': '147 Airport Dr, Airport', 'phone': '+1-555-0107'}
]

for loc_data in locations:
    location = Location(**loc_data)
    db.add(location)

db.commit()
print('Initial locations created successfully')
"
```

### 3. Redis Configuration

```bash
# Configure Redis
sudo tee /etc/redis/redis.conf << EOF
# Network
bind 127.0.0.1
port 6379
protected-mode yes

# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Security
requirepass your_redis_password_here
EOF

# Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

## Application Deployment

### 1. Application Structure Setup

```bash
# Create application directory
sudo mkdir -p /opt/dealership-ai
sudo chown dealership:dealership /opt/dealership-ai

# Clone or copy application files
cd /opt/dealership-ai
# Copy all application files here

# Set proper permissions
sudo chown -R dealership:dealership /opt/dealership-ai
chmod +x /opt/dealership-ai/start-dev.sh
```

### 2. Environment Configuration

```bash
# Create production environment file
sudo tee /opt/dealership-ai/.env << EOF
# Database Configuration
DATABASE_URL=postgresql://dealership_user:secure_password_here@localhost:5432/dealership_ai
REDIS_URL=redis://:your_redis_password_here@localhost:6379/0

# AI/LLM Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=dealership-ai-production

# Application Configuration
SECRET_KEY=your_secret_key_here_minimum_32_characters
DEBUG=False
ENVIRONMENT=production

# Email Configuration
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_USERNAME=your_email@your-domain.com
EMAIL_PASSWORD=your_email_password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False

# Payment Configuration
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Shipping Configuration
UPS_ACCESS_KEY=your_ups_access_key
UPS_USERNAME=your_ups_username
UPS_PASSWORD=your_ups_password
FEDEX_KEY=your_fedex_key
FEDEX_SECRET=your_fedex_secret
FEDEX_ACCOUNT_NUMBER=your_fedex_account
USPS_USERNAME=your_usps_username

# Monitoring Configuration
SENTRY_DSN=your_sentry_dsn_here

# Security Configuration
ALLOWED_HOSTS=your-domain.com,localhost,127.0.0.1
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
EOF

# Secure environment file
sudo chmod 600 /opt/dealership-ai/.env
sudo chown dealership:dealership /opt/dealership-ai/.env
```

### 3. Docker Compose Configuration

```yaml
# /opt/dealership-ai/docker-compose.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: dealership_ai
      POSTGRES_USER: dealership_user
      POSTGRES_PASSWORD: secure_password_here
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass your_redis_password_here
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://dealership_user:secure_password_here@postgres:5432/dealership_ai
      - REDIS_URL=redis://:your_redis_password_here@redis:6379/0
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    volumes:
      - ./backend:/app
      - /opt/dealership-ai/uploads:/app/uploads

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - NEXT_PUBLIC_API_URL=https://your-domain.com/api
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped
    volumes:
      - ./frontend:/app
      - /app/node_modules

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.celery worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://dealership_user:secure_password_here@postgres:5432/dealership_ai
      - REDIS_URL=redis://:your_redis_password_here@redis:6379/0
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    volumes:
      - ./backend:/app

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.celery beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://dealership_user:secure_password_here@postgres:5432/dealership_ai
      - REDIS_URL=redis://:your_redis_password_here@redis:6379/0
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    volumes:
      - ./backend:/app

volumes:
  postgres_data:
  redis_data:
```

### 4. Application Deployment

```bash
# Navigate to application directory
cd /opt/dealership-ai

# Build and start services
docker-compose build
docker-compose up -d

# Verify services are running
docker-compose ps

# Check logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Integration Configuration

### 1. Email Configuration

```python
# backend/app/core/email_config.py
import os
from typing import Dict, Any

EMAIL_CONFIG = {
    "host": os.getenv("EMAIL_HOST"),
    "port": int(os.getenv("EMAIL_PORT", 587)),
    "username": os.getenv("EMAIL_USERNAME"),
    "password": os.getenv("EMAIL_PASSWORD"),
    "use_tls": os.getenv("EMAIL_USE_TLS", "True").lower() == "true",
    "use_ssl": os.getenv("EMAIL_USE_SSL", "False").lower() == "true",
    "poll_interval": 30,  # seconds
    "max_emails_per_batch": 50,
    "folders": {
        "inbox": "INBOX",
        "processed": "Processed",
        "errors": "Errors"
    }
}
```

### 2. AI/LLM Configuration

```python
# backend/app/core/llm_config.py
import os
from typing import Dict, Any

LLM_CONFIG = {
    "primary_provider": "anthropic",
    "fallback_provider": "openai",
    "anthropic": {
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4000,
        "temperature": 0.1
    },
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "gpt-4-turbo-preview",
        "max_tokens": 4000,
        "temperature": 0.1
    },
    "langsmith": {
        "api_key": os.getenv("LANGSMITH_API_KEY"),
        "project": os.getenv("LANGSMITH_PROJECT", "dealership-ai"),
        "tracing": True
    }
}
```

### 3. Payment Configuration

```python
# backend/app/core/payment_config.py
import os
from typing import Dict, Any

PAYMENT_CONFIG = {
    "provider": "stripe",
    "stripe": {
        "secret_key": os.getenv("STRIPE_SECRET_KEY"),
        "publishable_key": os.getenv("STRIPE_PUBLISHABLE_KEY"),
        "webhook_secret": os.getenv("STRIPE_WEBHOOK_SECRET"),
        "currency": "usd",
        "success_url": "https://your-domain.com/payment/success",
        "cancel_url": "https://your-domain.com/payment/cancel"
    },
    "payment_methods": ["card", "bank_transfer"],
    "auto_capture": True,
    "retry_failed_payments": True,
    "max_retry_attempts": 3
}
```

### 4. Shipping Configuration

```python
# backend/app/core/shipping_config.py
import os
from typing import Dict, Any

SHIPPING_CONFIG = {
    "carriers": {
        "ups": {
            "access_key": os.getenv("UPS_ACCESS_KEY"),
            "username": os.getenv("UPS_USERNAME"),
            "password": os.getenv("UPS_PASSWORD"),
            "account_number": os.getenv("UPS_ACCOUNT_NUMBER"),
            "enabled": True
        },
        "fedex": {
            "key": os.getenv("FEDEX_KEY"),
            "secret": os.getenv("FEDEX_SECRET"),
            "account_number": os.getenv("FEDEX_ACCOUNT_NUMBER"),
            "meter_number": os.getenv("FEDEX_METER_NUMBER"),
            "enabled": True
        },
        "usps": {
            "username": os.getenv("USPS_USERNAME"),
            "password": os.getenv("USPS_PASSWORD"),
            "enabled": True
        },
        "dhl": {
            "site_id": os.getenv("DHL_SITE_ID"),
            "password": os.getenv("DHL_PASSWORD"),
            "account_number": os.getenv("DHL_ACCOUNT_NUMBER"),
            "enabled": True
        }
    },
    "default_carrier": "ups",
    "rate_shopping": True,
    "label_generation": True,
    "tracking_updates": True
}
```

## Monitoring and Observability

### 1. Sentry Configuration

```python
# backend/app/core/sentry_config.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
import os

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[
        FastApiIntegration(auto_enabling_instrumentations=False),
        SqlalchemyIntegration(),
    ],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "production"),
)
```

### 2. Health Check Endpoints

```python
# backend/app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
import redis
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check with dependencies."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    
    # Database check
    try:
        await db.execute("SELECT 1")
        health_status["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Redis check
    try:
        r = redis.Redis.from_url(os.getenv("REDIS_URL"))
        r.ping()
        health_status["checks"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    return health_status
```

### 3. Logging Configuration

```python
# backend/app/core/logging_config.py
import logging
import sys
from typing import Dict, Any

def setup_logging() -> Dict[str, Any]:
    """Configure application logging."""
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": "/var/log/dealership-ai/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "/var/log/dealership-ai/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "": {
                "level": "DEBUG",
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False
            }
        }
    }
    
    return logging_config
```

## Security Configuration

### 1. Application Security

```python
# backend/app/core/security.py
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from typing import Optional

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### 2. Database Security

```sql
-- Create read-only user for analytics
CREATE USER analytics_user WITH ENCRYPTED PASSWORD 'analytics_password';
GRANT CONNECT ON DATABASE dealership_ai TO analytics_user;
GRANT USAGE ON SCHEMA public TO analytics_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;

-- Create backup user
CREATE USER backup_user WITH ENCRYPTED PASSWORD 'backup_password';
GRANT CONNECT ON DATABASE dealership_ai TO backup_user;
GRANT USAGE ON SCHEMA public TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;

-- Enable row level security on sensitive tables
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- Create policies for location-based access
CREATE POLICY location_access ON customers
    FOR ALL TO dealership_user
    USING (location_id IN (SELECT location_id FROM user_locations WHERE user_id = current_user));

CREATE POLICY location_access ON orders
    FOR ALL TO dealership_user
    USING (location_id IN (SELECT location_id FROM user_locations WHERE user_id = current_user));
```

### 3. Network Security

```bash
# Configure fail2ban for SSH protection
sudo apt install -y fail2ban

sudo tee /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
EOF

sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

## Testing and Validation

### 1. System Health Checks

```bash
#!/bin/bash
# /opt/dealership-ai/health-check.sh

echo "=== Dealership AI System Health Check ==="
echo "Timestamp: $(date)"
echo

# Check if services are running
echo "1. Checking Docker services..."
docker-compose ps

echo
echo "2. Checking application endpoints..."

# Health check endpoint
curl -f http://localhost:8000/api/v1/health || echo "Backend health check failed"

# Database connection
curl -f http://localhost:8000/api/v1/health/detailed || echo "Detailed health check failed"

echo
echo "3. Checking external integrations..."

# Test email connection
python3 -c "
import smtplib
import os
from email.mime.text import MIMEText

try:
    server = smtplib.SMTP(os.getenv('EMAIL_HOST'), int(os.getenv('EMAIL_PORT')))
    server.starttls()
    server.login(os.getenv('EMAIL_USERNAME'), os.getenv('EMAIL_PASSWORD'))
    print('Email connection: OK')
    server.quit()
except Exception as e:
    print(f'Email connection: FAILED - {e}')
"

# Test Redis connection
python3 -c "
import redis
import os

try:
    r = redis.Redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
    print('Redis connection: OK')
except Exception as e:
    print(f'Redis connection: FAILED - {e}')
"

echo
echo "4. Checking disk space..."
df -h

echo
echo "5. Checking memory usage..."
free -h

echo
echo "=== Health Check Complete ==="
```

### 2. Load Testing

```python
# /opt/dealership-ai/load-test.py
import asyncio
import aiohttp
import time
from typing import List, Dict, Any

async def make_request(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    """Make a single HTTP request."""
    start_time = time.time()
    try:
        async with session.get(url) as response:
            end_time = time.time()
            return {
                "status": response.status,
                "response_time": end_time - start_time,
                "success": response.status == 200
            }
    except Exception as e:
        end_time = time.time()
        return {
            "status": 0,
            "response_time": end_time - start_time,
            "success": False,
            "error": str(e)
        }

async def load_test(base_url: str, concurrent_users: int, requests_per_user: int):
    """Run load test against the application."""
    print(f"Starting load test: {concurrent_users} users, {requests_per_user} requests each")
    
    connector = aiohttp.TCPConnector(limit=100)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        
        for user in range(concurrent_users):
            for request in range(requests_per_user):
                url = f"{base_url}/api/v1/health"
                task = make_request(session, url)
                tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Analyze results
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        response_times = [r["response_time"] for r in successful_requests]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        total_time = end_time - start_time
        requests_per_second = len(results) / total_time
        
        print(f"\n=== Load Test Results ===")
        print(f"Total requests: {len(results)}")
        print(f"Successful requests: {len(successful_requests)}")
        print(f"Failed requests: {len(failed_requests)}")
        print(f"Success rate: {len(successful_requests)/len(results)*100:.2f}%")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Requests per second: {requests_per_second:.2f}")
        print(f"Average response time: {avg_response_time:.3f} seconds")
        print(f"Min response time: {min_response_time:.3f} seconds")
        print(f"Max response time: {max_response_time:.3f} seconds")

if __name__ == "__main__":
    base_url = "http://localhost:8000"
    asyncio.run(load_test(base_url, 50, 20))  # 50 users, 20 requests each
```

### 3. Integration Testing

```python
# /opt/dealership-ai/integration-test.py
import requests
import json
import time
from typing import Dict, Any

def test_email_processing():
    """Test email processing workflow."""
    print("Testing email processing...")
    
    # Simulate email data
    email_data = {
        "from": "customer@example.com",
        "subject": "Need brake pads for 2019 Honda Civic",
        "body": "Hi, I need front brake pads for my 2019 Honda Civic. Can you provide a quote?",
        "location_id": 1
    }
    
    response = requests.post(
        "http://localhost:8000/api/v1/emails/process",
        json=email_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        print("✓ Email processing test passed")
        return response.json()
    else:
        print(f"✗ Email processing test failed: {response.status_code}")
        return None

def test_parts_lookup():
    """Test parts lookup functionality."""
    print("Testing parts lookup...")
    
    search_data = {
        "query": "brake pads Honda Civic 2019",
        "location_id": 1
    }
    
    response = requests.post(
        "http://localhost:8000/api/v1/parts/search",
        json=search_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        print("✓ Parts lookup test passed")
        return response.json()
    else:
        print(f"✗ Parts lookup test failed: {response.status_code}")
        return None

def test_order_creation():
    """Test order creation workflow."""
    print("Testing order creation...")
    
    order_data = {
        "customer_id": 1,
        "location_id": 1,
        "items": [
            {
                "part_id": 1,
                "quantity": 2,
                "unit_price": 45.99
            }
        ]
    }
    
    response = requests.post(
        "http://localhost:8000/api/v1/orders",
        json=order_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 201:
        print("✓ Order creation test passed")
        return response.json()
    else:
        print(f"✗ Order creation test failed: {response.status_code}")
        return None

def run_integration_tests():
    """Run all integration tests."""
    print("=== Integration Tests ===")
    
    tests = [
        test_email_processing,
        test_parts_lookup,
        test_order_creation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(None)
    
    passed_tests = len([r for r in results if r is not None])
    total_tests = len(tests)
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed_tests}/{total_tests}")
    print(f"Success rate: {passed_tests/total_tests*100:.1f}%")

if __name__ == "__main__":
    run_integration_tests()
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Database Connection Issues

**Problem**: Cannot connect to PostgreSQL database
```
Error: psycopg2.OperationalError: could not connect to server
```

**Solutions**:
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# Verify database exists and user has permissions
sudo -u postgres psql -c "\l"
sudo -u postgres psql -c "\du"

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 2. Redis Connection Issues

**Problem**: Cannot connect to Redis
```
Error: redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solutions**:
```bash
# Check if Redis is running
sudo systemctl status redis-server

# Check Redis logs
sudo tail -f /var/log/redis/redis-server.log

# Test Redis connection
redis-cli ping

# Restart Redis
sudo systemctl restart redis-server
```

#### 3. AI Agent Performance Issues

**Problem**: Slow response times from AI agents
```
Warning: Agent response time exceeds 30 seconds
```

**Solutions**:
```bash
# Check API key validity
curl -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
     https://api.anthropic.com/v1/messages

# Monitor LangSmith for agent performance
# Check system resources
htop
iostat 1

# Review agent logs
docker-compose logs celery-worker | grep -i error
```

#### 4. Email Processing Issues

**Problem**: Emails not being processed
```
Error: IMAP connection failed
```

**Solutions**:
```bash
# Test email connection manually
python3 -c "
import imaplib
import os
mail = imaplib.IMAP4_SSL(os.getenv('EMAIL_HOST'))
mail.login(os.getenv('EMAIL_USERNAME'), os.getenv('EMAIL_PASSWORD'))
print('Email connection successful')
mail.logout()
"

# Check email service logs
docker-compose logs backend | grep -i email

# Verify email credentials and settings
echo $EMAIL_HOST
echo $EMAIL_USERNAME
```

#### 5. Docker Container Issues

**Problem**: Containers not starting or crashing
```
Error: Container exited with code 1
```

**Solutions**:
```bash
# Check container logs
docker-compose logs [service_name]

# Check container status
docker-compose ps

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check system resources
docker system df
docker system prune  # Clean up unused resources
```

### Performance Optimization

#### 1. Database Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM parts_catalog WHERE vector @@ 'brake pads';

-- Create indexes for frequently queried columns
CREATE INDEX CONCURRENTLY idx_parts_catalog_vector ON parts_catalog USING ivfflat (vector vector_cosine_ops);

-- Update table statistics
ANALYZE parts_catalog;

-- Check database size and performance
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;
```

#### 2. Redis Optimization

```bash
# Monitor Redis performance
redis-cli --latency-history -i 1

# Check memory usage
redis-cli info memory

# Optimize Redis configuration
sudo nano /etc/redis/redis.conf
# Set maxmemory-policy to allkeys-lru
# Increase maxmemory if needed
```

#### 3. Application Optimization

```python
# Monitor application performance
# Add to backend/app/main.py

import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### Backup and Recovery

#### 1. Database Backup

```bash
#!/bin/bash
# /opt/dealership-ai/backup-db.sh

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="dealership_ai"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -h localhost -U dealership_user -d $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Database backup completed: db_backup_$DATE.sql.gz"
```

#### 2. Application Backup

```bash
#!/bin/bash
# /opt/dealership-ai/backup-app.sh

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup application files
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='.git' \
    /opt/dealership-ai

# Keep only last 7 days of backups
find $BACKUP_DIR -name "app_backup_*.tar.gz" -mtime +7 -delete

echo "Application backup completed: app_backup_$DATE.tar.gz"
```

### Monitoring Scripts

#### 1. System Monitoring

```bash
#!/bin/bash
# /opt/dealership-ai/monitor.sh

echo "=== System Monitoring Report ==="
echo "Timestamp: $(date)"
echo

# Check system resources
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)"

echo
echo "Memory Usage:"
free -h

echo
echo "Disk Usage:"
df -h

echo
echo "Docker Services:"
docker-compose ps

echo
echo "Application Health:"
curl -s http://localhost:8000/api/v1/health | jq .

echo
echo "Database Connections:"
sudo -u postgres psql -d dealership_ai -c "SELECT count(*) as active_connections FROM pg_stat_activity;"

echo
echo "Redis Memory Usage:"
redis-cli info memory | grep used_memory_human

echo
echo "=== Monitoring Complete ==="
```

This comprehensive installation guide provides detailed instructions for deploying the AI-powered dealership parts management system, including architecture diagrams, step-by-step installation procedures, configuration examples, monitoring setup, and troubleshooting guidance.
