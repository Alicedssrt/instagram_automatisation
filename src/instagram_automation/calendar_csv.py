"""Lecture, filtrage et reecriture du calendrier de publications (CSV).

Colonnes du CSV : date, time, image, caption, status, published_at, media_id, error
- date : "YYYY-MM-DD"
- time : "HH:MM" (24h)
- image : chemin relatif dans le depot (ex. "images/exemple.jpg")
- caption : legende du post
- status : "" / "pending" | "published" | "failed"
- published_at : horodatage ISO UTC au moment de la publication reussie
- media_id : identifiant du media retourne par l'API Instagram
- error : dernier message d'erreur en cas d'echec

Les lignes "published" ne sont jamais republiees. Les lignes "failed" (ou "pending",
ou tout post dont la date/heure est deja passee) sont considerees dues et reessayees
a chaque execution -- c'est ce qui permet de rattraper une execution manquee.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field, fields
from datetime import datetime
from zoneinfo import ZoneInfo

FIELDNAMES = [
    "date",
    "time",
    "image",
    "caption",
    "status",
    "published_at",
    "media_id",
    "error",
]

STATUS_PUBLISHED = "published"
STATUS_FAILED = "failed"
STATUS_PENDING = "pending"


class CalendarError(RuntimeError):
    """Erreur de lecture/parsing du calendrier CSV."""


@dataclass
class Post:
    row_index: int
    date: str
    time: str
    image: str
    caption: str
    status: str = ""
    published_at: str = ""
    media_id: str = ""
    error: str = ""
    extra: dict = field(default_factory=dict, repr=False)

    def local_datetime(self, tz: ZoneInfo) -> datetime:
        try:
            return datetime.strptime(
                f"{self.date} {self.time}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=tz)
        except ValueError as exc:
            raise CalendarError(
                f"Ligne {self.row_index}: date/heure invalide "
                f"({self.date!r} {self.time!r})"
            ) from exc

    def to_row(self) -> dict:
        row = dict(self.extra)
        row.update(
            {
                "date": self.date,
                "time": self.time,
                "image": self.image,
                "caption": self.caption,
                "status": self.status,
                "published_at": self.published_at,
                "media_id": self.media_id,
                "error": self.error,
            }
        )
        return row


_KNOWN_FIELDS = {f.name for f in fields(Post)} - {"row_index", "extra"}


def read_calendar(path: str) -> list[Post]:
    if not os.path.exists(path):
        raise CalendarError(f"Calendrier introuvable: {path}")

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise CalendarError(f"Calendrier vide ou sans en-tete: {path}")

        posts = []
        for index, row in enumerate(reader, start=2):  # ligne 1 = en-tete
            extra = {k: v for k, v in row.items() if k not in _KNOWN_FIELDS}
            posts.append(
                Post(
                    row_index=index,
                    date=(row.get("date") or "").strip(),
                    time=(row.get("time") or "").strip(),
                    image=(row.get("image") or "").strip(),
                    caption=row.get("caption") or "",
                    status=(row.get("status") or "").strip(),
                    published_at=(row.get("published_at") or "").strip(),
                    media_id=(row.get("media_id") or "").strip(),
                    error=row.get("error") or "",
                    extra=extra,
                )
            )
        return posts


def find_due_posts(posts: list[Post], now_local: datetime) -> list[Post]:
    tz = now_local.tzinfo
    due = []
    for post in posts:
        if post.status == STATUS_PUBLISHED:
            continue
        if post.local_datetime(tz) <= now_local:
            due.append(post)
    return due


def write_calendar(path: str, posts: list[Post]) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL, extrasaction="ignore"
        )
        writer.writeheader()
        for post in posts:
            writer.writerow(post.to_row())
    os.replace(tmp_path, path)
