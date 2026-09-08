"""Deterministic, evidence-bound enrichment for GamCryp X posts.

This module never discovers or guesses social accounts.  Operators may add a
verified account to the explicit registry after checking an official source.
Media is local-only: an official catalog logo, an approved local product asset,
or a generated card containing only facts already present in the content pack.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.distribution.content_pack import ContentPackLite
from app.distribution.x_queue import x_weighted_character_count
from app.strategies.catalog import get_opportunity


DEFAULT_ACCOUNT_REGISTRY = Path("config/distribution/x_official_accounts.json")
DEFAULT_MEDIA_DIR = Path("data/local/distribution/x_media")
HANDLE_RE = re.compile(r"^@[A-Za-z0-9_]{1,15}$")


class XOfficialAccount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    opportunity_id: str
    handle: str
    official_source_url: str
    verified: bool = False
    verified_at: str | None = None

    @field_validator("handle")
    @classmethod
    def valid_handle(cls, value: str) -> str:
        if not HANDLE_RE.fullmatch(value):
            raise ValueError("X handle must be an explicit @handle, not a guessed name")
        return value

    @field_validator("official_source_url")
    @classmethod
    def official_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("official X account evidence must use HTTPS")
        return value


class XMediaAsset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    kind: Literal["official_logo", "official_product_asset", "verified_fallback_card"]
    source: str


class XEnrichedPost(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    final_copy: str
    official_handle: str | None = None
    hashtags: tuple[str, ...] = ()
    media: XMediaAsset
    enrichment_fingerprint: str


class XOfficialAccountRegistry:
    def __init__(self, path: Path = DEFAULT_ACCOUNT_REGISTRY):
        self.path = path

    def resolve(self, opportunity_id: str) -> XOfficialAccount | None:
        if not self.path.is_file():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            records = payload.get("accounts", []) if isinstance(payload, dict) else []
            for raw in records:
                account = XOfficialAccount.model_validate(raw)
                if account.opportunity_id == opportunity_id and account.verified:
                    return account
        except (OSError, ValueError, TypeError):
            return None
        return None


def hashtags_for_pack(pack: ContentPackLite) -> tuple[str, ...]:
    """Return a small deterministic hashtag set; it never affects ranking."""
    tags: list[str] = []
    project = re.sub(r"[^A-Za-z0-9]", "", pack.facts.project_name)
    if len(project) >= 3:
        tags.append(f"#{project}")
    kind = pack.facts.opportunity_type.upper()
    if "GAME" in kind:
        tags.append("#GameFi")
    elif "DEPIN" in kind or "NODE" in kind:
        tags.append("#DePIN")
    elif "POINT" in kind:
        tags.append("#Points")
    tags.append("#Web3")
    return tuple(dict.fromkeys(tags))[:13]


def _verified_asset(pack: ContentPackLite) -> XMediaAsset | None:
    opportunity = get_opportunity(pack.source.opportunity_id)
    if opportunity and opportunity.logo_asset:
        candidate = Path("frontend") / opportunity.logo_asset.lstrip("/")
        if candidate.is_file():
            return XMediaAsset(path=str(candidate), kind="official_logo", source="catalog_official_logo")
    asset_dir = Path("data/local/video_assets") / pack.source.opportunity_id
    if asset_dir.is_dir():
        names = ("official-product", "official-game", "official-ui", "official-dashboard", "official-provider", "product", "gameplay", "dashboard", "ui")
        for stem in names:
            for candidate in sorted(asset_dir.glob(f"{stem}.*")):
                if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
                    return XMediaAsset(path=str(candidate), kind="official_product_asset", source="local_approved_asset")
    return None


def _fallback_values(pack: ContentPackLite) -> tuple[str, str]:
    insight = next((metric.display for metric in (pack.facts.modeled_return, pack.facts.net_earnings, pack.facts.capital) if metric and metric.status == "available"), "ROI is not modeled")
    catch = pack.facts.major_catch.strip() or "Review the evidence and assumptions before acting."
    return insight, catch


def generate_fallback_card(pack: ContentPackLite, output_dir: Path = DEFAULT_MEDIA_DIR) -> XMediaAsset:
    insight, catch = _fallback_values(pack)
    digest = hashlib.sha256(f"{pack.content_id}|{insight}|{catch}".encode()).hexdigest()[:16]
    path = output_dir / f"{pack.content_id}-{digest}.svg"
    output_dir.mkdir(parents=True, exist_ok=True)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">
<rect width="1080" height="1080" fill="#06101f"/><rect x="36" y="36" width="1008" height="1008" rx="36" fill="#0b1b31" stroke="#18d7e8" stroke-width="3"/>
<text x="72" y="130" fill="#18d7e8" font-family="Arial" font-size="32" font-weight="700">GAMCRYP · EVIDENCE CARD</text>
<text x="72" y="245" fill="#f2f7ff" font-family="Arial" font-size="58" font-weight="700">{html.escape(pack.facts.project_name)}</text>
<text x="72" y="350" fill="#91a8c4" font-family="Arial" font-size="30">VERIFIED INSIGHT</text><text x="72" y="410" fill="#ffffff" font-family="Arial" font-size="48" font-weight="700">{html.escape(insight)}</text>
<text x="72" y="590" fill="#91a8c4" font-family="Arial" font-size="30">THE CATCH</text><text x="72" y="650" fill="#ffc86b" font-family="Arial" font-size="32">{html.escape(catch[:85])}</text>
<text x="72" y="970" fill="#f2f7ff" font-family="Arial" font-size="38" font-weight="700">GamCryp · check the economics</text>
</svg>'''
    path.write_text(svg, encoding="utf-8")
    return XMediaAsset(path=str(path), kind="verified_fallback_card", source="verified_content_pack_facts")


def enrich_own_post(pack: ContentPackLite, base_copy: str, *, registry: XOfficialAccountRegistry | None = None, now: datetime | None = None) -> XEnrichedPost:
    registry = registry or XOfficialAccountRegistry()
    account = registry.resolve(pack.source.opportunity_id)
    tags = hashtags_for_pack(pack)
    suffix = " ".join(filter(None, [account.handle if account else "", *tags]))
    final_copy = base_copy.rstrip()
    if suffix:
        candidate = f"{final_copy}\n\n{suffix}"
        if x_weighted_character_count(candidate) <= 280:
            final_copy = candidate
        else:
            candidate = f"{final_copy}\n\n{account.handle if account else ''}".strip()
            final_copy = candidate if account and x_weighted_character_count(candidate) <= 280 else final_copy
            tags = () if final_copy == base_copy.rstrip() else tags
    media = _verified_asset(pack) or generate_fallback_card(pack)
    # Stable for the same source copy/media; worker restarts and calendar days
    # must not create a new enrichment identity.
    fingerprint = hashlib.sha256(f"{pack.content_id}|{final_copy}|{media.path}".encode()).hexdigest()
    return XEnrichedPost(final_copy=final_copy, official_handle=account.handle if account else None, hashtags=tags, media=media, enrichment_fingerprint=fingerprint)
