"""Operator-controlled, fail-closed X publishing for validated distribution packs."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import secrets
import tempfile
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.distribution.content_pack import (
    ContentPackLite,
    ContentReadiness,
    set_expected_source_hash,
    validate_pack,
)
from app.distribution.x_queue import (
    X_MAX_WEIGHTED_LENGTH,
    XPublishQueue,
    XQueueItem,
    contains_unsupported_idn_hostname,
    load_content_pack_batch,
    load_x_queue,
    x_content_checksum,
    x_weighted_character_count,
)
from app.distribution.x_enrichment import enrich_own_post
from app.distribution.x_quality import actionable_x_copy_blockers

logger = logging.getLogger(__name__)

X_API_BASE_URL = "https://api.x.com"
X_AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.x.com/2/oauth2/token"
X_SCOPES = ("tweet.read", "tweet.write", "users.read", "offline.access")
X_POST_ENDPOINT = "/2/tweets"
X_STATE_VERSION = "x-publisher-state-v1"
X_OAUTH_PENDING_MAX_AGE = timedelta(minutes=10)
MAX_SAFE_ERROR_LENGTH = 500
PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_][^{}]*\}")
SENSITIVE_TEXT_RE = re.compile(
    r"(?i)(client[_-]?secret|refresh[_-]?token|access[_-]?token|authorization|bearer|password|credential)"
    r"([\s:=]+)([^\s,;&]+)"
)
BEARER_RE = re.compile(r"(?i)Bearer\s+[^\s,;&]+")
PublicationStatus = Literal["publishing", "published", "failed", "ambiguous"]
ApprovalStatus = Literal["approved", "revoked"]


class XPublisherError(RuntimeError):
    """Safe operator-facing base error."""


class XConfigError(XPublisherError):
    pass


class XValidationError(XPublisherError):
    pass


class XApprovalError(XPublisherError):
    pass


class XDuplicateError(XPublisherError):
    pass


class XApiError(XPublisherError):
    pass


class XAmbiguousApiError(XApiError):
    """The request may have reached X; automatic retry is unsafe."""


class XAuthError(XPublisherError):
    pass


@dataclass(frozen=True)
class XPublisherConfig:
    content_pack_file: Path = Path("distribution/content_packs/learning_batch_001.json")
    queue_file: Path = Path("distribution/publish_queue/x_publish_queue.json")
    approval_file: Path = Path("data/local/x/approvals.json")
    publication_file: Path = Path("data/local/x/publications.json")
    token_file: Path = Path("data/local/x/token.json")
    oauth_pending_file: Path = Path("data/local/x/oauth_pending.json")
    publish_lock_file: Path = Path("data/local/x/publish.lock")
    client_id: str | None = None
    client_secret: str | None = None
    redirect_uri: str = "http://127.0.0.1:8765/callback"
    timeout_seconds: float = 20.0
    max_snapshot_age_seconds: int = 1800

    def __post_init__(self) -> None:
        callback = urlsplit(self.redirect_uri)
        if callback.scheme not in {"http", "https"} or not callback.netloc or not callback.path:
            raise XConfigError("GAMEFI_X_REDIRECT_URI must be an absolute HTTP(S) callback URL")
        if self.timeout_seconds <= 0:
            raise XConfigError("GAMEFI_X_HTTP_TIMEOUT_SECONDS must be greater than zero")
        if self.max_snapshot_age_seconds <= 0:
            raise XConfigError("GAMEFI_X_MAX_SNAPSHOT_AGE_SECONDS must be greater than zero")

    @classmethod
    def from_environment(cls) -> "XPublisherConfig":
        return cls(
            content_pack_file=Path(
                os.getenv("GAMEFI_X_CONTENT_PACK_FILE", "distribution/content_packs/learning_batch_001.json")
            ),
            queue_file=Path(os.getenv("GAMEFI_X_QUEUE_FILE", "distribution/publish_queue/x_publish_queue.json")),
            approval_file=Path(os.getenv("GAMEFI_X_APPROVAL_FILE", "data/local/x/approvals.json")),
            publication_file=Path(os.getenv("GAMEFI_X_PUBLICATION_FILE", "data/local/x/publications.json")),
            token_file=Path(os.getenv("GAMEFI_X_TOKEN_FILE", "data/local/x/token.json")),
            oauth_pending_file=Path(
                os.getenv("GAMEFI_X_OAUTH_PENDING_FILE", "data/local/x/oauth_pending.json")
            ),
            publish_lock_file=Path(os.getenv("GAMEFI_X_PUBLISH_LOCK_FILE", "data/local/x/publish.lock")),
            client_id=_optional_env("GAMEFI_X_CLIENT_ID"),
            client_secret=_optional_env("GAMEFI_X_CLIENT_SECRET"),
            redirect_uri=os.getenv("GAMEFI_X_REDIRECT_URI", "http://127.0.0.1:8765/callback").strip(),
            timeout_seconds=float(os.getenv("GAMEFI_X_HTTP_TIMEOUT_SECONDS", "20")),
            max_snapshot_age_seconds=int(os.getenv("GAMEFI_X_MAX_SNAPSHOT_AGE_SECONDS", "1800")),
        )


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    source_content_checksum: str
    approved_content_checksum: str
    approved_copy: str
    approved_at: str
    state: ApprovalStatus
    revoked_at: str | None = None


class PublicationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    content_checksum: str
    status: PublicationStatus
    attempted_at: str
    updated_at: str
    post_id: str | None = None
    safe_error: str | None = None


class OAuthToken(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    access_token: str
    token_type: str = "bearer"
    expires_at: str | None = None
    refresh_token: str | None = None
    scope: str | None = None


class OAuthPendingState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: str
    code_verifier: str
    created_at: str


class PublishPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    project: str
    readiness: ContentReadiness
    approval_state: str
    exact_final_copy: str
    weighted_character_count: int
    attribution_url: str
    content_checksum: str
    snapshot_id: str | None
    snapshot_timestamp: str | None
    refreshability: str | None
    would_publish: bool
    blockers: tuple[str, ...]
    network_called: bool = False
    official_handle: str | None = None
    hashtags: tuple[str, ...] = ()
    media_path: str | None = None
    media_kind: str | None = None
    media_source: str | None = None
    enrichment_fingerprint: str | None = None


class PublishResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    status: str
    post_id: str | None = None
    content_checksum: str
    network_called: bool
    detail: str


class JsonStateStore:
    def __init__(self, path: Path, *, collection_key: str) -> None:
        self.path = path
        self.collection_key = collection_key

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"state_version": X_STATE_VERSION, self.collection_key: []}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("state_version") != X_STATE_VERSION or not isinstance(payload.get(self.collection_key), list):
            raise XConfigError(f"Invalid X publisher state file: {self.path.name}")
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
            _chmod_private(self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)


class ApprovalStore:
    def __init__(self, path: Path) -> None:
        self.store = JsonStateStore(path, collection_key="approvals")

    def latest(self, content_id: str) -> ApprovalRecord | None:
        records = [
            ApprovalRecord.model_validate(item)
            for item in self.store.load()["approvals"]
            if item.get("content_id") == content_id
        ]
        return records[-1] if records else None

    def approve(self, record: ApprovalRecord) -> None:
        payload = self.store.load()
        payload["approvals"].append(record.model_dump(mode="json"))
        self.store.save(payload)

    def revoke(self, content_id: str, *, now: datetime) -> ApprovalRecord:
        current = self.latest(content_id)
        if current is None or current.state != "approved":
            raise XApprovalError("No active approval exists for this content_id")
        revoked = current.model_copy(update={"state": "revoked", "revoked_at": _iso(now)})
        payload = self.store.load()
        payload["approvals"].append(revoked.model_dump(mode="json"))
        self.store.save(payload)
        return revoked


class PublicationStore:
    def __init__(self, path: Path) -> None:
        self.store = JsonStateStore(path, collection_key="publications")

    def records(self, content_id: str) -> tuple[PublicationRecord, ...]:
        return tuple(
            PublicationRecord.model_validate(item)
            for item in self.store.load()["publications"]
            if item.get("content_id") == content_id
        )

    def append(self, record: PublicationRecord) -> None:
        payload = self.store.load()
        payload["publications"].append(record.model_dump(mode="json"))
        self.store.save(payload)

    def replace_latest(self, record: PublicationRecord) -> None:
        payload = self.store.load()
        records = payload["publications"]
        for index in range(len(records) - 1, -1, -1):
            if records[index].get("content_id") == record.content_id and records[index].get("content_checksum") == record.content_checksum:
                records[index] = record.model_dump(mode="json")
                self.store.save(payload)
                return
        raise XConfigError("Publication attempt state was not found")


class TokenStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> OAuthToken | None:
        if not self.path.is_file():
            return None
        return OAuthToken.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, token: OAuthToken) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(token.model_dump_json(indent=2))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
            _chmod_private(self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)


class XOAuthManager:
    def __init__(
        self,
        config: XPublisherConfig,
        *,
        client: httpx.Client | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.config = config
        self.client = client or httpx.Client(timeout=config.timeout_seconds)
        self.now = now
        self.token_store = TokenStore(config.token_file)

    def authorization_url(self) -> str:
        client_id = self._require_client_id()
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
        pending = OAuthPendingState(state=state, code_verifier=verifier, created_at=_iso(self.now()))
        _write_private_model(self.config.oauth_pending_file, pending)
        return f"{X_AUTHORIZE_URL}?{urlencode({'response_type': 'code', 'client_id': client_id, 'redirect_uri': self.config.redirect_uri, 'scope': ' '.join(X_SCOPES), 'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256'})}"

    def complete_authorization(self, callback_url: str) -> dict[str, Any]:
        pending = _load_private_model(self.config.oauth_pending_file, OAuthPendingState)
        pending_age = self.now() - _parse_datetime(pending.created_at)
        if pending_age < timedelta(0) or pending_age > X_OAUTH_PENDING_MAX_AGE:
            raise XAuthError("OAuth authorization state has expired; start authorization again")
        callback = urlsplit(callback_url)
        expected = urlsplit(self.config.redirect_uri)
        if (callback.scheme, callback.netloc, callback.path) != (expected.scheme, expected.netloc, expected.path):
            raise XAuthError("OAuth callback URL does not match GAMEFI_X_REDIRECT_URI")
        query = parse_qs(callback.query)
        if query.get("state", [None])[0] != pending.state:
            raise XAuthError("OAuth state mismatch")
        code = query.get("code", [None])[0]
        if not code:
            raise XAuthError("OAuth callback did not include an authorization code")
        token = self._token_request(
            {
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.config.redirect_uri,
                "code_verifier": pending.code_verifier,
            }
        )
        self.token_store.save(token)
        self.config.oauth_pending_file.unlink(missing_ok=True)
        return self.safe_status()

    def access_token(self) -> str:
        token = self.token_store.load()
        if token is None:
            raise XAuthError("OAuth token is missing; run x-publisher authorize-url and authorize")
        if not token.expires_at or _parse_datetime(token.expires_at) > self.now() + timedelta(seconds=60):
            return token.access_token
        if not token.refresh_token:
            raise XAuthError("OAuth token expired without a refresh token; authorize again")
        refreshed = self._token_request({"grant_type": "refresh_token", "refresh_token": token.refresh_token})
        if refreshed.refresh_token is None:
            refreshed = refreshed.model_copy(update={"refresh_token": token.refresh_token})
        self.token_store.save(refreshed)
        return refreshed.access_token

    def safe_status(self) -> dict[str, Any]:
        token = self.token_store.load()
        return {
            "client_id_configured": bool(self.config.client_id),
            "client_secret_configured": bool(self.config.client_secret),
            "redirect_uri": self.config.redirect_uri,
            "required_scopes": list(X_SCOPES),
            "token_file_present": self.config.token_file.is_file(),
            "token_has_refresh_token": bool(token and token.refresh_token),
            "token_expires_at": token.expires_at if token else None,
        }

    def _token_request(self, data: dict[str, str]) -> OAuthToken:
        client_id = self._require_client_id()
        request_data = dict(data)
        auth: tuple[str, str] | None = None
        if self.config.client_secret:
            auth = (client_id, self.config.client_secret)
        else:
            request_data["client_id"] = client_id
        try:
            response = self.client.post(X_TOKEN_URL, data=request_data, auth=auth)
        except httpx.HTTPError as exc:
            raise XAuthError(f"X OAuth request failed: {safe_error(exc)}") from exc
        if response.status_code >= 400:
            raise XAuthError(f"X OAuth request failed with status {response.status_code}: {safe_response(response)}")
        payload = response.json()
        expires_in = payload.get("expires_in")
        expires_at = _iso(self.now() + timedelta(seconds=int(expires_in))) if expires_in else None
        try:
            return OAuthToken(
                access_token=payload["access_token"],
                token_type=payload.get("token_type", "bearer"),
                expires_at=expires_at,
                refresh_token=payload.get("refresh_token"),
                scope=payload.get("scope"),
            )
        except Exception as exc:
            raise XAuthError("X OAuth response did not contain a valid access token") from exc

    def _require_client_id(self) -> str:
        if not self.config.client_id:
            raise XConfigError("GAMEFI_X_CLIENT_ID is required for OAuth authorization")
        return self.config.client_id


class XApiClient:
    def __init__(
        self,
        oauth: XOAuthManager,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.oauth = oauth
        self.client = client or httpx.Client(base_url=X_API_BASE_URL, timeout=oauth.config.timeout_seconds)

    def create_post(self, text: str) -> str:
        token = self.oauth.access_token()
        try:
            response = self.client.post(
                X_POST_ENDPOINT,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"text": text},
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise XAmbiguousApiError(
                "X create-post result is ambiguous after a network failure; reconcile in X before retrying"
            ) from exc
        except httpx.HTTPError as exc:
            raise XApiError(f"X create-post request failed: {safe_error(exc)}") from exc
        if response.status_code >= 500:
            raise XAmbiguousApiError(
                f"X create-post returned status {response.status_code}; reconcile in X before retrying"
            )
        if response.status_code != 201:
            raise XApiError(f"X create-post failed with status {response.status_code}: {safe_response(response)}")
        payload = response.json()
        post_id = str((payload.get("data") or {}).get("id") or "").strip()
        if not post_id:
            raise XAmbiguousApiError("X create-post response omitted the post id; reconcile in X before retrying")
        return post_id

    def authenticated_user(self) -> dict[str, Any]:
        """Return the user-context identity without exposing the access token."""
        return self._get_json(
            "/2/users/me",
            params={"user.fields": "username,verified,public_metrics"},
        )

    def search_recent(self, query: str, *, max_results: int = 25) -> dict[str, Any]:
        """Search recent public posts using the authenticated X API context."""
        return self._get_json(
            "/2/tweets/search/recent",
            params={
                "query": query,
                "max_results": str(max(10, min(max_results, 100))),
                "tweet.fields": "created_at,public_metrics,author_id,entities",
                "expansions": "author_id",
                "user.fields": "username,verified,public_metrics",
            },
        )

    def create_retweet(self, user_id: str, tweet_id: str) -> str:
        """Retweet one post for the authenticated user through the official API."""
        token = self.oauth.access_token()
        try:
            response = self.client.post(
                f"/2/users/{user_id}/retweets",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"tweet_id": tweet_id},
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise XAmbiguousApiError(
                "X retweet result is ambiguous after a network failure; reconcile in X before retrying"
            ) from exc
        except httpx.HTTPError as exc:
            raise XApiError(f"X retweet request failed: {safe_error(exc)}") from exc
        if response.status_code >= 500:
            raise XAmbiguousApiError(
                f"X retweet returned status {response.status_code}; reconcile in X before retrying"
            )
        if response.status_code >= 400:
            raise XApiError(f"X retweet failed with status {response.status_code}: {safe_response(response)}")
        payload = response.json()
        retweeted = (payload.get("data") or {}).get("retweeted")
        if retweeted is False:
            raise XApiError("X retweet response reported that the post was not retweeted")
        return tweet_id

    def _get_json(self, endpoint: str, *, params: dict[str, str]) -> dict[str, Any]:
        token = self.oauth.access_token()
        try:
            response = self.client.get(endpoint, params=params, headers={"Authorization": f"Bearer {token}"})
        except httpx.HTTPError as exc:
            raise XApiError(f"X read request failed: {safe_error(exc)}") from exc
        if response.status_code >= 400:
            raise XApiError(f"X read request failed with status {response.status_code}: {safe_response(response)}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise XApiError("X read response was not a JSON object")
        return payload


class XPublishingService:
    def __init__(
        self,
        config: XPublisherConfig,
        *,
        api_client: XApiClient | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.config = config
        self.now = now
        self.approvals = ApprovalStore(config.approval_file)
        self.publications = PublicationStore(config.publication_file)
        self.oauth = XOAuthManager(config, now=now)
        self.api_client = api_client or XApiClient(self.oauth)

    def queue_summary(self) -> dict[str, Any]:
        queue, _ = self._load_context()
        return {
            "queue_version": queue.queue_version,
            "source_batch_id": queue.source_batch_id,
            "publishable": [item.content_id for item in queue.publishable],
            "awaiting_human_approval": [item.content_id for item in queue.awaiting_human_approval],
            "blocked": [item.content_id for item in queue.blocked],
        }

    def preview(self, content_id: str) -> PublishPreview:
        queue, packs = self._load_context()
        item = _find_queue_item(queue, content_id)
        pack = _find_pack(packs, content_id)
        approval = self.approvals.latest(content_id)
        final_copy, approval_state = _effective_copy(item, pack, approval)
        enriched = enrich_own_post(pack, final_copy)
        final_copy = enriched.final_copy
        checksum = x_content_checksum(pack, final_copy)
        blockers = list(self._copy_blockers(item, pack, final_copy))
        blockers.extend(self._publication_blockers(item, checksum))
        if item.status is ContentReadiness.RED:
            blockers.append("RED content is permanently blocked from X publishing")
        return PublishPreview(
            content_id=item.content_id,
            project=item.project,
            readiness=item.status,
            approval_state=approval_state,
            exact_final_copy=final_copy,
            weighted_character_count=x_weighted_character_count(final_copy),
            attribution_url=item.attribution_url,
            content_checksum=checksum,
            snapshot_id=item.snapshot_id,
            snapshot_timestamp=item.snapshot_timestamp,
            refreshability=item.refreshability,
            would_publish=not blockers,
            blockers=tuple(dict.fromkeys(blockers)),
            official_handle=enriched.official_handle,
            hashtags=enriched.hashtags,
            media_path=enriched.media.path,
            media_kind=enriched.media.kind,
            media_source=enriched.media.source,
            enrichment_fingerprint=enriched.enrichment_fingerprint,
        )

    def approve(self, content_id: str, *, edited_copy: str | None = None) -> ApprovalRecord:
        queue, packs = self._load_context()
        item = _find_queue_item(queue, content_id)
        pack = _find_pack(packs, content_id)
        if item.status is ContentReadiness.RED:
            raise XApprovalError("RED content cannot be approved")
        if item.status is not ContentReadiness.YELLOW:
            raise XApprovalError("GREEN content does not require a YELLOW approval record")
        final_copy = edited_copy.strip() if edited_copy is not None else item.final_copy
        blockers = self._copy_blockers(item, pack, final_copy)
        if blockers:
            raise XApprovalError("Approval blocked: " + "; ".join(blockers))
        approved_at = self.now()
        record = ApprovalRecord(
            content_id=content_id,
            source_content_checksum=item.content_checksum,
            approved_content_checksum=x_content_checksum(pack, final_copy),
            approved_copy=final_copy,
            approved_at=_iso(approved_at),
            state="approved",
        )
        self.approvals.approve(record)
        return record

    def revoke(self, content_id: str) -> ApprovalRecord:
        return self.approvals.revoke(content_id, now=self.now())

    def publish(self, content_id: str, *, dry_run: bool, confirm_publish: bool = False) -> PublishResult | PublishPreview:
        preview = self.preview(content_id)
        if dry_run:
            return preview
        if not confirm_publish:
            raise XValidationError("Actual X publishing requires --confirm-publish")
        if not preview.would_publish:
            raise XValidationError("Publishing blocked: " + "; ".join(preview.blockers))
        now = self.now()
        attempt = PublicationRecord(
            content_id=content_id,
            content_checksum=preview.content_checksum,
            status="publishing",
            attempted_at=_iso(now),
            updated_at=_iso(now),
        )
        with _exclusive_publish_lock(self.config.publish_lock_file):
            duplicate_blockers = self._publication_blockers_by_id(content_id, preview.content_checksum)
            if duplicate_blockers:
                raise XDuplicateError("; ".join(duplicate_blockers))
            self.publications.append(attempt)
            try:
                post_id = self.api_client.create_post(preview.exact_final_copy)
            except XAmbiguousApiError as exc:
                ambiguous = attempt.model_copy(
                    update={"status": "ambiguous", "updated_at": _iso(self.now()), "safe_error": safe_error(exc)}
                )
                self.publications.replace_latest(ambiguous)
                raise
            except XPublisherError as exc:
                failed = attempt.model_copy(
                    update={"status": "failed", "updated_at": _iso(self.now()), "safe_error": safe_error(exc)}
                )
                self.publications.replace_latest(failed)
                raise
            published = attempt.model_copy(
                update={"status": "published", "updated_at": _iso(self.now()), "post_id": post_id}
            )
            self.publications.replace_latest(published)
        return PublishResult(
            content_id=content_id,
            status="published",
            post_id=post_id,
            content_checksum=preview.content_checksum,
            network_called=True,
            detail="Post created through the official X API",
        )

    def publish_next(self, *, dry_run: bool, confirm_publish: bool = False) -> PublishResult | PublishPreview:
        queue, _ = self._load_context()
        for item in queue.publishable + queue.awaiting_human_approval:
            preview = self.preview(item.content_id)
            if preview.would_publish:
                return self.publish(item.content_id, dry_run=dry_run, confirm_publish=confirm_publish)
        raise XValidationError("No currently publishable X queue item exists")

    def confirm_manual_publication(self, content_id: str, *, checksum: str) -> PublicationRecord:
        preview = self.preview(content_id)
        if preview.content_checksum != checksum:
            raise XValidationError("manual outbox checksum does not match current X content")
        if not preview.would_publish:
            raise XValidationError("manual confirmation blocked: " + "; ".join(preview.blockers))
        now = _iso(self.now())
        record = PublicationRecord(
            content_id=content_id,
            content_checksum=checksum,
            status="published",
            attempted_at=now,
            updated_at=now,
            safe_error="confirmed manually outside the X API",
        )
        with _exclusive_publish_lock(self.config.publish_lock_file):
            if self._publication_blockers_by_id(content_id, checksum):
                raise XDuplicateError("same content_id and checksum was already published")
            self.publications.append(record)
        return record

    def _load_context(self) -> tuple[XPublishQueue, tuple[ContentPackLite, ...]]:
        queue = load_x_queue(self.config.queue_file)
        batch_bytes = self.config.content_pack_file.read_bytes()
        if hashlib.sha256(batch_bytes).hexdigest() != queue.source_batch_hash:
            raise XValidationError("X queue is stale relative to the canonical content-pack artifact")
        _, packs = load_content_pack_batch(self.config.content_pack_file)
        ids = [item.content_id for item in queue.items]
        if len(ids) != len(set(ids)) or set(ids) != {pack.content_id for pack in packs}:
            raise XValidationError("X queue inventory does not match the canonical content-pack artifact")
        return queue, packs

    def _copy_blockers(self, item: XQueueItem, pack: ContentPackLite, final_copy: str) -> tuple[str, ...]:
        blockers: list[str] = []
        if item.channel != "X":
            blockers.append("queue item channel is not X")
        if item.content_checksum != x_content_checksum(pack, item.final_copy):
            blockers.append("queue content checksum does not match the canonical pack")
        candidate = pack.model_copy(
            update={"editorial": pack.editorial.model_copy(update={"x_post": final_copy})}
        )
        candidate = set_expected_source_hash(candidate)
        validation = validate_pack(candidate)
        if validation.errors:
            blockers.extend(f"content-pack validation: {error}" for error in validation.errors)
        if PLACEHOLDER_RE.search(final_copy):
            blockers.append("unresolved template placeholder remains")
        if "[object Object]" in final_copy:
            blockers.append("object serialization placeholder remains")
        if contains_unsupported_idn_hostname(final_copy):
            blockers.append("non-ASCII/IDN URL host syntax is unsupported")
        if item.attribution_url_required and item.attribution_url not in final_copy:
            blockers.append("exact attribution URL is missing from final copy")
        blockers.extend(_attribution_url_blockers(item))
        weighted_count = x_weighted_character_count(final_copy)
        if weighted_count > X_MAX_WEIGHTED_LENGTH:
            blockers.append(f"X weighted character count {weighted_count} exceeds {X_MAX_WEIGHTED_LENGTH}")
        if pack.source.opportunity_id != "gamcryp-methodology" and item.project.lower() not in final_copy.lower():
            blockers.append("project-specific final copy does not name the project")
        blockers.extend(_unsafe_wording_blockers(final_copy))
        blockers.extend(actionable_x_copy_blockers(pack, final_copy))
        if pack.claims:
            if not item.snapshot_timestamp:
                blockers.append("numeric content is missing snapshot timestamp")
            else:
                age = self.now() - _parse_datetime(item.snapshot_timestamp)
                if age.total_seconds() > self.config.max_snapshot_age_seconds:
                    blockers.append("snapshot-backed numeric content is stale")
            if pack.facts.freshness.display.lower() != "fresh":
                blockers.append("numeric content source freshness is not fresh")
        return tuple(dict.fromkeys(blockers))

    def _publication_blockers(self, item: XQueueItem, checksum: str) -> tuple[str, ...]:
        return self._publication_blockers_by_id(item.content_id, checksum)

    def _publication_blockers_by_id(self, content_id: str, checksum: str) -> tuple[str, ...]:
        blockers: list[str] = []
        records = self.publications.records(content_id)
        if any(record.status == "published" and record.content_checksum == checksum for record in records):
            blockers.append("same content_id and checksum were already published")
        if any(record.status in {"publishing", "ambiguous"} for record in records):
            blockers.append("an unresolved publishing/ambiguous attempt requires manual reconciliation")
        return tuple(blockers)


def _find_queue_item(queue: XPublishQueue, content_id: str) -> XQueueItem:
    try:
        return queue.find(content_id)
    except KeyError as exc:
        raise XValidationError(f"Unknown X queue content_id: {content_id}") from exc


def _find_pack(packs: tuple[ContentPackLite, ...], content_id: str) -> ContentPackLite:
    matches = [pack for pack in packs if pack.content_id == content_id]
    if len(matches) != 1:
        raise XValidationError(f"Canonical content pack not found: {content_id}")
    return matches[0]


def _effective_copy(
    item: XQueueItem,
    pack: ContentPackLite,
    approval: ApprovalRecord | None,
) -> tuple[str, str]:
    if not item.approval_required:
        return item.final_copy, "not_required"
    if approval is None or approval.state != "approved":
        return item.final_copy, "awaiting_human_approval"
    if approval.source_content_checksum != item.content_checksum:
        return item.final_copy, "approval_invalidated_by_content_change"
    if x_content_checksum(pack, approval.approved_copy) != approval.approved_content_checksum:
        return item.final_copy, "approval_record_checksum_mismatch"
    return approval.approved_copy, "approved"


def _attribution_url_blockers(item: XQueueItem) -> tuple[str, ...]:
    parsed = urlsplit(item.attribution_url)
    blockers: list[str] = []
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"gamcryp.com", "www.gamcryp.com"}:
        blockers.append("attribution URL must use the canonical GamCryp HTTPS host")
    query = parse_qs(parsed.query)
    expected = {
        "utm_source": "x",
        "utm_medium": "social",
        "utm_campaign": "distribution-mvp",
        "utm_content": item.content_id,
    }
    for key, value in expected.items():
        if query.get(key) != [value]:
            blockers.append(f"attribution URL has invalid {key}")
    return tuple(blockers)


def _unsafe_wording_blockers(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    forbidden = ("guaranteed", "risk-free", "no risk", "buy this", "start this now", "easy profit")
    return tuple(f"forbidden recommendation/promise wording: {phrase}" for phrase in forbidden if phrase in lowered)


@contextmanager
def _exclusive_publish_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise XDuplicateError("Another X publish operation may be in progress") from exc
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        path.unlink(missing_ok=True)


def safe_error(value: object) -> str:
    text = BEARER_RE.sub("Bearer [redacted]", str(value))
    return SENSITIVE_TEXT_RE.sub(lambda match: f"{match.group(1)}{match.group(2)}[redacted]", text)[:MAX_SAFE_ERROR_LENGTH]


def safe_response(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return safe_error(response.text)
    return safe_error(_redact_mapping(payload))


def _redact_mapping(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[redacted]" if re.search(r"(?i)(secret|token|authorization|password|credential)", str(key)) else _redact_mapping(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_mapping(item) for item in value[:20]]
    return value


def _write_private_model(path: Path, value: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value.model_dump_json(indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        _chmod_private(path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _load_private_model(path: Path, model: type[BaseModel]) -> Any:
    if not path.is_file():
        raise XAuthError(f"OAuth state file is missing: {path.name}")
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _chmod_private(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        logger.debug("x_private_chmod_skipped", extra={"path_name": path.name})


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise XValidationError("Snapshot timestamp must include timezone information")
    return parsed.astimezone(UTC)
