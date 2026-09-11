import pytest

from instagram_automation.config import Config
from instagram_automation.image_host import ImageHostError, resolve_image_url


def make_config(**overrides) -> Config:
    defaults = dict(
        ig_user_id="ig123",
        ig_access_token="token",
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


def test_github_raw_builds_expected_url():
    config = make_config()
    url = resolve_image_url("images/exemple.jpg", config)
    assert url == (
        "https://raw.githubusercontent.com/alicedussart/instagram_automatisation"
        "/main/images/exemple.jpg"
    )


def test_github_raw_strips_leading_slash():
    config = make_config()
    url = resolve_image_url("/images/exemple.jpg", config)
    assert "//images/" not in url.replace("https://", "")


def test_github_raw_respects_branch():
    config = make_config(github_branch="dev")
    url = resolve_image_url("images/a.jpg", config)
    assert url.endswith("/dev/images/a.jpg")


def test_unknown_strategy_raises():
    config = make_config(image_host="cloudinary")
    with pytest.raises(ImageHostError):
        resolve_image_url("images/a.jpg", config)


def test_empty_image_ref_raises():
    config = make_config()
    with pytest.raises(ImageHostError):
        resolve_image_url("", config)


def test_github_raw_missing_repository_raises():
    config = make_config(github_repository="")
    with pytest.raises(ImageHostError):
        resolve_image_url("images/a.jpg", config)
