from types import SimpleNamespace

from app.config import LLMSettings
from app.redis_cache import llm_cache_contract, llm_cache_key, llm_cache_payload, usage_to_jsonable
from app.schema import CTISummary


def _summary():
    return CTISummary(
        summary="APT28 activity.",
        ttps=[],
        indicators_of_compromise=[],
        threat_actors=["APT28"],
        confidence_score=0.8,
        report_metadata={"source": "unit-test"},
        yara_rules=[],
    )


def test_llm_cache_key_changes_when_prompt_changes():
    settings = LLMSettings(model="test-model")

    first = llm_cache_key(llm_cache_contract("report text", "prompt one", settings))
    second = llm_cache_key(llm_cache_contract("report text", "prompt two", settings))

    assert first != second


def test_llm_cache_payload_contains_summary_and_usage():
    contract = llm_cache_contract("report text", "prompt", LLMSettings(model="test-model"))
    payload = llm_cache_payload(
        _summary(),
        contract,
        duration_ms=42,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15),
    )

    assert payload["summary"]["summary"] == "APT28 activity."
    assert payload["duration_ms"] == 42
    assert payload["usage"] == {
        "request_tokens": 10,
        "response_tokens": 5,
        "total_tokens": 15,
    }


def test_usage_to_jsonable_returns_none_without_provider_usage():
    assert usage_to_jsonable(None) is None
