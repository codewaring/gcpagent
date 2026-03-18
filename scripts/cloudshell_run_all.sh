#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR="${1:-$HOME/demo0908}"
JD_DIR="$WORKSPACE_DIR/jd-agent-gcp"
RECRUITER_DIR="$WORKSPACE_DIR/recruiter-agent"
SESSION_NAME="demo0908"

if ! command -v tmux >/dev/null 2>&1; then
  echo "[error] tmux is required in Cloud Shell. Install it first: sudo apt-get update && sudo apt-get install -y tmux"
  exit 1
fi

if [[ ! -f "$JD_DIR/.env.cloudshell" || ! -f "$RECRUITER_DIR/.env.cloudshell" ]]; then
  echo "[error] Missing .env.cloudshell files. Run bootstrap first:"
  echo "       bash $JD_DIR/scripts/cloudshell_bootstrap.sh $WORKSPACE_DIR"
  exit 1
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "[info] Existing tmux session '$SESSION_NAME' found. Killing it."
  tmux kill-session -t "$SESSION_NAME"
fi

JD_CMD="cd '$JD_DIR' && source .venv/bin/activate && set -a && source .env.cloudshell && set +a && python -m uvicorn src.main:app --host 0.0.0.0 --port 8080"
RECRUITER_CMD="cd '$RECRUITER_DIR' && source .venv/bin/activate && set -a && source .env.cloudshell && set +a && python -m uvicorn src.main:app --host 0.0.0.0 --port 8090"

tmux new-session -d -s "$SESSION_NAME" -n jd-agent "$JD_CMD"
tmux new-window -t "$SESSION_NAME":2 -n recruiter-agent "$RECRUITER_CMD"

echo "[done] Started local demo services in tmux session: $SESSION_NAME"
echo "[info] Attach logs: tmux attach -t $SESSION_NAME"
echo "[info] Stop all: tmux kill-session -t $SESSION_NAME"
echo "[info] Health checks:"
echo "       curl -sS http://127.0.0.1:8080/health"
echo "       curl -sS http://127.0.0.1:8090/health"
