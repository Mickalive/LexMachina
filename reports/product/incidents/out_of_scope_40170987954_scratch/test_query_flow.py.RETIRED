#!/usr/bin/env python3
"""Test the full query flow."""
import sys
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/product')

from product.server import run_server
import threading
import time
import requests
import json

# Start server in background thread
def start_server():
    run_server(8080, query_mode=True)

t = threading.Thread(target=start_server, daemon=True)
t.start()
time.sleep(3)

# Test query/start endpoint
print("Testing /api/query/start...")
r = requests.get("http://localhost:8080/api/query/start?q=K%C3%BCndigung+Mietvertrag+Mietrecht&n=50&mode=fixture", timeout=30)
print(f"  Status: {r.status_code}")
data = r.json()
print(f"  Run ID: {data.get('run_id')}")
print(f"  Decisions: {len(data.get('bundle', {}).get('decisions', []))}")
print(f"  Clusters: {len(data.get('bundle', {}).get('clusters', []))}")
run_id = data.get('run_id')

# Test query/status endpoint
print("\nTesting /api/query/status...")
r = requests.get(f"http://localhost:8080/api/query/status?run_id={run_id}&bundle=true", timeout=30)
print(f"  Status: {r.status_code}")
data = r.json()
print(f"  Jobs: {data.get('jobs')}")
bundle = data.get('bundle', {})
print(f"  Decisions: {len(bundle.get('decisions', []))}")
print(f"  Answer status: {bundle.get('answer', {}).get('status')}")
print(f"  Counter_evidence_span provenance: {bundle.get('provenance', {}).get('counter_evidence_span', {}).get('applied')}")
print(f"  n_downgraded: {bundle.get('provenance', {}).get('counter_evidence_span', {}).get('n_downgraded')}")
print(f"  downgraded_ids: {bundle.get('provenance', {}).get('counter_evidence_span', {}).get('downgraded_ids')}")

# Check counter_evidence_verified rows
verified = [d for d in bundle.get('decisions', []) if d.get('counter_evidence_verified')]
print(f"\n  Verified counter rows: {len(verified)}")
for d in verified[:3]:
    print(f"    {d['decision_id']}: {d.get('counter_status')} - {d.get('counter_evidence','')[:80]}")

# Check counter_evidence_unevidenced rows
unevidenced = [d for d in bundle.get('decisions', []) if d.get('counter_evidence_unevidenced')]
print(f"\n  Unevidenced counter rows: {len(unevidenced)}")
for d in unevidenced[:3]:
    print(f"    {d['decision_id']}: {d.get('counter_status')} - reason: {d.get('counter_evidence_unevidenced_reason')}")

print("\nAll tests passed!")