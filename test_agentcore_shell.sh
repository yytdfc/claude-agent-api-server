#!/bin/bash
#
# Test script for shell_client.py with AWS Bedrock AgentCore
#
# This script sets up environment variables and launches the shell client
# in AgentCore mode for testing.
#
# Usage:
#   1. Edit the environment variables below with your credentials
#   2. Run: ./test_agentcore_shell.sh
#

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}AWS Bedrock AgentCore Shell Test${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# ============================================================================
# Configuration - EDIT THESE VALUES
# ============================================================================

# Your AWS Bedrock AgentCore credentials
# export TOKEN="eyJraWQiOiJBZXh1NE1MRXl5TlJWdnR0cXVzajZ1NE0rUE9iQ054QklXYVN0M0JpanE4PSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJlODkxNTNkMC1jMGQxLTcwMTEtMGNkMy02ODdkNzc3NzNkMWIiLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtd2VzdC0yLmFtYXpvbmF3cy5jb21cL3VzLXdlc3QtMl9Tdzh5eUZmQlQiLCJjbGllbnRfaWQiOiIyZDJjcXFqdnBmMWVjcWpnNmdoMXU2Zml2bCIsIm9yaWdpbl9qdGkiOiJiMzVjNWQ3NC1mZDM5LTQxNDQtYmUxNi03MzhjZDNhMjgxYTQiLCJldmVudF9pZCI6ImEzYTViMWJjLWFiODEtNGFiZi1iYmY0LTgyZmQ3NjFiMWQ5OSIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE3NjE2NDQwMjMsImV4cCI6MTc2MTczMDQyMywiaWF0IjoxNzYxNjQ0MDIzLCJqdGkiOiJiYjgzOTlmYS0xNDYyLTQ5MmItYjU4NS00ZDA4YjRjYTkxMmEiLCJ1c2VybmFtZSI6InRlc3R1c2VyIn0.gbaNEct3V_FTVcIA7-H0EyNeVMDsHGkfPmvE5gBeW7aY3JAwf9UPxhpxdp2lFMENtw4CzQHmnVl6f_vhGRq3BVQpRnGElwPkfQFSljphDBWF_ajZ-TeE5P757aAB-J4ImtPBwtK-8M2yJFnA82vE8XZNQWpsMm3q435KrcfN8X8WEAwmXamiOCG9QoYYhfofXOze1bNTBTyl379K5Ew19hjUoNY5NsJpvZaKYoKq_QpLgKBKWQNtlthZcsc2hb8uk5YUu9BmsRjgJ0o6HGyNkIz4rEPASHL3aeyxOYPnq6jMmhoVnGkW5KIgyBiZBjUH54u7CeaxMNuSF0RaTDbkfQ"
export AGENT_ARN="arn:aws:bedrock-agentcore:us-west-2:236995464743:runtime/claude_code_2-2xV3BV3a5H"

# AWS Region (default: us-west-2)
export AWS_REGION="${AWS_REGION:-us-west-2}"


# ============================================================================
# Launch Shell Client
# ============================================================================

echo -e "${GREEN}Launching shell client in AgentCore mode...${NC}"
echo ""
echo -e "${YELLOW}Tip: Type 'exit' or 'quit' to exit, Ctrl+C to interrupt${NC}"
echo ""

# Run the shell client
# python3 cli_client/shell_client.py --agentcore --region "$AWS_REGION" 
python3 cli_client/pty_client.py --agentcore --region "$AWS_REGION" # --agentcore-url http://127.0.0.1:8000/invocations

echo ""
echo -e "${BLUE}Session ended${NC}"
