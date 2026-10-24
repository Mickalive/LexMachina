#!/usr/bin/env python3
"""Test script for the query_app server progressive endpoints."""
import subprocess
import time
import requests
import sys

def test_server():
    # Start server
    server = subprocess.Popen(
        [sys.executable, "-u", "product/query_app.py", "--fixture", "--port", "8803"],
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
        resp = requests.get("http://127.0.0.1:8803/api/health", timeout=10)
        print(f"Health: {resp.status_code}")
        
        # Test query start
        print("Testing query start...")
        resp = requests.get("http://127.0.0.1:8803/api/query/start?q=K%C3%BCndigung%20Mietvertrag%20Mietrecht&n=50", timeout=30)
        print(f"Start: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            run_id = data.get('run_id')
            print(f"  Run ID: {run_id}")
            print(f"  Decisions: {len(data.get('bundle', {}).get('decisions', []))}")
            print(f"  Clusters: {len(data.get('bundle', {}).get('clusters', []))}")
            
            # Test expand
            print("Testing query expand...")
            resp = requests.get(f"http://127.0.0.1:8803/api/query/expand?run_id={run_id}&wait_s=30", timeout=60)
            print(f"Expand: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  Decisions: {len(data.get('bundle', {}).get('decisions', []))}")
                print(f"  Clusters: {len(data.get('bundle', {}).get('clusters', []))}")
            
            # Test enrich
            print("Testing query enrich...")
            resp = requests.get(f"http://127.0.0.1:8803/api/query/enrich?run_id={run_id}&wait_s=60", timeout=120)
            print(f"Enrich: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  Decisions: {len(data.get('bundle', {}).get('decisions', []))}")
                print(f"  Clusters: {len(data.get('bundle', {}).get('clusters', []))}")
                print(f"  Answer status: {data.get('bundle', {}).get('answer', {}).get('status')}")
                print(f"  Answer method: {data.get('bundle', {}).get('answer', {}).get('method')}")
                print(f"  Cited: {len(data.get('bundle', {}).get('answer', {}).get('cited_decision_ids', []))}")
        else:
            print(f"  Error: {resp.text[:500]}")
        
        # Read server output
        print("\nServer output:")
        server.terminate()
        try:
            stdout, _ = server.communicate(timeout=5)
            print(stdout[-3000:])
        except subprocess.TimeoutExpired:
            server.kill()
            stdout, _ = server.communicate()
            print(stdout[-3000:])
            
    except Exception as e:
        print(f"Test error: {e}")
        server.terminate()
        try:
            stdout, _ = server.communicate(timeout=5)
            print("Server output:")
            print(stdout[-3000:])
        except subprocess.TimeoutExpired:
            server.kill()
            stdout, _ = server.communicate()
            print("Server output:")
            print(stdout[-3000:])
        return False
    
    return True

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)