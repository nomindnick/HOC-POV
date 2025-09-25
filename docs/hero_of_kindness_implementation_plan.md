# Hero of Kindness CPRA Filter - Implementation Plan v2.0

## Overview

This implementation plan provides a structured, sprint-based approach for building the Hero of Kindness CPRA Filter with an AI coding assistant. Each sprint is designed to be completed in 1-2 hours, with explicit acceptance criteria for validation.

## Technology Stack

### Core Technologies
- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2, SQLModel/SQLAlchemy, SQLite
- **Frontend**: React + Vite, TypeScript, TailwindCSS, React Query
- **LLM Integration**: Ollama via httpx (async)
- **Task Queue**: FastAPI BackgroundTasks with asyncio worker pool
- **Testing**: pytest, pytest-asyncio
- **File Handling**: python-multipart, hashlib, pathlib

### Dependencies
```txt
# requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlmodel==0.0.14
pydantic==2.5.0
httpx==0.26.0
python-multipart==0.0.6
pandas==2.1.0
openpyxl==3.1.0
pytest==7.4.0
pytest-asyncio==0.23.0
python-dotenv==1.0.0
```

```json
// package.json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.0.0",
    "axios": "^1.6.0",
    "react-dropzone": "^14.2.0",
    "tailwindcss": "^3.4.0",
    "recharts": "^2.10.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

## Project Structure
```
cpra-filter/
├── backend/
│   ├── app.py                    # FastAPI app initialization
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ingest.py             # File upload endpoints
│   │   ├── classify.py           # LLM classification endpoints
│   │   ├── review.py             # Review and override endpoints
│   │   ├── sampling.py           # Statistical sampling endpoints
│   │   ├── export.py             # Export generation endpoints
│   │   ├── models.py             # Ollama model management
│   │   └── settings.py           # Config management endpoints
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py               # Database connection
│   │   ├── schema.py             # SQLModel definitions
│   │   └── crud.py               # Database operations
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py             # Ollama API client
│   │   ├── prompt.py             # Prompt templates
│   │   └── fewshot.json          # Few-shot examples
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── email_parser.py       # Email parsing utilities
│   │   ├── hashing.py            # SHA-256 operations
│   │   ├── sampling.py           # Stratified sampling
│   │   ├── metrics.py            # Accuracy metrics with Wilson CI
│   │   └── export.py             # Export formatters
│   └── config.py                 # Environment config
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Process.tsx       # Upload and processing
│   │   │   ├── Review.tsx        # Document review
│   │   │   ├── Sampling.tsx      # QA sampling
│   │   │   ├── Exports.tsx       # Export management
│   │   │   └── Settings.tsx      # Configuration
│   │   ├── components/
│   │   │   ├── Dropzone.tsx      # File upload component
│   │   │   ├── ProgressBar.tsx   # Processing progress
│   │   │   ├── EmailGrid.tsx     # Review grid
│   │   │   ├── DetailPane.tsx    # Email detail view
│   │   │   ├── ModelSelect.tsx   # Model dropdown
│   │   │   └── MetricsChart.tsx  # Calibration plots
│   │   ├── api/
│   │   │   └── client.ts         # API client
│   │   └── types/
│   │       └── index.ts          # TypeScript types
│   ├── vite.config.ts
│   └── tailwind.config.js
├── data/
│   └── projects/
│       └── <project-id>/
│           ├── db.sqlite
│           ├── imports/
│           └── exports/
├── tests/
│   ├── __init__.py
│   ├── golden_set/
│   │   ├── generate.py           # Create test data
│   │   ├── emails/               # Test email files
│   │   └── labels.csv            # Ground truth
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_llm.py
│   │   ├── test_sampling.py
│   │   └── test_metrics.py
│   └── e2e/
│       └── test_workflow.py
├── scripts/
│   ├── generate_golden_set.py
│   ├── eval_on_golden_set.py
│   └── seed_project.py
├── .env.example
├── README.md
├── requirements.txt
├── package.json
└── cpra-filter              # CLI wrapper script
```

---

## Sprint Breakdown

### Sprint 1: Repository Scaffold & Development Environment
**Duration**: 1 hour

**Tasks**:
1. Initialize Git repository with .gitignore
2. Create directory structure
3. Set up Python virtual environment
4. Initialize FastAPI backend with health endpoint
5. Initialize React frontend with Vite
6. Configure proxy for API calls
7. Add development scripts

**Acceptance Criteria**:
```bash
# Backend serves health check
curl http://localhost:8000/api/health
# Returns: {"status": "ok", "timestamp": "..."}

# Frontend proxies to backend
npm run dev  # Opens browser
# Network tab shows /api/health succeeds
```

**Deliverables**:
- Working development environment
- Health endpoint responding
- Frontend-backend communication verified

---

### Sprint 2: Database Schema & Models
**Duration**: 1-2 hours

**Tasks**:
1. Define SQLModel entities:
   ```python
   class Project(SQLModel, table=True):
       id: int = Field(primary_key=True)
       name: str
       created_at: datetime
       config_json: str  # JSON string
   
   class Email(SQLModel, table=True):
       id: int = Field(primary_key=True)
       project_id: int = Field(foreign_key="project.id")
       path: str
       sha256: str = Field(index=True)
       subject: Optional[str]
       from_addr: Optional[str]
       to_addr: Optional[str]
       date: Optional[datetime]
       body_text: str
       meta_json: str
   
   class Classification(SQLModel, table=True):
       id: int = Field(primary_key=True)
       email_id: int = Field(foreign_key="email.id")
       run_id: str = Field(index=True)
       model: str
       prompt_version: str
       params_json: str
       responsive_pred: bool
       confidence: float
       labels_json: str
       reason: str
       created_at: datetime
   ```

2. Create database initialization
3. Implement basic CRUD operations
4. Add database migrations placeholder

**Acceptance Criteria**:
```python
# Unit test passes
def test_create_email():
    email = create_email(project_id=1, path="/test.txt", 
                         sha256="abc", body_text="test")
    assert email.id is not None
    retrieved = get_email(email.id)
    assert retrieved.sha256 == "abc"
```

**Deliverables**:
- Database schema implemented
- CRUD operations working
- Unit tests passing

---

### Sprint 3: Email Ingestion Pipeline
**Duration**: 1-2 hours

**Tasks**:
1. Implement `POST /api/ingest` endpoint
2. Create email parser for RFC-822 headers:
   ```python
   def parse_email_file(filepath: Path) -> EmailData:
       # Extract Subject, From, To, Date
       # Everything after first blank line is body
   ```
3. Implement SHA-256 hashing for duplicates
4. Store emails with metadata in database
5. Handle batch uploads

**Acceptance Criteria**:
```bash
# Upload test emails
curl -X POST http://localhost:8000/api/ingest \
  -F "project_id=1" \
  -F "files=@test1.txt" \
  -F "files=@test2.txt"
# Returns: {"count": 2, "duplicates": 0}

# Verify in database
SELECT COUNT(*) FROM email WHERE project_id = 1;
# Returns: 2
```

**Deliverables**:
- File upload working
- Email parsing with headers
- Duplicate detection via SHA-256
- Batch processing capability

---

### Sprint 4: Ollama Client & Model Discovery
**Duration**: 1 hour

**Tasks**:
1. Create Ollama client wrapper:
   ```python
   class OllamaClient:
       async def list_models(self) -> List[ModelInfo]
       async def generate(self, prompt: str, model: str, 
                         temperature: float = 0.7) -> str
       async def health_check(self) -> bool
   ```
2. Implement `GET /api/models` endpoint
3. Add graceful error handling for Ollama offline
4. Create model caching mechanism

**Acceptance Criteria**:
```bash
# With Ollama running
curl http://localhost:8000/api/models
# Returns: [{"name": "phi4:mini", "size": "3.8GB"}, ...]

# With Ollama stopped
curl http://localhost:8000/api/models
# Returns: {"error": "Ollama not available", "models": []}
```

**Deliverables**:
- Ollama client with async support
- Model discovery endpoint
- Error handling for offline Ollama

---

### Sprint 5: Prompt Template & Few-Shot System
**Duration**: 1-2 hours

**Tasks**:
1. Create prompt template engine:
   ```python
   class PromptBuilder:
       def __init__(self, fewshot_path: str)
       def build(self, email: Email) -> str
   ```
2. Implement few-shot examples in JSON
3. Add domain-specific examples for "lead" disambiguation
4. Version tracking for prompts

**Few-Shot Examples Structure**:
```json
{
  "version": "1.0",
  "system": "You are a careful legal assistant...",
  "examples": [
    {
      "subject": "RE: Fountain water test results",
      "body": "Lab found 19 ppb lead...",
      "output": {
        "responsive": true,
        "confidence": 0.92,
        "reason": "Lead contamination in water",
        "labels": ["lead", "water"]
      }
    },
    {
      "subject": "Hiring a lead teacher",
      "body": "Offer letter draft...",
      "output": {
        "responsive": false,
        "confidence": 0.94,
        "reason": "'lead' refers to role",
        "labels": []
      }
    }
  ]
}
```

**Acceptance Criteria**:
```python
# Test prompt generation
prompt = builder.build(email)
assert "You are a careful legal assistant" in prompt
assert "Lab found 19 ppb lead" in prompt  # Few-shot example
assert email.body_text in prompt
```

**Deliverables**:
- Prompt template system
- Few-shot examples (7-10 examples)
- Version tracking implemented

---

### Sprint 6: Classification API & Worker Queue
**Duration**: 2 hours

**Tasks**:
1. Implement classification endpoints:
   ```python
   @app.post("/api/classify/start")
   async def start_classification(
       project_id: int,
       model: str,
       params: ClassificationParams,
       background_tasks: BackgroundTasks
   )
   
   @app.get("/api/classify/status")
   async def get_status(project_id: int)
   ```
2. Create async worker pool
3. Implement JSON parsing with recovery
4. Add progress tracking

**Robust JSON Parsing**:
```python
def parse_llm_response(raw: str) -> ClassificationResult:
    # Strip markdown if present
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            # Validate and clamp values
            confidence = max(0, min(1, data.get('confidence', 0)))
            return ClassificationResult(...)
        except json.JSONDecodeError:
            # Retry with fixes
    raise ParseError(f"Cannot parse: {raw[:200]}")
```

**Acceptance Criteria**:
```bash
# Start classification
curl -X POST http://localhost:8000/api/classify/start \
  -d '{"project_id": 1, "model": "phi4:mini"}'
# Returns: {"run_id": "uuid-here"}

# Check status
curl http://localhost:8000/api/classify/status?project_id=1
# Returns: {"queued": 45, "processing": 5, "done": 50, "failed": 0}
```

**Deliverables**:
- Classification API working
- Async processing with queue
- Progress tracking
- Robust JSON parsing

---

### Sprint 7: React Frontend - Process Page
**Duration**: 2 hours

**Tasks**:
1. Create Process page with:
   - Model selection dropdown
   - Drag-and-drop zone (react-dropzone)
   - Start/pause/resume buttons
   - Progress visualization
2. Implement real-time status polling
3. Add file validation in UI

**Component Structure**:
```tsx
const ProcessPage: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState<Status>();
  
  // Poll status every 2 seconds when processing
  useQuery({
    queryKey: ['status', projectId],
    queryFn: fetchStatus,
    enabled: processing,
    refetchInterval: 2000
  });
  
  return (
    <div>
      <ModelSelect onChange={setModel} />
      <Dropzone onDrop={setFiles} />
      <ProgressBar {...status} />
      <button onClick={startProcessing}>Start</button>
    </div>
  );
};
```

**Acceptance Criteria**:
- Can drag and drop 50 .txt files
- Model dropdown populated from API
- Progress updates live during processing
- Pause/resume functions work

**Deliverables**:
- Complete Process page
- File upload working
- Live progress updates
- Model selection integrated

---

### Sprint 8: Review Interface with Grid & Details
**Duration**: 2 hours

**Tasks**:
1. Create Review page with three tabs:
   - Responsive
   - Non-responsive
   - Low confidence (<0.65)
2. Implement email grid with sorting/filtering
3. Build detail pane with override controls
4. Add bulk operations

**Grid Configuration**:
```tsx
const columns = [
  { field: 'subject', headerName: 'Subject', flex: 2 },
  { field: 'from', headerName: 'From', flex: 1 },
  { field: 'date', headerName: 'Date', width: 120 },
  { field: 'predicted', headerName: 'Predicted', width: 100 },
  { field: 'confidence', headerName: 'Confidence', width: 100,
    renderCell: (params) => <ConfidenceBadge value={params.value} />
  },
  { field: 'final', headerName: 'Final', width: 100 },
  { field: 'changed', headerName: 'Changed', width: 80,
    renderCell: (params) => params.value ? '✓' : ''
  }
];
```

**Acceptance Criteria**:
- Grid displays emails correctly
- Click row to see details
- Override classification persists
- Bulk select and reclassify works
- Filters work (confidence range, keyword)

**Deliverables**:
- Three-tab review interface
- Sortable/filterable grid
- Detail pane with overrides
- Bulk operations

---

### Sprint 9: Export System
**Duration**: 1-2 hours

**Tasks**:
1. Implement export endpoints:
   ```python
   @app.post("/api/export/responsive")
   async def export_responsive(project_id: int) -> ExportResult
   
   @app.get("/api/export/audit")
   async def export_audit(project_id: int) -> StreamingResponse
   ```
2. Create export formatters for:
   - Responsive document copies
   - CSV audit log
   - Index file
3. Implement streaming for large exports

**Audit Log Format**:
```csv
email_id,sha256,subject,from,to,date,predicted_responsive,confidence,
final_responsive,changed_by,changed_at,model,prompt_version,labels,reason
1,abc123,"Water test results",john@school.edu,admin@district.edu,2024-01-15,
true,0.92,true,attorney@firm.com,2024-01-20,phi4:mini,1.0,"[lead,water]",
"Lead contamination in water"
```

**Acceptance Criteria**:
```bash
# Export responsive documents
curl -X POST http://localhost:8000/api/export/responsive?project_id=1
# Creates: /data/projects/1/exports/2024-01-20/
# With original files and index.csv

# Download audit log
curl http://localhost:8000/api/export/audit?project_id=1 > audit.csv
# CSV contains all required fields
```

**Deliverables**:
- Export API endpoints
- File copying with structure
- CSV generation
- Streaming support

---

### Sprint 10: Statistical Sampling Engine
**Duration**: 2 hours

**Tasks**:
1. Implement stratified sampling:
   ```python
   def create_stratified_sample(
       emails: List[Email],
       classifications: List[Classification],
       size: int,
       seed: int
   ) -> List[SamplingItem]:
       # Stratify by predicted class × confidence bins
       bins = [
           ('responsive', 0.0, 0.3),
           ('responsive', 0.3, 0.6),
           ('responsive', 0.6, 0.8),
           ('responsive', 0.8, 1.0),
           ('non_responsive', 0.0, 0.3),
           # ...
       ]
   ```
2. Create sampling API endpoints
3. Implement blind review mode
4. Calculate metrics with Wilson confidence intervals

**Wilson CI Implementation**:
```python
def wilson_ci(successes: int, trials: int, confidence: float = 0.95):
    """Calculate Wilson confidence interval for proportion"""
    from scipy import stats
    if trials == 0:
        return (0, 0)
    
    p_hat = successes / trials
    z = stats.norm.ppf((1 + confidence) / 2)
    
    denominator = 1 + z**2 / trials
    center = (p_hat + z**2 / (2 * trials)) / denominator
    margin = z * sqrt(p_hat * (1 - p_hat) / trials + 
                      z**2 / (4 * trials**2)) / denominator
    
    return (max(0, center - margin), min(1, center + margin))
```

**Acceptance Criteria**:
- Sample created with proper stratification
- Blind review hides predictions until labeled
- Metrics calculated with 95% Wilson CIs
- Calibration plot data generated

**Deliverables**:
- Stratified sampling algorithm
- Blind review interface
- Metrics with confidence intervals
- Calibration analysis

---

### Sprint 11: Sampling UI & Reports
**Duration**: 1-2 hours

**Tasks**:
1. Create Sampling page with:
   - Sample configuration
   - Blind review workflow
   - Metrics display
   - Calibration chart
2. Implement report generation

**UI Components**:
```tsx
const SamplingPage: React.FC = () => {
  return (
    <div>
      <SampleConfig onGenerate={createSample} />
      <BlindReview 
        items={samplingItems}
        onLabel={saveLabel}
      />
      <MetricsDisplay metrics={metrics} />
      <CalibrationChart data={calibrationData} />
      <ExportButton format="markdown" />
    </div>
  );
};
```

**Report Output** (Markdown):
```markdown
# Sampling Report - Project Alpha
Generated: 2024-01-20 14:30

## Metrics (95% CI)
- Accuracy: 0.89 (0.84-0.93)
- Precision: 0.85 (0.78-0.91)
- Recall: 0.94 (0.89-0.97)
- F1 Score: 0.89

## Confusion Matrix
|              | Pred Responsive | Pred Non-Responsive |
|--------------|----------------|---------------------|
| True Resp    | 47             | 3                   |
| True Non-Resp| 8              | 42                  |

## Calibration Analysis
Model confidence is well-calibrated in 0.6-0.9 range.
Underconfident below 0.6, slightly overconfident above 0.9.
```

**Acceptance Criteria**:
- Sample generation with size/seed config
- Blind review workflow functions
- Metrics display with CIs
- Report exports correctly

**Deliverables**:
- Complete sampling interface
- Metrics visualization
- Report generation
- Calibration plots

---

### Sprint 12: Golden Set Generation & Testing
**Duration**: 2 hours

**Tasks**:
1. Create synthetic email generator:
   ```python
   def generate_golden_set(count: int = 200):
       emails = []
       # 40% clear responsive
       # 40% clear non-responsive
       # 20% edge cases
       
       # Edge cases include:
       # - "lead teacher" vs "lead paint"
       # - "mold the students" vs "mold in classroom"
       # - Mixed context emails
   ```

2. Generate diverse test scenarios
3. Create evaluation script
4. Establish baseline metrics

**Example Generated Emails**:
```python
edge_cases = [
    {
        "subject": "Lead teacher workshop next week",
        "body": "Our lead teachers will discuss leading...",
        "label": False
    },
    {
        "subject": "Question about pencil lead",
        "body": "Is the lead in pencils toxic?",
        "label": False  # Not about environmental hazard
    },
    {
        "subject": "Lead paint inspection results", 
        "body": "Inspector found deteriorating lead paint...",
        "label": True
    }
]
```

**Acceptance Criteria**:
```bash
# Generate golden set
python scripts/generate_golden_set.py
# Creates 200 emails in tests/golden_set/emails/
# Creates tests/golden_set/labels.csv

# Run evaluation
python scripts/eval_on_golden_set.py
# Outputs:
# Accuracy: 0.87
# Precision: 0.83
# Recall: 0.92
# F1: 0.87
```

**Deliverables**:
- 200 synthetic test emails
- Ground truth labels
- Evaluation script
- Baseline metrics established

---

### Sprint 13: Error Handling & Robustness
**Duration**: 1-2 hours

**Tasks**:
1. Implement comprehensive error handling:
   - Malformed JSON recovery
   - Timeout handling
   - Retry with exponential backoff
   - Dead letter queue for failures

2. Add validation and clamping:
   ```python
   def validate_classification(data: dict) -> Classification:
       # Clamp confidence to [0, 1]
       confidence = max(0, min(1, float(data.get('confidence', 0))))
       
       # Truncate reason to 200 chars
       reason = str(data.get('reason', ''))[:200]
       
       # Validate responsive is boolean
       responsive = bool(data.get('responsive', False))
       
       # Validate labels is list
       labels = data.get('labels', [])
       if not isinstance(labels, list):
           labels = []
   ```

3. Add circuit breaker for Ollama
4. Implement graceful degradation

**Acceptance Criteria**:
- Malformed JSON doesn't crash processing
- Timeouts are handled gracefully
- Failed items go to manual review queue
- System remains responsive under errors

**Deliverables**:
- Robust error handling throughout
- Validation for all inputs
- Retry mechanisms
- Manual review queue for failures

---

### Sprint 14: Persistence & Idempotence
**Duration**: 1 hour

**Tasks**:
1. Implement resume capability:
   ```python
   def resume_classification(project_id: int, run_id: str):
       # Find emails without classification for this run
       # Skip already processed
       # Continue from last position
   ```

2. Add idempotence via hashing:
   - Check SHA-256 before re-importing
   - Skip duplicate classifications
   - Make all operations idempotent

3. Add force re-classify option

**Acceptance Criteria**:
```bash
# Start classification
curl -X POST /api/classify/start
# Kill process mid-way

# Resume classification
curl -X POST /api/classify/resume
# Only processes remaining emails

# Force re-classify
curl -X POST /api/classify/start?force=true
# Re-processes all emails
```

**Deliverables**:
- Resume capability
- Idempotent operations
- Force re-classify option
- Duplicate prevention

---

### Sprint 15: CLI Wrapper & Cross-Platform Support
**Duration**: 1 hour

**Tasks**:
1. Create CLI wrapper script:
   ```python
   #!/usr/bin/env python
   # cpra-filter
   import click
   
   @click.group()
   def cli():
       pass
   
   @cli.command()
   def up():
       """Start the CPRA Filter application"""
       # Start backend
       # Start frontend
       # Open browser
   
   @cli.command()
   def test():
       """Run tests on golden set"""
   ```

2. Create platform-specific launchers:
   - Windows: `cpra-filter.bat`
   - Linux: `cpra-filter.sh`

3. Test on both platforms

**Acceptance Criteria**:
```bash
# Single command startup
cpra-filter up
# Opens browser to http://localhost:5173
# Backend running on :8000

# Run tests
cpra-filter test
# Runs golden set evaluation
```

**Deliverables**:
- CLI wrapper with commands
- Cross-platform launchers
- Tested on Windows and Ubuntu

---

### Sprint 16: Documentation & Polish
**Duration**: 1-2 hours

**Tasks**:
1. Create comprehensive README:
   ```markdown
   # Hero of Kindness CPRA Filter
   
   ## Quick Start
   1. Install Ollama
   2. Pull a model: `ollama pull phi4:mini`
   3. Install: `pip install -e .`
   4. Run: `cpra-filter up`
   
   ## Features
   - Local LLM classification
   - Statistical quality control
   - Comprehensive audit trails
   ...
   ```

2. Add inline documentation
3. Create user guide with screenshots
4. Add example workflow video/GIF

**Acceptance Criteria**:
- New user can follow README to completion
- All APIs documented
- Example project included
- Screenshots/demo available

**Deliverables**:
- Complete README
- API documentation
- User guide
- Sample project

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_parser.py
def test_parse_email_with_headers():
    content = "Subject: Test\nFrom: user@example.com\n\nBody"
    result = parse_email(content)
    assert result.subject == "Test"
    assert result.from_addr == "user@example.com"
    assert result.body == "Body"

# tests/unit/test_metrics.py  
def test_wilson_ci():
    lower, upper = wilson_ci(85, 100, confidence=0.95)
    assert 0.76 < lower < 0.78
    assert 0.90 < upper < 0.92
```

### Integration Tests
```python
# tests/e2e/test_workflow.py
async def test_full_workflow():
    # Upload files
    response = await client.post("/api/ingest", files=files)
    assert response.status_code == 200
    
    # Start classification
    response = await client.post("/api/classify/start")
    run_id = response.json()["run_id"]
    
    # Wait for completion
    while True:
        status = await client.get("/api/classify/status")
        if status.json()["queued"] == 0:
            break
    
    # Export results
    response = await client.post("/api/export/responsive")
    assert Path(response.json()["path"]).exists()
```

### Golden Set Evaluation
```bash
# Automated regression testing
python scripts/eval_on_golden_set.py --model phi4:mini
# Saves results to tests/golden_set/results/

# Compare models
python scripts/compare_models.py
# Generates comparison report
```

---

## Development Workflow with AI Assistant

### Effective Prompting for Each Sprint

**Sprint Start Template**:
```
"I'm working on Sprint X of the Hero of Kindness CPRA Filter project. 
Here are the acceptance criteria: [paste criteria]
Please implement the required components following the existing 
project structure and patterns."
```

**Testing Template**:
```
"Please create comprehensive unit tests for [component] that verify:
1. [Acceptance criterion 1]
2. [Acceptance criterion 2]
Include edge cases and error conditions."
```

**Debug Template**:
```
"The [feature] is failing with error: [error message]
Current code: [paste code]
Expected behavior: [description]
Please diagnose and fix the issue."
```

### Sprint Completion Checklist
- [ ] All acceptance criteria met
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code reviewed (by AI or peer)
- [ ] Committed to version control

---

## Performance Benchmarks

### Target Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Processing Speed | >100 emails/min | Time 1000 emails |
| Memory Usage | <2GB app | Monitor during processing |
| UI Response | <100ms | Measure API latency |
| Classification Accuracy | >87% F1 | Golden set evaluation |
| Startup Time | <5 seconds | Time from launch to ready |

### Load Testing
```python
# tests/performance/load_test.py
async def test_concurrent_processing():
    # Upload 1000 emails
    # Start classification with 4 workers
    # Measure: time, memory, CPU
    # Assert: <10 minutes, <2GB RAM
```

---

## Deployment & Maintenance

### Local Deployment
```bash
# Production mode
cpra-filter up --production
# Uses gunicorn, production React build
```

### Backup & Recovery
```bash
# Backup project
cpra-filter backup --project-id 1 --output backup.tar.gz

# Restore project  
cpra-filter restore --input backup.tar.gz
```

### Monitoring
- Log rotation configured
- Error tracking to file
- Performance metrics logged
- Audit trail maintained

---

## Security Considerations

### Data Protection
- All processing local only
- No external API calls except Ollama
- File permissions restricted
- Optional encryption at rest (future)

### Audit & Compliance
- Complete action logging
- User attribution for changes
- Immutable audit trail
- Export for legal discovery

---

## Future Enhancements Roadmap

### Phase 2 (Months 1-3)
- [ ] EML/MSG file support
- [ ] PST archive extraction
- [ ] Attachment text extraction
- [ ] Thread deduplication

### Phase 3 (Months 4-6)
- [ ] PDF support with OCR
- [ ] Active learning feedback
- [ ] Multi-user collaboration
- [ ] Advanced calibration

### Phase 4 (Months 7-12)
- [ ] Custom model fine-tuning
- [ ] Cloud deployment option
- [ ] API for external systems
- [ ] Privilege detection

---

## Conclusion

This implementation plan provides a systematic approach to building the Hero of Kindness CPRA Filter. Each sprint delivers working functionality that can be tested and validated. The modular architecture ensures maintainability and enables future enhancements without major refactoring.

By following these sprints with an AI coding assistant, you'll have a production-ready application that significantly streamlines CPRA document review while maintaining the high standards required for legal compliance. The focus on testing, metrics, and documentation ensures the tool is both reliable and defensible in legal proceedings.