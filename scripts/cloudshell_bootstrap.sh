#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR="${1:-$HOME/demo0908}"
PROJECT_ID="${PROJECT_ID:-demo0908}"
MODEL_REGION="${MODEL_REGION:-us-central1}"
MODEL_NAME="${MODEL_NAME:-gemini-2.5-pro}"
JD_REPO_URL="${JD_REPO_URL:-https://github.com/codewaring/gcpagent.git}"
RECRUITER_REPO_URL="${RECRUITER_REPO_URL:-https://github.com/codewaring/recruiter-agent.git}"

clone_or_update() {
  local repo_url="$1"
  local target_dir="$2"
  if [[ -d "$target_dir/.git" ]]; then
    echo "[info] Updating $target_dir"
    git -C "$target_dir" fetch origin
    git -C "$target_dir" pull --ff-only origin main || true
  else
    echo "[info] Cloning $repo_url -> $target_dir"
    git clone "$repo_url" "$target_dir"
  fi
}

setup_venv() {
  local dir="$1"
  if [[ ! -d "$dir/.venv" ]]; then
    echo "[info] Creating venv in $dir"
    python3 -m venv "$dir/.venv"
  fi
  # shellcheck disable=SC1091
  source "$dir/.venv/bin/activate"
  python -m pip install --upgrade pip
  python -m pip install -r "$dir/requirements.txt"
  deactivate
}

mkdir -p "$WORKSPACE_DIR"
cd "$WORKSPACE_DIR"

clone_or_update "$JD_REPO_URL" "$WORKSPACE_DIR/jd-agent-gcp"
clone_or_update "$RECRUITER_REPO_URL" "$WORKSPACE_DIR/recruiter-agent"

setup_venv "$WORKSPACE_DIR/jd-agent-gcp"
setup_venv "$WORKSPACE_DIR/recruiter-agent"

cat > "$WORKSPACE_DIR/jd-agent-gcp/.env.cloudshell" <<EOF
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_LOCATION=$MODEL_REGION
GOOGLE_GENAI_USE_VERTEXAI=true
MODEL_NAME=$MODEL_NAME
TEMPLATE_DIR=templates
REFERENCE_BUCKET=jackytest007
APPLICATION_BUCKET=jackytest008
APPLICATION_PREFIX=job-applications
REFERENCE_PREFIX=
REFERENCE_ENABLED=true
EOF

cat > "$WORKSPACE_DIR/recruiter-agent/.env.cloudshell" <<EOF
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_LOCATION=$MODEL_REGION
GOOGLE_GENAI_USE_VERTEXAI=true
MODEL_NAME=$MODEL_NAME
SOURCE_API_BASE_URL=http://127.0.0.1:8080
EOF

echo "[done] Workspace prepared at: $WORKSPACE_DIR"
echo "[next] Open Cloud Shell Editor / Cloud Code at: $WORKSPACE_DIR"
echo "[next] Start both local services with:"
echo "       bash $WORKSPACE_DIR/jd-agent-gcp/scripts/cloudshell_run_all.sh $WORKSPACE_DIR"
