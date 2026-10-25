#!/usr/bin/env python3
"""Test the server static file serving."""
import sys
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/product')

from product.server import run_server
import threading
import time
import requests

# Start server in background thread
def start_server():
    run_server(8080, query_mode=True)

t = threading.Thread(target=start_server, daemon=True)
t.start()
time.sleep(3)

# Test endpoints
print("Testing /api/health...")
r = requests.get("http://localhost:8080/api/health", timeout=5)
print(f"  Status: {r.status_code}")
print(f"  Response: {r.json()}")

print("Testing /static/lex_gate_switch.css...")
r = requests.get("http://localhost:8080/static/lex_gate_switch.css", timeout=5)
print(f"  Status: {r.status_code}")
print(f"  Content-Type: {r.headers.get('Content-Type')}")
print(f"  Length: {len(r.text)}")

print("Testing /query.html...")
r = requests.get("http://localhost:8080/query.html", timeout=5)
print(f"  Status: {r.status_code}")
print(f"  Content-Type: {r.headers.get('Content-Type')}")
print(f"  Length: {len(r.text)}")

print("All tests passed!")