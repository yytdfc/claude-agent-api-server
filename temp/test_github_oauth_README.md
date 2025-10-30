# GitHub OAuth Test Script

Temporary test script for testing GitHub OAuth authentication endpoint.

Uses the same environment variables as `cli_client/pty_client.py` for consistency.

## Prerequisites

1. Server must be running:
   ```bash
   ./serve
   # or
   uv run backend/server.py
   ```

2. Environment variables:
   - `TOKEN` (required): JWT authentication token (contains user_id in 'sub' claim)
   - `WORKLOAD_IDENTITY_TOKEN` (optional): The workload identity token from AgentCore
   - `SESSION_ID` (optional): AgentCore session ID (auto-generated from user_id if not provided)
   - `AGENTCORE_URL` or `SERVER_URL` (optional): Server URL (default: "http://127.0.0.1:8000")

## Usage

### Basic Usage (Test via /invocations)

```bash
# Minimal - only TOKEN required
export TOKEN="your-jwt-token-here"
uv run temp/test_github_oauth.py

# With all optional variables
export TOKEN="your-jwt-token-here"
export WORKLOAD_IDENTITY_TOKEN="your-workload-token-here"
export SESSION_ID="user-123@workspace"
uv run temp/test_github_oauth.py
```

### Test Direct Endpoint

```bash
export TOKEN="your-jwt-token-here"
export WORKLOAD_IDENTITY_TOKEN="your-workload-token-here"
uv run temp/test_github_oauth.py --mode direct
```

### Test Both Endpoints

```bash
export TOKEN="your-jwt-token-here"
export WORKLOAD_IDENTITY_TOKEN="your-workload-token-here"
uv run temp/test_github_oauth.py --mode both
```

### With Custom Server URL

```bash
export TOKEN="your-jwt-token-here"
export AGENTCORE_URL="http://localhost:8080"
# or
export SERVER_URL="http://localhost:8080"
uv run temp/test_github_oauth.py
```

## Expected Output

### Success with Access Token

```
🧪 Testing GitHub OAuth Authentication
================================================================================
Server URL: http://127.0.0.1:8000
User ID: e89153d0-c0d1-7011-0cd3-687d77773d1b
JWT Token: eyJ0eXAiOiJKV1QiLCJhbGciOi...
Workload Token: eyJhbGciOiJSUzI1NiI...

📤 Request Headers:
   Content-Type: application/json
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...
   ...

🔀 Testing via /invocations endpoint...

📥 Response Status: 200

✅ Success! Response:
{
  "access_token": "gho_xxxxxxxxxxxx",
  "token_type": "Bearer",
  "session_uri": "test-user-123",
  "session_status": "COMPLETED",
  "gh_auth": {
    "status": "success",
    "message": "GitHub CLI authenticated successfully"
  }
}

🎉 Access token obtained!
   Token (first 20 chars): gho_xxxxxxxxxxxxxxxx...
   ✅ GitHub CLI authenticated: GitHub CLI authenticated successfully
```

### Authorization Required

```
📥 Response Status: 200

✅ Success! Response:
{
  "authorization_url": "https://github.com/login/oauth/authorize?client_id=...",
  "token_type": "Bearer",
  "session_uri": "test-user-123",
  "session_status": "IN_PROGRESS"
}

🔗 Authorization required!
   Please open this URL in your browser:
   https://github.com/login/oauth/authorize?client_id=...

   Session URI: test-user-123
   Session Status: IN_PROGRESS
```

### Error Cases

```
❌ Request failed with status 400
Error details:
{
  "detail": "Missing x-amzn-bedrock-agentcore-runtime-workload-accesstoken header"
}
```

```
❌ Request failed with status 500
Error details:
{
  "detail": "Failed to get GitHub OAuth token: ValidationException - ..."
}
```

## How It Works

1. Script reads JWT token from `TOKEN` environment variable (required)
2. Script reads optional environment variables:
   - `WORKLOAD_IDENTITY_TOKEN`: Workload token for OAuth operations
   - `SESSION_ID`: AgentCore session ID (auto-generated if not provided)
   - `AGENTCORE_URL` or `SERVER_URL`: Server endpoint URL
3. Extracts user_id from JWT token (for display purposes)
4. Sets HTTP headers (only includes headers if corresponding env vars are set):
   - `Authorization`: Bearer JWT token (always included)
   - `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id`: Session identifier (if SESSION_ID set or auto-generated)
   - `X-Amzn-Bedrock-AgentCore-Runtime-Workload-AccessToken`: Workload token (if WORKLOAD_IDENTITY_TOKEN set)
5. Calls the endpoint (either `/invocations` or `/oauth/github/token` directly)
6. Displays the response and analyzes the result

## Test Modes

- `invocations`: Tests via the unified `/invocations` endpoint (default)
- `direct`: Tests the direct `/oauth/github/token` endpoint
- `both`: Tests both endpoints sequentially

## Environment Variables Summary

All environment variables used by both `pty_client.py` and `test_github_oauth.py`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TOKEN` | Yes | - | JWT authentication token with user_id in 'sub' claim |
| `WORKLOAD_IDENTITY_TOKEN` | No | - | Workload identity token for OAuth operations |
| `SESSION_ID` | No | auto-generated | AgentCore session ID (format: `user_id@workspace` or `user_id@workspace/project`) |
| `AGENTCORE_URL` | No | - | Full AgentCore invocations URL (overrides AGENT_ARN) |
| `SERVER_URL` | No | `http://127.0.0.1:8000` | Server URL (fallback if AGENTCORE_URL not set) |
| `AGENT_ARN` | No | - | Agent ARN (only used in pty_client.py AgentCore mode) |
| `AWS_REGION` | No | `us-west-2` | AWS region (only used in pty_client.py AgentCore mode) |

## Troubleshooting

### "TOKEN environment variable not set"

Set the JWT token environment variable:
```bash
export TOKEN="your-jwt-token-here"
```

### Missing workload token (optional)

The `WORKLOAD_IDENTITY_TOKEN` is optional. If not set, the script will still work but certain OAuth operations may fail:
```bash
export WORKLOAD_IDENTITY_TOKEN="your-token-here"  # Optional
```

### "Could not connect to server"

Make sure the server is running:
```bash
./serve
```

### "Failed to get GitHub OAuth token: ValidationException"

Check that:
1. Workload token is valid and not expired
2. GitHub OAuth provider is configured correctly in AgentCore
3. User has proper permissions

### "gh CLI not installed"

The script will still work and obtain the access token, but won't automatically configure gh CLI. Install gh if needed:
```bash
# macOS
brew install gh

# Linux
# See https://github.com/cli/cli#installation
```

## Clean Up

This is a temporary test script. When done testing:

```bash
rm temp/test_github_oauth.py
rm temp/test_github_oauth_README.md
```
