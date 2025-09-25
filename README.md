# Hero of Kindness CPRA Filter

A local, offline-first web application for processing California Public Records Act (CPRA) requests related to environmental hazards at school facilities.

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Ollama installed and running

### Installation

1. Clone the repository:
```bash
git clone git@github.com:nomindnick/HOC-POV.git
cd HOC-POC
```

2. Set up Python environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

4. Install at least one Ollama model:
```bash
ollama pull phi4-mini:3.8b
# or
ollama pull gemma3:4b
```

### Running the Application

Start both backend and frontend with one command:
```bash
./cpra-filter up
```

The application will:
- Start the FastAPI backend on http://localhost:8000
- Start the React frontend on http://localhost:5173
- Open your default browser to the frontend

### Development

Check system dependencies:
```bash
./cpra-filter check
```

Run tests:
```bash
./cpra-filter test
```

### Project Structure

```
cpra-filter/
├── backend/          # FastAPI backend
│   ├── api/         # API endpoints
│   ├── db/          # Database models
│   ├── llm/         # LLM integration
│   └── utils/       # Utilities
├── frontend/         # React + Vite frontend
│   └── src/
│       ├── pages/   # Page components
│       ├── components/
│       └── api/     # API client
├── tests/           # Test suite
├── data/           # Project data storage
└── scripts/        # Utility scripts
```

### Features

- **Local LLM Integration**: Uses Ollama for completely offline document classification
- **Email Ingestion**: Parse and process `.txt` email files
- **Smart Classification**: Disambiguates terms like "lead" (metal vs. leadership role)
- **Statistical QA**: Stratified sampling with confidence intervals
- **Comprehensive Audit Trail**: Full tracking of all classification decisions
- **Export Capabilities**: Generate document sets with detailed logs

## Sprint 1 - Complete ✅

This represents the completion of Sprint 1 from the implementation plan:
- ✅ Git repository initialized and connected to GitHub
- ✅ Complete project directory structure
- ✅ FastAPI backend with health endpoint
- ✅ React frontend with Vite and TypeScript
- ✅ Frontend-backend proxy configuration
- ✅ CLI wrapper script for easy startup
- ✅ All acceptance criteria met

### Verification

Backend health check:
```bash
curl http://localhost:8000/api/health
```

Frontend proxy test:
```bash
curl http://localhost:5173/api/health
```

## Next Steps

- Sprint 2: Database Schema & Models
- Sprint 3: Email Ingestion Pipeline
- Sprint 4: Ollama Client & Model Discovery
- Sprint 5: Prompt Template & Few-Shot System

See `docs/hero_of_kindness_implementation_plan.md` for the full roadmap.