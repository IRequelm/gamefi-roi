from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from app.distribution.content_pack import ContentPackValidationError, ContentReadiness, ContentPackLite, serialize_batch, set_expected_source_hash
from app.distribution.manual_outbox import XManualOutbox, manual_ready_record
from app.distribution.x_publisher import (
    ApprovalRecord,
    XAmbiguousApiError,
    XApiClient,
    XApiError,
    XApprovalError,
    XAuthError,
    XConfigError,
    XDuplicateError,
    XOAuthManager,
    XPublisherConfig,
    XPublishingService,
    XValidationError,
    safe_error,
)
from app.distribution.x_queue import (
    X_MAX_WEIGHTED_LENGTH,
    contains_unsupported_idn_hostname,
    build_x_publish_queue,
    editorial_order_from_handoff,
    load_content_pack_batch,
    load_x_queue,
    write_x_queue,
    x_content_checksum,
    x_weighted_character_count,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_BATCH = ROOT / "distribution/content_packs/learning_batch_001.json"
SOURCE_HANDOFF = ROOT / "distribution/publish_queue/next_publish_queue.json"
SOURCE_X_QUEUE = ROOT / "distribution/publish_queue/x_publish_queue.json"
METHODOLOGY_ID = "x-gamcryp-methodology-not-recommendation-20260831"
DFK_ID = "x-dfk-lock-risk-20260831"
FARMERS_ID = "x-farmers-world-tiny-economics-20260831"
GRASS_ID = "x-grass-roi-unavailable-20260831"
SPLINTERLANDS_ID = "x-splinterlands-expected-value-20260831"
DIMO_ID = "x-dimo-subscription-catch-20260831"
SNAPSHOT_TIME = datetime(2026, 8, 31, 21, 33, 44, tzinfo=UTC)


class FakeApiClient:
    def __init__(self, *, post_id: str = "1900000000000000000", error: Exception | None = None) -> None:
        self.post_id = post_id
        self.error = error
        self.calls: list[str] = []

    def create_post(self, text: str) -> str:
        self.calls.append(text)
        if self.error:
            raise self.error
        return self.post_id


def _config(tmp_path: Path) -> XPublisherConfig:
    content_path = tmp_path / "learning_batch.json"
    queue_path = tmp_path / "x_queue.json"
    payload = json.loads(SOURCE_BATCH.read_text(encoding="utf-8"))
    test_yellow = {DFK_ID, FARMERS_ID, SPLINTERLANDS_ID}
    packs: list[ContentPackLite] = []
    for raw in payload["packs"]:
        pack = ContentPackLite.model_validate(raw)
        if pack.content_id in test_yellow:
            pack = pack.model_copy(
                update={
                    "editorial": pack.editorial.model_copy(update={"readiness": ContentReadiness.YELLOW}),
                    "facts": pack.facts.model_copy(update={"freshness": pack.facts.freshness.model_copy(update={"display": "fresh", "value": "fresh"})}),
                    "source": pack.source.model_copy(update={"snapshot_timestamp": SNAPSHOT_TIME.isoformat()}),
                }
            )
            pack = set_expected_source_hash(pack)
        packs.append(pack)
    batch = serialize_batch(packs, batch_id=payload["batch_id"], generated_at=payload["generated_at"], source_dataset=payload["source_dataset"])
    content_bytes = (json.dumps(batch, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    content_path.write_bytes(content_bytes)
    queue = build_x_publish_queue(
        batch_payload=batch,
        packs=tuple(packs),
        source_batch_bytes=content_bytes,
        editorial_order=editorial_order_from_handoff(SOURCE_HANDOFF),
    )
    write_x_queue(queue_path, queue)
    return XPublisherConfig(
        content_pack_file=content_path,
        queue_file=queue_path,
        approval_file=tmp_path / "local/approvals.json",
        publication_file=tmp_path / "local/publications.json",
        token_file=tmp_path / "local/token.json",
        oauth_pending_file=tmp_path / "local/oauth_pending.json",
        publish_lock_file=tmp_path / "local/publish.lock",
        client_id="test-client",
    )


def _service(
    tmp_path: Path,
    *,
    now: datetime = SNAPSHOT_TIME + timedelta(minutes=5),
    api: FakeApiClient | None = None,
) -> tuple[XPublishingService, FakeApiClient]:
    fake = api or FakeApiClient()
    service = XPublishingService(_config(tmp_path), api_client=fake, now=lambda: now)  # type: ignore[arg-type]
    return service, fake


def _valid_dfk_copy(service: XPublishingService) -> str:
    url = service.preview(DFK_ID).attribution_url
    return (
        "DeFi Kingdoms model: $40.64 capital, $0.0136/day net, 1% 30D ROI. "
        "Confidence is HIGH; risk is VERY HIGH due to lock and exit terms. "
        f"Analytical comparison, not a recommendation.\n\n{url}"
    )


def test_committed_x_queue_matches_canonical_content_inventory() -> None:
    queue = load_x_queue(SOURCE_X_QUEUE)
    payload, packs = load_content_pack_batch(SOURCE_BATCH)
    expected = build_x_publish_queue(
        batch_payload=payload,
        packs=packs,
        source_batch_bytes=SOURCE_BATCH.read_bytes(),
        editorial_order=editorial_order_from_handoff(SOURCE_HANDOFF),
    )

    assert queue.model_dump(mode="json") == expected.model_dump(mode="json")
    assert [item.content_id for item in queue.publishable] == [METHODOLOGY_ID]
    assert all(item.status is ContentReadiness.RED for item in queue.blocked)
    assert all(item.status is ContentReadiness.RED for item in queue.blocked)


def test_queue_generation_is_deterministic_and_red_never_enters_publishable(tmp_path: Path) -> None:
    source_bytes = SOURCE_BATCH.read_bytes()
    payload, packs = load_content_pack_batch(SOURCE_BATCH)
    kwargs = {
        "batch_payload": payload,
        "packs": packs,
        "source_batch_bytes": source_bytes,
        "editorial_order": editorial_order_from_handoff(SOURCE_HANDOFF),
    }
    first = build_x_publish_queue(**kwargs)
    second = build_x_publish_queue(**kwargs)
    output = tmp_path / "queue.json"
    write_x_queue(output, first)

    assert first == second
    assert load_x_queue(output) == first
    assert not any(item.status is ContentReadiness.RED for item in first.publishable)


def test_green_methodology_is_publishable_and_character_count_is_valid(tmp_path: Path) -> None:
    service, _ = _service(tmp_path, now=datetime(2026, 9, 1, tzinfo=UTC))
    preview = service.preview(METHODOLOGY_ID)
    _, packs = load_content_pack_batch(service.config.content_pack_file)
    methodology_pack = next(pack for pack in packs if pack.content_id == METHODOLOGY_ID)

    assert preview.readiness is ContentReadiness.GREEN
    assert preview.approval_state == "not_required"
    assert preview.would_publish is True
    assert preview.weighted_character_count == 274
    assert preview.weighted_character_count <= X_MAX_WEIGHTED_LENGTH
    assert "not a recommendation" in preview.exact_final_copy
    assert ":::writing" not in preview.exact_final_copy
    assert not any(line.strip() == ":::" for line in preview.exact_final_copy.splitlines())
    assert preview.weighted_character_count == x_weighted_character_count(preview.exact_final_copy)
    assert preview.content_checksum == x_content_checksum(methodology_pack, preview.exact_final_copy)


def test_x_queue_serialization_contains_only_clean_public_copy() -> None:
    queue_text = SOURCE_X_QUEUE.read_text(encoding="utf-8")
    queue = load_x_queue(SOURCE_X_QUEUE)

    assert ":::writing" not in queue_text
    assert not any(line.strip() == ":::" for item in queue.items for line in item.final_copy.splitlines())


def test_queue_generation_rejects_wrapper_contaminated_pack() -> None:
    source_bytes = SOURCE_BATCH.read_bytes()
    payload, packs = load_content_pack_batch(SOURCE_BATCH)
    methodology = next(pack for pack in packs if pack.content_id == METHODOLOGY_ID)
    contaminated = methodology.model_copy(
        update={
            "editorial": methodology.editorial.model_copy(
                update={"x_post": f':::writing{{variant="social_post"}}\n{methodology.editorial.x_post}\n:::'}
            )
        }
    )
    replaced = tuple(contaminated if pack.content_id == METHODOLOGY_ID else pack for pack in packs)

    with pytest.raises(ContentPackValidationError, match="non-content wrapper marker"):
        build_x_publish_queue(
            batch_payload=payload,
            packs=replaced,
            source_batch_bytes=source_bytes,
            editorial_order=editorial_order_from_handoff(SOURCE_HANDOFF),
        )


def test_wrapper_contaminated_copy_cannot_be_approved_or_checksummed_as_publishable(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    clean_copy = _valid_dfk_copy(service)
    wrapped_copy = f':::writing{{variant="social_post" id="12345"}}\n{clean_copy}\n:::'

    with pytest.raises(XApprovalError, match="non-content wrapper marker"):
        service.approve(DFK_ID, edited_copy=wrapped_copy)

    _, packs = load_content_pack_batch(service.config.content_pack_file)
    dfk_pack = next(pack for pack in packs if pack.content_id == DFK_ID)
    assert x_content_checksum(dfk_pack, clean_copy) != x_content_checksum(dfk_pack, wrapped_copy)


def test_x_weighted_count_uses_23_char_urls_and_conservative_unicode() -> None:
    assert x_weighted_character_count("a https://example.com/a/very/long/path") == 25
    assert x_weighted_character_count("A") == 1
    assert x_weighted_character_count("界") == 2


@pytest.mark.parametrize(
    ("plain_text_length", "expected", "valid"),
    [(255, 279, True), (256, 280, True), (257, 281, False)],
)
def test_x_weighted_count_exact_url_boundaries(
    plain_text_length: int,
    expected: int,
    valid: bool,
) -> None:
    text = "a" * plain_text_length + " https://example.com/path"
    weighted_count = x_weighted_character_count(text)

    assert weighted_count == expected
    assert (weighted_count <= X_MAX_WEIGHTED_LENGTH) is valid


@pytest.mark.parametrize(
    ("punctuation", "expected"),
    [
        (".", 24),
        (",", 24),
        ("!", 24),
        ("?", 24),
        (":", 24),
        (";", 24),
        (")", 24),
        ("]", 24),
        ("}", 24),
        ("'", 24),
        ('"', 24),
        ("\u2019", 24),
        ("\u201d", 24),
        ("\u3002", 25),
        ("\uff0c", 25),
    ],
)
def test_x_weighted_count_counts_trailing_url_punctuation_as_text(
    punctuation: str,
    expected: int,
) -> None:
    assert x_weighted_character_count(f"https://example.com{punctuation}") == expected


def test_x_weighted_count_handles_url_parentheses_without_stripping_valid_path_characters() -> None:
    assert x_weighted_character_count("(https://example.com/path)") == 25
    assert x_weighted_character_count("https://example.com/path_(valid)") == 23


def test_x_weighted_count_handles_queries_fragments_and_multiple_urls() -> None:
    assert x_weighted_character_count("https://example.com/path?q=a,b#section") == 23
    assert x_weighted_character_count("https://example.com/a https://gamcryp.com/b") == 47
    assert x_weighted_character_count("x.co") == 23
    assert x_weighted_character_count("x.co.") == 24


@pytest.mark.parametrize("emoji", ["👨‍🎤", "🙋🏽", "👨‍👩‍👧‍👦", "🇹🇷", "1️⃣"])
def test_x_weighted_count_handles_complex_emoji_sequences(emoji: str) -> None:
    assert x_weighted_character_count(emoji) == 2
    assert x_weighted_character_count(f"https://example.com{emoji}") == 25


def test_x_weighted_count_handles_unicode_malformed_and_empty_text() -> None:
    assert x_weighted_character_count("界é") == 3
    assert x_weighted_character_count("https://") == 23
    assert x_weighted_character_count("abchttps://example.com") >= len("abchttps://example.com")
    assert x_weighted_character_count("") == 0


@pytest.mark.parametrize("idn_url", ["例.中国", "https://例.中国"])
def test_non_ascii_idn_hosts_are_blocked(idn_url: str, tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    edited_copy = f"{_valid_dfk_copy(service)} {idn_url}"

    assert contains_unsupported_idn_hostname(edited_copy) is True
    with pytest.raises(XApprovalError, match="non-ASCII/IDN URL host syntax"):
        service.approve(DFK_ID, edited_copy=edited_copy)


@pytest.mark.parametrize("prose", ["GamCryp açıklaması güvenlidir.", "GamCryp analysis 🔍✨"])
def test_unicode_and_emoji_prose_remain_supported(prose: str) -> None:
    assert contains_unsupported_idn_hostname(prose) is False
    assert x_weighted_character_count(prose) > 0


def test_ascii_gamcryp_url_remains_supported() -> None:
    url = "https://gamcryp.com/methodology?utm_source=x&utm_medium=social"

    assert contains_unsupported_idn_hostname(url) is False
    assert x_weighted_character_count(url) == 23


def test_yellow_awaits_explicit_approval(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    preview = service.preview(DFK_ID)

    assert preview.readiness is ContentReadiness.YELLOW
    assert preview.approval_state == "awaiting_human_approval"
    assert preview.would_publish is False
    assert any("explicit checksum-bound human approval" in blocker for blocker in preview.blockers)


def test_yellow_cannot_publish_before_approval(tmp_path: Path) -> None:
    service, api = _service(tmp_path)

    with pytest.raises(XValidationError, match="explicit checksum-bound"):
        service.publish(DFK_ID, dry_run=False, confirm_publish=True)
    assert api.calls == []


def test_yellow_can_publish_once_after_checksum_bound_approval(tmp_path: Path) -> None:
    service, api = _service(tmp_path)
    approved = service.approve(DFK_ID, edited_copy=_valid_dfk_copy(service))
    result = service.publish(DFK_ID, dry_run=False, confirm_publish=True)

    assert approved.state == "approved"
    assert result.status == "published"
    assert result.post_id == api.post_id
    assert len(api.calls) == 1
    records = service.publications.records(DFK_ID)
    assert records[-1].status == "published"
    assert records[-1].post_id == api.post_id


def test_red_cannot_be_approved_or_published(tmp_path: Path) -> None:
    service, api = _service(tmp_path)

    with pytest.raises(XApprovalError, match="RED content"):
        service.approve(DIMO_ID)
    with pytest.raises(XValidationError, match="RED content"):
        service.publish(DIMO_ID, dry_run=False, confirm_publish=True)
    assert api.calls == []


def test_all_committed_red_projects_are_hard_blocked(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    queue = load_x_queue(service.config.queue_file)

    assert len(queue.blocked) == 5
    for item in queue.blocked:
        preview = service.preview(item.content_id)
        assert preview.would_publish is False
        assert "RED content is permanently blocked from X publishing" in preview.blockers


def test_approval_is_invalidated_when_source_content_checksum_changes(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    record = service.approve(DFK_ID, edited_copy=_valid_dfk_copy(service))
    queue_payload = json.loads(service.config.queue_file.read_text(encoding="utf-8"))
    item = next(item for item in queue_payload["awaiting_human_approval"] if item["content_id"] == DFK_ID)
    item["content_checksum"] = "a" * 64
    service.config.queue_file.write_text(json.dumps(queue_payload), encoding="utf-8")

    preview = service.preview(DFK_ID)
    assert record.source_content_checksum != "a" * 64
    assert preview.approval_state == "approval_invalidated_by_content_change"
    assert preview.would_publish is False


def test_tampered_approval_copy_checksum_is_rejected(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    valid = service.approve(DFK_ID, edited_copy=_valid_dfk_copy(service))
    tampered = valid.model_copy(update={"approved_copy": valid.approved_copy + " altered"})
    payload = service.approvals.store.load()
    payload["approvals"].append(tampered.model_dump(mode="json"))
    service.approvals.store.save(payload)

    preview = service.preview(DFK_ID)
    assert preview.approval_state == "approval_record_checksum_mismatch"
    assert preview.would_publish is False


def test_revoke_removes_yellow_publishability(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    service.approve(DFK_ID, edited_copy=_valid_dfk_copy(service))
    assert service.preview(DFK_ID).would_publish is True

    service.revoke(DFK_ID)
    preview = service.preview(DFK_ID)
    assert preview.approval_state == "awaiting_human_approval"
    assert preview.would_publish is False


def test_stale_snapshot_blocks_numeric_yellow_approval(tmp_path: Path) -> None:
    service, _ = _service(tmp_path, now=SNAPSHOT_TIME + timedelta(hours=2))

    with pytest.raises(XApprovalError, match="stale"):
        service.approve(DFK_ID, edited_copy=_valid_dfk_copy(service))


def test_unresolved_url_placeholder_blocks_approval(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    copy = _valid_dfk_copy(service).replace(service.preview(DFK_ID).attribution_url, "{url}")

    with pytest.raises(XApprovalError, match="placeholder"):
        service.approve(DFK_ID, edited_copy=copy)


def test_linkless_posts_keep_source_metadata_without_repeating_the_url(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    copy = _valid_dfk_copy(service).replace(service.preview(DFK_ID).attribution_url, "https://gamcryp.com")

    record = service.approve(DFK_ID, edited_copy=copy)
    assert record.content_id == DFK_ID
    assert service.preview(DFK_ID).attribution_url.startswith("https://gamcryp.com/")


def test_unsupported_numeric_claim_in_edited_copy_is_rejected(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    copy = _valid_dfk_copy(service).replace("1% 30D ROI", "99% 30D ROI")

    with pytest.raises(XApprovalError, match="unsupported numeric"):
        service.approve(DFK_ID, edited_copy=copy)


@pytest.mark.parametrize("promise", ["guaranteed", "risk-free", "no risk", "buy this", "easy profit"])
def test_promise_or_recommendation_wording_is_rejected(tmp_path: Path, promise: str) -> None:
    service, _ = _service(tmp_path)
    copy = _valid_dfk_copy(service).replace("Analytical comparison", promise)

    with pytest.raises(XApprovalError, match="forbidden recommendation/promise wording"):
        service.approve(DFK_ID, edited_copy=copy)


def test_same_content_and_checksum_duplicate_is_blocked(tmp_path: Path) -> None:
    service, api = _service(tmp_path)
    service.publish(METHODOLOGY_ID, dry_run=False, confirm_publish=True)

    with pytest.raises(XValidationError, match="already published"):
        service.publish(METHODOLOGY_ID, dry_run=False, confirm_publish=True)


def test_manual_confirmation_records_duplicate_and_clears_outbox(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    preview = service.preview(METHODOLOGY_ID)
    outbox = XManualOutbox(tmp_path / "x_manual_ready.json")
    outbox.prepare(
        manual_ready_record(
            content_id=METHODOLOGY_ID,
            post_text=preview.exact_final_copy,
            source_url=preview.attribution_url,
            checksum=preview.content_checksum,
            now=SNAPSHOT_TIME,
        )
    )

    service.confirm_manual_publication(METHODOLOGY_ID, checksum=preview.content_checksum)
    outbox.clear(content_id=METHODOLOGY_ID, checksum=preview.content_checksum)

    assert outbox.current().published is True
    confirmed_preview = service.preview(METHODOLOGY_ID)
    assert confirmed_preview.would_publish is False
    assert "already published" in confirmed_preview.blockers[0]
    with pytest.raises(XValidationError, match="already published"):
        service.publish(METHODOLOGY_ID, dry_run=False, confirm_publish=True)


def test_api_failure_does_not_mark_published(tmp_path: Path) -> None:
    api = FakeApiClient(error=XApiError("status=401 access_token=secret-value"))
    service, _ = _service(tmp_path, api=api)

    with pytest.raises(XApiError):
        service.publish(METHODOLOGY_ID, dry_run=False, confirm_publish=True)
    record = service.publications.records(METHODOLOGY_ID)[-1]
    assert record.status == "failed"
    assert record.post_id is None
    assert "secret-value" not in (record.safe_error or "")


def test_ambiguous_api_failure_is_recorded_and_not_retried(tmp_path: Path) -> None:
    api = FakeApiClient(error=XAmbiguousApiError("timeout after send"))
    service, _ = _service(tmp_path, api=api)

    with pytest.raises(XAmbiguousApiError):
        service.publish(METHODOLOGY_ID, dry_run=False, confirm_publish=True)
    assert service.publications.records(METHODOLOGY_ID)[-1].status == "ambiguous"
    with pytest.raises(XValidationError, match="manual reconciliation"):
        service.publish(METHODOLOGY_ID, dry_run=False, confirm_publish=True)
    assert len(api.calls) == 1


def test_dry_run_makes_zero_network_calls(tmp_path: Path) -> None:
    service, api = _service(tmp_path)
    preview = service.publish(METHODOLOGY_ID, dry_run=True)

    assert preview.network_called is False
    assert preview.would_publish is True
    assert api.calls == []
    assert service.publications.records(METHODOLOGY_ID) == ()


def test_actual_publish_requires_explicit_confirmation(tmp_path: Path) -> None:
    service, api = _service(tmp_path)

    with pytest.raises(XValidationError, match="confirm-publish"):
        service.publish(METHODOLOGY_ID, dry_run=False, confirm_publish=False)
    assert api.calls == []


def test_official_api_request_construction_and_success_response(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={"data": {"id": "1999999999999999999"}})

    config = _config(tmp_path)
    oauth = XOAuthManager(config)
    oauth.access_token = lambda: "private-token"  # type: ignore[method-assign]
    client = XApiClient(oauth, client=httpx.Client(base_url="https://api.x.com", transport=httpx.MockTransport(handler)))

    post_id = client.create_post("GamCryp test body")

    assert post_id == "1999999999999999999"
    assert requests[0].method == "POST"
    assert requests[0].url.path == "/2/tweets"
    assert json.loads(requests[0].content) == {"text": "GamCryp test body"}
    assert requests[0].headers["authorization"] == "Bearer private-token"


def test_x_read_and_retweet_endpoints_use_user_context(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/2/users/me":
            return httpx.Response(200, json={"data": {"id": "42", "username": "GamCryp"}})
        if request.url.path == "/2/tweets/search/recent":
            return httpx.Response(200, json={"data": [], "meta": {"result_count": 0}})
        return httpx.Response(200, json={"data": {"retweeted": True}})

    config = _config(tmp_path)
    oauth = XOAuthManager(config)
    oauth.access_token = lambda: "private-token"  # type: ignore[method-assign]
    client = XApiClient(oauth, client=httpx.Client(base_url="https://api.x.com", transport=httpx.MockTransport(handler)))

    assert client.authenticated_user()["data"]["username"] == "GamCryp"
    assert client.search_recent("GameFi")["meta"]["result_count"] == 0
    assert client.create_retweet("42", "123") == "123"
    assert [request.url.path for request in requests] == ["/2/users/me", "/2/tweets/search/recent", "/2/users/42/retweets"]
    assert json.loads(requests[-1].content) == {"tweet_id": "123"}


def test_official_api_5xx_is_ambiguous_and_error_redacts_secrets(tmp_path: Path) -> None:
    config = _config(tmp_path)
    oauth = XOAuthManager(config)
    oauth.access_token = lambda: "private-token"  # type: ignore[method-assign]
    client = XApiClient(
        oauth,
        client=httpx.Client(
            base_url="https://api.x.com",
            transport=httpx.MockTransport(lambda request: httpx.Response(503, json={"access_token": "secret"})),
        ),
    )

    with pytest.raises(XAmbiguousApiError, match="reconcile"):
        client.create_post("GamCryp test body")
    assert "secret-value" not in safe_error("Bearer secret-value access_token=secret-value")


def test_oauth_authorization_url_uses_pkce_and_required_scopes(tmp_path: Path) -> None:
    config = _config(tmp_path)
    oauth = XOAuthManager(config, now=lambda: datetime(2026, 9, 1, tzinfo=UTC))
    url = oauth.authorization_url()
    query = httpx.QueryParams(urlsplit(url).query)

    assert url.startswith("https://x.com/i/oauth2/authorize?")
    assert query["response_type"] == "code"
    assert query["client_id"] == "test-client"
    assert query["code_challenge_method"] == "S256"
    assert set(query["scope"].split()) == {"tweet.read", "tweet.write", "users.read", "offline.access"}
    assert config.oauth_pending_file.is_file()


def test_oauth_callback_must_match_configured_redirect_uri(tmp_path: Path) -> None:
    config = _config(tmp_path)
    oauth = XOAuthManager(config, now=lambda: datetime(2026, 9, 1, tzinfo=UTC))
    authorization_url = oauth.authorization_url()
    state = httpx.QueryParams(urlsplit(authorization_url).query)["state"]

    with pytest.raises(XAuthError, match="does not match"):
        oauth.complete_authorization(f"https://attacker.example/callback?code=code&state={state}")


def test_oauth_pending_state_expires(tmp_path: Path) -> None:
    config = _config(tmp_path)
    started_at = datetime(2026, 9, 1, tzinfo=UTC)
    oauth = XOAuthManager(config, now=lambda: started_at)
    authorization_url = oauth.authorization_url()
    state = httpx.QueryParams(urlsplit(authorization_url).query)["state"]
    oauth.now = lambda: started_at + timedelta(minutes=11)

    with pytest.raises(XAuthError, match="expired"):
        oauth.complete_authorization(f"{config.redirect_uri}?code=code&state={state}")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("redirect_uri", "not-a-url", "absolute HTTP"),
        ("timeout_seconds", 0, "greater than zero"),
        ("max_snapshot_age_seconds", 0, "greater than zero"),
    ],
)
def test_publisher_configuration_fails_closed(field: str, value: object, message: str) -> None:
    with pytest.raises(XConfigError, match=message):
        XPublisherConfig(**{field: value})


def test_current_yellow_and_red_inventory_remains_fail_closed(tmp_path: Path) -> None:
    service, _ = _service(tmp_path, now=datetime(2026, 9, 1, tzinfo=UTC))
    queue = load_x_queue(service.config.queue_file)

    assert {item.content_id for item in queue.awaiting_human_approval} == {
        DFK_ID,
        FARMERS_ID,
        GRASS_ID,
        SPLINTERLANDS_ID,
    }
    assert all(not service.preview(item.content_id).would_publish for item in queue.awaiting_human_approval)
    assert all(not service.preview(item.content_id).would_publish for item in queue.blocked)
