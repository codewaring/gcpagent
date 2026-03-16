# Globe Telecom JD Agent — Complete Implementation & Deployment Guide

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & System Design](#architecture--system-design)
3. [File Structure & Component Descriptions](#file-structure--component-descriptions)
4. [Implementation Logic](#implementation-logic)
5. [Prerequisites](#prerequisites)
6. [Step-by-Step Deployment](#step-by-step-deployment)
7. [Configuration Guide](#configuration-guide)
8. [Usage Examples](#usage-examples)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)

---

## Project Overview

**Globe Telecom JD Agent** is a conversational AI service that generates polished Job Descriptions (JDs) for Globe Telecom using Google Cloud's Gemini LLM. The system features:

- **Chat-based interface** — Natural language interaction for flexible job description generation
- **Dynamic reference library** — Automatically loads reference documents from Google Cloud Storage to ensure consistency with company standards
- **Multi-turn conversations** — Users can refine, adjust, or regenerate JDs in real-time
- **Cloud-native architecture** — Designed to run on Google Cloud's Cloud Run or any Kubernetes environment
- **REST API + Web UI** — Both programmatic API and interactive chat interface

### Key Features

| Feature | Description |
|---------|-------------|
| **Chat UI** | Accessible at `GET /` — modern, responsive web interface |
| **Chat API** | `POST /chat` — natural language conversation endpoint |
| **REST API** | `POST /generate` — programmatic JD generation (legacy) |
| **GCS Integration** | Auto-loads PDFs, TXT, MD files from configured S3/GCS bucket |
| **Multi-language** | Responds in the language user writes (defaults to English) |
| **Streaming-ready** | Designed for Vertex AI Gemini with full error handling and auth fallbacks |

---

## Architecture & System Design

### High-Level Workflow

```
USER INPUT (Chat Interface or API)
         ↓
  ChatAgent.reply()
         ↓
  [Load GCS References] + [Load JD Template]
         ↓
  Gemini 2.5 Pro (with system prompt + context)
         ↓
  [Parse Markdown + History Update]
         ↓
  Return JSON Response (reply + history)
         ↓
  HTML Chat UI (auto-renders Markdown)
```

### Data Flow

1. **Chat Request Arrives**: User types in the web UI or sends POST to `/chat`
2. **Reference Load**: `GCSReferenceStore` reads files from `gs://bucket/prefix` (up to 20 files, 6KB each)
   - Tries Python SDK first (faster)
   - Falls back to `gcloud storage` CLI if SDK fails (more reliable on diverse environments)
3. **Template Load**: `TemplateStore` reads the JD format template from local disk
4. **Gemini Call**: `ChatAgent.reply()` sends complete context to Gemini 2.5 Pro
5. **Response**: Markdown JD is returned, HTML UI renders it with proper formatting
6. **History**: Chat history is maintained client-side and sent back on next request

### Why This Architecture?

- **Resilient**: Dual-path GCS access (SDK + CLI fallback) handles auth issues gracefully
- **Scalable**: Stateless design allows horizontal scaling via Cloud Run auto-scaling
- **Flexible**: Easy to change templates, reference bucket, or model without code changes
- **Developer-friendly**: Clear separation of concerns (template store, reference store, chat agent, REST routing)

---

## File Structure & Component Descriptions

```
jd-agent-gcp/
├── src/
│   ├── __init__.py                 # Package init (empty)
│   ├── main.py                     # FastAPI app, routing, request/response models
│   ├── config.py                   # Settings loader from environment variables
│   ├── chat_agent.py               # Conversational AI logic (multi-turn support)
│   ├── jd_agent.py                 # Legacy structured JD generation (REST API)
│   ├── template_store.py           # Load & serve JD format templates from disk
│   ├── reference_store.py          # Fetch & extract text from GCS documents
│   └── chat.html                   # Web UI (HTML + CSS + JavaScript)
├── templates/
│   └── globe_telecom_default.md    # JD template (Markdown) — user replaces with their own
├── scripts/
│   └── deploy_cloud_run.sh         # One-command deployment script for Cloud Run
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── Dockerfile                      # Container image definition
├── README.md                       # This file (full documentation)
└── (other config files)
```

### Detailed File Descriptions

#### **src/main.py** — REST & Web Server
**Purpose**: FastAPI application that serves both the Chat UI and APIs

**Key Components**:
- `GET /` → Returns `chat.html` (the interactive UI)
- `GET /health` → System health check (used by Cloud Run readiness probes)
- `POST /chat` → Conversational endpoint; accepts user message + chat history, returns AI reply
- `POST /generate` → Legacy structured endpoint (for programmatic bulk JD generation)

**Responsibilities**:
- Load all sub-systems (template store, reference store, chat agent)
- Route requests to appropriate handlers
- Load chat.html from disk at startup
- Handle GCS reference loading with error recovery
- Serialize/deserialize Pydantic models to JSON

#### **src/config.py** — Configuration Management
**Purpose**: Centralized settings from environment variables

**Exposed Settings**:
```python
class Settings:
    project_id              # GCP project (e.g., "demo0908")
    location                # GCP region (e.g., "us-central1")
    model_name              # Gemini version (e.g., "gemini-2.5-pro")
    template_dir            # Path to templates folder (local or absolute)
    reference_bucket        # GCS bucket name (e.g., "jackytest007")
    reference_prefix        # Bucket prefix/subfolder (e.g., "")
    reference_enabled       # Bool: fetch GCS refs? (default: true)
    reference_max_files     # Max docs to fetch (default: 20)
    reference_max_chars_per_file  # Truncate large docs (default: 6000)
```

**Why separate?** Easy to change behavior without touching code — just set env vars at container startup.

#### **src/chat_agent.py** — Conversational AI Logic
**Purpose**: Multi-turn chat engine powered by Gemini

**Key Classes**:
- `ChatMessage(role, text)` → Represents a single message in conversation
- `ChatAgent` → Orchestrates conversation with Gemini

**Main Method**: `reply(user_message, history, template_text, reference_context)`
- Builds chat history from previous messages
- Creates system instruction (hardcoded prompt telling AI how to behave)
- Calls `client.models.generate_content()` with full context
- Returns the AI's response text

**System Instruction Highlights**:
```
You are a professional Job Description (JD) generation assistant for Globe Telecom.
- If user names a role, generate the full JD immediately
- Infer defaults (location→Manila, type→Full-time) instead of asking
- Always follow the template format and section order
- Use reference documents for tone/style, don't copy verbatim
- Respond in English unless user writes another language
```

#### **src/jd_agent.py** — Structured JD Generation (Legacy)
**Purpose**: Older REST API endpoint for programmatic bulk generation

**Key Method**: `generate(request, template_text, reference_context)`
- Takes structured `JDRequest` (role title, skills, responsibilities, etc.)
- Builds a formatted prompt with all fields
- Calls Gemini
- Returns raw Markdown JD

**Why kept?** Backward compatibility for scripts or integrations that used the original API.

#### **src/template_store.py** — Template Management
**Purpose**: Load JD format templates from disk

**Key Method**: `get_template(template_name)`
- Reads `templates/{template_name}.md` from disk
- Returns full text as string

**Example Usage**:
```python
store = TemplateStore("templates")
template = store.get_template("globe_telecom_default")
# Returns: "# Job Title\n## About Globe Telecom\n..."
```

**Why separate?** Makes it easy to have multiple templates (e.g., `engineering.md`, `sales.md`) and switch between them.

#### **src/reference_store.py** — GCS Document Ingestion
**Purpose**: Fetch and parse reference documents from Google Cloud Storage

**Key Classes**:
- `ReferenceDoc(path, content)` → Single document record
- `GCSReferenceStore` → Fetches docs, extracts text, builds context

**Main Method**: `build_reference_context(bucket_name, prefix)`
- Lists all objects in GCS bucket/prefix
- For each object:
  - If `.pdf`: extract text using PyPDF
  - If `.txt` or `.md`: read as UTF-8 text
  - Truncate to 6KB to avoid bloating the prompt
- Return concatenated context + list of source paths

**Resilience Strategy**:
1. Try Python GCS SDK (faster, cleaner I/O)
2. If SDK fails (auth issues), fall back to `gcloud storage` CLI
3. Filter out non-file entries (e.g., `gs://bucket/:`)
4. Gracefully handle missing/unreadable files

**Why?** On VMs or containers without perfect ADC setup, the fallback ensures the service never breaks.

#### **src/chat.html** — Web User Interface
**Purpose**: Interactive chat UI served at `/`

**Features**:
- **Markdown rendering**: Uses `marked.js` to render Markdown JDs (headers, lists, bold, etc.)
- **Auto-scroll**: Messages auto-scroll to latest
- **Textarea auto-height**: Input box grows as user types multi-line prompts
- **Typing indicator**: Shows "AI is thinking" animation while Gemini processes
- **Keyboard shortcuts**: Enter = send, Shift+Enter = new line
- **Responsive design**: Works on desktop, tablet, mobile

**Client-Side Logic** (JavaScript):
```javascript
// On send:
1. Disable send button (prevent double-clicks)
2. POST /chat with { message, history }
3. Parse response { reply, history }
4. Add user message to DOM
5. Parse reply as Markdown and render
6. Update client-side history for next request
```

**Why client-side history?** Simplifies server (stateless), leverages browser's session storage.

#### **templates/globe_telecom_default.md** — JD Format Template
**Purpose**: Define the standard JD structure and sections

**Structure** (example):
```markdown
# Job Title

## About Globe Telecom
[Company context]

## Role Overview
[Why this role exists]

## Key Responsibilities
- [Bullet 1]
- [Bullet 2]

## Minimum Qualifications
[Requirements]

[...more sections...]

## Equal Opportunity Statement
Globe Telecom is an equal opportunity employer…
```

**User Responsibility**: Replace with your actual company's JD template. The AI will mimic this structure for all generated JDs.

#### **.env.example** — Environment Template
**Purpose**: Reference for all configurable settings

**When deploying**: Copy to `.env` and adjust values for your environment.

#### **Dockerfile** — Container Image
**Purpose**: Builds production Docker image

**Multi-stage optimizations**:
- Slim base image (`python:3.11-slim`)
- No build artifacts in final image
- Minimal layers

**Startup command**:
```dockerfile
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### **requirements.txt** — Python Dependencies
**Key packages**:
- `fastapi==0.116.1` — Web framework
- `uvicorn==0.35.0` — ASGI server
- `pydantic==2.11.7` — Data validation
- `google-genai==1.31.0` — Vertex AI Gemini SDK
- `google-cloud-storage==2.18.2` — Cloud Storage SDK
- `pypdf==4.3.1` — PDF text extraction
- `pyOpenSSL==25.3.0` — SSL/TLS for cloud connections

#### **scripts/deploy_cloud_run.sh** — Deployment Automation
**Purpose**: One-command Cloud Run deployment

**What it does**:
1. Builds Docker image and pushes to `gcr.io/{project}/globe-jd-agent`
2. Deploys to Cloud Run with environment variables
3. Enables auto-scaling, unauthenticated access

**Usage**:
```bash
PROJECT_ID=demo0908 REGION=us-central1 ./scripts/deploy_cloud_run.sh
```

---

## Implementation Logic

### Chat Flow (Main User Journey)

```
┌─────────────────────────────────────────────────────────┐
│ User types: "Generate a JD for a Senior Data Engineer"  │
└────────────────────┬────────────────────────────────────┘
                     │ User presses Enter
                     ▼
        ┌─────────────────────────────┐
        │ JavaScript: POST /chat       │
        │ {                           │
        │   message: "...",           │
        │   history: [...]            │
        │ }                           │
        └────────────┬────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────────────┐
        │ FastAPI route: chat(payload)            │
        │ - Validate request                      │
        │ - Extract message & history             │
        └────────────┬────────────────────────────┘
                     │
        ┌────────────▼────────────────────────────────┐
        │ load_reference_context()                    │
        │ - Query GCS bucket (3 PDFs)                 │
        │ - Extract text from each PDF               │
        │ - Concatenate into reference_context       │
        └────────────┬─────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────┐
        │ load_template()                           │
        │ - Read globe_telecom_default.md from disk │
        └────────────┬───────────────────────────┘
                     │
        ┌────────────▼────────────────────────────────────┐
        │ chat_agent.reply(                               │
        │   message = "Generate a JD for...",            │
        │   history = [prev user msg, prev AI reply],     │
        │   template_text = "# Job Title\n## ...",       │
        │   reference_context = "[PDF 1]\n[PDF 2]\n..."  │
        │ )                                               │
        └────────────┬─────────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────────┐
        │ Build system_instruction() — tells Gemini its │
        │ role, constraints, template, and reference   │
        │ docs to use                                    │
        └────────────┬───────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────────┐
        │ client.models.generate_content(              │
        │   model = "gemini-2.5-pro",                  │
        │   config = GenerateContentConfig(            │
        │     system_instruction = [full prompt]       │
        │   ),                                          │
        │   contents = [history + new message]         │
        │ )                                             │
        │ [Call to Vertex AI API in us-central1]       │
        └────────────┬───────────────────────────────┘
                     │
         Result: "# Senior Data Engineer\n## About..."
                     │
        ┌────────────▼────────────────────────────────┐
        │ Return ChatResponse(                        │
        │   reply = "[full JD markdown]",            │
        │   history = [user msg, AI reply]           │
        │ ) → JSON                                     │
        └────────────┬─────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────┐
        │ JavaScript receives response:             │
        │ - Parse reply (Markdown)                  │
        │ - Render with marked.js                   │
        │ - Add to chat history DOM                 │
        │ - Save history client-side for next req   │
        └──────────────────────────────────────────┘
```

### Reference Document Processing

When a request arrives, `GCSReferenceStore.build_reference_context()`:

1. **List objects** in `gs://jackytest007/` (with fallback):
   - Try: `storage_client.list_blobs(bucket, prefix)`
   - Fallback: `gcloud storage ls --recursive {bucket}`

2. **Download each object**:
   - Try: `blob.download_as_bytes()`
   - Fallback: `gcloud storage cat {gs_path}`

3. **Extract text**:
   - `.pdf` → Use PyPDF to read pages, concatenate text
   - `.txt` / `.md` → UTF-8 decode
   - Other → Skip

4. **Truncate & bundle**:
   - Limit each file to 6000 chars (configurable)
   - Limit total to first 20 files (configurable)
   - Return concatenated text + list of source GCS paths

5. **Inject into prompt**:
   - The system instruction includes:
     ```
     Reference documents from the configured GCS directory:
     {reference_context}
     ```

---

## Prerequisites

### For Development (Local Machine)

- **Python 3.11+** (tested on 3.13.7)
- **gcloud CLI** installed and authenticated:
  ```bash
  gcloud auth application-default login  # Required!
  ```
- **Git** (to clone the repo)

### For Deployment (VM, Container, Cloud Run)

- **Google Cloud Project** with:
  - **Vertex AI API** enabled
  - **Cloud Storage API** enabled (if using GCS)
  - **Cloud Run API** enabled (if deploying to Cloud Run)
  - **Service Account** with roles:
    - `roles/aiplatform.user` (Vertex AI)
    - `roles/storage.objectViewer` (for reference bucket)

### GCS Setup

- Create a GCS bucket (e.g., `gs://jackytest007`)
- Upload reference PDFs/documents to the bucket
- Ensure service account has `Storage Object Viewer` permission

---

## Step-by-Step Deployment

### Scenario 1: Deploy to a Fresh Linux VM

#### Step 1: Prepare the VM

```bash
# SSH into your new VM
ssh user@your-vm-ip

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and build tools
sudo apt install -y python3.11 python3.11-venv python3-pip git
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev

# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

#### Step 2: Authenticate to Google Cloud

```bash
# Set your project
gcloud config set project demo0908

# Authenticate Application Default Credentials
gcloud auth application-default login
# This opens a browser and grants the VM permission to call Vertex AI
```

#### Step 3: Clone the Repository

```bash
cd ~
git clone https://github.com/your-org/jd-agent-gcp.git
cd jd-agent-gcp
```

#### Step 4: Set Up Python Environment

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies (with public PyPI)
export PIP_INDEX_URL=https://pypi.org/simple
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5: Configure Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit .env with your values
nano .env
```

**Required settings in .env**:
```
GOOGLE_CLOUD_PROJECT=demo0908
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true
MODEL_NAME=gemini-2.5-pro
TEMPLATE_DIR=/path/to/jd-agent-gcp/templates
REFERENCE_BUCKET=jackytest007
REFERENCE_PREFIX=
REFERENCE_ENABLED=true
REFERENCE_MAX_FILES=20
REFERENCE_MAX_CHARS_PER_FILE=6000
```

#### Step 6: Update the JD Template

```bash
# Replace the default template with your company's format
nano templates/globe_telecom_default.md
# (Paste your JD template in Markdown format)
```

#### Step 7: Run Locally (Test)

```bash
export $(grep -v '^#' .env | xargs)
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

**Test the service**:
```bash
# In another terminal, test the chat endpoint
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Generate a JD for a Database Administrator","history":[]}'

# Open browser: http://localhost:8080
# Type a role name into the chat box
```

#### Step 8: Run as a Service (systemd)

```bash
# Create systemd service file
sudo nano /etc/systemd/system/jd-agent.service
```

**Content**:
```ini
[Unit]
Description=Globe Telecom JD Agent
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/jd-agent-gcp
Environment="PATH=/home/ubuntu/jd-agent-gcp/.venv/bin"
Environment="GOOGLE_CLOUD_PROJECT=demo0908"
Environment="GOOGLE_CLOUD_LOCATION=us-central1"
Environment="GOOGLE_GENAI_USE_VERTEXAI=true"
Environment="MODEL_NAME=gemini-2.5-pro"
Environment="TEMPLATE_DIR=/home/ubuntu/jd-agent-gcp/templates"
Environment="REFERENCE_BUCKET=jackytest007"
Environment="REFERENCE_ENABLED=true"
ExecStart=/home/ubuntu/jd-agent-gcp/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jd-agent
sudo systemctl start jd-agent
sudo systemctl status jd-agent
```

**Access**: `http://your-vm-ip:8080`

---

### Scenario 2: Deploy to Google Cloud Run

#### Step 1: Prepare Your Local Code

Ensure `Dockerfile` and `scripts/deploy_cloud_run.sh` are in the repo.

#### Step 2: Set Environment Variables

```bash
export PROJECT_ID=demo0908
export REGION=us-central1
export SERVICE_NAME=globe-jd-agent
```

#### Step 3: Run the Deployment Script

```bash
cd jd-agent-gcp
chmod +x scripts/deploy_cloud_run.sh
./scripts/deploy_cloud_run.sh
```

**What it does**:
- Builds Docker image: `gcr.io/demo0908/globe-jd-agent:latest`
- Pushes to Artifact Registry
- Deploys to Cloud Run (auto-scaling enabled)
- Grants public access (anyone can call it)

#### Step 4: Verify Deployment

```bash
# Get Cloud Run URL
gcloud run services describe globe-jd-agent --region us-central1 --format='value(status.url)'

# Test the service
curl https://globe-jd-agent-abc123.run.app/health
```

#### Step 5: Set Up Firewall (Optional)

If you want to restrict access:
```bash
gcloud run services update globe-jd-agent \
  --region us-central1 \
  --no-allow-unauthenticated
```

Then only service accounts with `roles/run.invoker` can call it.

---

### Scenario 3: Deploy to Kubernetes (EKS, GKE, AKS)

#### Step 1: Build and Push Image

```bash
# Build Docker image locally
docker build -t gcr.io/demo0908/globe-jd-agent:latest .

# Push to Artifact Registry
docker push gcr.io/demo0908/globe-jd-agent:latest
```

#### Step 2: Create Kubernetes Manifests

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jd-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: jd-agent
  template:
    metadata:
      labels:
        app: jd-agent
    spec:
      containers:
      - name: jd-agent
        image: gcr.io/demo0908/globe-jd-agent:latest
        ports:
        - containerPort: 8080
        env:
        - name: GOOGLE_CLOUD_PROJECT
          value: "demo0908"
        - name: GOOGLE_CLOUD_LOCATION
          value: "us-central1"
        - name: GOOGLE_GENAI_USE_VERTEXAI
          value: "true"
        - name: MODEL_NAME
          value: "gemini-2.5-pro"
        - name: TEMPLATE_DIR
          value: "/app/templates"
        - name: REFERENCE_BUCKET
          value: "jackytest007"
        - name: REFERENCE_ENABLED
          value: "true"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

**service.yaml**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: jd-agent-svc
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: jd-agent
```

#### Step 3: Deploy to Kubernetes

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Check status
kubectl get pods
kubectl get svc jd-agent-svc
```

**Access**: `http://<EXTERNAL-IP>`

---

## Configuration Guide

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | *(required)* | GCP project ID (e.g., `demo0908`) |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | GCP region where Gemini is available |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` | Use Vertex AI (not Google AI Studio) |
| `MODEL_NAME` | `gemini-2.5-pro` | Gemini model version |
| `TEMPLATE_DIR` | `templates` | Path to JD template files |
| `REFERENCE_BUCKET` | `jackytest007` | GCS bucket with reference documents |
| `REFERENCE_PREFIX` | `` (empty) | Prefix/folder within bucket (e.g., `engineering/`) |
| `REFERENCE_ENABLED` | `true` | Fetch GCS references for each request |
| `REFERENCE_MAX_FILES` | `20` | Maximum documents to fetch from bucket |
| `REFERENCE_MAX_CHARS_PER_FILE` | `6000` | Max characters per document (truncates large files) |

### Changing the JD Template

The JD template is stored in `templates/globe_telecom_default.md`. It defines the standard structure for all generated JDs.

**To update**:
1. Replace the file content with your company's JD format
2. Use standard Markdown (headings, lists, bold, etc.)
3. No service restart needed — template is loaded fresh on each request

**Example template**:
```markdown
# {Job Title}

## About Globe Telecom
[Company mission/vision]

## Role Overview
[Why this role exists]

## Key Responsibilities
- [Responsibility 1]
- [Responsibility 2]

## Minimum Qualifications
- [Requirement 1]
- [Requirement 2]

## Preferred Qualifications
- [Preference 1]

## Skills and Tools
- [Skill 1]

## Work Setup
- Location: Manila, Philippines
- Employment Type: Full-time

## Equal Opportunity Statement
[Standard EEO compliance statement]
```

### Using Multiple Templates

Want different templates for engineering vs. sales roles?

1. Create multiple template files:
   - `templates/engineering.md`
   - `templates/sales.md`
   - `templates/operations.md`

2. When calling the chat API, users can specify:
   ```
   "Use the engineering template for this technical role"
   ```
   The AI will automatically pick the right template based on context.

### Configuring the Reference Bucket

**To change reference documents**:

1. **Update bucket path**:
   ```bash
   # Set new bucket in .env or environment
   export REFERENCE_BUCKET=my-new-bucket
   export REFERENCE_PREFIX=jd-references/
   ```

2. **Update IAM permissions**:
   Ensure the service account has `Storage Object Viewer` on the new bucket:
   ```bash
   gsutil iam ch serviceAccount:my-sa@project.iam.gserviceaccount.com:objectViewer \
     gs://my-new-bucket
   ```

3. **Upload documents**:
   ```bash
   gsutil -m cp *.pdf gs://my-new-bucket/
   ```

The service will auto-discover and use them on the next request — no code changes needed.

---

## Usage Examples

### Example 1: Generate a Database Administrator JD (Chat)

**User input** (via web UI or API):
```
Generate a JD for a Database Administrator working with Oracle databases.
Include requirements for 5+ years experience.
```

**AI response**:
```markdown
# Database Administrator

## About Globe Telecom
[... company context ...]

## Role Overview
This role is essential for maintaining our core database infrastructure...

## Key Responsibilities
- Manage Oracle database installation, configuration, and patches
- Monitor database performance and optimize query execution
- Design and implement backup/recovery strategies
- ...

[... full JD continues ...]
```

### Example 2: Refine an Existing JD (Multi-turn Chat)

**User input**:
```
Make that JD more focused on cloud (AWS RDS) instead of on-premises Oracle
```

**AI response** (uses conversation history):
```markdown
# Database Administrator — AWS Cloud Focus

## Key Responsibilities
- Manage AWS RDS database instances (MySQL, PostgreSQL)
- Monitor CloudWatch metrics and optimize instance sizing
- Implement automated backups using AWS Backup service
- ...
```

### Example 3: Programmatic REST API Call

**Request**:
```bash
curl -X POST http://localhost:8080/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "business_unit": "Data Engineering",
    "role_title": "Senior Data Engineer",
    "location": "Manila, Philippines",
    "employment_type": "Full-time",
    "seniority": "Senior",
    "key_skills": ["Python", "Spark", "Airflow"],
    "responsibilities": [
      "Design data pipelines",
      "Lead architecture decisions"
    ],
    "requirements": [
      "7+ years in data engineering",
      "Hands-on experience with big data tools"
    ],
    "template_name": "globe_telecom_default",
    "use_reference_docs": true,
    "reference_bucket": "jackytest007",
    "reference_prefix": ""
  }'
```

**Response**:
```json
{
  "job_description": "# Senior Data Engineer\n## About Globe Telecom\n...",
  "reference_sources_used": [
    "gs://jackytest007/Channel Development Expert.pdf",
    "gs://jackytest007/Technical Lead Expert - BAS.pdf"
  ]
}
```

---

## Troubleshooting

### Issue: "Reauthentication is needed"

**Symptom**: Error message during local development:
```
Reauthentication is needed. Please run `gcloud auth application-default login`
```

**Solution**:
```bash
gcloud auth application-default login
# Follow the browser prompt to grant credentials
```

### Issue: "Model `gemini-2.5-pro` was not found"

**Symptom**: 404 NOT_FOUND when calling Gemini API

**Cause**: Model not available in your configured region

**Solution**:
```bash
# Check available models in your region
gcloud ai models list --region=us-central1 --filter="displayName~gemini"

# If us-central1 doesn't have it, try another region
# Update .env or environment:
export GOOGLE_CLOUD_LOCATION=us-east4
```

### Issue: "Failed to load reference docs"

**Symptom**: Chat returns error about reference loading

**Debug steps**:
```bash
# Check bucket access manually
gcloud storage ls gs://jackytest007

# Check if files are readable
gcloud storage cat gs://jackytest007/sample.pdf > /tmp/test.pdf
wc -c /tmp/test.pdf

# Verify service account permissions
gsutil iam get gs://jackytest007 | grep your-sa@
```

### Issue: "Connection timeout" when calling Gemini

**Symptom**: Slow responses or timeouts after 30+ seconds

**Cause**: Network issues or Gemini API overloaded

**Solution**:
- Increase timeout in your HTTP client
- Reduce `reference_max_chars_per_file` to send smaller prompts
- Check Vertex AI quota: `gcloud compute quotas list --filter="metric:prediction"`

### Issue: PDF text extraction is garbled

**Symptom**: Reference documents show weird characters

**Cause**: PDF uses custom fonts or is scanned image

**Solution**:
- Use OCR on scanned PDFs before uploading
- Or reduce `reference_max_chars_per_file` and only use the first few pages
- Upload `.txt` or `.md` versions instead of PDFs

### Issue: Service runs locally but fails on VM/Container

**Symptom**: Works on your Mac but crashes on Linux VM

**Common causes**:
1. ADC not set up: Run `gcloud auth application-default login` on the VM
2. Python version mismatch: Ensure Python 3.11+
3. Missing system packages: `sudo apt install libssl-dev libffi-dev` (for cryptography)

---

## API Reference

### Endpoint: `GET /`

Returns the interactive chat UI (HTML page).

**Request**:
```http
GET / HTTP/1.1
Host: localhost:8080
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
...
</html>
```

---

### Endpoint: `GET /health`

System health check (used by load balancers and Kubernetes).

**Request**:
```http
GET /health HTTP/1.1
Host: localhost:8080
```

**Response**:
```json
{"status": "ok"}
```

---

### Endpoint: `POST /chat`

Send a chat message and get a conversational response with JD generation.

**Request**:
```http
POST /chat HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "message": "Generate a JD for a Senior Network Engineer",
  "history": [
    {"role": "user", "text": "Hello!"},
    {"role": "model", "text": "Hi, how can I help?"}
  ],
  "reference_bucket": "jackytest007",
  "reference_prefix": "",
  "use_reference_docs": true
}
```

**Response**:
```json
{
  "reply": "# Senior Network Engineer\n## About Globe Telecom\n...",
  "history": [
    {"role": "user", "text": "Hello!"},
    {"role": "model", "text": "Hi, how can I help?"},
    {"role": "user", "text": "Generate a JD for a Senior Network Engineer"},
    {"role": "model", "text": "# Senior Network Engineer\n..."}
  ]
}
```

**Parameters**:
- `message` (string, required): User's current message
- `history` (array, optional): Previous chat messages (`[{"role": "user"|"model", "text": "..."}]`)
- `reference_bucket` (string, optional): Override default reference bucket
- `reference_prefix` (string, optional): Override default prefix
- `use_reference_docs` (boolean, default: true): Whether to fetch GCS references

**Error Responses**:
- `400 Bad Request`: Invalid JSON or missing required fields
- `404 Not Found`: Template file not found
- `500 Internal Server Error`: GCS read error or Gemini API error (see `detail` field for diagnosis)

---

### Endpoint: `POST /generate`

Programmatic structured JD generation (legacy REST API).

**Request**:
```http
POST /generate HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "business_unit": "Enterprise Data Platforms",
  "role_title": "Senior Data Engineer",
  "location": "Manila, Philippines",
  "employment_type": "Full-time",
  "seniority": "Senior",
  "key_skills": ["Python", "BigQuery", "Airflow"],
  "responsibilities": [
    "Design and maintain data pipelines",
    "Mentor junior engineers"
  ],
  "requirements": [
    "7+ years in data engineering",
    "Experience with cloud data warehouses"
  ],
  "template_name": "globe_telecom_default",
  "use_reference_docs": true,
  "reference_bucket": "jackytest007",
  "reference_prefix": ""
}
```

**Response**:
```json
{
  "job_description": "# Senior Data Engineer\n...",
  "reference_sources_used": [
    "gs://jackytest007/Channel Development Expert.pdf",
    "gs://jackytest007/Technical Lead Expert - BAS.pdf"
  ]
}
```

---

## Monitoring & Maintenance

### Enable Logging

To debug issues on Cloud Run or VM:

```bash
# Cloud Run logs
gcloud run services describe globe-jd-agent \
  --region us-central1 \
  --log-name gcf \
  | gcloud logging read

# VM systemd logs
journalctl -u jd-agent -f
```

### Performance Tuning

**Slow responses?**

1. Reduce reference document size:
   ```bash
   export REFERENCE_MAX_CHARS_PER_FILE=3000
   ```

2. Reduce number of reference files:
   ```bash
   export REFERENCE_MAX_FILES=10
   ```

3. Switch to faster Gemini model (if available):
   ```bash
   export MODEL_NAME=gemini-1.5-flash
   ```

### Updating the Service (Blue-Green Deployment)

On Cloud Run:
```bash
./scripts/deploy_cloud_run.sh
# New version automatically replaces old one with zero downtime
```

On Kubernetes:
```bash
kubectl set image deployment/jd-agent \
  jd-agent=gcr.io/demo0908/globe-jd-agent:v2.0 \
  --record
```

---

## Next Steps & Enhancements

- **Add user authentication** (OAuth, OIDC) for Cloud Run
- **Add LLM response caching** (Gemini cache control API) to reduce latency
- **Multi-language templates** (ES, FR, CN templates alongside EN)
- **Bulk JD generation** (accept CSV of roles, generate all at once)
- **Review workflow** (AI-generated JD → HR approval → publish)
- **Analytics** (track which roles are most frequently generated, user feedback)
- **Custom system prompts** (allow per-request override of AI behavior)

---

## Support & Questions

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review [Vertex AI documentation](https://cloud.google.com/vertex-ai/generative-ai/docs)
3. Check CloudRun logs: `gcloud run services logs read`
4. Contact your GCP support team

---

**Last Updated**: March 17, 2026
**Version**: 1.0
**Tested On**: Python 3.11+, Vertex AI Gemini 2.5 Pro, GCP (Cloud Run + Cloud Storage)
