#!/bin/bash
# Quick start guide for JD Agent with Gallery

echo "🚀 Globe Telecom JD Agent - Quick Test"
echo "======================================"
echo ""

# Default values
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
BASE_URL="http://$HOST:$PORT"

echo "📍 Service URL: $BASE_URL"
echo ""

# 1. Health check
echo "1️⃣ Health Check"
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q "ok"; then
    echo "✅ Service is running"
else
    echo "❌ Service is not responding"
    exit 1
fi
echo ""

# 2. List existing JDs
echo "2️⃣ Existing JDs"
curl -s "$BASE_URL/api/jds" | python3 -c "import sys, json; jds = json.load(sys.stdin); print(f'  Found {len(jds)} JD(s)'); [print(f'  • {jd[\"role_title\"]} ({jd[\"jd_id\"]})') for jd in jds]"
echo ""

# 3. Generate a new JD
echo "3️⃣ Generating new JD..."
RESPONSE=$(curl -s -X POST "$BASE_URL/chat" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Generate a JD for a Cloud Infrastructure Engineer",
    "history": []
  }')

JD_PREVIEW=$(echo "$RESPONSE" | python3 -c "import sys, json; d = json.load(sys.stdin); print(d['reply'][:200])")
echo "  Reply preview: $JD_PREVIEW..."
echo ""

# 4. Wait for storage
sleep 2

# 5. List JDs again
echo "4️⃣ Updated JD List"
JDLIST=$(curl -s "$BASE_URL/api/jds")
COUNT=$(echo "$JDLIST" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "  Total JDs now: $COUNT"
echo ""

# 6. Show URLs
echo "5️⃣ Access URLs"
echo ""
echo "  📋 Chat Interface (Generate JDs):"
echo "     $BASE_URL/"
echo ""
echo "  🎨 JD Gallery (View All JDs):"
echo "     $BASE_URL/gallery"
echo ""
echo "  🔌 API Endpoints:"
echo "     List all JDs:    $BASE_URL/api/jds"
echo "     Get JD detail:   $BASE_URL/api/jds/{jd_id}"
echo ""
echo "✨ System ready!"
