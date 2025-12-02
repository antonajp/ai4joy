#!/bin/bash
# Improv Olympics - Manual Deployment Script
# Use this for manual deployments (Cloud Build is preferred for production)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${PROJECT_ID:-coherent-answer-479115-e1}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="improv-olympics-app"
IMAGE_NAME="improv-olympics"
ARTIFACT_REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/improv-app"

# Parse arguments
BUILD_ONLY=false
DEPLOY_ONLY=false
TAG="latest"

while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --deploy-only)
            DEPLOY_ONLY=true
            shift
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--build-only] [--deploy-only] [--tag TAG]"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Improv Olympics - Manual Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Tag: ${TAG}"
echo ""

# Check prerequisites
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker not found${NC}"
    exit 1
fi

# Set project
gcloud config set project "${PROJECT_ID}"

# Configure Docker for Artifact Registry
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Build image
if [ "$DEPLOY_ONLY" = false ]; then
    echo -e "${YELLOW}Building Docker image...${NC}"

    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Ensure buildx builder exists with multi-platform support
    if ! docker buildx inspect multiarch-builder > /dev/null 2>&1; then
        echo -e "${YELLOW}Creating multi-architecture builder...${NC}"
        docker buildx create --name multiarch-builder --use --bootstrap
    else
        docker buildx use multiarch-builder
    fi

    # Build and push in one step using buildx (required for cross-platform)
    echo -e "${YELLOW}Building and pushing image for linux/amd64...${NC}"
    docker buildx build \
        --platform linux/amd64 \
        --build-arg BUILD_DATE="${BUILD_DATE}" \
        --build-arg GIT_COMMIT="${GIT_COMMIT}" \
        --tag "${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${TAG}" \
        --tag "${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${GIT_COMMIT}" \
        --tag "${ARTIFACT_REGISTRY}/${IMAGE_NAME}:latest" \
        --push \
        .

    echo -e "${GREEN}✓ Image built and pushed successfully${NC}"
    echo ""
fi

# Deploy to Cloud Run
if [ "$BUILD_ONLY" = false ]; then
    echo -e "${YELLOW}Deploying to Cloud Run...${NC}"

    gcloud run deploy "${SERVICE_NAME}" \
        --image="${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${TAG}" \
        --region="${REGION}" \
        --platform=managed \
        --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_LOCATION=${REGION},USE_FIRESTORE_AUTH=true" \
        --quiet

    echo -e "${GREEN}✓ Deployed successfully${NC}"
    echo ""

    # Get service URL
    SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
        --region="${REGION}" \
        --format='value(status.url)')

    echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"
    echo ""

    # Test health endpoint
    echo -e "${YELLOW}Testing health endpoint...${NC}"
    if curl -f "${SERVICE_URL}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Health check passed${NC}"
    else
        echo -e "${RED}✗ Health check failed${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
