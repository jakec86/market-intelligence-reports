import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dealer_health import _parse_scores, _render_score_bars

SAMPLE = """\
---SCORES---
Inventory Health|74|yellow|→|Under-merch rising
Pricing Position|88|green|↑|95% at market
Engagement (VDPs)|61|red|↓|VDPs down 4.8%
Reputation|82|green|→|4.7 star
Lead Performance|55|red|↓|0.03 leads/VIN
Marketplace Investment|70|yellow|→|Premium only
---END SCORES---

### 📊 Health Snapshot — Test Dealer
Some narrative text.
"""

def test_parse_scores_extracts_six_dimensions():
    scores, narrative = _parse_scores(SAMPLE)
    assert len(scores) == 6

def test_parse_scores_fields():
    scores, _ = _parse_scores(SAMPLE)
    s = scores[0]
    assert s["name"] == "Inventory Health"
    assert s["score"] == 74
    assert s["color"] == "yellow"
    assert s["trend"] == "→"
    assert s["driver"] == "Under-merch rising"

def test_parse_scores_strips_block_from_narrative():
    _, narrative = _parse_scores(SAMPLE)
    assert "---SCORES---" not in narrative
    assert "Health Snapshot" in narrative

def test_parse_scores_graceful_on_missing_block():
    scores, narrative = _parse_scores("Just some text with no block.")
    assert scores == []
    assert narrative == "Just some text with no block."

def test_render_score_bars_returns_html_string():
    scores, _ = _parse_scores(SAMPLE)
    html = _render_score_bars(scores)
    assert "<div" in html
    assert "74%" in html
    assert "88%" in html

def test_render_score_bars_empty_list():
    assert _render_score_bars([]) == ""
