"""Content Pack Lite contracts and validation.

Content packs are draft distribution artifacts. They reference GamCryp source
facts and snapshots, but they do not calculate ROI or change production data.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field

from app.strategies.refreshability import Refreshability, classify_refreshability

CONTENT_PACK_VERSION = "content-pack-lite-v1"
DISTRIBUTION_CAMPAIGN = "distribution-mvp"
FINANCIAL_CLAIM_TOKEN_RE = re.compile(
    r"(?<![\w])(?:<\s*)?(?:"
    r"[+-]?\$[0-9][0-9,]*(?:\.[0-9]+)?(?:/day)?"
    r"|[+-]?[0-9][0-9,]*(?:\.[0-9]+)?%"
    r"|[0-9][0-9,]*(?:\.[0-9]+)?\s+days"
    r")(?![\w])"
)
DISPLAY_NUMERIC_RE = re.compile(
    r"^\s*(?P<threshold><)?\s*(?P<sign>[+-])?\s*\$?"
    r"(?P<number>[0-9][0-9,]*(?:\.[0-9]+)?)"
    r"(?P<suffix>/day|%|\s+days)?\s*$"
)
VALID_SOURCE_PATH_PREFIXES = (
    "facts.",
    "opportunity.",
    "ranking.",
    "snapshot.",
    "source.",
    "strategy.",
)


class ContentReadiness(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    url: str


class ContentSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opportunity_id: str
    strategy_id: str | None = None
    snapshot_id: str | None = None
    snapshot_timestamp: str | None = None
    source_snapshot_hash: str
    strategy_version: str | None = None
    adapter_contract_version: str | None = None
    model_version: str | None = None
    scoring_methodology_version: str | None = None
    refreshability: Refreshability | None = None
    official_source_refs: list[SourceReference] = Field(default_factory=list)


class MetricFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str | None = None
    unit: str | None = None
    display: str
    source_path: str
    status: str = "available"
    reason: str | None = None


class ScoreFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int | None = None
    label: str | None = None
    display: str
    source_path: str
    status: str = "available"
    reason: str | None = None


class ContentFactSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    opportunity_type: str
    capital: MetricFact | None = None
    modeled_return: MetricFact | None = None
    net_earnings: MetricFact | None = None
    break_even: MetricFact | None = None
    risk: ScoreFact | None = None
    confidence: ScoreFact | None = None
    freshness: MetricFact
    reward_source: str
    major_catch: str


class ContentClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    text: str
    source_path: str
    source_value: str
    display_value: str


class EditorialContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_angle: str
    readiness: ContentReadiness
    hook: str
    core_message: str
    x_post: str
    youtube_title: str | None = None
    youtube_short_script: str | None = None
    youtube_description: str | None = None
    visual_plan: list[str] = Field(default_factory=list)
    thumbnail_text: str | None = None
    disclosure: str


class DistributionLinks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_site_url: str
    content_id: str
    x_utm_url: str
    youtube_utm_url: str


class ContentPackLite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_id: str
    content_pack_version: str = CONTENT_PACK_VERSION
    source: ContentSource
    facts: ContentFactSet
    claims: list[ContentClaim] = Field(default_factory=list)
    editorial: EditorialContent
    distribution: DistributionLinks
    created_at: str


@dataclass(frozen=True)
class ContentPackValidation:
    content_id: str
    readiness: ContentReadiness
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    unsupported_numeric_claims: tuple[str, ...]


class ContentPackValidationError(ValueError):
    """Raised when a content-pack batch fails structural validation."""


def canonical_json(value: Any) -> str:
    """Return deterministic JSON for hashing and file serialization."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def source_snapshot_hash(value: Any) -> str:
    """Hash source-derived facts without including creative/editorial text."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def expected_source_hash(pack: ContentPackLite) -> str:
    """Recompute the pack hash from source-derived fields only."""

    source = pack.source.model_dump(mode="json")
    source.pop("source_snapshot_hash", None)
    if source.get("refreshability") is None:
        source.pop("refreshability", None)
    return source_snapshot_hash(
        {
            "claims": [claim.model_dump(mode="json") for claim in pack.claims],
            "facts": pack.facts.model_dump(mode="json"),
            "source": source,
        }
    )


def set_expected_source_hash(pack: ContentPackLite) -> ContentPackLite:
    """Return a copy with the deterministic source hash filled in."""

    return pack.model_copy(
        update={
            "source": pack.source.model_copy(update={"source_snapshot_hash": expected_source_hash(pack)}),
        }
    )


def build_utm_url(
    canonical_url: str,
    *,
    source: str,
    medium: str,
    campaign: str = DISTRIBUTION_CAMPAIGN,
    content_id: str,
) -> str:
    """Build a stable attribution URL without changing production tracking."""

    parts = urlsplit(canonical_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(
        {
            "utm_source": source,
            "utm_medium": medium,
            "utm_campaign": campaign,
            "utm_content": content_id,
        }
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(sorted(query.items())), parts.fragment))


def serialize_pack(pack: ContentPackLite) -> dict[str, Any]:
    return pack.model_dump(mode="json", exclude_none=True)


def serialize_batch(
    packs: list[ContentPackLite],
    *,
    batch_id: str,
    generated_at: str,
    source_dataset: str,
) -> dict[str, Any]:
    validate_batch(packs)
    readiness_counts = {readiness.value: 0 for readiness in ContentReadiness}
    for pack in packs:
        readiness_counts[pack.editorial.readiness.value] += 1
    return {
        "batch_id": batch_id,
        "content_pack_version": CONTENT_PACK_VERSION,
        "generated_at": generated_at,
        "source_dataset": source_dataset,
        "readiness_counts": readiness_counts,
        "packs": [serialize_pack(pack) for pack in sorted(packs, key=lambda item: item.content_id)],
    }


def write_batch(
    path: Path,
    packs: list[ContentPackLite],
    *,
    batch_id: str,
    generated_at: str,
    source_dataset: str,
) -> None:
    document = serialize_batch(
        packs,
        batch_id=batch_id,
        generated_at=generated_at,
        source_dataset=source_dataset,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_batch(packs: list[ContentPackLite]) -> tuple[ContentPackValidation, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    validations = []
    for pack in packs:
        if pack.content_id in seen:
            duplicates.append(pack.content_id)
        seen.add(pack.content_id)
        validations.append(validate_pack(pack))
    if duplicates:
        raise ContentPackValidationError(f"Duplicate content_id values: {', '.join(sorted(set(duplicates)))}")
    invalid = [result for result in validations if result.errors]
    if invalid:
        details = "; ".join(
            f"{result.content_id}: {', '.join(result.errors)}" for result in invalid if result.errors
        )
        raise ContentPackValidationError(details)
    return tuple(validations)


def validate_pack(pack: ContentPackLite) -> ContentPackValidation:
    errors: list[str] = []
    warnings: list[str] = []
    claim_integrity_failed = False

    if pack.content_pack_version != CONTENT_PACK_VERSION:
        errors.append(f"Unsupported content_pack_version {pack.content_pack_version}")
    if pack.source.source_snapshot_hash != expected_source_hash(pack):
        errors.append("source_snapshot_hash does not match source-derived facts")
    if pack.source.strategy_id and not pack.source.snapshot_id:
        errors.append("modeled strategy pack is missing snapshot_id")
    if pack.source.strategy_id and not pack.source.snapshot_timestamp:
        errors.append("modeled strategy pack is missing snapshot_timestamp")

    unsupported_numeric_claims = tuple(unsupported_numeric_tokens(pack))
    if unsupported_numeric_claims:
        errors.append("editorial text contains unsupported numeric claim(s)")

    for claim in pack.claims:
        if not claim.source_path.startswith(VALID_SOURCE_PATH_PREFIXES):
            errors.append(f"claim {claim.claim_id} has invalid source_path {claim.source_path}")
            claim_integrity_failed = True
        if not claim.source_value.strip():
            errors.append(f"claim {claim.claim_id} is missing source_value")
            claim_integrity_failed = True
        if not claim.display_value.strip():
            errors.append(f"claim {claim.claim_id} is missing display_value")
            claim_integrity_failed = True
        try:
            resolved_value = resolve_claim_source_value(pack, claim.source_path)
        except KeyError:
            errors.append(f"claim {claim.claim_id} source_path does not resolve: {claim.source_path}")
            claim_integrity_failed = True
        else:
            if not source_values_match(resolved_value, claim.source_value):
                errors.append(f"claim {claim.claim_id} source_value does not match {claim.source_path}")
                claim_integrity_failed = True
            elif not display_value_matches_source(resolved_value, claim.display_value):
                errors.append(f"claim {claim.claim_id} display_value does not represent {claim.source_path}")
                claim_integrity_failed = True

    derived_readiness = derive_readiness(pack, unsupported_numeric_claims=unsupported_numeric_claims)
    if claim_integrity_failed:
        derived_readiness = ContentReadiness.RED
    if pack.editorial.readiness != derived_readiness:
        errors.append(
            f"readiness must be rule-derived as {derived_readiness.value}, "
            f"not {pack.editorial.readiness.value}"
        )

    if pack.facts.risk and pack.facts.risk.label in {"HIGH", "VERY HIGH"}:
        warnings.append(f"high risk context: {pack.facts.risk.label}")
    if pack.facts.confidence and pack.facts.confidence.label in {"LOW", "MODERATE"}:
        warnings.append(f"confidence context: {pack.facts.confidence.label}")
    if pack.facts.freshness.display.lower() == "stale":
        warnings.append("source snapshot is stale")
    authoritative_refreshability = _authoritative_refreshability(pack)
    if _has_available_financial_claim(pack) and authoritative_refreshability != Refreshability.AUTO_REFRESHABLE:
        label = authoritative_refreshability.value if authoritative_refreshability else "UNCLASSIFIED"
        warnings.append(f"numeric publication blocked by refreshability: {label}")
    if (
        _has_available_financial_claim(pack)
        and pack.source.refreshability is not None
        and pack.source.refreshability != authoritative_refreshability
    ):
        warnings.append("content-pack refreshability metadata does not match the canonical strategy classification")

    return ContentPackValidation(
        content_id=pack.content_id,
        readiness=derived_readiness,
        errors=tuple(errors),
        warnings=tuple(warnings),
        unsupported_numeric_claims=unsupported_numeric_claims,
    )


def resolve_claim_source_value(pack: ContentPackLite, source_path: str) -> str:
    """Resolve a claim against explicit source-derived fields in the pack.

    The resolver deliberately supports only declared fact paths. It never evaluates
    arbitrary attributes or expressions supplied by content authors.
    """

    facts: tuple[MetricFact | ScoreFact | None, ...] = (
        pack.facts.capital,
        pack.facts.modeled_return,
        pack.facts.net_earnings,
        pack.facts.break_even,
        pack.facts.risk,
        pack.facts.confidence,
        pack.facts.freshness,
    )
    resolved: dict[str, str] = {}
    for fact in facts:
        if fact is None:
            continue
        if isinstance(fact, MetricFact):
            if fact.value is not None:
                resolved[fact.source_path] = str(fact.value)
            continue
        if fact.score is not None:
            resolved[f"{fact.source_path}.score"] = str(fact.score)
        if fact.label is not None:
            resolved[f"{fact.source_path}.label"] = fact.label

    source_values = {
        "source.opportunity_id": pack.source.opportunity_id,
        "source.strategy_id": pack.source.strategy_id,
        "source.snapshot_id": pack.source.snapshot_id,
        "source.snapshot_timestamp": pack.source.snapshot_timestamp,
        "source.strategy_version": pack.source.strategy_version,
        "source.adapter_contract_version": pack.source.adapter_contract_version,
        "source.model_version": pack.source.model_version,
        "source.scoring_methodology_version": pack.source.scoring_methodology_version,
        "source.refreshability": pack.source.refreshability.value if pack.source.refreshability else None,
    }
    resolved.update({path: str(value) for path, value in source_values.items() if value is not None})
    if source_path not in resolved:
        raise KeyError(source_path)
    return resolved[source_path]


def source_values_match(resolved_value: str, claimed_value: str) -> bool:
    """Compare exact source values, allowing only meaning-preserving decimals."""

    if resolved_value == claimed_value:
        return True
    try:
        return Decimal(resolved_value) == Decimal(claimed_value)
    except (InvalidOperation, ValueError):
        return False


def display_value_matches_source(source_value: str, display_value: str) -> bool:
    """Verify a displayed number is a faithful rounded or threshold source value."""

    match = DISPLAY_NUMERIC_RE.fullmatch(display_value)
    try:
        source_decimal = Decimal(source_value)
    except InvalidOperation:
        return display_value == source_value
    if match is None:
        return False
    rendered_number = match.group("number").replace(",", "")
    displayed_decimal = Decimal(rendered_number)
    if match.group("sign") == "-":
        displayed_decimal = -displayed_decimal
    source_for_display = source_decimal * Decimal("100") if match.group("suffix") == "%" else source_decimal
    if match.group("threshold"):
        return abs(source_for_display) < abs(displayed_decimal)
    decimal_places = len(rendered_number.partition(".")[2])
    quantum = Decimal("1").scaleb(-decimal_places)
    return source_for_display.quantize(quantum, rounding=ROUND_HALF_UP) == displayed_decimal


def derive_readiness(
    pack: ContentPackLite,
    *,
    unsupported_numeric_claims: tuple[str, ...] | None = None,
) -> ContentReadiness:
    unsupported = unsupported_numeric_claims
    if unsupported is None:
        unsupported = tuple(unsupported_numeric_tokens(pack))
    if unsupported:
        return ContentReadiness.RED
    if pack.source.strategy_id and not pack.source.snapshot_id:
        return ContentReadiness.RED
    authoritative_refreshability = _authoritative_refreshability(pack)
    if _has_available_financial_claim(pack) and authoritative_refreshability != Refreshability.AUTO_REFRESHABLE:
        return ContentReadiness.RED
    if (
        _has_available_financial_claim(pack)
        and pack.source.refreshability is not None
        and pack.source.refreshability != authoritative_refreshability
    ):
        return ContentReadiness.RED
    if _has_available_financial_claim(pack) and pack.facts.freshness.display.lower() == "stale":
        return ContentReadiness.RED
    if pack.facts.modeled_return and pack.facts.modeled_return.status == "unavailable":
        return ContentReadiness.YELLOW
    if pack.facts.risk and pack.facts.risk.label in {"HIGH", "VERY HIGH"}:
        return ContentReadiness.YELLOW
    if pack.facts.confidence and pack.facts.confidence.label in {"LOW", "MODERATE"}:
        return ContentReadiness.YELLOW
    return ContentReadiness.GREEN


def _authoritative_refreshability(pack: ContentPackLite) -> Refreshability | None:
    if not pack.source.strategy_id:
        return None
    return classify_refreshability(pack.source.strategy_id).refreshability


def unsupported_numeric_tokens(pack: ContentPackLite) -> list[str]:
    allowed = {_normalize_token(claim.display_value) for claim in pack.claims}
    allowed.update(_normalize_token(claim.source_value) for claim in pack.claims)
    threshold_tokens = {token[1:] for token in allowed if token.startswith("<")}
    allowed.update(threshold_tokens)
    text = "\n".join(
        item
        for item in (
            pack.editorial.hook,
            pack.editorial.core_message,
            pack.editorial.x_post,
            pack.editorial.youtube_title or "",
            pack.editorial.youtube_short_script or "",
            pack.editorial.youtube_description or "",
            pack.editorial.thumbnail_text or "",
            "\n".join(pack.editorial.visual_plan),
        )
        if item
    )
    unsupported: list[str] = []
    for match in FINANCIAL_CLAIM_TOKEN_RE.finditer(text):
        token = _normalize_token(match.group(0))
        if token not in allowed and token not in unsupported:
            unsupported.append(token)
    return unsupported


def _has_available_financial_claim(pack: ContentPackLite) -> bool:
    financial_facts = (pack.facts.capital, pack.facts.modeled_return, pack.facts.net_earnings, pack.facts.break_even)
    return any(fact is not None and fact.status == "available" for fact in financial_facts)


def _normalize_token(token: str) -> str:
    return re.sub(r"\s+", "", token.strip()).lower()
