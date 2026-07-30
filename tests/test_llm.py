from app.llm import SEMANTIC_LAYER_PATH, _sql_system_prompt, _strip_code_fence


def test_strip_code_fence_removes_markdown_sql_fence():
    raw = "```sql\nSELECT 1\n```"
    assert _strip_code_fence(raw) == "SELECT 1"


def test_strip_code_fence_removes_bare_fence():
    raw = "```\nSELECT 1\n```"
    assert _strip_code_fence(raw) == "SELECT 1"


def test_strip_code_fence_passthrough_when_no_fence():
    raw = "SELECT 1"
    assert _strip_code_fence(raw) == "SELECT 1"


def test_semantic_layer_file_exists_and_is_readable():
    assert SEMANTIC_LAYER_PATH.exists()
    text = SEMANTIC_LAYER_PATH.read_text()
    assert "tce" in text
    assert "fleet_utilization_rate" in text


def test_system_prompt_grounds_in_semantic_layer_not_raw_schema():
    prompt = _sql_system_prompt(today="2026-07-30")
    # The 5 metric names from the semantic layer must be present verbatim —
    # this is the actual grounding mechanism the project is built around.
    for metric in ["tce", "fleet_utilization_rate", "avg_freight_rate_by_route",
                    "voyage_profitability", "ballast_ratio"]:
        assert metric in prompt
    assert "SELECT" in prompt
    assert "only SELECT" in prompt.lower() or "single postgresql select" in prompt.lower()


def test_system_prompt_includes_join_key_notes():
    prompt = _sql_system_prompt(today="2026-07-30")
    assert "voyages.vessel_id" in prompt
    assert "voyage_costs.voyage_id" in prompt
