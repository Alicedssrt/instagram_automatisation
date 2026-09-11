import responses

from instagram_automation.config import Config
from instagram_automation.instagram import InstagramAPIError, InstagramClient

BASE = "https://graph.facebook.com/v21.0"


def make_config(**overrides) -> Config:
    defaults = dict(
        ig_user_id="ig123",
        ig_access_token="token-abc",
        graph_api_version="v21.0",
        timezone="Europe/Paris",
        image_host="github_raw",
        github_repository="alicedussart/instagram_automatisation",
        github_branch="main",
        calendar_path="data/calendrier.csv",
        dry_run=False,
        max_posts_per_run=25,
    )
    defaults.update(overrides)
    return Config(**defaults)


@responses.activate
def test_publish_post_full_sequence():
    config = make_config()
    client = InstagramClient(config)

    responses.add(
        responses.POST,
        f"{BASE}/ig123/media",
        json={"id": "container-1"},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/container-1",
        json={"status_code": "FINISHED"},
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/ig123/media_publish",
        json={"id": "media-1"},
        status=200,
    )

    media_id = client.publish_post("https://example.com/a.jpg", "Une legende")

    assert media_id == "media-1"
    assert len(responses.calls) == 3

    create_call = responses.calls[0]
    assert "image_url=https" in create_call.request.body or "image_url" in create_call.request.body
    assert "access_token=token-abc" in create_call.request.body

    publish_call = responses.calls[2]
    assert "creation_id=container-1" in publish_call.request.body


@responses.activate
def test_wait_until_ready_polls_until_finished():
    config = make_config()
    client = InstagramClient(config)

    responses.add(
        responses.GET,
        f"{BASE}/container-1",
        json={"status_code": "IN_PROGRESS"},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/container-1",
        json={"status_code": "FINISHED"},
        status=200,
    )

    client.wait_until_ready("container-1", timeout=5, interval=0)

    assert len(responses.calls) == 2


@responses.activate
def test_wait_until_ready_raises_on_error_status():
    config = make_config()
    client = InstagramClient(config)

    responses.add(
        responses.GET,
        f"{BASE}/container-1",
        json={"status_code": "ERROR"},
        status=200,
    )

    try:
        client.wait_until_ready("container-1", timeout=5, interval=0)
        assert False, "devrait lever InstagramAPIError"
    except InstagramAPIError as exc:
        assert "ERROR" in str(exc)


@responses.activate
def test_create_container_raises_on_meta_error():
    config = make_config()
    client = InstagramClient(config)

    responses.add(
        responses.POST,
        f"{BASE}/ig123/media",
        json={"error": {"message": "Invalid parameter", "code": 100}},
        status=400,
    )

    try:
        client.create_container("https://example.com/a.jpg", "c")
        assert False, "devrait lever InstagramAPIError"
    except InstagramAPIError as exc:
        assert "Invalid parameter" in str(exc)


@responses.activate
def test_expired_token_error_message_is_explicit():
    config = make_config()
    client = InstagramClient(config)

    responses.add(
        responses.POST,
        f"{BASE}/ig123/media",
        json={"error": {"message": "Error validating access token", "code": 190}},
        status=400,
    )

    try:
        client.create_container("https://example.com/a.jpg", "c")
        assert False, "devrait lever InstagramAPIError"
    except InstagramAPIError as exc:
        assert "expire" in str(exc) or "invalide" in str(exc)
