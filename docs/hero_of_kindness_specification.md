# Hero of Kindness CPRA Filter - Application Specification v2.0

## Executive Summary

The Hero of Kindness CPRA Filter (`cpra-filter`) is a local, offline-first web application designed to assist California public agencies and their legal representatives in efficiently processing California Public Records Act (CPRA) requests related to environmental hazards at school facilities. The application uses local Large Language Models (LLMs) via Ollama to pre-filter email documents, identifying which are likely responsive to broad environmental hazard requests while maintaining high recall to minimize false negatives.

**Key Innovation**: Addresses the "lead problem" where keyword searches return thousands of false positives (e.g., "lead teacher" vs. "lead in water").

## Background & Problem Statement

### The Challenge
A CPRA request submitted by "Hero of Kindness" seeks extensive records from California public schools regarding environmental conditions, including but not limited to:
- **Mold** (inspection, testing, remediation, moisture intrusion)
- **Lead** (water testing, plumbing maintenance, paint/glazing)
- **Asbestos** (inspection, abatement, management, monitoring)
- **Other environmental hazards** (radon, PCBs, pesticides, VOCs, IAQ)
- **Building and infrastructure systems** (HVAC, roofing, windows, drainage)
- **Funding and remediation plans** (state/federal funding applications)

The broad nature of search terms results in massive document sets with many false positives, creating significant review burden for legal teams. For example, "lead" returns results about "lead teachers," "leadership," and "lead time" that are clearly non-responsive.

### The Solution
An AI-powered pre-filtering system that:
- Reduces attorney review time by 70-90%
- Maintains >95% recall to minimize risk of missing responsive documents
- Provides transparency through confidence scoring and reasoning
- Enables quality control through statistical sampling and human review
- Operates entirely offline to protect sensitive data

## Technical Architecture

### Technology Stack
- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2, SQLModel/SQLAlchemy, SQLite
- **Frontend**: React + Vite, TypeScript, TailwindCSS, React Query
- **LLM Integration**: Ollama (local models), httpx for API calls
- **Task Queue**: FastAPI background tasks with asyncio worker pool
- **Testing**: pytest, golden set evaluation framework

### Deployment Model
- Local web service (FastAPI) accessible via browser
- No external network calls (except to local Ollama)
- Cross-platform support (Ubuntu Linux, Windows 10/11)
- Single-command startup with automatic browser launch

## Core Features

### 1. Document Ingestion
- **Drag-and-drop interface** for batch file upload
- **Folder selection** for bulk import
- Initial support for `.txt` email format (one email per file)
- RFC-822 style header parsing (`Subject`, `From`, `To`, `Date`)
- SHA-256 hash-based duplicate detection
- File validation with clear error messages

### 2. LLM Processing Engine
- **Local LLM integration** via Ollama API
- **Model discovery** from Ollama (`/api/tags` endpoint)
- Support for multiple small models:
  - gemma3:4b
  - phi-4-mini  
  - qwen2.5-7b-instruct
  - Any model available via `ollama list`
- **Few-shot prompting** with domain-specific examples
- Structured JSON output:
  ```json
  {
    "responsive": true/false,
    "confidence": 0.0-1.0,
    "reason": "≤200 chars justification",
    "labels": ["mold", "lead", "asbestos", ...]
  }
  ```

### 3. Processing Interface
- Real-time progress tracking:
  - Queued / Processing / Completed / Failed counts
  - Processing rate (emails/minute)
  - Estimated time remaining
- Pause/resume/cancel capabilities
- Configurable concurrency and batch sizes
- Automatic recovery from interruptions

### 4. Review Interface
- **Three-bucket categorization**:
  - Responsive documents
  - Non-responsive documents  
  - Low confidence documents (configurable threshold, default <0.65)
- **Grid view with columns**:
  - Subject, From, To, Date
  - Predicted class, Confidence
  - Final class (after review)
  - Labels, Changed flag
- **Detail pane** for selected emails:
  - Full email content
  - LLM reasoning and confidence
  - Manual override controls
  - Attorney notes field
  - Change history tracking
- **Advanced features**:
  - Search and filtering (keyword, confidence range, date, sender)
  - Bulk operations for multiple selections
  - Keyboard shortcuts for efficient review
  - Persistent filter preferences

### 5. Statistical Sampling & QA Module
- **Stratified random sampling**:
  - Class bins: predicted responsive vs. non-responsive
  - Confidence bins: [0-0.3), [0.3-0.6), [0.6-0.8), [0.8-1.0]
  - Configurable sample size with statistical power calculation
- **Blind review mode**:
  - Hides model prediction until human labels
  - Prevents anchoring bias
  - Tracks reviewer identity and timestamp
- **Metrics calculation**:
  - Precision, Recall, F1 score
  - **95% Wilson confidence intervals** for all metrics
  - Confusion matrix visualization
  - Calibration plot (predicted vs. observed confidence)
- **Quality reports**:
  - Statistical accuracy metrics
  - Error analysis by category
  - Model calibration assessment

### 6. Export Capabilities
- **Responsive document set**:
  - Copies original files to export folder
  - Maintains original filenames
  - Generates index CSV with metadata
- **Comprehensive audit log**:
  ```csv
  email_id,sha256,subject,from,to,date,predicted_responsive,
  confidence,final_responsive,changed_by,changed_at,model,
  prompt_version,labels,reason
  ```
- **Sampling report**:
  - Detailed metrics with confidence intervals
  - Confusion matrix
  - Calibration data
  - Markdown summary for documentation

### 7. Configuration Management
- **Model settings**:
  - Default model selection
  - Temperature and top_p parameters
  - Max concurrent workers
- **Processing thresholds**:
  - Low confidence threshold (default 0.65)
  - Sampling rate
  - Max file size
- **Storage configuration**:
  - Database path
  - Import/export directories
  - Cache management

## User Workflow

### Phase 1: Setup & Configuration
1. Launch application via `cpra-filter up`
2. System validates Ollama availability
3. Select LLM model from discovered options
4. Configure confidence thresholds and processing parameters

### Phase 2: Document Import
1. Navigate to Process page
2. Drag-and-drop `.txt` files or select folder
3. System performs duplicate detection via SHA-256
4. Review import summary and confirm

### Phase 3: Automated Classification
1. Click "Start Processing"
2. Monitor real-time progress
3. System processes through queue with:
   - Automatic retry on failures
   - Graceful JSON parsing recovery
   - Timeout handling (configurable)

### Phase 4: Statistical Sampling
1. Navigate to Sampling page
2. System generates stratified sample
3. Perform blind review of sample
4. Review accuracy metrics and confidence intervals
5. Adjust thresholds if needed based on calibration

### Phase 5: Full Document Review
1. Navigate to Review page
2. Start with low-confidence items
3. Spot-check high-confidence classifications
4. Apply manual overrides as needed
5. Add attorney notes for key decisions

### Phase 6: Export & Documentation
1. Generate responsive document set
2. Export comprehensive audit log
3. Generate sampling QA report
4. Archive project for records retention

## LLM Prompt Engineering

### System Prompt
```
You are a careful legal assistant helping classify emails for a CPRA request 
regarding environmental hazards and building-system conditions at K-12 schools 
and district facilities. Determine whether the email meaningfully discusses or 
pertains to such environmental conditions. Avoid false positives where words 
like "lead" mean "leadership," "lead teacher," "lead time," or other unrelated 
senses. Output only valid JSON per the schema.
```

### Few-Shot Examples

**Responsive - Lead in Water**
- Subject: "RE: Fountain water test results - Rm 12"
- Body: "Lab found 19 ppb lead in the east hallway fountain"
- Output: `{"responsive": true, "confidence": 0.92, "reason": "Lead contamination in water", "labels": ["lead", "water"]}`

**Non-Responsive - Lead Teacher**
- Subject: "Hiring a lead teacher for 2nd grade"
- Body: "Offer letter draft attached"
- Output: `{"responsive": false, "confidence": 0.94, "reason": "'lead' refers to role, not metal", "labels": []}`

**Edge Case - Mixed Context**
- Subject: "Lead paint concern from parent"
- Body: "Parent asked if we tested. Referred to lead counselor"
- Output: `{"responsive": true, "confidence": 0.67, "reason": "Mentions lead paint testing inquiry", "labels": ["lead", "paint"]}`

## API Endpoints

```
# Health & Status
GET  /api/health                          -> {"status": "ok", "ollama": true}
GET  /api/models                          -> [{"model": "qwen2.5:7b", "size": "7B"}]

# Ingestion
POST /api/ingest                          -> {"count": 150, "duplicates": 3}

# Classification
POST /api/classify/start                  -> {"run_id": "uuid"}
GET  /api/classify/status?project=X       -> {"queued": 50, "processing": 2, "done": 98}

# Review
GET  /api/emails?project=X&bucket=Y       -> Paginated results with filters
GET  /api/email/{id}                      -> Full email with classification
POST /api/review/{id}                     -> Update classification/notes

# Sampling
POST /api/sampling/create                 -> {"sampling_id": "uuid"}
GET  /api/sampling/{id}/next              -> Next item for blind review
POST /api/sampling/{id}/label             -> Save human label
GET  /api/sampling/{id}/report            -> Metrics with Wilson CIs

# Export
POST /api/export/responsive               -> {"path": "/exports/2024-01-15/"}
GET  /api/export/audit                    -> CSV stream
GET  /api/sampling/export                 -> CSV + Markdown report
```

## Data Model

### SQLModel Entities

```python
class Project(SQLModel):
    id: int
    name: str
    created_at: datetime
    config_json: dict

class Email(SQLModel):
    id: int
    project_id: int
    path: str
    sha256: str
    subject: Optional[str]
    from_addr: Optional[str]
    to_addr: Optional[str]
    date: Optional[datetime]
    body_text: str
    meta_json: dict

class Classification(SQLModel):
    id: int
    email_id: int
    run_id: str
    model: str
    prompt_version: str
    params_json: dict
    responsive_pred: bool
    confidence: float
    labels_json: list
    reason: str
    created_at: datetime

class Review(SQLModel):
    id: int
    email_id: int
    reviewer: str
    final_responsive: bool
    note: Optional[str]
    changed_from_pred: bool
    created_at: datetime

class Sampling(SQLModel):
    id: int
    project_id: int
    seed: int
    size: int
    method_json: dict
    created_at: datetime

class SamplingItem(SQLModel):
    id: int
    sampling_id: int
    email_id: int
    human_label: Optional[bool]
    reviewer: Optional[str]
    reviewed_at: Optional[datetime]
```

## Performance Requirements

- Process minimum 100 emails per minute (model-dependent)
- Support projects with 10,000+ documents
- UI response time <100ms for all interactions
- Background processing non-blocking
- Memory usage <2GB for application (excluding LLM)
- LLM models runnable on 16GB RAM systems
- SQLite optimized with appropriate indexes
- Graceful degradation under load

## Security & Privacy

- **Data isolation**: All processing performed locally
- **No external calls**: Network requests only to localhost:11434 (Ollama)
- **Minimal logging**: No email bodies in logs
- **Session management**: Ephemeral sessions, configurable retention
- **Audit trail**: All user actions logged with timestamps
- **Data portability**: Export all project data for archival
- **Future enhancements**: Encryption at rest, signed exports

## Testing Strategy

### Unit Tests
- Email parsing edge cases
- Prompt rendering consistency
- JSON parsing with malformed responses
- Sampling stratification
- Metric calculations with edge cases
- Wilson CI accuracy

### Golden Set
- 200+ synthetic emails with known labels
- Mix of clear positives, clear negatives, and edge cases
- Automated evaluation script
- Regression testing on model/prompt changes
- Performance benchmarking

### Integration Tests
- End-to-end workflow automation
- API endpoint testing
- Database transaction handling
- Export format validation

### User Acceptance Testing
- Attorney workflow validation
- Cross-platform UI consistency
- Performance under realistic loads
- Export compatibility with legal systems

## Error Handling & Resilience

### Robust JSON Parsing
```python
# Strip markdown, fix quotes, extract JSON
# Retry with exponential backoff
# Fallback to manual review queue
```

### Classification Errors
- Automatic retry with backoff
- Error categorization (timeout, parsing, model)
- Manual review queue for failures
- Detailed error logging with context

### Recovery Mechanisms
- Resume processing after crash
- Idempotent operations via hashing
- Transaction-safe database updates
- Automatic session recovery

## Success Metrics

- **Efficiency**: 70-90% reduction in manual review time
- **Accuracy**: >95% recall for responsive documents
- **Precision**: >80% for high-confidence (>0.8) classifications  
- **Confidence Calibration**: Within 10% of predicted vs. observed
- **User Adoption**: >80% attorney satisfaction
- **Performance**: Process 1000 documents in <10 minutes
- **Reliability**: <1% failure rate in production

## Installation & Setup

```bash
# Prerequisites
1. Install Python 3.11+
2. Install Node.js 18+
3. Install and start Ollama
4. Pull at least one model:
   ollama pull phi4:mini

# Application Setup
git clone https://github.com/org/cpra-filter
cd cpra-filter
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
npm install

# Launch
cpra-filter up  # Starts backend and opens browser
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ambiguous terms ("lead") | False positives/negatives | Few-shot examples, confidence scoring |
| Model drift | Accuracy degradation | Version tracking, regular sampling |
| CPU performance | Slow processing | Queue management, model selection |
| User error | Incorrect classifications | Undo/history, audit trail |
| Data sensitivity | Privacy breach | Local-only, minimal logging |
| JSON parsing failures | Processing stops | Robust parsing, fallback queues |

## Roadmap

### Version 1.0 (Current Scope)
- Core functionality for .txt emails
- Basic review and export
- Statistical sampling
- Ollama integration

### Version 2.0 (3-6 months)
- Email formats: .eml, .msg, .mbox, .pst
- Attachment text extraction
- Deduplication and threading
- Advanced calibration

### Version 3.0 (6-12 months)  
- PDF support with OCR
- Multi-user collaboration
- Active learning feedback loop
- Cloud deployment option

### Version 4.0 (Future)
- Custom model fine-tuning
- Integration with legal platforms
- Advanced analytics dashboard
- Automated privilege detection

## Compliance & Legal Considerations

- Maintains defensible search methodology
- Complete audit trail for legal proceedings
- Statistical validation for meet-and-confer
- Supports proportionality arguments
- Preserves attorney-client privilege markers
- Enables quality control documentation
- Reproducible results with version tracking

## Conclusion

The Hero of Kindness CPRA Filter represents a practical application of AI technology to solve a pressing legal challenge. By combining local LLMs with robust engineering, statistical validation, and thoughtful UX design, the application empowers legal teams to handle broad CPRA requests efficiently while maintaining the high standards required for legal document production. The focus on accuracy metrics, confidence calibration, and comprehensive audit trails ensures the tool meets both practical and legal requirements for document review.