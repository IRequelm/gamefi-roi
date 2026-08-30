from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.publishing.youtube import (
    DuplicateUploadError,
    PublishStateStore,
    TokenStore,
    YouTubeApiError,
    YouTubeConfigError,
    YouTubeManifestError,
    YouTubePublishManifest,
    YouTubePublisher,
    YouTubePublisherConfig,
    format_youtube_exception,
    load_manifest,
    load_refreshed_credentials,
    redact_sensitive_text,
    sanitize_mapping,
)


class FakeExecute:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response or {}
        self.error = error
        self.num_retries = None
        self.called = 0

    def execute(self, num_retries=0):
        self.called += 1
        self.num_retries = num_retries
        if self.error is not None:
            raise self.error
        return self.response


class FakeVideosResource:
    def __init__(self):
        self.insert_calls = []
        self.update_calls = []
        self.list_calls = []
        self.next_insert = FakeExecute({"id": "abc123VIDEO"})
        self.next_update = FakeExecute({"id": "abc123VIDEO", "status": {"privacyStatus": "private"}})
        self.next_list = FakeExecute(
            {
                "items": [
                    {
                        "id": "abc123VIDEO",
                        "snippet": {
                            "title": "Current title",
                            "description": "Current description",
                            "categoryId": "28",
                            "thumbnails": {"high": {"url": "https://i.example/thumb.jpg"}},
                        },
                        "status": {"privacyStatus": "private", "uploadStatus": "processed"},
                        "processingDetails": {"processingStatus": "succeeded"},
                        "contentDetails": {"hasCustomThumbnail": True},
                    }
                ]
            }
        )

    def insert(self, **kwargs):
        self.insert_calls.append(kwargs)
        return self.next_insert

    def update(self, **kwargs):
        self.update_calls.append(kwargs)
        return self.next_update

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return self.next_list


class FakeThumbnailsResource:
    def __init__(self):
        self.set_calls = []
        self.next_set = FakeExecute({"kind": "youtube#thumbnailSetResponse", "items": [{"default": {}}]})

    def set(self, **kwargs):
        self.set_calls.append(kwargs)
        return self.next_set


class FakeYouTubeService:
    def __init__(self):
        self.videos_resource = FakeVideosResource()
        self.thumbnails_resource = FakeThumbnailsResource()

    def videos(self):
        return self.videos_resource

    def thumbnails(self):
        return self.thumbnails_resource


class FakeCredentials:
    def __init__(self, *, valid=False, expired=True, refresh_token="refresh-token"):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.refreshed = False

    def refresh(self, request):
        self.refreshed = True
        self.valid = True
        self.expired = False

    def to_json(self):
        return '{"token": "new-access", "refresh_token": "new-refresh"}'


class FakeTokenStore:
    def __init__(self, credentials):
        self.credentials = credentials
        self.saved = []

    @property
    def exists(self):
        return True

    def load_credentials(self, scopes):
        return self.credentials

    def save_credentials(self, credentials):
        self.saved.append(credentials.to_json())


def _config(tmp_path: Path, *, with_token: bool = True) -> YouTubePublisherConfig:
    client_file = tmp_path / "client_secret.json"
    client_file.write_text('{"installed": {"client_id": "x"}}', encoding="utf-8")
    token_file = tmp_path / "token.json" if with_token else None
    if token_file is not None:
        token_file.write_text("{}", encoding="utf-8")
    return YouTubePublisherConfig(
        client_secrets_file=client_file,
        token_file=token_file,
        state_file=tmp_path / "state.json",
        max_retries=1,
    )


def _manifest(tmp_path: Path, **overrides) -> YouTubePublishManifest:
    video = tmp_path / "short.mp4"
    video.write_bytes(b"video-bytes")
    thumbnail = tmp_path / "thumb.png"
    thumbnail.write_bytes(b"png-bytes")
    payload = {
        "content_id": "gamcryp-test-short-001",
        "video_path": video,
        "thumbnail_path": thumbnail,
        "title": "GamCryp test Short",
        "description": "Approved content description.",
        "tags": ("GamCryp", "Web3"),
        "privacy": "private",
        "category_id": "28",
        "publish_at": datetime.now(UTC) + timedelta(days=1),
        "source_snapshot_id": "snapshot-123",
        "source_snapshot_timestamp": datetime(2026, 8, 30, tzinfo=UTC),
    }
    payload.update(overrides)
    return YouTubePublishManifest.model_validate(payload)


def _publisher(tmp_path: Path, *, service: FakeYouTubeService | None = None) -> YouTubePublisher:
    return YouTubePublisher(
        config=_config(tmp_path),
        service=service or FakeYouTubeService(),
        media_factory=lambda path, **kwargs: {"path": path, **kwargs},
    )


def test_missing_credentials_config_is_explicit(tmp_path) -> None:
    publisher = YouTubePublisher(
        config=YouTubePublisherConfig(client_secrets_file=None, token_file=None, state_file=tmp_path / "state.json")
    )

    state = publisher.validate_auth_state()

    assert state.configured is False
    assert state.authorized is False
    assert "missing" in state.detail.lower()
    with pytest.raises(YouTubeConfigError):
        publisher.dry_run_upload(_manifest(tmp_path))


def test_manifest_rejects_invalid_video_and_thumbnail_paths(tmp_path) -> None:
    video = tmp_path / "missing.mp4"
    thumbnail = tmp_path / "thumb.gif"
    thumbnail.write_bytes(b"not-supported")
    manifest = _manifest(tmp_path, video_path=video, thumbnail_path=thumbnail)
    publisher = _publisher(tmp_path)

    with pytest.raises(YouTubeManifestError, match="video file does not exist"):
        publisher.dry_run_upload(manifest)

    video.write_bytes(b"video")
    with pytest.raises(YouTubeManifestError, match="thumbnail file must be JPEG or PNG"):
        publisher.dry_run_upload(manifest)


def test_dry_run_validates_files_without_mutating_youtube_or_state(tmp_path) -> None:
    service = FakeYouTubeService()
    publisher = _publisher(tmp_path, service=service)

    result = publisher.dry_run_upload(_manifest(tmp_path))

    assert result.status == "ready"
    assert result.would_mutate is False
    assert service.videos_resource.insert_calls == []
    assert not (tmp_path / "state.json").exists()
    assert result.to_safe_dict()["response"]["video_file"] == "short.mp4"


def test_token_refresh_path_saves_refreshed_token(tmp_path) -> None:
    credentials = FakeCredentials(valid=False, expired=True, refresh_token="refresh-token")
    token_store = FakeTokenStore(credentials)

    refreshed = load_refreshed_credentials(
        config=_config(tmp_path),
        token_store=token_store,  # type: ignore[arg-type]
        request_factory=lambda: object(),
    )

    assert refreshed.valid is True
    assert credentials.refreshed is True
    assert token_store.saved == ['{"token": "new-access", "refresh_token": "new-refresh"}']


def test_upload_records_state_and_duplicate_retry_does_not_reupload(tmp_path) -> None:
    service = FakeYouTubeService()
    publisher = _publisher(tmp_path, service=service)
    manifest = _manifest(tmp_path)

    first = publisher.upload_video(manifest)
    second = publisher.upload_video(manifest)

    assert first.status == "uploaded"
    assert second.status == "skipped_duplicate"
    assert second.would_mutate is False
    assert first.video_id == second.video_id == "abc123VIDEO"
    assert len(service.videos_resource.insert_calls) == 1
    stored = PublishStateStore(tmp_path / "state.json").find(manifest.content_id)
    assert stored is not None
    assert stored.video_id == "abc123VIDEO"


def test_duplicate_content_id_with_different_checksum_fails_closed(tmp_path) -> None:
    publisher = _publisher(tmp_path)
    manifest = _manifest(tmp_path)
    publisher.upload_video(manifest)
    Path(manifest.video_path).write_bytes(b"different-video")

    with pytest.raises(DuplicateUploadError):
        publisher.upload_video(manifest)


def test_metadata_validation_and_update_preserves_existing_snippet_fields(tmp_path) -> None:
    service = FakeYouTubeService()
    publisher = _publisher(tmp_path, service=service)

    result = publisher.update_video_metadata(video_id="abc123VIDEO", title="New title")

    assert result.status == "metadata_updated"
    call = service.videos_resource.update_calls[0]
    assert call["part"] == "snippet"
    assert call["body"]["snippet"]["title"] == "New title"
    assert call["body"]["snippet"]["description"] == "Current description"
    assert call["body"]["snippet"]["categoryId"] == "28"

    with pytest.raises(ValidationError):
        YouTubePublishManifest.model_validate(
            {
                "content_id": "bad-schedule",
                "video_path": tmp_path / "short.mp4",
                "title": "Title",
                "description": "Description",
                "privacy": "unlisted",
                "publish_at": datetime.now(UTC) + timedelta(days=1),
            }
        )


def test_thumbnail_upload_and_verification_use_official_thumbnail_surface(tmp_path) -> None:
    service = FakeYouTubeService()
    publisher = _publisher(tmp_path, service=service)
    thumb = tmp_path / "thumb.jpg"
    thumb.write_bytes(b"jpeg")

    result = publisher.set_thumbnail(video_id="abc123VIDEO", image_path=thumb)
    verify = publisher.verify_thumbnail("abc123VIDEO")

    assert result.status == "thumbnail_set"
    assert service.thumbnails_resource.set_calls[0]["videoId"] == "abc123VIDEO"
    assert service.thumbnails_resource.set_calls[0]["media_body"]["mimetype"] == "image/jpeg"
    assert verify.status == "thumbnail_verified"
    assert verify.to_safe_dict()["response"]["hasCustomThumbnail"] is True


def test_api_errors_are_structured_and_redacted(tmp_path) -> None:
    class SecretError(RuntimeError):
        content = b'{"error":"access_token=abc refresh_token=def client_secret=ghi"}'

    service = FakeYouTubeService()
    service.videos_resource.next_insert = FakeExecute(error=SecretError("Authorization: Bearer secret-token"))
    publisher = _publisher(tmp_path, service=service)

    with pytest.raises(YouTubeApiError) as exc_info:
        publisher.upload_video(_manifest(tmp_path))

    message = str(exc_info.value)
    assert "upload_video" in message
    assert "abc" not in message
    assert "def" not in message
    assert "ghi" not in message
    assert "secret-token" not in message
    assert "[redacted]" in message


def test_safe_log_redaction_and_response_sanitization() -> None:
    redacted = redact_sensitive_text("client_secret=abc refresh_token:def Authorization: Bearer xyz")
    safe = sanitize_mapping({"id": "abc123VIDEO", "access_token": "secret", "nested": {"clientSecret": "secret"}})

    assert "abc" not in redacted
    assert "def" not in redacted
    assert "xyz" not in redacted
    assert safe["id"] == "abc123VIDEO"
    assert safe["access_token"] == "[redacted]"
    assert safe["nested"]["clientSecret"] == "[redacted]"


def test_manifest_loading_rejects_secret_fields(tmp_path) -> None:
    video = tmp_path / "short.mp4"
    video.write_bytes(b"video")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "content_id": "with-secret",
                "video_path": str(video),
                "title": "Title",
                "description": "Description",
                "client_secret": "must-not-exist",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(YouTubeManifestError, match="validation failed"):
        load_manifest(manifest_path)


def test_format_youtube_exception_keeps_status_but_not_secrets() -> None:
    class Response:
        status = 403
        reason = "Forbidden"

    class ApiFailure(Exception):
        resp = Response()
        content = b"api_key=hidden-token"

    message = format_youtube_exception(ApiFailure("boom"), operation="verify_video")

    assert "status=403" in message
    assert "Forbidden" in message
    assert "hidden-token" not in message