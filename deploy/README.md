# AWS Amplify Deployment

This directory contains scripts and configuration for deploying the web client to AWS Amplify.

## Files

- `amplify.yml` - Amplify build configuration
- `deploy.sh` - Unified deployment script (creates or updates Amplify app)
- `README.md` - This file

## Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```

2. **Node.js and npm** installed (for building the web client)

3. **jq** installed (for JSON parsing)
   ```bash
   # macOS
   brew install jq

   # Ubuntu/Debian
   sudo apt-get install jq
   ```

## Quick Start

Simply run the deployment script:

```bash
cd deploy
./deploy.sh
```

The script will automatically:
- ✅ Check if Amplify app exists (create if new, update if exists)
- ✅ Configure environment variables from `web_client/.env`
- ✅ Build the web client
- ✅ Create deployment package
- ✅ Upload and deploy to Amplify

## How It Works

### First Time Deployment

When running for the first time:
1. Creates new Amplify app named `claude-agent-web-client`
2. Configures environment variables
3. Creates branch `main`
4. Builds and deploys the web client
5. Provides URL to access the app

### Subsequent Deployments

When app already exists:
1. Updates environment variables (in case `.env` changed)
2. Builds the web client with latest changes
3. Deploys new version to existing app
4. No duplicate apps created

## Environment Variables

Environment variables are automatically loaded from `web_client/.env` during deployment.

Current environment variables:

- `VITE_USE_INVOCATIONS` - API mode (invocations vs direct REST)
- `VITE_TERMINAL_USE_STREAMING` - Terminal output mode (SSE vs polling)
- `VITE_COGNITO_REGION` - AWS Cognito region
- `VITE_COGNITO_USER_POOL_ID` - Cognito User Pool ID
- `VITE_COGNITO_CLIENT_ID` - Cognito Client ID
- `VITE_DEFAULT_SERVER_URL` - Backend API server URL
- `VITE_DEFAULT_CWD` - Default working directory
- `VITE_DEFAULT_MODEL` - Default Claude model
- `VITE_DEFAULT_BACKGROUND_MODEL` - Default background model
- `VITE_DEFAULT_ENABLE_PROXY` - Enable LiteLLM proxy
- `VITE_HIDE_SETTINGS_BUTTON` - Hide settings button

To update environment variables:

1. Edit `web_client/.env`
2. Run `./deploy.sh` (environment variables will be updated automatically)

## GitHub Integration (Optional)

For continuous deployment on every push:

1. After first deployment, open Amplify Console
2. Click "Connect branch"
3. Authorize GitHub
4. Select repository: `https://github.com/yytdfc/claude-agent-api-server.git`
5. Select branch: `main`
6. Amplify will automatically deploy on every push

## Configuration

Edit `deploy.sh` to customize:

```bash
APP_NAME="claude-agent-web-client"  # Amplify app name
REGION="us-west-2"                  # AWS region
BRANCH_NAME="main"                  # Git branch name
GITHUB_REPO="https://github.com/yytdfc/claude-agent-api-server.git"
```

## Custom Domain

To add a custom domain:

1. Open AWS Amplify Console
2. Select your app
3. Go to "Domain management"
4. Click "Add domain"
5. Follow the DNS verification steps

## Monitoring

View deployment status and logs:

```bash
# List all apps
aws amplify list-apps --region us-west-2

# Get app details
aws amplify get-app --app-id <APP_ID> --region us-west-2

# List deployments
aws amplify list-jobs --app-id <APP_ID> --branch-name main --region us-west-2
```

Or use the AWS Console:
https://console.aws.amazon.com/amplify/home?region=us-west-2

## Troubleshooting

### Build fails with "npm not found"

Amplify.yml specifies Node.js version. Check that your build uses a compatible version.

### Environment variables not updating

Run `./deploy.sh` again - it automatically syncs environment variables from `.env` file.

### 404 on page refresh

The `amplify.yml` includes SPA redirect rules. Verify they're applied in Amplify Console under "Rewrites and redirects".

### CORS errors

Ensure your backend server URL in `VITE_DEFAULT_SERVER_URL` allows CORS from the Amplify domain.

### Deployment stuck or failed

Check deployment logs in Amplify Console or run:
```bash
aws amplify get-job --app-id <APP_ID> --branch-name main --job-id <JOB_ID> --region us-west-2
```

## Clean Up

To delete the Amplify app:

```bash
APP_ID=$(aws amplify list-apps --region us-west-2 --query "apps[?name=='claude-agent-web-client'].appId" --output text)
aws amplify delete-app --app-id $APP_ID --region us-west-2
```
