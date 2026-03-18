#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-demo0908}"
REGION="${REGION:-asia-southeast1}"

jd_url=$(gcloud run services describe jd-agent-gcp --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')
recruiter_url=$(gcloud run services describe recruiter-agent --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')

echo "jd-agent-gcp:   $jd_url"
echo "recruiter-agent: $recruiter_url"

echo "[check] public health"
echo -n "jd-agent: "
curl -sS -o /tmp/jd_health.txt -w '%{http_code}\n' "$jd_url/health"
cat /tmp/jd_health.txt

echo -n "recruiter-agent: "
curl -sS -o /tmp/recruiter_health.txt -w '%{http_code}\n' "$recruiter_url/health"
cat /tmp/recruiter_health.txt

echo "[check] public end-to-end rerank"
curl -sS -X POST "$recruiter_url/chat-rerank" \
  -H 'Content-Type: application/json' \
  -d '{"message":"prioritize leadership and stakeholder communication","history":[]}' \
  > /tmp/recruiter_e2e.json

python3 - <<'PY'
import json
p='/tmp/recruiter_e2e.json'
raw=open(p, encoding='utf-8').read()
try:
    data=json.loads(raw)
except Exception:
    print('E2E response is not JSON:')
    print(raw[:500])
    raise SystemExit(1)
print('keys:', sorted(data.keys()))
print('ranked_count:', len(data.get('ranked_candidates', []) or []))
print('reply_preview:', (data.get('reply','')[:180]).replace('\n', ' '))
PY

echo "[done] Cloud Run verification completed"
