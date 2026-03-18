#!/usr/bin/env bash
# Generate demo JD data directly to GCS
# Run this in Cloud Shell to populate the Gallery with sample data

set -euo pipefail

PROJECT_ID="${1:-demo0908}"
BUCKET="jackytest007"
PREFIX="generated-jds"

echo "🚀 Generating demo JD data..."
echo "   Project: $PROJECT_ID"
echo "   Bucket: $BUCKET"
echo ""

# Helper function to generate UUID-like ID
generate_id() {
  echo "$(head -c 4 /dev/urandom | od -An -tx1 | tr -d ' ')"
}

# Sample JD 1: Technical Lead
create_sample_jd() {
  local jd_id="$1"
  local title="$2"
  local unit="$3"
  local location="$4"
  
  cat << 'JDCONTENT'
# Technical Lead - Enterprise Systems

## About the Role

We are seeking an experienced Technical Lead to lead our enterprise systems team. You will be responsible for architecting scalable solutions, mentoring junior engineers, and driving technical excellence across our platform.

## Key Responsibilities

- Design and architect enterprise-grade systems
- Lead cross-functional technical initiatives
- Mentor and develop team members
- Ensure code quality and best practices
- Collaborate with product and business teams

## Required Qualifications

- 7+ years of software development experience
- 3+ years in a leadership role
- Strong experience with cloud platforms (GCP, AWS, or Azure)
- Proficiency in Python, Java, or Go
- Experience with microservices architecture
- Excellent communication and leadership skills

## Preferred Qualifications

- Experience with Kubernetes and containerization
- Knowledge of distributed systems
- Experience with CI/CD pipelines
- Background in telecommunications or enterprise software

## Compensation and Benefits

- Competitive salary package
- Health insurance and benefits
- Professional development opportunities
- Flexible working arrangements
- Team building activities
JDCONTENT
}

# Create sample JDs
SAMPLES=(
  "3d5e83c7:Software Engineer:Enterprise Platform:Manila\,_Philippines"
  "c888c0e6:Database Administrator:Cloud Services:Manila\,_Philippines"
  "ef658af6:Senior Engineer:DevOps:Manila\,_Philippines"
)

for sample in "${SAMPLES[@]}"; do
  IFS=':' read -r jd_id title unit location <<< "$sample"
  
  echo "📝 Creating JD: $jd_id ($title)..."
  
  # Create JD content
  jd_content=$(create_sample_jd "$jd_id" "$title" "$unit" "$location")
  
  # Upload to GCS
  blob_path="$PREFIX/jd-$jd_id.md"
  echo "$jd_content" | gcloud storage cp - "gs://$BUCKET/$blob_path" \
    --content-type="text/markdown" 2>&1 | grep -v "Uploading\|Copying" || true
  
  echo "   ✓ Uploaded to gs://$BUCKET/$blob_path"
done

echo ""
echo "📋 Updating index file..."

# Create index JSON
index_json=$(cat << 'INDEXEOF'
{
  "3d5e83c7": {
    "jd_id": "3d5e83c7",
    "role_title": "Software Engineer",
    "business_unit": "Enterprise Platform",
    "location": "Manila, Philippines",
    "created_at": "2026-03-18T10:00:00.000000",
    "tags": ["demo", "platform"]
  },
  "c888c0e6": {
    "jd_id": "c888c0e6",
    "role_title": "Database Administrator",
    "business_unit": "Cloud Services",
    "location": "Manila, Philippines",
    "created_at": "2026-03-18T10:05:00.000000",
    "tags": ["demo", "database"]
  },
  "ef658af6": {
    "jd_id": "ef658af6",
    "role_title": "Senior Engineer",
    "business_unit": "DevOps",
    "location": "Manila, Philippines",
    "created_at": "2026-03-18T10:10:00.000000",
    "tags": ["demo", "devops"]
  }
}
INDEXEOF
)

echo "$index_json" | gcloud storage cp - "gs://$BUCKET/$PREFIX/.index.json" \
  --content-type="application/json" 2>&1 | grep -v "Uploading\|Copying" || true

echo "✓ Index file updated"
echo ""
echo "✅ Demo data generated successfully!"
echo ""
echo "📖 Next steps:"
echo "   1. Go to Cloud Shell Web Preview (port 8080)"
echo "   2. Click on /gallery path"
echo "   3. Refresh the page (Ctrl+R or Cmd+R)"
echo "   4. You should now see the sample JDs in the gallery!"
echo ""
