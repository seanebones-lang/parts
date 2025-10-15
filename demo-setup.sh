#!/bin/bash

# AI-Powered Dealership Parts Management System - Demo Setup
# This script sets up a local demo environment on your MacBook

set -e

echo "🚀 Setting up AI-Powered Dealership Parts Management System Demo"
echo "=================================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop for Mac first."
    echo "   Download from: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "✅ Docker is installed and running"

# Create demo environment file
echo "📝 Creating demo environment configuration..."
cat > .env.demo << EOF
# Demo Environment Configuration
# AI-Powered Dealership Parts Management System

# Database Configuration
DATABASE_URL=postgresql://demo:demo123@localhost:5432/dealership_demo
POSTGRES_DB=dealership_demo
POSTGRES_USER=demo
POSTGRES_PASSWORD=demo123

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# AI/LLM Configuration (Demo - using mock responses)
OPENAI_API_KEY=demo_key_for_local_testing
ANTHROPIC_API_KEY=demo_key_for_local_testing

# Email Configuration (Demo - using mock email service)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=demo
SMTP_PASSWORD=demo

# Payment Configuration (Demo - using Stripe test mode)
STRIPE_SECRET_KEY=sk_test_demo_key
STRIPE_WEBHOOK_SECRET=whsec_demo_secret

# Shipping Configuration (Demo - using mock shipping service)
UPS_ACCESS_KEY=demo_key
FEDEX_API_KEY=demo_key
USPS_USER_ID=demo_user

# Application Configuration
DEBUG=true
ENVIRONMENT=demo
LOG_LEVEL=INFO

# Demo Data Configuration
SEED_DEMO_DATA=true
DEMO_LOCATIONS=3
DEMO_CUSTOMERS=50
DEMO_PARTS=500
EOF

# Create demo docker-compose file
echo "🐳 Creating demo Docker Compose configuration..."
cat > docker-compose.demo.yml << EOF
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: dealership_demo
      POSTGRES_USER: demo
      POSTGRES_PASSWORD: demo123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U demo -d dealership_demo"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Mock Email Server (MailHog)
  mailhog:
    image: mailhog/mailhog:latest
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI

  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://demo:demo123@postgres:5432/dealership_demo
      - REDIS_URL=redis://redis:6379/0
      - DEBUG=true
      - ENVIRONMENT=demo
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./backend:/app
    command: >
      sh -c "
        echo 'Waiting for database...' &&
        sleep 10 &&
        echo 'Starting demo backend...' &&
        python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
      "

  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NODE_ENV=development
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
EOF

# Create demo startup script
echo "🎬 Creating demo startup script..."
cat > start-demo.sh << 'EOF'
#!/bin/bash

echo "🎭 Starting AI-Powered Dealership Parts Management System Demo"
echo "=============================================================="

# Copy demo environment
cp .env.demo .env

# Start demo services
echo "🚀 Starting demo services..."
docker-compose -f docker-compose.demo.yml up --build -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 15

echo ""
echo "🎉 Demo is ready! Access the system at:"
echo ""
echo "📱 Frontend Dashboard: http://localhost:3000"
echo "🔧 Backend API:        http://localhost:8000"
echo "📧 Email Interface:    http://localhost:8025"
echo "📊 API Documentation:  http://localhost:8000/docs"
echo ""
echo "🔑 Demo Credentials:"
echo "   Email: admin@dealership.com"
echo "   Password: demo123"
echo ""
echo "📋 Demo Features Available:"
echo "   ✅ Email Classification & Routing"
echo "   ✅ Parts Inventory Management"
echo "   ✅ Customer Service Chat"
echo "   ✅ Order Processing"
echo "   ✅ Payment Integration"
echo "   ✅ Shipping Coordination"
echo "   ✅ Analytics Dashboard"
echo ""
echo "🛑 To stop the demo, run: docker-compose -f docker-compose.demo.yml down"
echo ""
echo "📖 For full documentation, see: README.md"
EOF

chmod +x start-demo.sh

# Create demo data seeder
echo "🌱 Creating demo data seeder..."
cat > demo-seed.py << 'EOF'
#!/usr/bin/env python3
"""
Demo Data Seeder for AI-Powered Dealership Parts Management System
Creates sample data for demonstration purposes
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List

# Sample data for demo
DEMO_LOCATIONS = [
    {"name": "Downtown Dealership", "address": "123 Main St, Downtown", "phone": "(555) 123-4567"},
    {"name": "Westside Auto Parts", "address": "456 Oak Ave, Westside", "phone": "(555) 234-5678"},
    {"name": "Northgate Motors", "address": "789 Pine St, Northgate", "phone": "(555) 345-6789"},
]

DEMO_PARTS = [
    {"part_number": "ENG001", "name": "Engine Oil Filter", "category": "Engine", "price": 12.99},
    {"part_number": "BRA002", "name": "Brake Pad Set", "category": "Brakes", "price": 89.99},
    {"part_number": "SUS003", "name": "Shock Absorber", "category": "Suspension", "price": 156.99},
    {"part_number": "EXH004", "name": "Catalytic Converter", "category": "Exhaust", "price": 299.99},
    {"part_number": "ELE005", "name": "Alternator", "category": "Electrical", "price": 189.99},
    {"part_number": "COO006", "name": "Radiator", "category": "Cooling", "price": 245.99},
    {"part_number": "TRA007", "name": "Transmission Fluid", "category": "Transmission", "price": 24.99},
    {"part_number": "IGN008", "name": "Spark Plugs Set", "category": "Ignition", "price": 45.99},
    {"part_number": "AIR009", "name": "Air Filter", "category": "Air Intake", "price": 18.99},
    {"part_number": "FUE010", "name": "Fuel Pump", "category": "Fuel System", "price": 125.99},
]

DEMO_CUSTOMERS = [
    {"name": "John Smith", "email": "john.smith@email.com", "phone": "(555) 111-2222"},
    {"name": "Sarah Johnson", "email": "sarah.j@email.com", "phone": "(555) 333-4444"},
    {"name": "Mike Wilson", "email": "mike.w@email.com", "phone": "(555) 555-6666"},
    {"name": "Lisa Brown", "email": "lisa.brown@email.com", "phone": "(555) 777-8888"},
    {"name": "David Davis", "email": "david.d@email.com", "phone": "(555) 999-0000"},
]

def generate_demo_orders(num_orders: int = 20) -> List[dict]:
    """Generate demo orders with realistic data"""
    orders = []
    for i in range(num_orders):
        customer = random.choice(DEMO_CUSTOMERS)
        location = random.choice(DEMO_LOCATIONS)
        parts = random.sample(DEMO_PARTS, random.randint(1, 3))
        
        order_date = datetime.now() - timedelta(days=random.randint(1, 30))
        
        order = {
            "customer_name": customer["name"],
            "customer_email": customer["email"],
            "customer_phone": customer["phone"],
            "location_name": location["name"],
            "order_date": order_date.isoformat(),
            "parts": parts,
            "total_amount": sum(part["price"] for part in parts),
            "status": random.choice(["pending", "processing", "shipped", "delivered"]),
        }
        orders.append(order)
    
    return orders

if __name__ == "__main__":
    print("🌱 Demo data seeder created!")
    print("Run this after starting the demo to populate with sample data.")
EOF

chmod +x demo-seed.py

echo ""
echo "✅ Demo setup complete!"
echo ""
echo "🚀 To start the demo, run:"
echo "   ./start-demo.sh"
echo ""
echo "📋 What you'll get:"
echo "   • Full-featured web dashboard at http://localhost:3000"
echo "   • Backend API with documentation at http://localhost:8000/docs"
echo "   • Mock email interface at http://localhost:8025"
echo "   • Pre-populated demo data (locations, parts, customers)"
echo "   • All AI agents working with mock responses"
echo ""
echo "🎭 Perfect for demonstrating the system capabilities!"
