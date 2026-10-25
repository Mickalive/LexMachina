import json

with open('/home/runner/work/LexMachina/LexMachina/results/product/offline_slice/20261024T142517Z/rent-default.bundle.json') as f:
    bundle = json.load(f)

print(f'Query: {bundle.get("query")}')
print(f'Decisions: {len(bundle.get("decisions", []))}')

counter_docs = [d for d in bundle.get('decisions', []) if d.get('counter_evidence_span')]
print(f'Docs with counter_evidence_span: {len(counter_docs)}')
for d in counter_docs[:5]:
    span = d['counter_evidence_span']
    print(f'  {d["decision_id"]}: selected={span.get("selected")}, reason={span.get("reason_code")}, verified={d.get("counter_evidence_verified")}, status={d.get("counter_status")}, evidence_head={d.get("counter_evidence","")[:80]}')

verified = [d for d in bundle.get('decisions', []) if d.get('counter_evidence_verified')]
print(f'Docs with counter_evidence_verified=True: {len(verified)}')
for d in verified[:5]:
    print(f'  {d["decision_id"]}: status={d.get("counter_status")}, evidence={d.get("counter_evidence","")[:100]}')

prov = bundle.get('provenance', {})
span_prov = prov.get('counter_evidence_span', {})
print(f'counter_evidence_span provenance: applied={span_prov.get("applied")}, n_candidates={span_prov.get("n_candidates")}, n_selected={span_prov.get("n_selected")}, n_abstained={span_prov.get("n_abstained")}, abstention_reasons={span_prov.get("abstention_reasons")}, n_downgraded={span_prov.get("n_downgraded")}, downgraded_ids={span_prov.get("downgraded_ids")}')