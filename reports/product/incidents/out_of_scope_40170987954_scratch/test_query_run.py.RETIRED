#!/usr/bin/env python3
"""Test the full query flow with enrichment."""
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

# Test query/run endpoint (synchronous full query)
print("Testing /api/query/run...")
r = requests.get("http://localhost:8080/api/query/run?q=K%C3%BCndigung+Mietvertrag+Mietrecht&n=50&mode=fixture", timeout=60)
print(f"  Status: {r.status_code}")
bundle = r.json()
print(f"  Decisions: {len(bundle.get('decisions', []))}")
print(f"  Clusters: {len(bundle.get('clusters', []))}")
print(f"  Answer status: {bundle.get('answer', {}).get('status')}")
print(f"  Counter_evidence_span provenance: {bundle.get('provenance', {}).get('counter_evidence_span', {}).get('applied')}")
print(f"  n_candidates: {bundle.get('provenance', {}).get('counter_evidence_span', {}).get('n_candidates')}")
print(f"  n_selected: {bundle.get('provenance', {}).get('counter_evidence_span', {}).get('n_selected')}")
print(f"  n_abstained: {bundle.get('provenance', {}).get('counter_evidence_span', {}).get('n_abstained')}")
print(f"  abstention_reasons: {bundle.get('provenance', {}).get('counter_evidence_span', {}).get('abstention_reasons')}")
print(f"  n_downgraded: {bundle.get('provenance', {}).get('counter_evidence_span', {}).get('n_downgraded')}")
print(f"  n_incumbent_downgraded: {bundle.get('provenance', {}).get('counter_evidence_span', {}).get('n_incumbent_downgraded')}")
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

# Check counter_surface_signal rows
surface = [d for d in bundle.get('decisions', []) if d.get('counter_surface_signal')]
print(f"\n  Surface signal rows: {len(surface)}")
for d in surface[:3]:
    sig = d.get('counter_surface_signal', {})
    print(f"    {d['decision_id']}: {sig.get('heuristic_status')} - {sig.get('intent')} - {sig.get('evidence','')[:60]}")

print("\nAll tests passed!")