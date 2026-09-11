"""Orchestration : lit le calendrier, publie les posts dus, met a jour le CSV.

Point d'entree unique : run(). Utilise par __main__.py (`python -m instagram_automation`)
et par le workflow GitHub Actions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .calendar_csv import (
    STATUS_FAILED,
    STATUS_PUBLISHED,
    find_due_posts,
    read_calendar,
    write_calendar,
)
from .config import Config, ConfigError
from .image_host import ImageHostError, resolve_image_url
from .instagram import InstagramAPIError, InstagramClient

logger = logging.getLogger("instagram_automation")


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        config = Config.load()
    except ConfigError as exc:
        logger.error("Configuration invalide: %s", exc)
        return 1

    tz = ZoneInfo(config.timezone)
    now_local = datetime.now(tz)

    posts = read_calendar(config.calendar_path)
    due_posts = find_due_posts(posts, now_local)

    if not due_posts:
        logger.info("Rien a publier (aucun post du a %s).", now_local.isoformat())
        return 0

    if len(due_posts) > config.max_posts_per_run:
        logger.warning(
            "%d posts dus, limite a %d par execution (garde-fou anti rate-limit).",
            len(due_posts),
            config.max_posts_per_run,
        )
        due_posts = due_posts[: config.max_posts_per_run]

    client = None if config.dry_run else InstagramClient(config)

    published = failed = simulated = 0
    changed = False

    for post in due_posts:
        try:
            image_url = resolve_image_url(post.image, config)
        except ImageHostError as exc:
            logger.error("Ligne %d: %s", post.row_index, exc)
            post.status = STATUS_FAILED
            post.error = str(exc)
            changed = True
            failed += 1
            continue

        if config.dry_run:
            logger.info(
                "[DRY_RUN] publierait: %s %s -> %s (%s)",
                post.date,
                post.time,
                image_url,
                post.caption,
            )
            simulated += 1
            continue

        try:
            media_id = client.publish_post(image_url, post.caption)
        except InstagramAPIError as exc:
            logger.error("Ligne %d: echec de publication: %s", post.row_index, exc)
            post.status = STATUS_FAILED
            post.error = str(exc)
            changed = True
            failed += 1
            continue

        logger.info("Ligne %d: publie avec succes (media_id=%s).", post.row_index, media_id)
        post.status = STATUS_PUBLISHED
        post.published_at = datetime.now(timezone.utc).isoformat()
        post.media_id = media_id
        post.error = ""
        changed = True
        published += 1

    if changed and not config.dry_run:
        write_calendar(config.calendar_path, posts)

    logger.info(
        "Termine: %d publies, %d echoues, %d simules.", published, failed, simulated
    )
    return 1 if failed else 0
