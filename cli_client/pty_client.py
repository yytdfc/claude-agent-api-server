#!/usr/bin/env python3
"""
PTY Terminal Client for Claude Agent API Server

Interactive PTY terminal client that provides full terminal emulation
with support for interactive applications like vim, nano, htop, etc.

Usage:
    python pty_client.py [--url URL] [--cwd CWD]

Examples:
    python pty_client.py
    python pty_client.py --url http://localhost:8001
    python pty_client.py --cwd /workspace
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
from typing import Optional

import httpx


class PTYClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", initial_cwd: Optional[str] = None):
        self.base_url = base_url
        self.invocations_url = f"{base_url}/invocations"
        self.initial_cwd = initial_cwd or "/workspace"
        self.session_id = None
        self.running = False
        self.output_seq = 0

        self.old_tty_settings = None

    def create_session(self) -> bool:
        try:
            with httpx.Client() as client:
                rows, cols = self._get_terminal_size()

                response = client.post(
                    self.invocations_url,
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
        while self.running:
            try:
                with httpx.Client() as client:
                    response = client.post(
                        self.invocations_url,
                        json={
                            "path": "/terminal/sessions/{session_id}/output",
                            "method": "GET",
                            "path_params": {"session_id": self.session_id},
                            "payload": {"seq": self.output_seq}
                        },
                        timeout=5.0
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

            except Exception as e:
                if self.running:
                    time.sleep(0.1)

    def send_input(self):
        while self.running:
            try:
                if sys.stdin.isatty():
                    readable, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if readable:
                        data = os.read(sys.stdin.fileno(), 1024)
                        if data:
                            with httpx.Client() as client:
                                client.post(
                                    self.invocations_url,
                                    json={
                                        "path": "/terminal/sessions/{session_id}/input",
                                        "method": "POST",
                                        "path_params": {"session_id": self.session_id},
                                        "payload": {"data": data.decode('utf-8', errors='replace')}
                                    },
                                    timeout=2.0
                                )
                else:
                    time.sleep(0.1)

            except Exception as e:
                if self.running:
                    time.sleep(0.1)

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
        description="PTY Terminal Client for Claude Agent API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="Base URL of the API server (default: http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--cwd",
        help="Initial working directory (default: /workspace)"
    )

    args = parser.parse_args()

    try:
        client = PTYClient(base_url=args.url, initial_cwd=args.cwd)
        return client.run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
