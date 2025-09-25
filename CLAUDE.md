# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Hero of Kindness CPRA Filter - a local, offline-first web application designed to help California public agencies process California Public Records Act (CPRA) requests related to environmental hazards at school facilities. It uses local Large Language Models (LLMs) via Ollama to pre-filter email documents.

## Key Commands

### Development Setup
```bash
# Install Python dependencies
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .

# Install Node.js dependencies
npm install

# Start the application
cpra-filter up  # Starts backend on :8000 and frontend on :5173
```

### Testing
```bash
# Run unit tests
pytest tests/unit/

# Run golden set evaluation
python scripts/eval_on_golden_set.py

# Run end-to-end tests
pytest tests/e2e/
```

### Build & Deploy
```bash
# Production mode
cpra-filter up --production

# Generate golden test set
python scripts/generate_golden_set.py

# Backup project
cpra-filter backup --project-id 1 --output backup.tar.gz
```

## Architecture Overview

### Technology Stack
- **Backend**: FastAPI (Python 3.11+) with SQLModel/SQLAlchemy, SQLite database
- **Frontend**: React + Vite, TypeScript, TailwindCSS, React Query
- **LLM Integration**: Ollama for local model inference
- **Task Processing**: FastAPI BackgroundTasks with asyncio worker pool

### Core Data Flow
1. **Ingestion**: Email files (.txt format) uploaded and parsed for RFC-822 headers
2. **Classification**: LLMs classify emails as responsive/non-responsive to CPRA request
3. **Review**: Three-bucket system (responsive, non-responsive, low confidence)
4. **Sampling**: Statistical QA with stratified sampling and Wilson confidence intervals
5. **Export**: Generate document sets with comprehensive audit logs

### Key API Endpoints
- `POST /api/ingest` - Upload email files
- `POST /api/classify/start` - Begin LLM classification
- `GET /api/classify/status?project=X` - Check processing status
- `GET /api/emails?project=X&bucket=Y` - Retrieve emails for review
- `POST /api/review/{id}` - Update classifications
- `POST /api/sampling/create` - Generate QA sample
- `POST /api/export/responsive` - Export responsive documents

### Database Schema (SQLModel)
- **Project**: Project configuration and metadata
- **Email**: Parsed email content with SHA-256 deduplication
- **Classification**: LLM predictions with confidence scores
- **Review**: Human overrides and attorney notes
- **Sampling/SamplingItem**: Statistical QA tracking

### LLM Prompt Engineering
The system uses few-shot prompting to disambiguate terms like "lead" (metal vs. leadership role). Key components:
- System prompt defining legal assistant role
- Domain-specific examples for edge cases
- JSON schema for structured output
- Robust parsing with fallback mechanisms

## Project Structure
```
cpra-filter/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── api/                # API endpoints
│   ├── db/                 # Database models and CRUD
│   ├── llm/                # Ollama integration
│   └── utils/              # Helpers (parsing, metrics, export)
├── frontend/
│   └── src/
│       ├── pages/          # React page components
│       ├── components/     # Reusable UI components
│       └── api/            # API client
├── data/
│   └── projects/           # Project data storage
├── tests/
│   ├── golden_set/         # Synthetic test emails
│   ├── unit/               # Unit tests
│   └── e2e/                # Integration tests
└── scripts/                # Utility scripts
```

## Important Implementation Details

### Email Parsing
- Expects .txt files with RFC-822 headers (Subject, From, To, Date)
- Body starts after first blank line
- SHA-256 hashing for duplicate detection

### LLM Classification
- Uses Ollama API at localhost:11434
- Supports models: gemma3:4b, phi-4-mini, qwen2.5-7b-instruct
- JSON output with responsive/confidence/reason/labels
- Robust parsing handles malformed responses

### Statistical Sampling
- Stratified by predicted class × confidence bins
- Wilson confidence intervals for metrics
- Blind review mode to prevent bias
- Calibration analysis for confidence accuracy

### Error Handling
- Exponential backoff for retries
- Graceful JSON parsing recovery
- Manual review queue for failures
- Resume capability after interruptions

## Performance Targets
- Process >100 emails/minute (model-dependent)
- Support 10,000+ document projects
- UI response <100ms
- Memory usage <2GB (excluding LLM)
- Compatible with 16GB RAM systems