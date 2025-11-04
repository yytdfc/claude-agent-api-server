#!/bin/bash
set -e

# AWS Amplify Unified Deployment Script
# Creates app if it doesn't exist, updates and deploys if it does

# Configuration
APP_NAME="claude-agent-web-client"
REGION="us-west-2"
BRANCH_NAME="main"
GITHUB_REPO="https://github.com/yytdfc/claude-agent-api-server.git"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}AWS Amplify Unified Deployment Script${NC}"
echo "========================================"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed${NC}"
    echo "Please install jq:"
    echo "  macOS: brew install jq"
    echo "  Ubuntu: sudo apt-get install jq"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✓${NC} AWS CLI configured"

# Check if app already exists
APP_ID=$(aws amplify list-apps --region $REGION --query "apps[?name=='$APP_NAME'].appId" --output text 2>/dev/null || echo "")

if [ -z "$APP_ID" ]; then
    echo -e "${YELLOW}Creating new Amplify app: $APP_NAME${NC}"

    # Create Amplify app
    CREATE_OUTPUT=$(aws amplify create-app \
        --name "$APP_NAME" \
        --region "$REGION" \
        --platform WEB \
        --build-spec file://$(dirname "$0")/amplify.yml \
        --custom-rules '[
            {
                "source": "/<*>",
                "target": "/index.html",
                "status": "200"
            }
        ]' \
        --output json)

    APP_ID=$(echo "$CREATE_OUTPUT" | jq -r '.app.appId')
    echo -e "${GREEN}✓${NC} Created Amplify app with ID: $APP_ID"
    IS_NEW_APP=true
else
    echo -e "${GREEN}✓${NC} Found existing Amplify app with ID: $APP_ID"
    IS_NEW_APP=false
fi

# Set environment variables from .env file
echo -e "${YELLOW}Configuring environment variables...${NC}"

# Read environment variables from web_client/.env
ENV_VARS=$(cat ../web_client/.env | grep -v '^#' | grep -v '^$' | while IFS='=' read -r key value; do
    # Remove quotes from value
    value=$(echo "$value" | sed 's/^"\(.*\)"$/\1/')
    echo "\"$key\": \"$value\""
done | paste -sd ',' -)

# Update environment variables
aws amplify update-app \
    --app-id "$APP_ID" \
    --region "$REGION" \
    --environment-variables "{$ENV_VARS}" \
    > /dev/null

echo -e "${GREEN}✓${NC} Environment variables configured"

# Build the web client
echo -e "${YELLOW}Building web client...${NC}"
cd ../web_client
npm run build
cd ../deploy

echo -e "${GREEN}✓${NC} Build complete"

# Check if branch exists
BRANCH_EXISTS=$(aws amplify list-branches \
    --app-id "$APP_ID" \
    --region "$REGION" \
    --query "branches[?branchName=='$BRANCH_NAME'].branchName" \
    --output text 2>/dev/null || echo "")

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
echo -e "${YELLOW}Creating deployment...${NC}"

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
DEFAULT_DOMAIN=$(aws amplify get-app \
    --app-id "$APP_ID" \
    --region "$REGION" \
    --query "app.defaultDomain" \
    --output text)

echo ""
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================"
echo "App ID: $APP_ID"
echo "Branch: $BRANCH_NAME"
echo "Job ID: $JOB_ID"
echo "URL: https://$BRANCH_NAME.$DEFAULT_DOMAIN"
echo ""
echo "Monitor deployment status:"
echo "https://console.aws.amazon.com/amplify/home?region=$REGION#/$APP_ID/$BRANCH_NAME/$JOB_ID"
echo ""

if [ "$IS_NEW_APP" = true ]; then
    echo -e "${YELLOW}Optional: Connect GitHub for Continuous Deployment${NC}"
    echo "1. Open: https://console.aws.amazon.com/amplify/home?region=$REGION#/$APP_ID"
    echo "2. Click 'Connect branch'"
    echo "3. Select GitHub and authorize"
    echo "4. Repository: $GITHUB_REPO"
    echo "5. Branch: $BRANCH_NAME"
    echo ""
fi
