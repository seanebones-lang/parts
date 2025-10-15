# Engineer Setup Guide - Complete Runtime Environment

## System Requirements
- Python 3.8+ (recommended 3.11+)
- Node.js 18+ (for frontend)
- Docker (optional, for containerized deployment)
- Git

## Quick Start (5 minutes)

### 1. Clone Repository
```bash
git clone https://github.com/seanebones-lang/Parrts-Dist-RAG.git
cd Parrts-Dist-RAG
```

### 2. Python Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### 3. Initialize System
```bash
# Build vector database with sample data
python3 data_loader.py

# Generate initial analytics
python3 analytics.py
```

### 4. Start Complete System
```bash
# Option A: Quick demo (recommended for testing)
python3 demo/rag_demo.py

# Option B: Full system with API + Dashboard
./start_demo.sh
```

## Verification Tests

### Test 1: Core RAG Engine
```bash
python3 demo/test_runner.py --health
python3 demo/test_runner.py --quick
```

### Test 2: API Endpoints
```bash
# Start API server
cd backend && python3 parts_rag_demo.py &

# Test endpoints
curl -X POST http://localhost:8000/query_parts \
  -H "Content-Type: application/json" \
  -d '{"text": "brake pads for 2019 Honda Civic"}'
```

### Test 3: Dashboard
```bash
# Start dashboard
streamlit run dashboard.py --server.port 8501

# Access at http://localhost:8501
```

## Complete System Architecture

### Backend Components
- **FastAPI Server**: `backend/parts_rag_demo.py`
- **AI Agents**: `backend/app/agents/`
- **Services**: `backend/app/services/`
- **Models**: `backend/app/models/`
- **API Endpoints**: `backend/app/api/v1/endpoints/`

### Frontend Components
- **Next.js App**: `frontend/`
- **React Components**: `frontend/components/`
- **Pages**: `frontend/app/`

### Demo Components
- **RAG Core**: `demo/rag_demo.py`
- **Test Suite**: `demo/test_runner.py`
- **Security Layer**: `demo/security_layer.py`
- **ERP Integration**: `demo/erp_integration.py`

## Key Files for Verification

### Core System Files
- `data_loader.py` - Builds vector database
- `analytics.py` - Generates metrics and ROI
- `logger.py` - Professional logging system
- `dashboard.py` - Streamlit dashboard
- `stripe_mock.py` - Payment processing simulation
- `email_mock.py` - Email processing simulation

### Configuration Files
- `requirements.txt` - Python dependencies
- `start_demo.sh` - Complete system startup
- `demo-setup.sh` - Docker-based setup
- `docker-compose.yml` - Container orchestration

### Documentation
- `README.md` - Main system documentation
- `COMPLETE_SYSTEM_README.md` - Complete system overview
- `MASTER_HEIST_CHECKLIST.md` - Production checklist

## Troubleshooting

### Common Issues
1. **FAISS Import Error**: Install with `pip install faiss-cpu`
2. **Sentence Transformers Error**: Install with `pip install sentence-transformers`
3. **Port Conflicts**: Change ports in startup scripts
4. **Permission Errors**: Make scripts executable with `chmod +x *.sh`

### Dependencies Verification
```bash
# Check critical dependencies
python3 -c "import fastapi, langchain, faiss, sentence_transformers, streamlit; print('All dependencies OK')"
```

## Production Deployment

### Docker Setup
```bash
# Build and run with Docker
./demo-setup.sh
./start-demo.sh
```

### Manual Production Setup
1. Install PostgreSQL with pgvector extension
2. Install Redis for caching
3. Configure environment variables
4. Run database migrations
5. Start services with proper process management

## System Capabilities Verification

### AI Agents (13 total)
- Email Classifier Agent
- Customer Service Agent  
- Parts Lookup Agent
- Inventory Manager Agent
- Pricing & Invoice Agent
- Payment Agent
- Shipping Coordinator Agent
- Supplier Sourcing Agent
- Follow-up Agent
- Supervisor Agent

### Key Features
- RAG-powered parts search across 7 locations
- Email processing with automatic routing
- Payment integration with Stripe
- Real-time analytics and ROI calculations
- Mobile-optimized dashboard
- Professional logging and audit trails

## Contact Information
For technical support or deployment questions, refer to the main README.md file.
