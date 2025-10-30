#!/usr/bin/env python3
"""
PTY Terminal Client for Claude Agent API Server and AWS Bedrock AgentCore

Interactive PTY terminal client that provides full terminal emulation
with support for interactive applications like vim, nano, htop, etc.

Usage:
    python pty_client.py [--url URL] [--cwd CWD]

Environment Variables:
    TOKEN              - JWT Bearer token for authentication (optional)
    SESSION_ID         - Session ID (optional, auto-generated if not provided)
    AGENTCORE_URL      - Full invocations URL (optional, overrides --url and AGENT_ARN)
    AGENT_ARN          - Agent ARN for invocation (optional, auto-constructs URL)
    AWS_REGION         - AWS region (optional, defaults to us-west-2, used with AGENT_ARN)
    WORKLOAD_IDENTITY_TOKEN - Workload identity token (optional, for OAuth operations)

Examples:
    # Basic usage (local server)
    python pty_client.py
    python pty_client.py --url http://localhost:8001
    python pty_client.py --cwd /workspace

    # With authentication
    export TOKEN="your-jwt-token"
    python pty_client.py

    # With full AgentCore URL
    export TOKEN="your-jwt-token"
    export AGENTCORE_URL="https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/your-arn/invocations"
    python pty_client.py

    # With Agent ARN (auto-constructs URL)
    export TOKEN="your-jwt-token"
    export AGENT_ARN="your-agent-arn"
    export AWS_REGION="us-west-2"
    python pty_client.py
"""

import argparse
import sys
import os
import time
import threading
import select
import termios
import tty
import signal
import uuid
import urllib.parse
import json
from typing import Optional

import httpx


class PTYClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        initial_cwd: Optional[str] = None
    ):
        self.initial_cwd = initial_cwd or "/workspace"
        self.session_id = None
        self.running = False
        self.output_seq = 0
        self.old_tty_settings = None
        self.use_streaming = True  # Try SSE streaming first

        # Read environment variables
        self.auth_token = os.environ.get('TOKEN')
        self.session_id_header = os.environ.get('SESSION_ID') or str(uuid.uuid4())
        self.workload_token = os.environ.get('WORKLOAD_IDENTITY_TOKEN')

        # Determine base URL with priority: AGENTCORE_URL > AGENT_ARN > base_url arg > default
        if os.environ.get('AGENTCORE_URL'):
            self.base_url = os.environ.get('AGENTCORE_URL')
        elif os.environ.get('AGENT_ARN'):
            # Construct URL from AGENT_ARN
            agent_arn = os.environ.get('AGENT_ARN')
            region = os.environ.get('AWS_REGION', 'us-west-2')
            encoded_arn = urllib.parse.quote(agent_arn, safe='')
            self.base_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations"
        elif base_url:
            self.base_url = base_url
        else:
            self.base_url = "http://127.0.0.1:8000"

        # For invocations endpoint - use base_url directly if it contains 'invocations',
        # otherwise append '/invocations'
        if 'invocations' in self.base_url:
            self.invocations_url = self.base_url
        else:
            self.invocations_url = f"{self.base_url}/invocations"

    def _get_headers(self):
        """Get HTTP headers for requests."""
        headers = {"Content-Type": "application/json"}

        # Add auth token if available
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        # Add session ID if available
        if self.session_id_header:
            headers["X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"] = self.session_id_header

        # Add workload token if available
        if self.workload_token:
            headers["X-Amzn-Bedrock-AgentCore-Runtime-Workload-AccessToken"] = self.workload_token

        return headers

    def create_session(self) -> bool:
        try:
            with httpx.Client() as client:
                rows, cols = self._get_terminal_size()

                response = client.post(
                    self.invocations_url,
                    headers=self._get_headers(),
                    json={
                        "path": "/terminal/sessions",
                        "method": "POST",
                        "payload": {
                            "rows": rows,
                            "cols": cols,
                            "cwd": self.initial_cwd,
                            "shell": "bash"
                        }
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    self.session_id = data.get("session_id")
                    print(f"✓ Terminal session created: {self.session_id[:8]}...")
                    return True
                else:
                    print(f"✗ Failed to create session: {response.status_code}")
                    print(response.text)
                    return False

        except Exception as e:
            print(f"✗ Error creating session: {e}")
            return False

    def close_session(self):
        if not self.session_id:
            return

        try:
            with httpx.Client() as client:
                client.post(
                    self.invocations_url,
                    headers=self._get_headers(),
                    json={
                        "path": "/terminal/sessions/{session_id}",
                        "method": "DELETE",
                        "path_params": {"session_id": self.session_id}
                    },
                    timeout=5.0
                )
        except:
            pass

    def _get_terminal_size(self):
        try:
            import struct
            import fcntl
            s = struct.pack('HHHH', 0, 0, 0, 0)
            t = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, s)
            rows, cols = struct.unpack('HHHH', t)[:2]
            return rows, cols
        except:
            return 24, 80

    def _setup_raw_mode(self):
        if not sys.stdin.isatty():
            return

        self.old_tty_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())

    def _restore_tty(self):
        if self.old_tty_settings and sys.stdin.isatty():
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_tty_settings)

    def _handle_resize(self, signum, frame):
        if not self.session_id:
            return

        try:
            rows, cols = self._get_terminal_size()
            with httpx.Client() as client:
                client.post(
                    self.invocations_url,
                    headers=self._get_headers(),
                    json={
                        "path": "/terminal/sessions/{session_id}/resize",
                        "method": "POST",
                        "path_params": {"session_id": self.session_id},
                        "payload": {"rows": rows, "cols": cols}
                    },
                    timeout=2.0
                )
        except:
            pass

    def stream_output(self):
        """Stream output using SSE (Server-Sent Events)."""
        try:
            # Construct SSE URL
            if self.agentcore_mode:
                # For agentcore/invocations mode, use invocations endpoint
                stream_url = self.invocations_url
                headers = self._get_headers()
                # We'll use POST with stream path in body
                is_invocations = True
            else:
                # For direct mode, use direct stream endpoint
                stream_url = f"{self.base_url}/terminal/sessions/{self.session_id}/stream"
                headers = self._get_headers()
                is_invocations = False

            # Create streaming request
            with httpx.Client(timeout=None) as client:
                if is_invocations:
                    # For invocations mode, POST with path in body
                    json_data = {
                        "path": "/terminal/sessions/{session_id}/stream",
                        "method": "GET",
                        "path_params": {"session_id": self.session_id}
                    }
                    stream_context = client.stream("POST", stream_url, headers=headers, json=json_data)
                else:
                    # For direct mode, direct GET
                    stream_context = client.stream("GET", stream_url, headers=headers)

                with stream_context as response:
                    if response.status_code != 200:
                        print(f"✗ SSE connection failed: {response.status_code}", file=sys.stderr)
                        print("→ Falling back to polling mode", file=sys.stderr)
                        self.use_streaming = False
                        self.poll_output()
                        return

                    # Process SSE events line by line
                    buffer = ""
                    for line in response.iter_lines():
                        if not self.running:
                            break

                        line = line.strip()

                        # SSE format: "data: {...}"
                        if line.startswith("data: "):
                            try:
                                json_str = line[6:]  # Remove "data: " prefix
                                data = json.loads(json_str)

                                output = data.get("output", "")
                                if output:
                                    sys.stdout.write(output)
                                    sys.stdout.flush()

                                self.output_seq = data.get("seq", self.output_seq)

                                exit_code = data.get("exit_code")
                                if exit_code is not None:
                                    self.running = False
                                    break

                            except json.JSONDecodeError:
                                pass
                            except Exception as e:
                                if self.running:
                                    print(f"\n✗ Stream error: {e}", file=sys.stderr)
                                    break

        except Exception as e:
            print(f"\n✗ Streaming failed: {e}", file=sys.stderr)
            print("→ Falling back to polling mode", file=sys.stderr)
            self.use_streaming = False
            self.poll_output()

    def poll_output(self):
        """Poll output using HTTP requests (fallback mode)."""
        client = httpx.Client(timeout=5.0)
        try:
            while self.running:
                try:
                    response = client.post(
                        self.invocations_url,
                        headers=self._get_headers(),
                        json={
                            "path": "/terminal/sessions/{session_id}/output",
                            "method": "GET",
                            "path_params": {"session_id": self.session_id},
                            "payload": {"seq": self.output_seq}
                        }
                    )

                    if response.status_code == 200:
                        data = response.json()
                        output = data.get("output", "")
                        if output:
                            sys.stdout.write(output)
                            sys.stdout.flush()

                        self.output_seq = data.get("seq", self.output_seq)

                        exit_code = data.get("exit_code")
                        if exit_code is not None:
                            self.running = False
                            break

                    time.sleep(0.05)

                except Exception:
                    if self.running:
                        time.sleep(0.1)
        finally:
            client.close()

    def send_input(self):
        client = httpx.Client(timeout=2.0)
        try:
            while self.running:
                try:
                    if sys.stdin.isatty():
                        readable, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if readable:
                            data = os.read(sys.stdin.fileno(), 1024)
                            if data:
                                try:
                                    client.post(
                                        self.invocations_url,
                                        headers=self._get_headers(),
                                        json={
                                            "path": "/terminal/sessions/{session_id}/input",
                                            "method": "POST",
                                            "path_params": {"session_id": self.session_id},
                                            "payload": {"data": data.decode('utf-8', errors='replace')}
                                        }
                                    )
                                except:
                                    pass
                    else:
                        time.sleep(0.1)

                except Exception:
                    if self.running:
                        time.sleep(0.1)
        finally:
            client.close()

    def run(self):
        print("PTY Terminal Client")
        print(f"Mode: {'AgentCore' if self.agentcore_mode else 'Direct'}")
        print(f"Endpoint: {self.invocations_url}")
        if self.agentcore_mode and self.agentcore_session_id:
            print(f"Session ID: {self.agentcore_session_id}")
        print(f"Working directory: {self.initial_cwd}")

        # Display mode
        mode = "SSE Streaming" if self.use_streaming else "HTTP Polling"
        print(f"Output mode: {mode}")
        print()

        if not self.create_session():
            return 1

        signal.signal(signal.SIGWINCH, self._handle_resize)

        self.running = True

        # Choose output method based on streaming support
        output_method = self.stream_output if self.use_streaming else self.poll_output
        output_thread = threading.Thread(target=output_method, daemon=True)
        input_thread = threading.Thread(target=self.send_input, daemon=True)

        try:
            self._setup_raw_mode()

            output_thread.start()
            input_thread.start()

            while self.running:
                time.sleep(0.1)
                if not output_thread.is_alive() or not input_thread.is_alive():
                    break

        except KeyboardInterrupt:
            print("\r\n^C - Exiting...")
        finally:
            self.running = False
            self._restore_tty()

            output_thread.join(timeout=1.0)
            input_thread.join(timeout=1.0)

            self.close_session()
            print("\nSession closed")

        return 0


def main():
    parser = argparse.ArgumentParser(
        description="PTY Terminal Client for Claude Agent API Server and AWS Bedrock AgentCore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--url",
        help="Base URL of the API server (default: http://127.0.0.1:8000 or from AGENTCORE_URL/AGENT_ARN env vars)"
    )
    parser.add_argument(
        "--cwd",
        help="Initial working directory (default: /workspace)"
    )
    parser.add_argument(
        "--no-streaming",
        action="store_true",
        help="Disable SSE streaming, use HTTP polling instead"
    )

    args = parser.parse_args()

    try:
        client = PTYClient(
            base_url=args.url,
            initial_cwd=args.cwd
        )

        # Override streaming setting if requested
        if args.no_streaming:
            client.use_streaming = False

        return client.run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
