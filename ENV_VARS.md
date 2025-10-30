# Environment Variables Reference

This document describes all environment variables used across the Claude Agent API Server client tools.

## Overview

All client tools (`cli_client/pty_client.py`, `temp/test_github_oauth.py`, web client) use a consistent set of environment variables. This allows you to set variables once and use them across all tools.

## Environment Variables

### Authentication & Identity

#### `TOKEN` (Optional/Required)
- **Type**: JWT token string
- **Required**: Yes for AgentCore mode, Optional for local mode with authentication
- **Description**: JWT Bearer token for authentication. Contains `user_id` in the 'sub' claim.
- **Example**:
  ```bash
  export TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
  ```

#### `WORKLOAD_IDENTITY_TOKEN` (Optional)
- **Type**: Token string
- **Required**: No
- **Description**: Workload identity token from AWS Bedrock AgentCore, required for OAuth operations like GitHub authentication.
- **Example**:
  ```bash
  export WORKLOAD_IDENTITY_TOKEN="eyJhbGciOiJSUzI1NiIsImtpZCI6..."
  ```

#### `SESSION_ID` (Optional)
- **Type**: String
- **Required**: No (auto-generated if not provided)
- **Description**: AgentCore session ID. Format: `user_id@workspace` or `user_id@workspace/project_name`
- **Default**: Auto-generated from user_id in JWT token
- **Example**:
  ```bash
  export SESSION_ID="user-123@workspace"
  export SESSION_ID="user-123@workspace/my-project"
  ```

### Server URLs

#### `AGENTCORE_URL` (Optional)
- **Type**: URL string
- **Required**: No
- **Description**: Base URL WITHOUT `/invocations` suffix. Takes priority over `AGENT_ARN` and `SERVER_URL`.
- **Important**: Do NOT include `/invocations` suffix - client adds it automatically
- **Example**:
  ```bash
  # Correct (no /invocations)
  export AGENTCORE_URL="https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/arn%3Aaws%3Abedrock%3A..."

  # Incorrect (has /invocations)
  export AGENTCORE_URL="https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/arn%3Aaws%3Abedrock%3A.../invocations"
  ```

#### `SERVER_URL` (Optional)
- **Type**: URL string
- **Required**: No
- **Default**: `http://127.0.0.1:8000`
- **Description**: Server URL for local mode or custom deployments. Used as fallback if `AGENTCORE_URL` not set.
- **Example**:
  ```bash
  export SERVER_URL="http://localhost:8080"
  ```

#### `AGENT_ARN` (Optional)
- **Type**: ARN string
- **Required**: No (only if constructing AgentCore URL)
- **Description**: AWS Bedrock Agent ARN. Used by `pty_client.py` to auto-construct AgentCore URL.
- **Example**:
  ```bash
  export AGENT_ARN="arn:aws:bedrock:us-west-2:123456789012:agent/ABCDEFGHIJ"
  ```

#### `AWS_REGION` (Optional)
- **Type**: AWS region string
- **Required**: No
- **Default**: `us-west-2`
- **Description**: AWS region used when constructing URL from `AGENT_ARN`.
- **Example**:
  ```bash
  export AWS_REGION="us-east-1"
  ```

## URL Convention

**Important**: All URLs should be provided **WITHOUT** the `/invocations` suffix.

- ✅ Correct: `http://127.0.0.1:8000`
- ❌ Incorrect: `http://127.0.0.1:8000/invocations`

The client tools automatically append `/invocations` when making API calls.

## URL Priority Order

Tools determine the server URL using this priority:

1. **AGENTCORE_URL** (if set) - highest priority
2. **AGENT_ARN** (if set) - constructs URL using AWS_REGION
3. **--url** command line argument (pty_client.py only)
4. **SERVER_URL** (if set)
5. **Default**: `http://127.0.0.1:8000` - lowest priority

All URLs in the priority chain follow the convention of NOT including `/invocations`.

## Usage Examples

### Local Development (No Auth)

```bash
# No environment variables needed
uv run cli_client/pty_client.py
uv run temp/test_github_oauth.py
```

### Local Development (With Auth)

```bash
export TOKEN="your-jwt-token"
uv run cli_client/pty_client.py
uv run temp/test_github_oauth.py
```

### Local Development (Custom Port)

```bash
export SERVER_URL="http://localhost:8080"
uv run cli_client/pty_client.py
```

### AgentCore Deployment (Direct URL)

```bash
export TOKEN="your-jwt-token"
# Note: URL WITHOUT /invocations suffix
export AGENTCORE_URL="https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/your-arn"
export WORKLOAD_IDENTITY_TOKEN="your-workload-token"  # For OAuth operations

uv run cli_client/pty_client.py
uv run temp/test_github_oauth.py
```

### AgentCore Deployment (With ARN)

```bash
export TOKEN="your-jwt-token"
export AGENT_ARN="arn:aws:bedrock:us-west-2:123456789012:agent/ABCDEFGHIJ"
export AWS_REGION="us-west-2"
export WORKLOAD_IDENTITY_TOKEN="your-workload-token"

uv run cli_client/pty_client.py
```

### With Custom Session ID

```bash
export TOKEN="your-jwt-token"
export SESSION_ID="user-123@workspace/my-project"
uv run cli_client/pty_client.py
```

### Full Configuration

```bash
export TOKEN="your-jwt-token"
export WORKLOAD_IDENTITY_TOKEN="your-workload-token"
export SESSION_ID="user-123@workspace/my-project"
# Note: URL WITHOUT /invocations suffix
export AGENTCORE_URL="https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/your-arn"

# Now all tools will use these settings
uv run cli_client/pty_client.py
uv run temp/test_github_oauth.py
```

## Header Mapping

Environment variables are mapped to HTTP headers as follows:

| Environment Variable | HTTP Header | Always Included? |
|---------------------|-------------|------------------|
| `TOKEN` | `Authorization: Bearer <token>` | Only if TOKEN is set |
| `SESSION_ID` | `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` | Only if SESSION_ID is set or auto-generated |
| `WORKLOAD_IDENTITY_TOKEN` | `X-Amzn-Bedrock-AgentCore-Runtime-Workload-AccessToken` | Only if WORKLOAD_IDENTITY_TOKEN is set |

## Tools Using These Variables

- **cli_client/pty_client.py**: PTY terminal client
- **temp/test_github_oauth.py**: GitHub OAuth test script
- **web_client**: Web UI (uses TOKEN for authentication)

## Best Practices

1. **Security**: Never commit tokens to git. Use environment variables or secrets management.

2. **Development**: Create a `.env` file (gitignored) for local development:
   ```bash
   # .env
   TOKEN=your-dev-token
   SERVER_URL=http://localhost:8000
   ```

3. **Production**: Use proper secrets management (AWS Secrets Manager, etc.)

4. **Testing**: Set minimal required variables:
   ```bash
   export TOKEN="test-token"
   # Other variables auto-generated or use defaults
   ```

5. **Reusability**: Set variables once in your shell session to use across all tools:
   ```bash
   # Set once
   export TOKEN="..."
   export AGENTCORE_URL="..."

   # Use with any tool
   uv run cli_client/pty_client.py
   uv run temp/test_github_oauth.py
   ```

## Troubleshooting

### "TOKEN environment variable not set" (AgentCore mode)
```bash
export TOKEN="your-jwt-token"
```

### Headers not being sent
Check if environment variables are actually set:
```bash
echo $TOKEN
echo $SESSION_ID
echo $WORKLOAD_IDENTITY_TOKEN
```

### Wrong URL being used
Check priority order. `AGENTCORE_URL` overrides everything:
```bash
unset AGENTCORE_URL  # If you want to use SERVER_URL instead
```

### Session ID format issues
Ensure format is correct:
```bash
# Correct formats:
export SESSION_ID="user-id@workspace"
export SESSION_ID="user-id@workspace/project-name"

# Incorrect:
export SESSION_ID="just-a-random-string"
```
