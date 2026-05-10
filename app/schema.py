"""Pydantic models and cache-backed grounding helpers for CTI summaries."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, field_validator


ATTACK_ENTERPRISE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
MALPEDIA_ACTORS_URL = "https://malpedia.caad.fkie.fraunhofer.de/actors"

CACHE_DIR = Path(__file__).resolve().parent / "cache"
TTP_CACHE_PATH = CACHE_DIR / "ttps.txt"
THREAT_ACTOR_CACHE_PATH = CACHE_DIR / "threat_actors.txt"

REQUEST_TIMEOUT_SECONDS = 30
SCHEMA_HINT_LIMIT = 100

_ATTACK_ID_PATTERN = re.compile(r"^(TA|T)(\d+)(?:\.(\d+))?$")
_HYPHEN_PATTERN = re.compile(r"\s*[-\u2013\u2014]\s*")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def _normalize_text(value: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", value).strip()


def _normalize_lookup_key(value: str) -> str:
    normalized = _normalize_text(value)
    normalized = _HYPHEN_PATTERN.sub("-", normalized)
    return normalized.casefold()


def _unique_values(values: Iterable[str]) -> List[str]:
    unique: List[str] = []
    seen: set[str] = set()

    for raw_value in values:
        cleaned = _normalize_text(raw_value)
        if not cleaned:
            continue

        lookup_key = _normalize_lookup_key(cleaned)
        if lookup_key in seen:
            continue

        seen.add(lookup_key)
        unique.append(cleaned)

    return unique


def _write_cache(cache_path: Path, values: Iterable[str]) -> List[str]:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_values = _unique_values(values)
    cache_path.write_text("\n".join(normalized_values) + ("\n" if normalized_values else ""), encoding="utf-8")
    return normalized_values


def _load_cache(cache_path: Path) -> List[str]:
    if not cache_path.exists():
        return []

    return _unique_values(cache_path.read_text(encoding="utf-8").splitlines())


def _extract_attack_external_id(item: dict[str, Any], prefix: str) -> Optional[str]:
    for reference in item.get("external_references", []):
        if reference.get("source_name") != "mitre-attack":
            continue

        external_id = _normalize_text(str(reference.get("external_id", "")))
        if external_id.startswith(prefix):
            return external_id

    return None


def _attack_sort_key(entry: str) -> tuple[int, int, int, str]:
    identifier = entry.split(" - ", 1)[0]
    match = _ATTACK_ID_PATTERN.match(identifier)
    if not match:
        return (2, 0, 0, identifier)

    kind, major, minor = match.groups()
    return (0 if kind == "TA" else 1, int(major), int(minor or 0), identifier)


def _build_grounding_lookup(values: List[str], *, include_attack_aliases: bool = False) -> dict[str, str]:
    lookup: dict[str, str] = {}

    for value in values:
        lookup.setdefault(_normalize_lookup_key(value), value)
        if include_attack_aliases and " - " in value:
            attack_id, attack_name = value.split(" - ", 1)
            lookup.setdefault(_normalize_lookup_key(attack_id), value)
            lookup.setdefault(_normalize_lookup_key(attack_name), value)

    return lookup


def _normalize_grounded_values(
    values: List[str],
    grounded_values: List[str],
    *,
    include_attack_aliases: bool = False,
) -> List[str]:
    if not values:
        return []

    lookup = _build_grounding_lookup(grounded_values, include_attack_aliases=include_attack_aliases)
    normalized: List[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = _normalize_text(value)
        if not cleaned:
            continue

        canonical_value = lookup.get(_normalize_lookup_key(cleaned), cleaned)
        lookup_key = _normalize_lookup_key(canonical_value)
        if lookup_key in seen:
            continue

        seen.add(lookup_key)
        normalized.append(canonical_value)

    return normalized


def _apply_grounding_hints(field_schema: dict[str, Any] | None, grounded_values: List[str], label: str) -> None:
    if not field_schema or not grounded_values:
        return

    hinted_values = grounded_values[:SCHEMA_HINT_LIMIT]
    example_values = hinted_values[: min(10, len(hinted_values))]
    description = field_schema.get("description", "").rstrip()
    suffix = f" Prefer values from the current {label} cache when they match the report. Unknown or new values are still allowed."

    field_schema["description"] = f"{description}{suffix}"
    field_schema["examples"] = [example_values]
    field_schema["x-suggested-values"] = hinted_values
    field_schema["x-cache-size"] = len(grounded_values)


def fetch_valid_ttps() -> List[str]:
    """Fetch active enterprise ATT&CK tactics and techniques, then cache them."""
    try:
        response = requests.get(ATTACK_ENTERPRISE_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        bundle = response.json()

        tactics: List[str] = []
        techniques: List[str] = []

        for item in bundle.get("objects", []):
            if not isinstance(item, dict):
                continue
            if item.get("revoked") or item.get("x_mitre_deprecated"):
                continue

            item_type = item.get("type")
            domains = item.get("x_mitre_domains", [])
            if domains and "enterprise-attack" not in domains:
                continue

            name = _normalize_text(str(item.get("name", "")))
            if not name:
                continue

            if item_type == "x-mitre-tactic":
                attack_id = _extract_attack_external_id(item, "TA")
                if attack_id:
                    tactics.append(f"{attack_id} - {name}")

            if item_type == "attack-pattern":
                attack_id = _extract_attack_external_id(item, "T")
                if attack_id:
                    techniques.append(f"{attack_id} - {name}")

        cached_values = [
            *sorted(_unique_values(tactics), key=_attack_sort_key),
            *sorted(_unique_values(techniques), key=_attack_sort_key),
        ]
        if not cached_values:
            raise RuntimeError("MITRE ATT&CK returned no active enterprise TTPs.")

        return _write_cache(TTP_CACHE_PATH, cached_values)
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        cached_values = load_ttps_from_cache()
        if cached_values:
            return cached_values
        raise RuntimeError("Failed to fetch TTPs from MITRE ATT&CK.") from exc


def load_ttps_from_cache() -> List[str]:
    """Load cached ATT&CK tactics and techniques from disk."""
    return _load_cache(TTP_CACHE_PATH)


def fetch_TAs_from_malpedia() -> List[str]:
    """Fetch Malpedia actor common names, then cache them."""
    try:
        response = requests.get(MALPEDIA_ACTORS_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        actor_names = [
            cell.get_text(" ", strip=True)
            for cell in soup.select("#families_list tbody.list td.common_name")
        ]

        cached_values = _unique_values(actor_names)
        if not cached_values:
            raise RuntimeError("Malpedia returned no actor names.")

        return _write_cache(THREAT_ACTOR_CACHE_PATH, cached_values)
    except (requests.RequestException, RuntimeError) as exc:
        cached_values = load_TAs_from_cache()
        if cached_values:
            return cached_values
        raise RuntimeError("Failed to fetch threat actors from Malpedia.") from exc


def load_TAs_from_cache() -> List[str]:
    """Load cached Malpedia threat actor names from disk."""
    return _load_cache(THREAT_ACTOR_CACHE_PATH)


class Indicator(BaseModel):
    """Encapsulates the details of an Indicator of Compromise (IOC)."""

    type: str = Field(..., description="The type of the indicator (e.g., 'ip-dst', 'domain', 'url', etc.).")
    value: str = Field(..., description="The value of the indicator (e.g., '192.168.1.1', 'example.com', 'http://malicious.com', etc.).")


class CTISummary(BaseModel):
    summary: str = Field(..., description="A short summary of the CTI report.")
    key_points: List[str] = Field(default_factory=list, description="A list of key points extracted from the report.")
    ttps: List[str] = Field(
        default_factory=list,
        description="A list of Tactics, Techniques, and Procedures (TTPs) mentioned in the report. Prefer canonical ATT&CK identifiers and names when possible.",
    )
    indicators: List[Indicator] = Field(default_factory=list, description="A list of Indicators of Compromise (IOCs) mentioned in the report.")
    threat_actors: List[str] = Field(
        default_factory=list,
        description="A list of threat actors mentioned in the report. Prefer the cached Malpedia common names when they match the report.",
    )
    confidence_score: Optional[float] = Field(None, description="A score indicating the confidence level of the extracted information.")
    report_metadata: Optional[dict] = Field(None, description="Additional metadata about the report (e.g., source, date, etc.).")
    yara_rules: List[str] = Field(default_factory=list, description="A list of YARA rules generated based on the report.")

    @field_validator("ttps")
    @classmethod
    def _normalize_ttps(cls, values: List[str]) -> List[str]:
        return _normalize_grounded_values(values, load_ttps_from_cache(), include_attack_aliases=True)

    @field_validator("threat_actors")
    @classmethod
    def _normalize_threat_actors(cls, values: List[str]) -> List[str]:
        return _normalize_grounded_values(values, load_TAs_from_cache())

    @classmethod
    def grounding_hints(cls, *, limit: int = SCHEMA_HINT_LIMIT) -> dict[str, List[str]]:
        return {
            "ttps": load_ttps_from_cache()[:limit],
            "threat_actors": load_TAs_from_cache()[:limit],
        }

    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:
        schema = super().model_json_schema(*args, **kwargs)
        properties = schema.get("properties", {})

        _apply_grounding_hints(properties.get("ttps"), load_ttps_from_cache(), "MITRE ATT&CK")
        _apply_grounding_hints(properties.get("threat_actors"), load_TAs_from_cache(), "Malpedia threat actor")

        return schema