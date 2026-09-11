import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from instagram_automation.calendar_csv import (
    CalendarError,
    Post,
    find_due_posts,
    read_calendar,
    write_calendar,
)

TZ = ZoneInfo("Europe/Paris")


def test_read_calendar_parses_all_rows(fixtures_dir):
    posts = read_calendar(os.path.join(fixtures_dir, "calendrier_sample.csv"))
    assert len(posts) == 4
    assert posts[0].status == "published"
    assert posts[0].media_id == "123456"
    assert posts[1].status == ""
    assert posts[2].status == "failed"
    assert posts[2].error == "Erreur precedente"


def test_read_calendar_missing_file_raises():
    with pytest.raises(CalendarError):
        read_calendar("does/not/exist.csv")


def test_find_due_posts_catches_up_past_and_skips_future(fixtures_dir):
    posts = read_calendar(os.path.join(fixtures_dir, "calendrier_sample.csv"))
    now = datetime(2026, 1, 1, 12, 0, tzinfo=TZ)

    due = find_due_posts(posts, now)
    due_captions = {p.caption for p in due}

    # publie -> jamais republie
    assert "Post passe, deja publie" not in due_captions
    # en attente et deja passe -> rattrape
    assert "Post passe, jamais publie" in due_captions
    # en echec et deja passe -> reessaye
    assert "Post passe, en echec" in due_captions
    # dans le futur -> ignore
    assert "Post futur, ne doit pas etre publie" not in due_captions


def test_find_due_posts_respects_timezone():
    posts = [
        Post(row_index=2, date="2026-01-01", time="10:00", image="i.jpg", caption="c")
    ]
    just_before = datetime(2026, 1, 1, 9, 59, tzinfo=TZ)
    just_after = datetime(2026, 1, 1, 10, 0, tzinfo=TZ)

    assert find_due_posts(posts, just_before) == []
    assert find_due_posts(posts, just_after) == posts


def test_local_datetime_invalid_raises():
    post = Post(row_index=2, date="not-a-date", time="10:00", image="i.jpg", caption="c")
    with pytest.raises(CalendarError):
        post.local_datetime(TZ)


def test_write_calendar_round_trip_preserves_data(tmp_path):
    src = os.path.join(os.path.dirname(__file__), "fixtures", "calendrier_sample.csv")
    posts = read_calendar(src)

    out_path = tmp_path / "out.csv"
    write_calendar(str(out_path), posts)

    reloaded = read_calendar(str(out_path))
    assert len(reloaded) == len(posts)
    for original, again in zip(posts, reloaded):
        assert original.date == again.date
        assert original.time == again.time
        assert original.image == again.image
        assert original.caption == again.caption
        assert original.status == again.status
        assert original.media_id == again.media_id
        assert original.error == again.error


def test_write_calendar_quotes_captions_with_commas(tmp_path):
    posts = [
        Post(
            row_index=2,
            date="2026-01-01",
            time="10:00",
            image="images/a.jpg",
            caption="Bonjour, le monde !",
        )
    ]
    out_path = tmp_path / "out.csv"
    write_calendar(str(out_path), posts)

    content = out_path.read_text(encoding="utf-8")
    assert '"Bonjour, le monde !"' in content

    reloaded = read_calendar(str(out_path))
    assert reloaded[0].caption == "Bonjour, le monde !"


def test_write_calendar_updates_status_after_publish(tmp_path):
    posts = [
        Post(
            row_index=2,
            date="2026-01-01",
            time="10:00",
            image="images/a.jpg",
            caption="c",
            status="pending",
        )
    ]
    posts[0].status = "published"
    posts[0].published_at = "2026-01-01T10:00:05+00:00"
    posts[0].media_id = "987"

    out_path = tmp_path / "out.csv"
    write_calendar(str(out_path), posts)

    reloaded = read_calendar(str(out_path))
    assert reloaded[0].status == "published"
    assert reloaded[0].media_id == "987"
