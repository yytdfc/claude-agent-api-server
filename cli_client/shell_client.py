#!/usr/bin/env python3
"""
Shell CLI Client for Claude Agent API Server

Interactive shell client that connects to the server via invocations API
and executes commands with streaming output using httpx.

Usage:
    python shell_client.py [--url URL] [--cwd CWD]

Examples:
    python shell_client.py
    python shell_client.py --url http://localhost:8000
    python shell_client.py --cwd /workspace
"""

import argparse
import sys
import json
from typing import Optional

import httpx


class ShellClient:
    """Interactive shell client using invocations API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", initial_cwd: Optional[str] = None):
        self.base_url = base_url
        self.invocations_url = f"{base_url}/invocations"
        self.current_cwd = initial_cwd or self._get_initial_cwd()
        self.running = True

    def _get_initial_cwd(self) -> str:
        """Get initial working directory from server."""
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.invocations_url,
                    json={
                        "path": "/shell/cwd",
                        "method": "GET"
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("cwd", "/workspace")
        except Exception as e:
            print(f"Warning: Could not get initial cwd: {e}")
        return "/workspace"

    def execute_command(self, command: str) -> None:
        """Execute a shell command with streaming output."""
        try:
            with httpx.Client() as client:
                # Stream the command execution
                with client.stream(
                    "POST",
                    self.invocations_url,
                    json={
                        "path": "/shell/execute",
                        "method": "POST",
                        "payload": {
                            "command": command,
                            "cwd": self.current_cwd
                        }
                    },
                    timeout=300.0  # 5 minutes timeout for long-running commands
                ) as response:
                    if response.status_code != 200:
                        print(f"Error: {response.status_code} {response.reason_phrase}")
                        return

                    # Stream output line by line
                    for chunk in response.iter_bytes():
                        if chunk:
                            print(chunk.decode('utf-8', errors='replace'), end='', flush=True)

                # Update current directory if it was a cd command
                if command.strip().startswith('cd '):
                    self._update_cwd()

        except httpx.TimeoutException:
            print("\nError: Command execution timed out")
        except httpx.RequestError as e:
            print(f"\nError: Failed to execute command: {e}")
        except KeyboardInterrupt:
            print("\n^C")
        except Exception as e:
            print(f"\nError: {e}")

    def _update_cwd(self) -> None:
        """Update current working directory from server."""
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.invocations_url,
                    json={
                        "path": "/shell/cwd",
                        "method": "GET"
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    self.current_cwd = data.get("cwd", self.current_cwd)
        except Exception as e:
            print(f"Warning: Could not update cwd: {e}")

    def run(self) -> None:
        """Run the interactive shell."""
        print("Shell CLI Client")
        print(f"Connected to: {self.base_url}")
        print(f"Working directory: {self.current_cwd}")
        print("Type 'exit' or 'quit' to exit, Ctrl+C to interrupt command")
        print()

        while self.running:
            try:
                # Show prompt
                prompt = f"\033[1;36m{self.current_cwd}\033[0m $ "
                command = input(prompt).strip()

                # Handle empty command
                if not command:
                    continue

                # Handle exit commands
                if command.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break

                # Execute command
                self.execute_command(command)

            except KeyboardInterrupt:
                print("\n^C")
                print("Type 'exit' or 'quit' to exit")
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive shell client for Claude Agent API Server"
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="Base URL of the API server (default: http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--cwd",
        help="Initial working directory"
    )

    args = parser.parse_args()

    # Create and run client
    client = ShellClient(base_url=args.url, initial_cwd=args.cwd)
    client.run()


if __name__ == "__main__":
    main()
