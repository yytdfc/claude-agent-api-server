#!/usr/bin/env python3
"""
Simple HTTP server for Claude Agent Web Client

Usage:
    python serve.py [port]

Example:
    python serve.py 8080
"""

import http.server
import socketserver
import sys
from pathlib import Path

# Default port
PORT = 8080

# Get port from command line argument if provided
if len(sys.argv) > 1:
    try:
        PORT = int(sys.argv[1])
    except ValueError:
        print(f"Invalid port number: {sys.argv[1]}")
        print("Usage: python serve.py [port]")
        sys.exit(1)

# Change to the web_client directory
web_client_dir = Path(__file__).parent
print(f"Serving from: {web_client_dir}")

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"\n{'='*60}")
    print(f"🚀 Claude Agent Web Client")
    print(f"{'='*60}")
    print(f"\n📡 Server running at: http://localhost:{PORT}")
    print(f"📂 Directory: {web_client_dir}")
    print(f"\n🔗 Open in browser: http://localhost:{PORT}")
    print(f"\n⚠️  Make sure the API server is running at http://127.0.0.1:8000")
    print(f"\n🛑 Press Ctrl+C to stop\n")
    print(f"{'='*60}\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down server...")
        sys.exit(0)
