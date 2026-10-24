def test_import():
    from frontier_counter_evidence_content_filter.filter import CounterEvidenceContentFilter
    f = CounterEvidenceContentFilter()
    res = f.filter_span({"counter_evidence": "hello world", "language": "de", "full_text": "hello world"})
    assert res.accepted in (True, False)
