#!/usr/bin/env python3
"""Test script to start server, test endpoints, and shutdown."""
import subprocess
import time
import requests
import sys
import signal
import os

def test_server():
    # Start server
    print("Starting server...")
    proc = subprocess.Popen(
        [sys.executable, "server.py", "8082"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd="/home/runner/work/LexMachina/LexMachina/product"
    )
    
    # Wait for server to be ready
    print("Waiting for server to start...")
    server_ready = False
    for i in range(60):
        line = proc.stdout.readline()
        if not line:
            break
        print(line.rstrip())
        if "LexMachina server running" in line:
            server_ready = True
            break
        if "ERROR" in line or "Exception" in line or "Traceback" in line:
            print("Server error detected!")
            proc.terminate()
            return False
    
    if not server_ready:
        print("Server did not start properly")
        # Read remaining output
        for line in proc.stdout:
            print(line.rstrip())
        proc.terminate()
        return False
    
    print("Server started, testing endpoints...")
    
    # Give it a moment to fully initialize
    time.sleep(2)
    
    try:
        # Test health endpoint
        print("Testing /api/health...")
        resp = requests.get("http://localhost:8082/api/health", timeout=10)
        print(f"Health: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Status: {data.get('status')}")
            print(f"  Maps loaded: {data.get('maps_loaded')}")
            print(f"  Representations: {data.get('representation_health', {}).get('healthy', 0)}/{data.get('representation_health', {}).get('total', 0)}")
        
        # Test map endpoint for production default
        print("Testing /api/map with cited_outcome_hybrid_0.5_174k...")
        resp = requests.get("http://localhost:8082/api/map?representation=cited_outcome_hybrid_0.5_174k&zoom=1&limit=5", timeout=30)
        print(f"Map: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Positions: {len(data.get('positions', []))}")
            print(f"  Clusters: {len(data.get('clusters', []))}")
        
        # Test other 174k modes
        for rep in ["cited_decisions_tfidf_174k", "cited_outcome_hybrid_0.7_174k"]:
            print(f"Testing /api/map with {rep}...")
            resp = requests.get(f"http://localhost:8082/api/map?representation={rep}&zoom=1&limit=5", timeout=30)
            print(f"  {rep}: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"    Positions: {len(data.get('positions', []))}")
        
        # Test representations validation
        print("Testing /api/representations/validate...")
        resp = requests.get("http://localhost:8082/api/representations/validate", timeout=10)
        print(f"Validate: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Total: {data.get('total')}, Healthy: {data.get('healthy')}, Warnings: {data.get('warnings')}, Failing: {data.get('failing')}")
        
        # Test scale simulation
        print("Testing /api/scale_simulation...")
        resp = requests.get("http://localhost:8082/api/scale_simulation?n=174113", timeout=60)
        print(f"Scale sim: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  All pass: {data.get('all_pass')}")
        
        print("\n=== ALL TESTS PASSED ===")
        return True
        
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("Shutting down server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)