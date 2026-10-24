#!/usr/bin/env python3
"""Test script for the query_app server."""
import subprocess
import time
import requests
import sys
import signal
import os

def test_server():
    # Start server
    server = subprocess.Popen(
        [sys.executable, "-u", "product/query_app.py", "--fixture", "--port", "8802"],
        cwd="/home/runner/work/LexMachina/LexMachina",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    try:
        # Wait for server to start
        time.sleep(3)
        
        # Check health
        print("Testing health endpoint...")
        resp = requests.get("http://127.0.0.1:8802/api/health", timeout=10)
        print(f"Health: {resp.status_code} - {resp.json()}")
        
        # Test query
        print("Testing query endpoint...")
        resp = requests.get("http://127.0.0.1:8802/api/query/run?q=K%C3%BCndigung%20Mietvertrag%20Mietrecht&n=20", timeout=60)
        print(f"Query: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Decisions: {len(data.get('decisions', []))}")
            print(f"  Clusters: {len(data.get('clusters', []))}")
            print(f"  Answer status: {data.get('answer', {}).get('status')}")
            print(f"  Answer method: {data.get('answer', {}).get('method')}")
        else:
            print(f"  Error: {resp.text[:500]}")
        
        # Read server output
        print("\nServer output:")
        server.terminate()
        try:
            stdout, _ = server.communicate(timeout=5)
            print(stdout[-2000:])
        except subprocess.TimeoutExpired:
            server.kill()
            stdout, _ = server.communicate()
            print(stdout[-2000:])
            
    except Exception as e:
        print(f"Test error: {e}")
        server.terminate()
        try:
            stdout, _ = server.communicate(timeout=5)
            print("Server output:")
            print(stdout[-2000:])
        except subprocess.TimeoutExpired:
            server.kill()
            stdout, _ = server.communicate()
            print("Server output:")
            print(stdout[-2000:])
        return False
    
    return True

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)