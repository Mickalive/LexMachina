from frontier_counter_evidence_content_filter.filter import CounterEvidenceContentFilter


def test_planted_letterhead_rejected():
    f = CounterEvidenceContentFilter()
    r = f.filter_span({
        "counter_evidence": "Kantonsgericht von Graubünden\nDretgira chantunala dal Grischun\nTribunale cantonale dei Grigioni\n________________________",
        "language": "de",
        "first_offset": 0,
    })
    assert not r.accepted


def test_planted_substantive_accepted():
    f = CounterEvidenceContentFilter()
    r = f.filter_span({
        "counter_evidence": "Für Minderungsansprüche oder entsprechende Verrechnungsforderungen, die einem Zahlungsverzug entgegenstehen, ist der Mieter behauptungs- und beweisbelastet. Die Mängel sind in sachlicher und zeitlicher Hinsicht genau zu beschreiben.",
        "language": "de",
        "full_text": "x" * 1000,
        "first_offset": 500,
    })
    assert r.accepted
