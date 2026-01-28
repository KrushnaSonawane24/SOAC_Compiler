# SOAC — Self-Optimizing AI Compiler

**Production-grade AI model optimization platform with explainable decisions, reproducible builds, and secure multi-user support.**

## ✨ Features

- **End-to-end compilation** - ONNX model → optimized variants → deployment artifacts
- **Policy-based optimization** - `accuracy_first`, `latency_first`, `mobile_first`, `balanced`
- **Accuracy-Locking Optimizer (ALO)** - Enforces ≤2% accuracy drop guarantee
- **Reproducible builds** - Deterministic outputs with build fingerprints
- **Explainable decisions** - Full audit trails for every optimization choice
- **Multi-format export** - TFLite, ONNX, TensorRT, CoreML
- **Secure multi-user** - JWT authentication with GitHub/Google OAuth
- **React dashboard** - Modern UI for job management and visualization
- **PDF reports** - Professional documentation for auditors/judges

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   React Frontend │────▶│   FastAPI Backend │
└─────────────────┘     └────────┬────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
   ┌─────────┐            ┌─────────────┐          ┌─────────────┐
   │Validator│───────────▶│  SOAC Core  │─────────▶│ Deployment  │
   └─────────┘            └─────────────┘          └─────────────┘
                                │
                      ┌─────────┴─────────┐
                      ▼                   ▼
                ┌──────────┐       ┌──────────────┐
                │Optimizer │       │ Benchmarker  │
                └──────────┘       └──────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- ONNX Runtime

### Backend Setup

```bash
# Clone and enter directory
cd "SOAC v2"

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run API
uvicorn backend.api:create_app --factory --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

### Access

- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

## 🐳 Docker (Optional)

```bash
# Build and run
docker-compose up --build

# Access
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

## 🔒 Security

- JWT-based authentication
- OAuth with GitHub and Google
- Per-user job isolation

## 📱 Deployment & Demos

We provide ready-to-use deployment pipelines for Android and NVIDIA PC.

- **Architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md) for details on the deployment pipeline.
- **Android TFLite:** See [demos/android/README.md](demos/android/README.md).
- **PC TensorRT:** See [demos/pc/run_inference.py](demos/pc/run_inference.py).

### Verification
Run the deployment verification script to test the entire pipeline:
```bash
venv\Scripts\python verify_deployment.py
```
- No secrets in repository
- Input validation and sandboxing

## 📊 Outputs (per job)

| File | Description |
|------|-------------|
| `soac_report.pdf` | Comprehensive optimization report |
| `job_summary.json` | Job metadata |
| `explainability.json` | Decision rationale |
| `build_fingerprint.json` | Reproducibility proof |
| `*.tflite` / `*.onnx` | Deployment artifacts |

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_auth -v
```

## 📁 Project Structure

```
SOAC v2/
├── backend/
│   ├── api/           # FastAPI routes
│   ├── auth/          # Authentication
│   ├── compiler/      # Model canonicalization
│   ├── optimizer/     # Variant generation
│   ├── benchmark/     # Performance testing
│   ├── deployment/    # Artifact creation
│   ├── orchestrator/  # Pipeline coordination
│   └── reporting/     # PDF/JSON/CSV exports
├── frontend/
│   └── src/           # React dashboard
├── tests/             # Pytest test suite
└── docker-compose.yml
```

## ⚠️ Known Limitations

1. **TensorRT/CoreML export requires platform-specific dependencies**
2. **Large models (>1GB) may require increased timeout settings**
3. **OAuth requires registration with GitHub/Google**

## 📜 License

MIT

---

*Built for production. Ready for judges.*
