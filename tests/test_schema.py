from pathlib import Path

from app import schema


class DummyResponse:
    def __init__(self, *, text: str = "", json_data=None):
        self.text = text
        self._json_data = json_data

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._json_data


def _configure_cache_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(schema, "TTP_CACHE_PATH", tmp_path / "cache" / "ttps.txt")
    monkeypatch.setattr(schema, "THREAT_ACTOR_CACHE_PATH", tmp_path / "cache" / "threat_actors.txt")


def test_loaders_ignore_blank_lines_and_duplicates(tmp_path, monkeypatch):
    _configure_cache_paths(tmp_path, monkeypatch)

    schema.TTP_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema.TTP_CACHE_PATH.write_text(
        "TA0001 - Initial Access\n\nTA0001 - Initial Access\nT1059 - Command and Scripting Interpreter\n",
        encoding="utf-8",
    )
    schema.THREAT_ACTOR_CACHE_PATH.write_text(
        "APT28\nAPT28\n\nLazarus Group\n",
        encoding="utf-8",
    )

    assert schema.load_ttps_from_cache() == [
        "TA0001 - Initial Access",
        "T1059 - Command and Scripting Interpreter",
    ]
    assert schema.load_TAs_from_cache() == ["APT28", "Lazarus Group"]


def test_fetch_valid_ttps_parses_attack_bundle_and_caches_results(tmp_path, monkeypatch):
    _configure_cache_paths(tmp_path, monkeypatch)

    payload = {
        "objects": [
            {
                "type": "x-mitre-tactic",
                "name": "Initial Access",
                "revoked": False,
                "x_mitre_deprecated": False,
                "x_mitre_domains": ["enterprise-attack"],
                "external_references": [
                    {"source_name": "mitre-attack", "external_id": "TA0001"}
                ],
            },
            {
                "type": "attack-pattern",
                "name": "Extra Window Memory Injection",
                "revoked": False,
                "x_mitre_deprecated": False,
                "x_mitre_domains": ["enterprise-attack"],
                "external_references": [
                    {"source_name": "mitre-attack", "external_id": "T1055.011"}
                ],
            },
            {
                "type": "attack-pattern",
                "name": "Deprecated Technique",
                "revoked": False,
                "x_mitre_deprecated": True,
                "x_mitre_domains": ["enterprise-attack"],
                "external_references": [
                    {"source_name": "mitre-attack", "external_id": "T0000"}
                ],
            },
            {
                "type": "attack-pattern",
                "name": "ICS Only Technique",
                "revoked": False,
                "x_mitre_deprecated": False,
                "x_mitre_domains": ["ics-attack"],
                "external_references": [
                    {"source_name": "mitre-attack", "external_id": "T9999"}
                ],
            },
        ]
    }

    monkeypatch.setattr(schema.requests, "get", lambda *args, **kwargs: DummyResponse(json_data=payload))

    cached_values = schema.fetch_valid_ttps()

    assert cached_values == [
        "TA0001 - Initial Access",
        "T1055.011 - Extra Window Memory Injection",
    ]
    assert schema.TTP_CACHE_PATH.read_text(encoding="utf-8").splitlines() == cached_values


def test_fetch_TAs_from_malpedia_parses_common_names_and_caches_results(tmp_path, monkeypatch):
    _configure_cache_paths(tmp_path, monkeypatch)

    html = """
    <div id="families_list">
      <table>
        <tbody class="list">
          <tr><td class="common_name">APT28</td></tr>
          <tr><td class="common_name"> Lazarus Group </td></tr>
          <tr><td class="common_name">APT28</td></tr>
        </tbody>
      </table>
    </div>
    """

    monkeypatch.setattr(schema.requests, "get", lambda *args, **kwargs: DummyResponse(text=html))

    cached_values = schema.fetch_TAs_from_malpedia()

    assert cached_values == ["APT28", "Lazarus Group"]
    assert schema.THREAT_ACTOR_CACHE_PATH.read_text(encoding="utf-8").splitlines() == cached_values


def test_cti_summary_uses_cached_grounding_hints_and_soft_normalization(tmp_path, monkeypatch):
    _configure_cache_paths(tmp_path, monkeypatch)

    schema.TTP_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema.TTP_CACHE_PATH.write_text(
        "TA0001 - Initial Access\nT1055.011 - Extra Window Memory Injection\n",
        encoding="utf-8",
    )
    schema.THREAT_ACTOR_CACHE_PATH.write_text(
        "APT28\nLazarus Group\n",
        encoding="utf-8",
    )

    model_schema = schema.CTISummary.model_json_schema()

    assert model_schema["properties"]["ttps"]["x-suggested-values"] == [
        "TA0001 - Initial Access",
        "T1055.011 - Extra Window Memory Injection",
    ]
    assert model_schema["properties"]["threat_actors"]["x-suggested-values"] == [
        "APT28",
        "Lazarus Group",
    ]
    assert "Prefer values from the current MITRE ATT&CK cache" in model_schema["properties"]["ttps"]["description"]
    assert "Prefer values from the current Malpedia threat actor cache" in model_schema["properties"]["threat_actors"]["description"]

    summary = schema.CTISummary(
        summary="Test summary",
        ttps=["t1055.011", "Brand New Technique"],
        threat_actors=["apt28", "Unknown Group"],
        confidence_score=None,
        report_metadata=None,
    )

    assert summary.ttps == [
        "T1055.011 - Extra Window Memory Injection",
        "Brand New Technique",
    ]
    assert summary.threat_actors == ["APT28", "Unknown Group"]