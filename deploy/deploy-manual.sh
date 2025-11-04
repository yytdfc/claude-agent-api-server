#!/bin/bash
set -e

# Manual Deployment Script for AWS Amplify
# Use this for direct file upload without Git integration

# Configuration
APP_NAME="claude-agent-web-client"
REGION="us-west-2"
BRANCH_NAME="main"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}AWS Amplify Manual Deployment${NC}"
echo "================================"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Get app ID
APP_ID=$(aws amplify list-apps --region $REGION --query "apps[?name=='$APP_NAME'].appId" --output text)

if [ -z "$APP_ID" ]; then
    echo -e "${RED}Error: Amplify app '$APP_NAME' not found${NC}"
    echo "Please run deploy-amplify.sh first to create the app"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found app: $APP_ID"

# Build the web client
echo -e "${YELLOW}Building web client...${NC}"
cd ../web_client
npm run build
cd ../deploy

echo -e "${GREEN}✓${NC} Build complete"

# Create deployment
echo -e "${YELLOW}Creating deployment...${NC}"

# Check if branch exists
BRANCH_EXISTS=$(aws amplify list-branches \
    --app-id "$APP_ID" \
    --region "$REGION" \
    --query "branches[?branchName=='$BRANCH_NAME'].branchName" \
    --output text || echo "")

if [ -z "$BRANCH_EXISTS" ]; then
    echo -e "${YELLOW}Creating branch: $BRANCH_NAME${NC}"
    aws amplify create-branch \
        --app-id "$APP_ID" \
        --branch-name "$BRANCH_NAME" \
        --region "$REGION" \
        > /dev/null
    echo -e "${GREEN}✓${NC} Branch created"
fi

# Create deployment
DEPLOYMENT=$(aws amplify create-deployment \
    --app-id "$APP_ID" \
    --branch-name "$BRANCH_NAME" \
    --region "$REGION" \
    --output json)

ZIP_UPLOAD_URL=$(echo "$DEPLOYMENT" | jq -r '.zipUploadUrl')
JOB_ID=$(echo "$DEPLOYMENT" | jq -r '.jobId')

echo -e "${GREEN}✓${NC} Deployment created (Job ID: $JOB_ID)"

# Create zip file
echo -e "${YELLOW}Creating deployment package...${NC}"
cd ../web_client/dist
zip -r ../../deploy/deployment.zip . > /dev/null
cd ../../deploy

echo -e "${GREEN}✓${NC} Package created"

# Upload zip file
echo -e "${YELLOW}Uploading to Amplify...${NC}"
curl -X PUT "$ZIP_UPLOAD_URL" \
    -H "Content-Type: application/zip" \
    --data-binary @deployment.zip \
    --silent \
    > /dev/null

echo -e "${GREEN}✓${NC} Upload complete"

# Start deployment
echo -e "${YELLOW}Starting deployment...${NC}"
aws amplify start-deployment \
    --app-id "$APP_ID" \
    --branch-name "$BRANCH_NAME" \
    --job-id "$JOB_ID" \
    --region "$REGION" \
    > /dev/null

echo -e "${GREEN}✓${NC} Deployment started"

# Clean up
rm deployment.zip

# Get app URL
APP_URL=$(aws amplify get-branch \
    --app-id "$APP_ID" \
    --branch-name "$BRANCH_NAME" \
    --region "$REGION" \
    --query "branch.branchName" \
    --output text)

DEFAULT_DOMAIN=$(aws amplify get-app \
    --app-id "$APP_ID" \
    --region "$REGION" \
    --query "app.defaultDomain" \
    --output text)

echo ""
echo -e "${GREEN}Deployment Complete!${NC}"
echo "================================"
echo "App ID: $APP_ID"
echo "Branch: $BRANCH_NAME"
echo "Job ID: $JOB_ID"
echo "URL: https://$BRANCH_NAME.$DEFAULT_DOMAIN"
echo ""
echo "Monitor deployment status:"
echo "https://console.aws.amazon.com/amplify/home?region=$REGION#/$APP_ID/$BRANCH_NAME/$JOB_ID"
