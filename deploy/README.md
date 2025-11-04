# AWS Amplify Deployment

This directory contains scripts and configuration for deploying the web client to AWS Amplify.

## Files

- `amplify.yml` - Amplify build configuration
- `deploy-amplify.sh` - Initial setup script (creates Amplify app)
- `deploy-manual.sh` - Manual deployment script (direct file upload)
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

## Deployment Options

### Option 1: GitHub Integration (Recommended)

1. **Initial Setup**
   ```bash
   cd deploy
   chmod +x deploy-amplify.sh
   ./deploy-amplify.sh
   ```

2. **Connect GitHub Repository**
   - Open AWS Amplify Console
   - Select your app
   - Click "Connect branch"
   - Follow GitHub OAuth flow
   - Select repository and branch
   - Amplify will automatically deploy on every push

### Option 2: Manual Deployment

For quick deployments without Git integration:

1. **Initial Setup** (if not done already)
   ```bash
   cd deploy
   chmod +x deploy-amplify.sh
   ./deploy-amplify.sh
   ```

2. **Deploy**
   ```bash
   chmod +x deploy-manual.sh
   ./deploy-manual.sh
   ```

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
2. Run `./deploy-amplify.sh` to sync variables to Amplify
3. Redeploy the app

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

Run `./deploy-amplify.sh` again to sync variables, then trigger a new deployment.

### 404 on page refresh

The `amplify.yml` includes SPA redirect rules. Verify they're applied in Amplify Console under "Rewrites and redirects".

### CORS errors

Ensure your backend server URL in `VITE_DEFAULT_SERVER_URL` allows CORS from the Amplify domain.

## Clean Up

To delete the Amplify app:

```bash
APP_ID=$(aws amplify list-apps --region us-west-2 --query "apps[?name=='claude-agent-web-client'].appId" --output text)
aws amplify delete-app --app-id $APP_ID --region us-west-2
```
