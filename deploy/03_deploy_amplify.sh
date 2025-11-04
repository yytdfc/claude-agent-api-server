#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.env"

if [ -f "${SCRIPT_DIR}/.agentcore_output" ]; then
    source "${SCRIPT_DIR}/.agentcore_output"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Step 3: Deploy Amplify Frontend${NC}"
echo "========================================"

if [ -z "$AWS_REGION" ]; then
    AWS_REGION=$(aws configure get region)
    AWS_REGION=${AWS_REGION:-us-west-2}
fi

echo "Configuration:"
echo "  App Name: ${AMPLIFY_APP_NAME}"
echo "  Branch: ${AMPLIFY_BRANCH_NAME}"
echo "  Region: ${AWS_REGION}"
echo ""

if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed${NC}"
    echo "Please install jq:"
    echo "  macOS: brew install jq"
    echo "  Ubuntu: sudo apt-get install jq"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo "Please install Node.js (version 18 or later):"
    echo "  macOS: brew install node"
    echo "  Ubuntu: sudo apt-get install nodejs npm"
    echo "  Or visit: https://nodejs.org/"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed${NC}"
    echo "Please install npm:"
    echo "  macOS: brew install node"
    echo "  Ubuntu: sudo apt-get install npm"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}Error: Node.js version 18 or later is required${NC}"
    echo "Current version: $(node --version)"
    echo "Please upgrade Node.js"
    exit 1
fi

echo -e "${GREEN}✓${NC} Node.js $(node --version) and npm $(npm --version) installed"

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✓${NC} AWS CLI configured"

APP_ID=$(aws amplify list-apps --region "$AWS_REGION" --query "apps[?name=='$AMPLIFY_APP_NAME'].appId" --output text 2>/dev/null || echo "")

if [ -z "$APP_ID" ]; then
    echo -e "${YELLOW}Creating new Amplify app: $AMPLIFY_APP_NAME${NC}"

    CREATE_OUTPUT=$(aws amplify create-app \
        --name "$AMPLIFY_APP_NAME" \
        --region "$AWS_REGION" \
        --platform WEB \
        --build-spec file://"${SCRIPT_DIR}/amplify.yml" \
        --custom-rules '[
            {
                "source": "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>",
                "target": "/index.html",
                "status": "200"
            }
        ]' \
        --tags \
            Project="${TAG_PROJECT}" \
        --output json)

    APP_ID=$(echo "$CREATE_OUTPUT" | jq -r '.app.appId')
    echo -e "${GREEN}✓${NC} Created Amplify app with ID: $APP_ID"
    IS_NEW_APP=true
else
    echo -e "${GREEN}✓${NC} Found existing Amplify app with ID: $APP_ID"
    IS_NEW_APP=false
fi

echo -e "${YELLOW}Updating SPA redirect rules...${NC}"
aws amplify update-app \
    --app-id "$APP_ID" \
    --region "$AWS_REGION" \
    --custom-rules '[
        {
            "source": "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>",
            "target": "/index.html",
            "status": "200"
        }
    ]' \
    > /dev/null 2>&1 || echo -e "${YELLOW}Note: Could not update custom rules via CLI${NC}"

echo -e "${GREEN}✓${NC} Redirect rules configured"

echo -e "${YELLOW}Configuring environment variables...${NC}"

ENV_VARS_JSON="{"
if [ -f "${SCRIPT_DIR}/../web_client/.env" ]; then
    while IFS='=' read -r key value; do
        if [[ ! "$key" =~ ^# ]] && [ -n "$key" ]; then
            value=$(echo "$value" | sed 's/^"\(.*\)"$/\1/')
            ENV_VARS_JSON="${ENV_VARS_JSON}\"$key\": \"$value\","
        fi
    done < "${SCRIPT_DIR}/../web_client/.env"
fi

if [ -n "$AGENT_RUNTIME_ARN" ]; then
    ENV_VARS_JSON="${ENV_VARS_JSON}\"VITE_AGENT_RUNTIME_ARN\": \"$AGENT_RUNTIME_ARN\","
fi

ENV_VARS_JSON="${ENV_VARS_JSON%,}}"

aws amplify update-app \
    --app-id "$APP_ID" \
    --region "$AWS_REGION" \
    --environment-variables "$ENV_VARS_JSON" \
    > /dev/null

echo -e "${GREEN}✓${NC} Environment variables configured"

echo -e "${YELLOW}Installing web client dependencies...${NC}"
cd "${SCRIPT_DIR}/../web_client"

if [ ! -d "node_modules" ]; then
    echo "Installing npm packages..."
    npm install
else
    echo "node_modules exists, updating dependencies..."
    npm install
fi

echo -e "${GREEN}✓${NC} Dependencies installed"

echo -e "${YELLOW}Building web client...${NC}"
npm run build
cd "${SCRIPT_DIR}"

echo -e "${GREEN}✓${NC} Build complete"

BRANCH_EXISTS=$(aws amplify list-branches \
    --app-id "$APP_ID" \
    --region "$AWS_REGION" \
    --query "branches[?branchName=='$AMPLIFY_BRANCH_NAME'].branchName" \
    --output text 2>/dev/null || echo "")

if [ -z "$BRANCH_EXISTS" ]; then
    echo -e "${YELLOW}Creating branch: $AMPLIFY_BRANCH_NAME${NC}"
    aws amplify create-branch \
        --app-id "$APP_ID" \
        --branch-name "$AMPLIFY_BRANCH_NAME" \
        --region "$AWS_REGION" \
        > /dev/null
    echo -e "${GREEN}✓${NC} Branch created"
fi

echo -e "${YELLOW}Creating deployment...${NC}"

DEPLOYMENT=$(aws amplify create-deployment \
    --app-id "$APP_ID" \
    --branch-name "$AMPLIFY_BRANCH_NAME" \
    --region "$AWS_REGION" \
    --output json)

ZIP_UPLOAD_URL=$(echo "$DEPLOYMENT" | jq -r '.zipUploadUrl')
JOB_ID=$(echo "$DEPLOYMENT" | jq -r '.jobId')

echo -e "${GREEN}✓${NC} Deployment created (Job ID: $JOB_ID)"

echo -e "${YELLOW}Creating deployment package...${NC}"
cd "${SCRIPT_DIR}/../web_client/dist"
zip -r "${SCRIPT_DIR}/deployment.zip" . > /dev/null
cd "${SCRIPT_DIR}"

echo -e "${GREEN}✓${NC} Package created"

echo -e "${YELLOW}Uploading to Amplify...${NC}"
UPLOAD_RESPONSE=$(curl -X PUT "$ZIP_UPLOAD_URL" \
    -H "Content-Type: application/zip" \
    --data-binary @deployment.zip \
    --write-out "%{http_code}" \
    --silent \
    --output /tmp/amplify_upload_response.txt)

if [ "$UPLOAD_RESPONSE" != "200" ]; then
    echo -e "${RED}Error: Upload failed with HTTP code $UPLOAD_RESPONSE${NC}"
    cat /tmp/amplify_upload_response.txt
    rm /tmp/amplify_upload_response.txt
    exit 1
fi

rm -f /tmp/amplify_upload_response.txt
echo -e "${GREEN}✓${NC} Upload complete (HTTP $UPLOAD_RESPONSE)"

echo -e "${YELLOW}Starting deployment...${NC}"
START_RESULT=$(aws amplify start-deployment \
    --app-id "$APP_ID" \
    --branch-name "$AMPLIFY_BRANCH_NAME" \
    --job-id "$JOB_ID" \
    --region "$AWS_REGION" \
    --output json 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to start deployment${NC}"
    echo "$START_RESULT"
    rm deployment.zip
    exit 1
fi

echo -e "${GREEN}✓${NC} Deployment started successfully"

rm deployment.zip

DEFAULT_DOMAIN=$(aws amplify get-app \
    --app-id "$APP_ID" \
    --region "$AWS_REGION" \
    --query "app.defaultDomain" \
    --output text)

APP_URL="https://${AMPLIFY_BRANCH_NAME}.${DEFAULT_DOMAIN}"

echo ""
echo -e "${GREEN}Step 3 Complete!${NC}"
echo "========================================"
echo "App ID: $APP_ID"
echo "Branch: $AMPLIFY_BRANCH_NAME"
echo "Job ID: $JOB_ID"
echo "URL: $APP_URL"
echo ""
echo "Monitor deployment status:"
echo "https://console.aws.amazon.com/amplify/home?region=$AWS_REGION#/$APP_ID/$AMPLIFY_BRANCH_NAME/$JOB_ID"
echo ""

echo "export AMPLIFY_APP_ID=${APP_ID}" > "${SCRIPT_DIR}/.amplify_output"
echo "export AMPLIFY_APP_URL=${APP_URL}" >> "${SCRIPT_DIR}/.amplify_output"

if [ "$IS_NEW_APP" = true ]; then
    echo -e "${YELLOW}Optional: Connect GitHub for Continuous Deployment${NC}"
    echo "1. Open: https://console.aws.amazon.com/amplify/home?region=$AWS_REGION#/$APP_ID"
    echo "2. Click 'Connect branch'"
    echo "3. Select GitHub and authorize"
    echo "4. Repository: $GITHUB_REPO"
    echo "5. Branch: $AMPLIFY_BRANCH_NAME"
    echo ""
fi
