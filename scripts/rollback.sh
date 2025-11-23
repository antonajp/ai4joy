#!/bin/bash
# Improv Olympics - Rollback Script
# Quickly rollback to a previous Cloud Run revision

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PROJECT_ID="${PROJECT_ID:-improvOlympics}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="improv-olympics-app"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Improv Olympics - Rollback${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Set project
gcloud config set project "${PROJECT_ID}"

# List recent revisions
echo -e "${YELLOW}Recent revisions:${NC}"
gcloud run revisions list \
    --service="${SERVICE_NAME}" \
    --region="${REGION}" \
    --limit=5 \
    --format="table(metadata.name,status.conditions[0].status,metadata.creationTimestamp)"

echo ""

# Get current traffic allocation
echo -e "${YELLOW}Current traffic allocation:${NC}"
gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --format="table(status.traffic[].revisionName,status.traffic[].percent)"

echo ""

# Prompt for revision to rollback to
if [ -z "${REVISION:-}" ]; then
    echo -e "${YELLOW}Enter revision name to rollback to (or 'previous' for last stable):${NC}"
    read -r REVISION
fi

# Handle 'previous' shortcut
if [ "${REVISION}" = "previous" ]; then
    REVISION=$(gcloud run revisions list \
        --service="${SERVICE_NAME}" \
        --region="${REGION}" \
        --limit=2 \
        --format="value(metadata.name)" | tail -n 1)
    echo -e "${YELLOW}Rolling back to: ${REVISION}${NC}"
fi

# Confirm rollback
echo ""
echo -e "${RED}WARNING: This will route 100% traffic to revision: ${REVISION}${NC}"
echo -e "${YELLOW}Continue? (yes/no)${NC}"
read -r CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo -e "${YELLOW}Rollback cancelled.${NC}"
    exit 0
fi

# Perform rollback
echo ""
echo -e "${YELLOW}Rolling back...${NC}"

gcloud run services update-traffic "${SERVICE_NAME}" \
    --region="${REGION}" \
    --to-revisions="${REVISION}=100"

echo -e "${GREEN}✓ Rollback complete${NC}"
echo ""

# Verify
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --format='value(status.url)')

echo -e "${YELLOW}Testing rolled-back service...${NC}"
if curl -f "${SERVICE_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Rollback successful!${NC}"
echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"
