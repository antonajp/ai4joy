#!/bin/bash
# Improv Olympics - Log Viewer Script
# Convenient access to Cloud Run logs

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-improvOlympics}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="improv-olympics-app"

# Parse arguments
MODE="${1:-tail}"
LIMIT="${2:-50}"

case "${MODE}" in
    tail)
        echo "Tailing logs for ${SERVICE_NAME}..."
        gcloud run services logs tail "${SERVICE_NAME}" \
            --region="${REGION}" \
            --project="${PROJECT_ID}"
        ;;
    read)
        echo "Reading last ${LIMIT} log entries..."
        gcloud run services logs read "${SERVICE_NAME}" \
            --region="${REGION}" \
            --project="${PROJECT_ID}" \
            --limit="${LIMIT}"
        ;;
    errors)
        echo "Reading error logs..."
        gcloud logging read \
            "resource.type=cloud_run_revision \
            AND resource.labels.service_name=${SERVICE_NAME} \
            AND severity>=ERROR" \
            --limit="${LIMIT}" \
            --project="${PROJECT_ID}" \
            --format=json
        ;;
    *)
        echo "Usage: $0 [tail|read|errors] [limit]"
        echo ""
        echo "Examples:"
        echo "  $0 tail          # Tail logs in real-time"
        echo "  $0 read 100      # Read last 100 log entries"
        echo "  $0 errors 50     # Read last 50 error logs"
        exit 1
        ;;
esac
