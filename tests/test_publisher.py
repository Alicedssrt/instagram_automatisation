import csv
from pathlib import Path

import responses

from instagram_automation import publisher

BASE = "https://graph.facebook.com/v21.0"


def _write_calendar(path: Path, rows: list[dict]) -> None:
    fieldnames = ["date", "time", "image", "caption", "status", "published_at", "media_id", "error"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({**{k: "" for k in fieldnames}, **row})


def _read_calendar(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _set_base_env(monkeypatch, calendar_path: Path, dry_run: str = "0"):
    monkeypatch.setenv("IG_USER_ID", "ig123")
    monkeypatch.setenv("IG_ACCESS_TOKEN", "token-abc")
    monkeypatch.setenv("GITHUB_REPOSITORY", "alicedussart/instagram_automatisation")
    monkeypatch.setenv("GITHUB_BRANCH", "main")
    monkeypatch.setenv("CALENDAR_PATH", str(calendar_path))
    monkeypatch.setenv("DRY_RUN", dry_run)
    monkeypatch.setenv("TIMEZONE", "Europe/Paris")


def test_dry_run_makes_no_api_call_and_does_not_rewrite_csv(tmp_path, monkeypatch):
    calendar_path = tmp_path / "calendrier.csv"
    _write_calendar(
        calendar_path,
        [{"date": "2024-01-01", "time": "09:00", "image": "images/a.jpg", "caption": "c"}],
    )
    _set_base_env(monkeypatch, calendar_path, dry_run="1")

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        # aucune requete ne doit etre enregistree/consommee
        exit_code = publisher.run()
        assert len(rsps.calls) == 0

    assert exit_code == 0
    rows = _read_calendar(calendar_path)
    assert rows[0]["status"] == ""


@responses.activate
def test_successful_publish_updates_csv_and_returns_zero(tmp_path, monkeypatch):
    calendar_path = tmp_path / "calendrier.csv"
    _write_calendar(
        calendar_path,
        [{"date": "2024-01-01", "time": "09:00", "image": "images/a.jpg", "caption": "c"}],
    )
    _set_base_env(monkeypatch, calendar_path)

    responses.add(responses.POST, f"{BASE}/ig123/media", json={"id": "container-1"}, status=200)
    responses.add(responses.GET, f"{BASE}/container-1", json={"status_code": "FINISHED"}, status=200)
    responses.add(
        responses.POST, f"{BASE}/ig123/media_publish", json={"id": "media-1"}, status=200
    )

    exit_code = publisher.run()

    assert exit_code == 0
    rows = _read_calendar(calendar_path)
    assert rows[0]["status"] == "published"
    assert rows[0]["media_id"] == "media-1"
    assert rows[0]["published_at"] != ""


@responses.activate
def test_one_failure_does_not_block_other_posts(tmp_path, monkeypatch):
    calendar_path = tmp_path / "calendrier.csv"
    _write_calendar(
        calendar_path,
        [
            {"date": "2024-01-01", "time": "09:00", "image": "images/broken.jpg", "caption": "echoue"},
            {"date": "2024-01-01", "time": "10:00", "image": "images/ok.jpg", "caption": "ok"},
        ],
    )
    _set_base_env(monkeypatch, calendar_path)

    responses.add(
        responses.POST,
        f"{BASE}/ig123/media",
        json={"error": {"message": "Invalid parameter", "code": 100}},
        status=400,
    )
    responses.add(responses.POST, f"{BASE}/ig123/media", json={"id": "container-2"}, status=200)
    responses.add(responses.GET, f"{BASE}/container-2", json={"status_code": "FINISHED"}, status=200)
    responses.add(
        responses.POST, f"{BASE}/ig123/media_publish", json={"id": "media-2"}, status=200
    )

    exit_code = publisher.run()

    assert exit_code == 1
    rows = _read_calendar(calendar_path)
    assert rows[0]["status"] == "failed"
    assert "Invalid parameter" in rows[0]["error"]
    assert rows[1]["status"] == "published"
    assert rows[1]["media_id"] == "media-2"


def test_no_due_posts_returns_zero_without_rewrite(tmp_path, monkeypatch):
    calendar_path = tmp_path / "calendrier.csv"
    _write_calendar(
        calendar_path,
        [{"date": "2999-01-01", "time": "09:00", "image": "images/a.jpg", "caption": "futur"}],
    )
    _set_base_env(monkeypatch, calendar_path)

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        exit_code = publisher.run()
        assert len(rsps.calls) == 0

    assert exit_code == 0
