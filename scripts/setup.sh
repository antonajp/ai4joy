#!/bin/bash
# Improv Olympics - Initial GCP Setup Script
# This script performs one-time setup for the GCP project

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${PROJECT_ID:-improvOlympics}"
REGION="${REGION:-us-central1}"
BILLING_ACCOUNT_ID="${BILLING_ACCOUNT_ID:-}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Improv Olympics - GCP Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found. Please install: https://cloud.google.com/sdk/install${NC}"
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Error: Terraform not found. Please install: https://www.terraform.io/downloads${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites met${NC}"
echo ""

# Authenticate
echo -e "${YELLOW}Authenticating with GCP...${NC}"
gcloud auth application-default login
echo -e "${GREEN}✓ Authenticated${NC}"
echo ""

# Set project
echo -e "${YELLOW}Setting GCP project: ${PROJECT_ID}${NC}"
gcloud config set project "${PROJECT_ID}"
echo -e "${GREEN}✓ Project set${NC}"
echo ""

# Link billing account (if provided)
if [ -n "${BILLING_ACCOUNT_ID}" ]; then
    echo -e "${YELLOW}Linking billing account...${NC}"
    gcloud billing projects link "${PROJECT_ID}" \
        --billing-account="${BILLING_ACCOUNT_ID}"
    echo -e "${GREEN}✓ Billing account linked${NC}"
else
    echo -e "${YELLOW}Warning: BILLING_ACCOUNT_ID not set. Please link manually.${NC}"
    echo "Find billing account: gcloud billing accounts list"
fi
echo ""

# Enable essential APIs (minimal set for Terraform)
echo -e "${YELLOW}Enabling essential APIs...${NC}"
gcloud services enable \
    cloudresourcemanager.googleapis.com \
    serviceusage.googleapis.com \
    cloudbilling.googleapis.com \
    iam.googleapis.com \
    storage.googleapis.com \
    iap.googleapis.com

echo -e "${GREEN}✓ Essential APIs enabled (including IAP for OAuth)${NC}"
echo ""

# Create Terraform state bucket
TERRAFORM_STATE_BUCKET="${PROJECT_ID}-terraform-state"
echo -e "${YELLOW}Creating Terraform state bucket: ${TERRAFORM_STATE_BUCKET}${NC}"

if gsutil ls "gs://${TERRAFORM_STATE_BUCKET}" &> /dev/null; then
    echo -e "${YELLOW}Bucket already exists. Skipping.${NC}"
else
    gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${TERRAFORM_STATE_BUCKET}"
    gsutil versioning set on "gs://${TERRAFORM_STATE_BUCKET}"
    gsutil lifecycle set - "gs://${TERRAFORM_STATE_BUCKET}" <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"numNewerVersions": 5}
      }
    ]
  }
}
EOF
    echo -e "${GREEN}✓ Terraform state bucket created${NC}"
fi
echo ""

# Create build artifacts bucket
BUILD_ARTIFACTS_BUCKET="${PROJECT_ID}-build-artifacts"
echo -e "${YELLOW}Creating build artifacts bucket: ${BUILD_ARTIFACTS_BUCKET}${NC}"

if gsutil ls "gs://${BUILD_ARTIFACTS_BUCKET}" &> /dev/null; then
    echo -e "${YELLOW}Bucket already exists. Skipping.${NC}"
else
    gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUILD_ARTIFACTS_BUCKET}"
    gsutil lifecycle set - "gs://${BUILD_ARTIFACTS_BUCKET}" <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 30}
      }
    ]
  }
}
EOF
    echo -e "${GREEN}✓ Build artifacts bucket created${NC}"
fi
echo ""

# Generate session encryption key
echo -e "${YELLOW}Generating session encryption key...${NC}"
ENCRYPTION_KEY=$(openssl rand -base64 32)
echo "SESSION_ENCRYPTION_KEY=${ENCRYPTION_KEY}" > .env.local
chmod 600 .env.local
echo -e "${GREEN}✓ Encryption key generated and saved to .env.local${NC}"
echo -e "${YELLOW}⚠ Keep .env.local secure! Do not commit to Git.${NC}"
echo ""

# Create terraform.tfvars from example
echo -e "${YELLOW}Creating terraform.tfvars...${NC}"
cd infrastructure/terraform

if [ -f terraform.tfvars ]; then
    echo -e "${YELLOW}terraform.tfvars already exists. Skipping.${NC}"
else
    cp terraform.tfvars.example terraform.tfvars

    # Update with actual values
    sed -i.bak "s|project_id = \"improvOlympics\"|project_id = \"${PROJECT_ID}\"|" terraform.tfvars
    sed -i.bak "s|billing_account_id = \"XXXXXX-YYYYYY-ZZZZZZ\"|billing_account_id = \"${BILLING_ACCOUNT_ID}\"|" terraform.tfvars
    sed -i.bak "s|session_encryption_key = \"REPLACE_WITH_GENERATED_KEY\"|session_encryption_key = \"${ENCRYPTION_KEY}\"|" terraform.tfvars
    rm -f terraform.tfvars.bak

    echo -e "${GREEN}✓ terraform.tfvars created${NC}"
    echo -e "${YELLOW}⚠ Review and customize terraform.tfvars before running 'terraform apply'${NC}"
fi

cd ../..
echo ""

# Initialize Terraform
echo -e "${YELLOW}Initializing Terraform...${NC}"
cd infrastructure/terraform
terraform init
echo -e "${GREEN}✓ Terraform initialized${NC}"
cd ../..
echo ""

# IAP OAuth Brand Setup Instructions
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}IMPORTANT: IAP OAuth Brand Setup${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo -e "${RED}MANUAL STEP REQUIRED:${NC} IAP OAuth Brand creation"
echo ""
echo "Before running 'terraform apply', you must create an OAuth consent screen:"
echo ""
echo "1. Visit the OAuth consent screen:"
echo "   https://console.cloud.google.com/apis/credentials/consent?project=${PROJECT_ID}"
echo ""
echo "2. Configure OAuth consent screen:"
echo "   - User Type: Internal (if using Google Workspace) or External"
echo "   - App name: Improv Olympics"
echo "   - Support email: (your email from terraform.tfvars)"
echo "   - Developer contact: (your email)"
echo "   - Click Save and Continue"
echo ""
echo "3. Skip Scopes section (click Save and Continue)"
echo ""
echo "4. Skip Test Users section if Internal (click Save and Continue)"
echo ""
echo "5. Review and click Back to Dashboard"
echo ""
echo -e "${YELLOW}This step is REQUIRED because Google only allows ONE OAuth brand per project,${NC}"
echo -e "${YELLOW}and it must be created manually via the console first.${NC}"
echo ""
echo "After completing this step, you can proceed with 'terraform apply'."
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Create OAuth consent screen (see instructions above)"
echo "2. Review and customize: infrastructure/terraform/terraform.tfvars"
echo "   - Set iap_support_email (must match OAuth consent screen email)"
echo "   - Add pilot users to iap_allowed_users list"
echo "3. Run: cd infrastructure/terraform && terraform plan"
echo "4. Deploy: terraform apply"
echo "5. Configure DNS nameservers at your domain registrar"
echo "6. Wait for SSL certificate provisioning (15-30 minutes)"
echo "7. Test OAuth flow by visiting https://ai4joy.org"
echo ""
echo -e "${YELLOW}Important files created:${NC}"
echo "  - .env.local (session encryption key - DO NOT COMMIT)"
echo "  - infrastructure/terraform/terraform.tfvars (Terraform config)"
echo ""
echo -e "${YELLOW}OAuth/IAP Documentation:${NC}"
echo "  - See docs/IAP_OAUTH_GUIDE.md for user management"
echo "  - See DEPLOYMENT.md for complete deployment guide"
echo ""
echo -e "${GREEN}Happy deploying!${NC}"
