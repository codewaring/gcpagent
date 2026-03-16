# Globe Telecom JD Agent on Google Cloud

A conversational job description generation agent with persistent storage and public gallery UI. Generate, store, and browse job descriptions using natural language and Gemini AI.

## 🎯 Features

### Interactive Chat Interface
- Natural language JD generation: *"Create a JD for a Senior Data Engineer"*
- Multi-turn conversation support
- English-language UI with real-time Markdown rendering
- Example prompts for quick start

### Public JD Gallery
- Browse all generated job descriptions
- Filter and sort by date, role, or business unit
- Professional UI with responsive design
- Automatic search and discovery

### REST APIs
- `GET /api/jds` - List all generated JDs with metadata
- `GET /api/jds/{id}` - Retrieve full JD details
- `POST /chat` - Generate JDs conversationally
- `GET /health` - Health check for load balancers

### Intelligent Storage
- Automatically saves JDs to Google Cloud Storage
- Metadata indexing for fast retrieval
- Graceful fallback from SDK to gcloud CLI

### Reference Integration
- Dynamically loads example JDs and templates from GCS
- Supports PDF, Markdown, and text documents
- Learns from your company's existing job descriptions

## Project Structure

```
jd-agent-gcp/
├── src/
│   ├── main.py                 # FastAPI app & all endpoints
│   ├── chat_agent.py           # Conversational JD generation
│   ├── jd_agent.py             # Structured API (backward compatible)
│   ├── jd_store.py             # GCS persistence layer
│   ├── reference_store.py      # Dynamic GCS document loading
│   ├── template_store.py       # Template management
│   ├── config.py               # Configuration from env vars
│   ├── chat.html               # Interactive chat UI
│   └── gallery.html            # Public gallery UI
├── templates/
│   └── globe_telecom_default.md  # JD format template
├── scripts/
│   └── deploy_cloud_run.sh     # Cloud Run deployment
├── Dockerfile
├── requirements.txt
├── .env.example
└── IMPLEMENTATION.md           # Architecture & deployment guides
```

## Prerequisites

- **Google Cloud Project**: `demo0908` (or your own)
- **GCS Bucket**: For storing generated JDs and reference documents
- **gcloud CLI**: Installed and authenticated
  ```bash
  gcloud auth application-default login
  ```
- **Python 3.11+** with pip
- **Vertex AI API** enabled in your GCP project

## Quick Start

### 1. Clone and Setup

```bash
cd jd-agent-gcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Authenticate with Google Cloud
gcloud auth application-default login
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings:
#   GOOGLE_CLOUD_PROJECT=demo0908
#   GOOGLE_CLOUD_LOCATION=us-central1
#   REFERENCE_BUCKET=jackytest007
```

Or set via environment:
```bash
export GOOGLE_CLOUD_PROJECT=demo0908
export GOOGLE_CLOUD_LOCATION=us-central1
export MODEL_NAME=gemini-2.5-pro
export REFERENCE_BUCKET=jackytest007
export REFERENCE_ENABLED=true
```

### 3. Run Locally

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8080
```

Open browser:
- **Chat**: http://127.0.0.1:8080/
- **Gallery**: http://127.0.0.1:8080/gallery

## Usage

### Via Chat UI

1. Open http://127.0.0.1:8080/
2. Type a prompt:
   ```
   Generate a JD for a Senior Data Engineer
   ```
3. View results in Markdown
4. Continue conversation for refinement:
   ```
   Remove the educational requirements and add cloud certifications
   ```

### Via Gallery

1. Open http://127.0.0.1:8080/gallery
2. Browse all generated JDs
3. Click to view full details with Markdown rendering

### Via REST API

**List all JDs:**
```bash
curl http://127.0.0.1:8080/api/jds | python -m json.tool
```

Response:
```json
[
  {
    "jd_id": "c888c0e6",
    "role_title": "Database Administrator",
    "business_unit": "Globe Telecom",
    "location": "Manila, Philippines",
    "created_at": "2026-03-16T16:37:06.003588",
    "tags": ["generated", "chat"]
  }
]
```

**Get specific JD:**
```bash
curl http://127.0.0.1:8080/api/jds/c888c0e6 | python -m json.tool
```

**Generate via API:**
```bash
curl -X POST http://127.0.0.1:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Write a Cloud Architect JD for Manila",
    "history": []
  }'
```

## Storage Architecture

Generated JDs are stored in Google Cloud Storage:

```
gs://YOUR_BUCKET/generated-jds/
├── .index.json           # Metadata index (auto-maintained)
├── jd-c888c0e6.md        # Individual JD files (Markdown)
├── jd-ef658af6.md
└── ...
```

- **Automatic indexing**: Metadata is updated whenever a JD is created
- **Fast retrieval**: Index enables quick listing and search
- **Resilient**: Falls back to gcloud CLI if SDK unavailable

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | `demo0908` | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Vertex AI region |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` | Use Vertex AI (vs public API) |
| `MODEL_NAME` | `gemini-2.5-pro` | Gemini model to use |
| `TEMPLATE_DIR` | `templates` | Path to JD templates |
| `REFERENCE_BUCKET` | `jackytest007` | GCS bucket for reference docs |
| `REFERENCE_PREFIX` | `` | Prefix filter in GCS |
| `REFERENCE_ENABLED` | `true` | Enable reference document loading |
| `REFERENCE_MAX_FILES` | `20` | Max reference files to load |
| `REFERENCE_MAX_CHARS_PER_FILE` | `6000` | Truncate files to this length |

## Deployment

### Cloud Run (Recommended)

```bash
# Update scripts/deploy_cloud_run.sh with your project/bucket
chmod +x scripts/deploy_cloud_run.sh
./scripts/deploy_cloud_run.sh
```

Required permissions for service account:
- `Vertex AI User` (for Gemini API)
- `Storage Object Viewer` (for reference documents)
- `Storage Object Creator` (for saving JDs)

### Kubernetes

See `IMPLEMENTATION.md` for Kubernetes YAML manifests.

### Linux VM

See `IMPLEMENTATION.md` for systemd service configuration.

## Architecture

```
┌──────────────┐
│ User Browser │
└──────┬───────┘
       │
       │ HTTP (REST / WebSocket)
       ▼
┌──────────────────────────────┐
│  FastAPI Application         │
│                              │
│  ┌────────────────────────┐  │
│  │ /chat   (UI + API)     │  │  ┌─────────────────┐
│  │ /gallery               │  ├─▶│  Vertex AI      │
│  │ /api/jds               │  │  │  Gemini API     │
│  │ /api/jds/{id}          │  │  └─────────────────┘
│  └────────────────────────┘  │
│           │                  │
│  ┌────────▼────────────────┐ │
│  │ ChatAgent               │ │
│  │ JDAgent                 │ │
│  │ ReferenceStore          │ │
│  │ TemplateStore           │ │
│  │ JDStore                 │ │
│  └────────┬────────────────┘ │
└───────────┼──────────────────┘
            │
            │ gRPC / HTTP
            ▼
    ┌──────────────────────┐
    │ Google Cloud Storage │
    │                      │
    │ • Generated JDs      │
    │ • Reference docs     │
    │ • Metadata index     │
    └──────────────────────┘
```

## Testing

Quick test of all functionality:

```bash
./test_gallery.sh
```

Or individual tests:

```bash
# Health check
curl http://127.0.0.1:8080/health

# List JDs
curl http://127.0.0.1:8080/api/jds

# Generate and store
curl -X POST http://127.0.0.1:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "JD for Senior Software Engineer", "history": []}'
```

## Troubleshooting

### Module not found errors
```bash
# Set PYTHONPATH if running from wrong directory
export PYTHONPATH=/path/to/jd-agent-gcp:$PYTHONPATH
```

### GCS authentication failures
```bash
# Re-authenticate with Application Default Credentials
gcloud auth application-default login
```

### Model not found
```bash
# Verify model availability in your region
gcloud compute machine-types describe standard-1 --zone=us-central1-a
# Supported models: gemini-2.5-pro (us-central1), gemini-2.0-pro
```

See `IMPLEMENTATION.md` for comprehensive troubleshooting guide.

## Next Steps

- Add authentication (OAuth2 / API keys)
- Implement audit logging (Cloud Logging)
- Add role-based access control (RBAC)
- Support for Gemini Enterprise with custom endpoints
- Database persistence for audit trail
- Advanced search and filtering in gallery
- Batch JD generation from CSV

## Documentation

- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** - Full architecture, deployment guides, API reference, troubleshooting
- **[.env.example](.env.example)** - Configuration template
- **[Dockerfile](Dockerfile)** - Container image definition

## License

This project is part of Globe Telecom's HR automation initiative.

---

**Built with ❤️ on Google Cloud**  
Vertex AI Gemini | FastAPI | Google Cloud Storage | Python

