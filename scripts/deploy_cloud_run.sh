#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-demo0908}"
REGION="${REGION:-asia-southeast1}"
SERVICE_NAME="${SERVICE_NAME:-globe-jd-agent}"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"
REFERENCE_BUCKET="${REFERENCE_BUCKET:-jackytest007}"
REFERENCE_PREFIX="${REFERENCE_PREFIX:-}"

# Enable required services once per project.
gcloud services enable run.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com --project "$PROJECT_ID"

gcloud builds submit --tag "$IMAGE" --project "$PROJECT_ID"

gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=true,MODEL_NAME=gemini-2.5-pro,TEMPLATE_DIR=templates,REFERENCE_BUCKET=${REFERENCE_BUCKET},REFERENCE_PREFIX=${REFERENCE_PREFIX},REFERENCE_ENABLED=true,REFERENCE_MAX_FILES=20,REFERENCE_MAX_CHARS_PER_FILE=6000" \
  --project "$PROJECT_ID"

echo "Deployed service: ${SERVICE_NAME}"
