"""Chargement de la configuration depuis les variables d'environnement.

Toutes les variables sont documentees dans .env.example. En local, un fichier .env
est charge automatiquement si python-dotenv est installe (present dans
requirements-dev.txt) ; en CI, les variables sont deja dans l'environnement
(secrets / vars GitHub Actions).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv est optionnel (pas requis en CI/prod)
    pass


class ConfigError(RuntimeError):
    """Configuration manquante ou invalide."""


def _get_bool(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: str) -> int:
    raw = os.environ.get(name, default)
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} doit etre un entier, recu: {raw!r}") from exc


@dataclass(frozen=True)
class Config:
    ig_user_id: str
    ig_access_token: str
    graph_api_version: str
    timezone: str
    image_host: str
    github_repository: str
    github_branch: str
    calendar_path: str
    dry_run: bool
    max_posts_per_run: int

    @classmethod
    def load(cls) -> "Config":
        ig_user_id = os.environ.get("IG_USER_ID", "").strip()
        ig_access_token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
        image_host = os.environ.get("IMAGE_HOST", "github_raw").strip()
        github_repository = os.environ.get("GITHUB_REPOSITORY", "").strip()

        missing = []
        if not ig_user_id:
            missing.append("IG_USER_ID")
        if not ig_access_token:
            missing.append("IG_ACCESS_TOKEN")
        if image_host == "github_raw" and not github_repository:
            missing.append("GITHUB_REPOSITORY")
        if missing:
            raise ConfigError(
                "Variables d'environnement manquantes: " + ", ".join(missing)
            )

        return cls(
            ig_user_id=ig_user_id,
            ig_access_token=ig_access_token,
            graph_api_version=os.environ.get("GRAPH_API_VERSION", "v21.0").strip(),
            timezone=os.environ.get("TIMEZONE", "Europe/Paris").strip(),
            image_host=image_host,
            github_repository=github_repository,
            github_branch=os.environ.get("GITHUB_BRANCH", "main").strip(),
            calendar_path=os.environ.get("CALENDAR_PATH", "data/calendrier.csv").strip(),
            dry_run=_get_bool("DRY_RUN", "0"),
            max_posts_per_run=_get_int("MAX_POSTS_PER_RUN", "25"),
        )
