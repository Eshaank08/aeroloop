from scripts.enrich_recorded_trace import enrich


def test_enrich_adds_reproducible_viewer_channels():
    payload = {"seed": 123, "frames": [{"t": 0.0, "p": [0.0, 0.0, 6.0]}]}
    enriched = enrich(payload)

    assert len(enriched["frames"][0]["wind"]) == 3
    assert enriched["frames"][0]["sensors"]["synthetic"] is True
    assert enriched["replay_channels"]["vision"] == "synthetic"
