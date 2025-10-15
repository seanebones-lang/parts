#!/bin/bash
# Parts RAG Demo - Quick Start Script
# One-click demo setup for presentation

echo "Parts RAG Demo - Quick Start"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "data_loader.py" ]; then
    echo "Error: Run this script from the Parrts-Dist-RAG root directory"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $python_version"

# Install dependencies if needed
echo "Checking dependencies..."

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

# Build the vector store with realistic data
echo "Building vector store with dealership data..."
python3 data_loader.py

# Test Stripe mock engine
echo "Testing Stripe mock engine..."
python3 stripe_mock.py

# Generate initial analytics
echo "Generating initial analytics..."
python3 analytics.py

# Generate sample CSV export
echo "Generating sample CSV export..."
python3 -c "
from analytics import export_metrics
import datetime
csv_data = export_metrics('csv')
with open('sample_analytics_report.csv', 'w') as f:
    f.write(csv_data)
print('Sample CSV exported: sample_analytics_report.csv')
"

# Check if the demo script exists
if [ ! -f "backend/parts_rag_demo.py" ]; then
    echo "Error: parts_rag_demo.py not found in backend directory"
    exit 1
fi

echo "Dependencies installed and vector store built!"
echo ""
echo "Demo Ready! Starting Full Stack..."
echo "=============================================="
echo ""
echo "Available Services:"
echo "  API Server: http://localhost:8000/"
echo "  Dashboard: http://localhost:8501/"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Demo Scenarios to try:"
echo "  1. Parts Query: 'brake pads for 2019 Honda Civic' (Green Auto-paid)"
echo "  2. Email Processing: Process mock emails with payment integration"
echo "  3. System Status: Check health, analytics, and ROI projections"
echo "  4. End-to-End: Query → RAG → Payment → Confirmation"
echo "  5. Analytics: Live metrics, export data, ROI calculations"
echo ""
echo "Pro tips:"
echo "  - Use ngrok to expose for mobile testing:"
echo "    ngrok http 8000 (API) or ngrok http 8501 (Dashboard)"
echo "  - Dashboard is mobile-optimized for field technicians"
echo "  - Email processing shows automation in action"
echo ""
echo "Logs saved to: logs/demo.log"
echo "Data stored in: data/faiss_index/"
echo "Sample CSV: sample_analytics_report.csv"
echo ""
echo "Starting full stack demo..."
echo "Press Ctrl+C to stop both services"
echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $API_PID $DASH_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start API server in background
echo "Starting API server..."
cd backend && python3 parts_rag_demo.py &
API_PID=$!

# Wait a moment for API to start
sleep 3

# Start Streamlit dashboard in background
echo "Starting Streamlit dashboard..."
cd .. && streamlit run dashboard.py --server.port 8501 --server.headless true &
DASH_PID=$!

# Wait for both services to start
sleep 5

echo ""
echo "Both services started successfully!"
echo "API Server PID: $API_PID"
echo "Dashboard PID: $DASH_PID"
echo ""
echo "Demo is live and ready!"
echo "Visit http://localhost:8501 for the interactive dashboard"
echo ""

# Keep script running and wait for interrupt
wait
