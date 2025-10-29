#!/usr/bin/env python3
"""
PTY Terminal Client for Claude Agent API Server and AWS Bedrock AgentCore

Interactive PTY terminal client that provides full terminal emulation
with support for interactive applications like vim, nano, htop, etc.

Usage:
    # Local API server mode
    python pty_client.py [--url URL] [--cwd CWD]

    # AgentCore mode (requires TOKEN environment variable)
    python pty_client.py --agentcore --agentcore-url https://your-agentcore-url/invocations
    python pty_client.py --agentcore --region us-west-2

Environment Variables (for AgentCore mode):
    TOKEN        - Bearer token for authentication
    AGENT_ARN    - Agent ARN for invocation (optional if --agentcore-url provided)
    AWS_REGION   - AWS region (optional, can use --region)

Examples:
    # Local mode
    python pty_client.py
    python pty_client.py --url http://localhost:8001
    python pty_client.py --cwd /workspace

    # AgentCore mode with direct URL
    export TOKEN="your-token"
    python pty_client.py --agentcore --agentcore-url https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/your-arn/invocations

    # AgentCore mode with ARN (auto-constructs URL)
    export TOKEN="your-token"
    export AGENT_ARN="your-agent-arn"
    python pty_client.py --agentcore --region us-west-2
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
from typing import Optional

import httpx


class PTYClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        initial_cwd: Optional[str] = None,
        agentcore_mode: bool = False,
        agentcore_url: Optional[str] = None,
        region: Optional[str] = None,
        agent_arn: Optional[str] = None,
        auth_token: Optional[str] = None
    ):
        self.agentcore_mode = agentcore_mode
        self.initial_cwd = initial_cwd or "/workspace"
        self.session_id = None
        self.running = False
        self.output_seq = 0
        self.old_tty_settings = None

        if agentcore_mode:
            # AgentCore mode setup
            self.auth_token = auth_token or os.environ.get('TOKEN')
            if not self.auth_token:
                raise ValueError("TOKEN environment variable is required for AgentCore mode")

            # Use direct URL if provided, otherwise construct from ARN
            if agentcore_url:
                self.base_url = agentcore_url
                self.agent_arn = None
                self.region = None
            else:
                self.agent_arn = agent_arn or os.environ.get('AGENT_ARN')
                self.region = region or os.environ.get('AWS_REGION', 'us-west-2')

                if not self.agent_arn:
                    raise ValueError("AGENT_ARN environment variable or --agentcore-url is required for AgentCore mode")

                # Construct AgentCore URL
                encoded_arn = urllib.parse.quote(self.agent_arn, safe='')
                self.base_url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{encoded_arn}/invocations"

            self.invocations_url = self.base_url
            self.agentcore_session_id = str(uuid.uuid4())
        else:
            # Local API server mode
            self.base_url = base_url or "http://127.0.0.1:8000"
            self.invocations_url = f"{self.base_url}/invocations"
            self.auth_token = None
            self.agentcore_session_id = None

    def _get_headers(self):
        """Get HTTP headers for requests."""
        headers = {"Content-Type": "application/json"}
        if self.agentcore_mode:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            headers["X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"] = self.agentcore_session_id
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

    def poll_output(self):
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
        print(f"Server: {self.base_url}")
        print(f"Working directory: {self.initial_cwd}")
        print()

        if not self.create_session():
            return 1

        signal.signal(signal.SIGWINCH, self._handle_resize)

        self.running = True

        output_thread = threading.Thread(target=self.poll_output, daemon=True)
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

    # Local API server options
    parser.add_argument(
        "--url",
        help="Base URL of the local API server (default: http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--cwd",
        help="Initial working directory (default: /workspace)"
    )

    # AgentCore options
    parser.add_argument(
        "--agentcore",
        action="store_true",
        help="Use AWS Bedrock AgentCore mode (requires TOKEN env var)"
    )
    parser.add_argument(
        "--agentcore-url",
        help="Direct AgentCore invocations URL"
    )
    parser.add_argument(
        "--region",
        help="AWS region for AgentCore (default: us-west-2 or AWS_REGION env var)"
    )
    parser.add_argument(
        "--agent-arn",
        help="Agent ARN for AgentCore (or use AGENT_ARN env var)"
    )

    args = parser.parse_args()

    try:
        if args.agentcore:
            # AgentCore mode
            client = PTYClient(
                initial_cwd=args.cwd,
                agentcore_mode=True,
                agentcore_url=args.agentcore_url,
                region=args.region,
                agent_arn=args.agent_arn
            )
        else:
            # Local API server mode
            client = PTYClient(
                base_url=args.url or "http://127.0.0.1:8000",
                initial_cwd=args.cwd
            )

        return client.run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
