#!/usr/bin/env python3
"""
Simple test script for /v1/messages endpoint
"""

import requests
import json

# Server URL
BASE_URL = "http://127.0.0.1:8000/"

def main():
    print("Testing /v1/messages endpoint...")

    response = requests.post(
        f"{BASE_URL}/v1/messages",
        headers={"x-api-key": "123"},
        json=json.load(open("error.json"))["payload"]
    )

    print(f"Status: {response.status_code}")
    print(response.text)
    print(f"Response:\n{json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    main()
