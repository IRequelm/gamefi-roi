"""Production-safe YouTube Data API publishing primitives for GamCryp."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config.settings import Settings

logger = logging.getLogger(__name__)

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_PUBLISH_SCOPES = ("https://www.googleapis.com/auth/youtube.force-ssl",)
SUPPORTED_VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".m4v", ".webm"})
SUPPORTED_THUMBNAIL_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})
MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024
MAX_SAFE_ERROR_LENGTH = 500
SENSITIVE_TEXT_PATTERN = re.compile(
    r"(?i)(client[_-]?secret|refresh[_-]?token|access[_-]?token|api[_-]?key|authorization|bearer|password|credential)"
    r"([\s:=]+)([^\s,;&]+)"
)
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(secret|token|authorization|password|credential|api[_-]?key|client[_-]?secret|refresh[_-]?token|access[_-]?token)"
)
BEARER_TEXT_PATTERN = re.compile(r"(?i)Bearer\s+[^\s,;&]+")
PrivacyStatus = Literal["private", "unlisted", "public"]


class YouTubePublisherError(RuntimeError):
    """Base class for safe, operator-facing publisher errors."""


class YouTubeConfigError(YouTubePublisherError):
    """Raised when YouTube publisher configuration is incomplete or unsafe."""


class YouTubeAuthError(YouTubePublisherError):
    """Raised when OAuth credentials are missing, invalid, or cannot refresh."""


class YouTubeApiError(YouTubePublisherError):
    """Raised when the YouTube Data API returns an error."""


class DuplicateUploadError(YouTubePublisherError):
    """Raised when a publish manifest would reuse a content id unsafely."""


class YouTubeManifestError(YouTubePublisherError):
    """Raised when a publish manifest is invalid."""


class YouTubePublishManifest(BaseModel):
    """Approved content manifest for one YouTube publish operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    video_path: Path
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=5000)
    thumbnail_path: Path | None = None
    tags: tuple[str, ...] = ()
    privacy: PrivacyStatus = "private"
    publish_at: datetime | None = None
    category_id: str | None = Field(default=None, pattern=r"^[0-9]{1,4}$")
    made_for_kids: bool = False
    source_snapshot_id: str | None = Field(default=None, max_length=120)
    source_snapshot_timestamp: datetime | None = None
    campaign_source: str | None = Field(default=None, max_length=80)
    campaign_medium: str | None = Field(default=None, max_length=80)
    campaign_campaign: str | None = Field(default=None, max_length=120)
    existing_video_id: str | None = Field(default=None, max_length=64)

    @field_validator("title", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("manifest text fields must not be blank")
        return text

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        raw_values = value.split(",") if isinstance(value, str) else list(value)  # type: ignore[arg-type]
        tags = tuple(str(item).strip() for item in raw_values if str(item).strip())
        if len(tags) > 30:
            raise ValueError("YouTube tag list must contain at most 30 tags")
        if any(len(tag) > 60 for tag in tags):
            raise ValueError("YouTube tags must be 60 characters or fewer")
        if len(",".join(tags)) > 500:
            raise ValueError("YouTube tag list exceeds the 500-character API limit")
        return tags

    @field_validator("publish_at", "source_snapshot_timestamp")
    @classmethod
    def normalize_aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("timestamps must include timezone information")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_scheduling(self) -> "YouTubePublishManifest":
        if self.publish_at is not None and self.privacy != "private":
            raise ValueError("scheduled publish_at requires privacy='private' for YouTube scheduling")
        return self

    def manifest_hash(self) -> str:
        payload = self.model_dump(mode="json")
        payload["video_path"] = Path(self.video_path).name
        if self.thumbnail_path is not None:
            payload["thumbnail_path"] = Path(self.thumbnail_path).name
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def safe_summary(self) -> dict[str, Any]:
        return {
            "content_id": self.content_id,
            "video_file": Path(self.video_path).name,
            "thumbnail_file": Path(self.thumbnail_path).name if self.thumbnail_path else None,
            "title": self.title,
            "privacy": self.privacy,
            "publish_at": self.publish_at.isoformat() if self.publish_at else None,
            "category_id": self.category_id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_snapshot_timestamp": self.source_snapshot_timestamp.isoformat()
            if self.source_snapshot_timestamp
            else None,
            "campaign_source": self.campaign_source,
            "campaign_medium": self.campaign_medium,
            "campaign_campaign": self.campaign_campaign,
            "has_existing_video_id": bool(self.existing_video_id),
        }


@dataclass(frozen=True)
class YouTubePublisherConfig:
    client_secrets_file: Path | None
    token_file: Path | None
    state_file: Path
    channel_handle: str = "@GamCryp"
    scopes: tuple[str, ...] = YOUTUBE_PUBLISH_SCOPES
    max_retries: int = 2

    @classmethod
    def from_settings(cls, settings: Settings) -> "YouTubePublisherConfig":
        return cls(
            client_secrets_file=Path(settings.youtube_oauth_client_secrets_file)
            if settings.youtube_oauth_client_secrets_file
            else None,
            token_file=Path(settings.youtube_oauth_token_file) if settings.youtube_oauth_token_file else None,
            state_file=Path(settings.youtube_publish_state_file),
            channel_handle=settings.youtube_channel_handle,
            max_retries=settings.youtube_max_retries,
        )

    def require_oauth_config(self, *, require_token_path: bool = True) -> None:
        if self.client_secrets_file is None:
            raise YouTubeConfigError("GAMEFI_YOUTUBE_OAUTH_CLIENT_SECRETS_FILE is required")
        if require_token_path and self.token_file is None:
            raise YouTubeConfigError("GAMEFI_YOUTUBE_OAUTH_TOKEN_FILE is required")


@dataclass(frozen=True)
class AuthState:
    configured: bool
    client_secrets_exists: bool
    token_exists: bool
    authorized: bool
    refresh_available: bool
    scopes: tuple[str, ...]
    detail: str

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "client_secrets_exists": self.client_secrets_exists,
            "token_exists": self.token_exists,
            "authorized": self.authorized,
            "refresh_available": self.refresh_available,
            "scopes": list(self.scopes),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class PublishRecord:
    content_id: str
    video_checksum_sha256: str
    manifest_hash: str
    video_id: str | None
    status: str
    uploaded_at: str


@dataclass(frozen=True)
class YouTubeOperationResult:
    operation: str
    status: str
    would_mutate: bool
    content_id: str | None = None
    video_id: str | None = None
    detail: str = ""
    response: Mapping[str, Any] | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "operation": self.operation,
            "status": self.status,
            "would_mutate": self.would_mutate,
            "content_id": self.content_id,
            "video_id": self.video_id,
            "detail": self.detail,
        }
        if self.response is not None:
            payload["response"] = sanitize_mapping(self.response)
        return payload


class TokenStore:
    """Local OAuth token store with best-effort private file permissions."""

    def __init__(self, path: Path | None):
        self.path = path

    @property
    def exists(self) -> bool:
        return self.path is not None and self.path.exists() and self.path.is_file()

    def load_credentials(self, scopes: Sequence[str] = YOUTUBE_PUBLISH_SCOPES) -> Any | None:
        if self.path is None or not self.path.exists():
            return None
        try:
            from google.oauth2.credentials import Credentials
        except ImportError as exc:  # pragma: no cover - exercised only without optional deps.
            raise YouTubeAuthError("Google OAuth libraries are not installed") from exc
        return Credentials.from_authorized_user_file(str(self.path), scopes=list(scopes))

    def save_credentials(self, credentials: Any) -> None:
        if not hasattr(credentials, "to_json"):
            raise YouTubeAuthError("OAuth credentials object cannot be serialized")
        self.save_credentials_json(credentials.to_json())

    def save_credentials_json(self, payload: str) -> None:
        if self.path is None:
            raise YouTubeConfigError("GAMEFI_YOUTUBE_OAUTH_TOKEN_FILE is required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=str(self.path.parent), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.write("\n")
            os.replace(temp_name, self.path)
            _chmod_private(self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


class PublishStateStore:
    """Small local manifest state file used to avoid duplicate uploads."""

    def __init__(self, path: Path):
        self.path = path

    def find(self, content_id: str) -> PublishRecord | None:
        records = self._read_records()
        raw = records.get(content_id)
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise YouTubeManifestError("YouTube publish state record is malformed")
        try:
            return PublishRecord(
                content_id=str(raw["content_id"]),
                video_checksum_sha256=str(raw["video_checksum_sha256"]),
                manifest_hash=str(raw["manifest_hash"]),
                video_id=str(raw["video_id"]) if raw.get("video_id") else None,
                status=str(raw["status"]),
                uploaded_at=str(raw["uploaded_at"]),
            )
        except KeyError as exc:
            raise YouTubeManifestError("YouTube publish state record is incomplete") from exc

    def record_uploaded(
        self,
        *,
        content_id: str,
        video_checksum_sha256: str,
        manifest_hash: str,
        video_id: str,
        now: datetime | None = None,
    ) -> PublishRecord:
        record = PublishRecord(
            content_id=content_id,
            video_checksum_sha256=video_checksum_sha256,
            manifest_hash=manifest_hash,
            video_id=video_id,
            status="uploaded",
            uploaded_at=(now or datetime.now(UTC)).isoformat(),
        )
        records = self._read_records()
        records[content_id] = {
            "content_id": record.content_id,
            "video_checksum_sha256": record.video_checksum_sha256,
            "manifest_hash": record.manifest_hash,
            "video_id": record.video_id,
            "status": record.status,
            "uploaded_at": record.uploaded_at,
        }
        self._write_records(records)
        return record

    def record_attempt(
        self,
        *,
        content_id: str,
        video_checksum_sha256: str,
        manifest_hash: str,
        status: Literal["uploading", "ambiguous"],
        now: datetime | None = None,
    ) -> PublishRecord:
        record = PublishRecord(
            content_id=content_id,
            video_checksum_sha256=video_checksum_sha256,
            manifest_hash=manifest_hash,
            video_id=None,
            status=status,
            uploaded_at=(now or datetime.now(UTC)).isoformat(),
        )
        records = self._read_records()
        records[content_id] = {
            "content_id": record.content_id,
            "video_checksum_sha256": record.video_checksum_sha256,
            "manifest_hash": record.manifest_hash,
            "video_id": None,
            "status": record.status,
            "uploaded_at": record.uploaded_at,
        }
        self._write_records(records)
        return record

    def mark_ambiguous(self, content_id: str) -> PublishRecord:
        """Retain an unreconciled historical upload without permitting retry."""
        records = self._read_records()
        raw = records.get(content_id)
        if not isinstance(raw, dict):
            raise YouTubeManifestError("No local publication record exists to reconcile")
        raw["status"] = "ambiguous"
        raw["video_id"] = None
        records[content_id] = raw
        self._write_records(records)
        reconciled = self.find(content_id)
        if reconciled is None:
            raise YouTubeManifestError("Reconciled publication record could not be reloaded")
        return reconciled

    def _read_records(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise YouTubeManifestError("YouTube publish state must be a JSON object")
        records = payload.get("records", payload)
        if not isinstance(records, dict):
            raise YouTubeManifestError("YouTube publish state records must be a JSON object")
        return records

    def _write_records(self, records: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "records": records}
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=str(self.path.parent), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temp_name, self.path)
            _chmod_private(self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


class YouTubePublisher:
    """Thin wrapper around YouTube Data API operations."""

    def __init__(
        self,
        *,
        config: YouTubePublisherConfig,
        service: Any | None = None,
        token_store: TokenStore | None = None,
        state_store: PublishStateStore | None = None,
        media_factory: Callable[..., Any] | None = None,
        request_factory: Callable[[], Any] | None = None,
    ):
        self.config = config
        self._service = service
        self.token_store = token_store or TokenStore(config.token_file)
        self.state_store = state_store or PublishStateStore(config.state_file)
        self.media_factory = media_factory or google_media_file_upload
        self.request_factory = request_factory or google_auth_request

    def validate_auth_state(self) -> AuthState:
        configured = self.config.client_secrets_file is not None and self.config.token_file is not None
        client_exists = self.config.client_secrets_file is not None and self.config.client_secrets_file.is_file()
        token_exists = self.token_store.exists
        authorized = False
        refresh_available = False
        detail = "OAuth config missing"
        if configured and not client_exists:
            detail = "OAuth client secrets file is missing"
        elif configured and not token_exists:
            detail = "OAuth token file is missing; first-time authorization is required"
        elif configured:
            try:
                credentials = self.token_store.load_credentials(self.config.scopes)
                authorized = bool(getattr(credentials, "valid", False))
                refresh_available = bool(getattr(credentials, "refresh_token", None))
                detail = "OAuth token is valid" if authorized else "OAuth token can refresh" if refresh_available else "OAuth token is invalid"
            except YouTubePublisherError as exc:
                detail = str(exc)
        return AuthState(configured, client_exists, token_exists, authorized, refresh_available, self.config.scopes, detail)

    def authorize_interactive(self) -> AuthState:
        self.config.require_oauth_config(require_token_path=True)
        assert self.config.client_secrets_file is not None
        if not self.config.client_secrets_file.is_file():
            raise YouTubeConfigError("OAuth client secrets file does not exist")
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as exc:  # pragma: no cover - exercised only without optional deps.
            raise YouTubeAuthError("google-auth-oauthlib is not installed") from exc
        flow = InstalledAppFlow.from_client_secrets_file(str(self.config.client_secrets_file), scopes=list(self.config.scopes))
        credentials = flow.run_local_server(
            port=0,
            access_type="offline",
            prompt="consent",
            authorization_prompt_message="Open this URL to authorize GamCryp YouTube publishing:\n{url}\n",
            success_message="GamCryp YouTube authorization complete. You can close this tab.",
        )
        self.token_store.save_credentials(credentials)
        return self.validate_auth_state()

    def dry_run_upload(self, manifest: YouTubePublishManifest) -> YouTubeOperationResult:
        validate_video_file(manifest.video_path)
        if manifest.thumbnail_path is not None:
            validate_thumbnail_file(manifest.thumbnail_path)
        checksum = sha256_file(manifest.video_path)
        duplicate = self._duplicate_record(manifest, checksum)
        status = "would_skip_duplicate" if duplicate else "ready"
        detail = "existing successful upload found" if duplicate else "validated manifest and local files; no API mutation performed"
        logger.info("youtube_publish_dry_run", extra={"content_id": manifest.content_id, "status": status})
        return YouTubeOperationResult(
            operation="dry_run_upload",
            status=status,
            would_mutate=False,
            content_id=manifest.content_id,
            video_id=duplicate.video_id if duplicate else manifest.existing_video_id,
            detail=detail,
            response=manifest.safe_summary(),
        )

    def check_capabilities(self) -> dict[str, Any]:
        """Read-only live probe; scopes prove authorization, never upload success."""
        result = {"configured": self.validate_auth_state().configured,
                  "authenticated": False, "channel_verified": False,
                  "upload_scope_verified": False, "upload_test_performed": False}
        try:
            credentials = load_refreshed_credentials(config=self.config, token_store=self.token_store, request_factory=self.request_factory)
            result["authenticated"] = bool(credentials.valid)
            service = self.service
            owned = self._execute(service.channels().list(part="id,snippet,contentDetails", mine=True), operation="verify_channel")
            intended = self._execute(service.channels().list(part="id", forHandle=self.config.channel_handle), operation="resolve_channel")
            intended_ids = {item["id"] for item in intended.get("items", [])}
            channels = owned.get("items", [])
            result["channel_ids"] = [item["id"] for item in channels]
            result["channel_verified"] = len(channels) == 1 and channels[0]["id"] in intended_ids
            raw = json.loads(self.config.token_file.read_text(encoding="utf-8"))
            scopes = raw.get("scopes", [])
            result["upload_scope_verified"] = result["channel_verified"] and any(scope in scopes for scope in (
                "https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl", "https://www.googleapis.com/auth/youtube"))
            result["detail"] = "Read-only auth/channel probe; permission inferred from stored scopes; no upload performed."
        except Exception as exc:
            result["error_category"] = type(exc).__name__
            result["detail"] = "Capability probe failed; no upload capability is claimed."
        return result

    def upload_video(self, manifest: YouTubePublishManifest) -> YouTubeOperationResult:
        self.config.require_oauth_config(require_token_path=True)
        validate_video_file(manifest.video_path)
        checksum = sha256_file(manifest.video_path)
        with _exclusive_upload_lock(self.config.state_file.with_suffix(".lock")):
            duplicate = self._duplicate_record(manifest, checksum)
            if duplicate is not None:
                logger.info("youtube_upload_skipped_duplicate", extra={"content_id": manifest.content_id, "video_id": duplicate.video_id})
                return YouTubeOperationResult("upload_video", "skipped_duplicate", False, manifest.content_id, duplicate.video_id, "same content_id and video checksum were already uploaded")
            manifest_hash = manifest.manifest_hash()
            body = self._video_body(manifest)
            media_body = self.media_factory(str(manifest.video_path), mimetype="video/*", resumable=True)
            request = self.service.videos().insert(part="snippet,status", body=body, media_body=media_body, notifySubscribers=False)
            self.state_store.record_attempt(
                content_id=manifest.content_id,
                video_checksum_sha256=checksum,
                manifest_hash=manifest_hash,
                status="uploading",
            )
            try:
                response = self._execute(request, operation="upload_video")
                video_id = str(response.get("id", "")).strip() if isinstance(response, Mapping) else ""
                if not video_id:
                    raise YouTubeApiError("YouTube upload response did not include a video id")
            except YouTubeApiError:
                self.state_store.record_attempt(
                    content_id=manifest.content_id,
                    video_checksum_sha256=checksum,
                    manifest_hash=manifest_hash,
                    status="ambiguous",
                )
                raise
            self.state_store.record_uploaded(
                content_id=manifest.content_id,
                video_checksum_sha256=checksum,
                manifest_hash=manifest_hash,
                video_id=video_id,
            )
        logger.info("youtube_upload_succeeded", extra={"content_id": manifest.content_id, "video_id": video_id})
        return YouTubeOperationResult("upload_video", "uploaded", True, manifest.content_id, video_id, "video uploaded through YouTube Data API", response)

    def set_thumbnail(self, *, video_id: str, image_path: Path, dry_run: bool = False) -> YouTubeOperationResult:
        safe_video_id = validate_video_id(video_id)
        validate_thumbnail_file(image_path)
        if dry_run:
            return YouTubeOperationResult("set_thumbnail", "ready", False, video_id=safe_video_id, detail="validated thumbnail file; no API mutation performed", response={"thumbnail_file": Path(image_path).name})
        self.config.require_oauth_config(require_token_path=True)
        media_body = self.media_factory(str(image_path), mimetype=thumbnail_mime_type(image_path), resumable=True)
        request = self.service.thumbnails().set(videoId=safe_video_id, media_body=media_body)
        response = self._execute(request, operation="set_thumbnail")
        logger.info("youtube_thumbnail_set", extra={"video_id": safe_video_id})
        return YouTubeOperationResult("set_thumbnail", "thumbnail_set", True, video_id=safe_video_id, detail="thumbnail uploaded through YouTube Data API", response=response)

    def update_video_metadata(
        self,
        *,
        video_id: str,
        title: str | None = None,
        description: str | None = None,
        tags: Sequence[str] | None = None,
        privacy: PrivacyStatus | None = None,
        publish_at: datetime | None = None,
        category_id: str | None = None,
    ) -> YouTubeOperationResult:
        safe_video_id = validate_video_id(video_id)
        updates = YouTubeMetadataUpdate(title=title, description=description, tags=tuple(tags) if tags is not None else None, privacy=privacy, publish_at=publish_at, category_id=category_id)
        if not updates.has_changes:
            raise YouTubeManifestError("metadata update requires at least one field")
        current = self.get_video_status(safe_video_id, parts=("snippet", "status"))
        body: dict[str, Any] = {"id": safe_video_id}
        parts: list[str] = []
        if updates.has_snippet_changes:
            snippet = dict(current.get("snippet", {})) if isinstance(current.get("snippet"), Mapping) else {}
            snippet["title"] = updates.title if updates.title is not None else snippet.get("title")
            snippet["description"] = updates.description if updates.description is not None else snippet.get("description")
            if updates.tags is not None:
                snippet["tags"] = list(updates.tags)
            if updates.category_id is not None:
                snippet["categoryId"] = updates.category_id
            if not snippet.get("title") or not snippet.get("categoryId"):
                raise YouTubeManifestError("metadata updates that touch snippet require title and categoryId")
            body["snippet"] = snippet
            parts.append("snippet")
        if updates.has_status_changes:
            status = dict(current.get("status", {})) if isinstance(current.get("status"), Mapping) else {}
            if updates.privacy is not None:
                status["privacyStatus"] = updates.privacy
            if updates.publish_at is not None:
                status["publishAt"] = updates.publish_at.isoformat().replace("+00:00", "Z")
                status["privacyStatus"] = "private"
            body["status"] = status
            parts.append("status")
        response = self._execute(self.service.videos().update(part=",".join(parts), body=body), operation="update_video_metadata")
        logger.info("youtube_metadata_updated", extra={"video_id": safe_video_id, "parts": parts})
        return YouTubeOperationResult("update_video_metadata", "metadata_updated", True, video_id=safe_video_id, detail="video metadata updated through YouTube Data API", response=response)

    def get_video_status(self, video_id: str, parts: Sequence[str] | None = None) -> dict[str, Any]:
        safe_video_id = validate_video_id(video_id)
        self.config.require_oauth_config(require_token_path=True)
        requested_parts = parts or ("snippet", "status", "processingDetails", "contentDetails")
        response = self._execute(self.service.videos().list(part=",".join(requested_parts), id=safe_video_id), operation="get_video_status")
        items = response.get("items")
        if not isinstance(items, list) or not items or not isinstance(items[0], dict):
            raise YouTubeApiError("YouTube video was not found or is not visible to the authenticated channel")
        return items[0]

    def verify_video(self, video_id: str) -> YouTubeOperationResult:
        status = self.get_video_status(video_id)
        upload_status = _nested_value(status, ("status", "uploadStatus")) or "unknown"
        processing_status = _nested_value(status, ("processingDetails", "processingStatus")) or "unknown"
        return YouTubeOperationResult(
            "verify_video",
            "verified",
            False,
            video_id=validate_video_id(video_id),
            detail=f"upload_status={upload_status}; processing_status={processing_status}",
            response={"id": status.get("id"), "privacyStatus": _nested_value(status, ("status", "privacyStatus")), "uploadStatus": upload_status, "processingStatus": processing_status},
        )

    def verify_thumbnail(self, video_id: str) -> YouTubeOperationResult:
        status = self.get_video_status(video_id, parts=("snippet", "contentDetails"))
        custom = _nested_value(status, ("contentDetails", "hasCustomThumbnail"))
        thumbnails = _nested_value(status, ("snippet", "thumbnails")) or {}
        return YouTubeOperationResult(
            "verify_thumbnail",
            "thumbnail_verified" if custom is True else "thumbnail_unknown",
            False,
            video_id=validate_video_id(video_id),
            detail="custom thumbnail is present" if custom is True else "custom thumbnail flag is unavailable or false",
            response={"id": status.get("id"), "hasCustomThumbnail": custom, "thumbnailKeys": sorted(thumbnails.keys()) if isinstance(thumbnails, Mapping) else []},
        )

    @property
    def service(self) -> Any:
        if self._service is None:
            credentials = load_refreshed_credentials(config=self.config, token_store=self.token_store, request_factory=self.request_factory)
            self._service = build_youtube_service(credentials)
        return self._service

    def _duplicate_record(self, manifest: YouTubePublishManifest, checksum: str) -> PublishRecord | None:
        record = self.state_store.find(manifest.content_id)
        if record is None:
            return None
        if record.status in {"uploading", "ambiguous"}:
            raise DuplicateUploadError(
                "content_id has an unresolved upload attempt; reconcile the YouTube channel before retrying"
            )
        if record.video_checksum_sha256 != checksum:
            raise DuplicateUploadError("content_id already exists with a different video checksum; choose a new content_id or review state")
        return record

    def reconcile_local_state(self) -> dict[str, Any]:
        """Read recorded uploads and block retries for missing channel videos."""
        outcome: dict[str, Any] = {"verified": [], "ambiguous": [], "errors": []}
        for raw in self.state_store._read_records().values():
            try:
                record = PublishRecord(**raw)
            except (TypeError, ValueError):
                outcome["errors"].append({"error_category": "YouTubeManifestError"})
                continue
            if record.status != "uploaded" or not record.video_id:
                if record.status == "ambiguous":
                    outcome["ambiguous"].append(record.content_id)
                continue
            try:
                self.get_video_status(record.video_id)
                outcome["verified"].append(record.content_id)
            except YouTubeApiError:
                self.state_store.mark_ambiguous(record.content_id)
                outcome["ambiguous"].append(record.content_id)
            except Exception as exc:
                outcome["errors"].append({"content_id": record.content_id, "error_category": type(exc).__name__})
        return outcome

    def _video_body(self, manifest: YouTubePublishManifest) -> dict[str, Any]:
        snippet: dict[str, Any] = {"title": manifest.title, "description": manifest.description}
        if manifest.tags:
            snippet["tags"] = list(manifest.tags)
        if manifest.category_id:
            snippet["categoryId"] = manifest.category_id
        status: dict[str, Any] = {
            "privacyStatus": manifest.privacy,
            "selfDeclaredMadeForKids": manifest.made_for_kids,
        }
        if manifest.publish_at:
            status["publishAt"] = manifest.publish_at.isoformat().replace("+00:00", "Z")
        return {"snippet": snippet, "status": status}

    def _execute(self, request: Any, *, operation: str) -> Mapping[str, Any]:
        try:
            try:
                response = request.execute(num_retries=self.config.max_retries)
            except TypeError:
                response = request.execute()
        except Exception as exc:
            raise YouTubeApiError(format_youtube_exception(exc, operation=operation)) from exc
        if not isinstance(response, Mapping):
            raise YouTubeApiError(f"{operation} returned a non-object response")
        return response


class YouTubeMetadataUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    tags: tuple[str, ...] | None = None
    privacy: PrivacyStatus | None = None
    publish_at: datetime | None = None
    category_id: str | None = Field(default=None, pattern=r"^[0-9]{1,4}$")

    @field_validator("title", "description")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("metadata text fields must not be blank")
        return text

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_optional_tags(cls, value: object) -> tuple[str, ...] | None:
        if value is None:
            return None
        return YouTubePublishManifest.normalize_tags(value)

    @field_validator("publish_at")
    @classmethod
    def normalize_publish_at(cls, value: datetime | None) -> datetime | None:
        return YouTubePublishManifest.normalize_aware_timestamp(value)

    @property
    def has_changes(self) -> bool:
        return any(value is not None for value in (self.title, self.description, self.tags, self.privacy, self.publish_at, self.category_id))

    @property
    def has_snippet_changes(self) -> bool:
        return any(value is not None for value in (self.title, self.description, self.tags, self.category_id))

    @property
    def has_status_changes(self) -> bool:
        return self.privacy is not None or self.publish_at is not None


def load_manifest(path: Path) -> YouTubePublishManifest:
    if not path.is_file():
        raise YouTubeManifestError(f"manifest file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    try:
        return YouTubePublishManifest.model_validate(payload)
    except Exception as exc:
        raise YouTubeManifestError(f"manifest validation failed: {redact_sensitive_text(str(exc))}") from exc


def load_refreshed_credentials(*, config: YouTubePublisherConfig, token_store: TokenStore, request_factory: Callable[[], Any]) -> Any:
    config.require_oauth_config(require_token_path=True)
    credentials = token_store.load_credentials(config.scopes)
    if credentials is None:
        raise YouTubeAuthError("OAuth token file is missing; run youtube-publisher authorize first")
    if getattr(credentials, "valid", False):
        return credentials
    if getattr(credentials, "expired", False) and getattr(credentials, "refresh_token", None):
        try:
            credentials.refresh(request_factory())
        except Exception as exc:
            raise YouTubeAuthError(format_youtube_exception(exc, operation="refresh_token")) from exc
        token_store.save_credentials(credentials)
        return credentials
    raise YouTubeAuthError("OAuth token is invalid and cannot refresh; run youtube-publisher authorize again")


def build_youtube_service(credentials: Any) -> Any:
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - exercised only without optional deps.
        raise YouTubeAuthError("google-api-python-client is not installed") from exc
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials, cache_discovery=False)


def google_media_file_upload(path: str, *, mimetype: str, resumable: bool = True) -> Any:
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:  # pragma: no cover - exercised only without optional deps.
        raise YouTubeAuthError("google-api-python-client is not installed") from exc
    return MediaFileUpload(path, mimetype=mimetype, resumable=resumable)


def google_auth_request() -> Any:
    try:
        from google.auth.transport.requests import Request
    except ImportError as exc:  # pragma: no cover - exercised only without optional deps.
        raise YouTubeAuthError("google-auth is not installed") from exc
    return Request()


def validate_video_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise YouTubeManifestError(f"video file does not exist: {path}")
    if path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        raise YouTubeManifestError("video file must be one of: .mp4, .mov, .m4v, .webm")
    if path.stat().st_size <= 0:
        raise YouTubeManifestError("video file must not be empty")


def validate_thumbnail_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise YouTubeManifestError(f"thumbnail file does not exist: {path}")
    if path.suffix.lower() not in SUPPORTED_THUMBNAIL_EXTENSIONS:
        raise YouTubeManifestError("thumbnail file must be JPEG or PNG")
    size = path.stat().st_size
    if size <= 0:
        raise YouTubeManifestError("thumbnail file must not be empty")
    if size > MAX_THUMBNAIL_BYTES:
        raise YouTubeManifestError("thumbnail file must be 2MB or smaller")


def validate_video_id(value: str) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", text):
        raise YouTubeManifestError("YouTube video id is invalid")
    return text


def thumbnail_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    raise YouTubeManifestError("thumbnail file must be JPEG or PNG")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def format_youtube_exception(exc: Exception, *, operation: str) -> str:
    status = getattr(getattr(exc, "resp", None), "status", None)
    reason = getattr(getattr(exc, "resp", None), "reason", "")
    content = getattr(exc, "content", "")
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    pieces = [operation]
    if status:
        pieces.append(f"status={status}")
    if reason:
        pieces.append(f"reason={reason}")
    safe_content = redact_sensitive_text(str(content or exc))[:MAX_SAFE_ERROR_LENGTH]
    if safe_content:
        pieces.append(f"error={safe_content}")
    return "; ".join(pieces)


def sanitize_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        text_key = str(key)
        if SENSITIVE_KEY_PATTERN.search(text_key):
            safe[text_key] = "[redacted]"
        elif isinstance(value, Mapping):
            safe[text_key] = sanitize_mapping(value)
        elif isinstance(value, list):
            safe[text_key] = [sanitize_mapping(item) if isinstance(item, Mapping) else item for item in value[:20]]
        else:
            safe[text_key] = value
    return safe


def redact_sensitive_text(value: str) -> str:
    redacted = BEARER_TEXT_PATTERN.sub("Bearer [redacted]", value)
    return SENSITIVE_TEXT_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}[redacted]", redacted)


def _nested_value(payload: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _chmod_private(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        logger.debug("youtube_private_chmod_skipped", extra={"path_name": path.name})


@contextmanager
def _exclusive_upload_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise DuplicateUploadError("another YouTube upload operation is already in progress") from exc
    try:
        os.close(descriptor)
        yield
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
