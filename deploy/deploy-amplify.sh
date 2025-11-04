#!/bin/bash
set -e

# AWS Amplify Deployment Script
# This script creates and configures an AWS Amplify app for the web client

# Configuration
APP_NAME="claude-agent-web-client"
REGION="us-west-2"
GITHUB_REPO=""  # Set this to your GitHub repository URL (e.g., https://github.com/user/repo)
GITHUB_BRANCH="main"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}AWS Amplify Deployment Script${NC}"
echo "================================"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
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
else
    echo -e "${GREEN}✓${NC} Found existing Amplify app with ID: $APP_ID"
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

# Get app details
APP_URL=$(aws amplify get-app --app-id "$APP_ID" --region "$REGION" --query "app.defaultDomain" --output text)

echo ""
echo -e "${GREEN}Deployment Configuration Complete!${NC}"
echo "================================"
echo "App ID: $APP_ID"
echo "Region: $REGION"
echo "Default Domain: https://$APP_URL"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Connect your GitHub repository in Amplify Console:"
echo "   https://console.aws.amazon.com/amplify/home?region=$REGION#/$APP_ID"
echo ""
echo "2. Or use manual deployment:"
echo "   cd web_client"
echo "   npm run build"
echo "   aws amplify create-deployment --app-id $APP_ID --branch-name main"
echo ""
echo "3. View your app:"
echo "   https://console.aws.amazon.com/amplify/home?region=$REGION#/$APP_ID"
