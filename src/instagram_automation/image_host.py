"""Resolution de l'URL publique d'une image, isolee du reste du script.

C'est le point d'evolutivite identifie dans le cahier des charges (section 5) :
pour basculer d'un hebergement sur le depot GitHub public vers un service dedie
(Cloudinary, AWS S3...), il suffit d'ajouter une implementation d'ImageHost et une
entree dans _STRATEGIES, sans toucher a instagram.py ni publisher.py.
"""

from __future__ import annotations

from typing import Protocol

from .config import Config


class ImageHostError(RuntimeError):
    """Impossible de resoudre l'URL publique d'une image."""


class ImageHost(Protocol):
    def resolve(self, image_ref: str, config: Config) -> str: ...


class GithubRawImageHost:
    """V1 : images versionnees dans le depot, servies via raw.githubusercontent.com.

    Suppose un depot public -- si le depot devient prive, raw.githubusercontent.com
    n'est plus accessible sans authentification et il faut basculer vers un autre
    ImageHost (Cloudinary, S3...).
    """

    def resolve(self, image_ref: str, config: Config) -> str:
        if not config.github_repository:
            raise ImageHostError(
                "GITHUB_REPOSITORY doit etre defini pour la strategie github_raw"
            )
        path = image_ref.lstrip("/")
        return (
            f"https://raw.githubusercontent.com/{config.github_repository}"
            f"/{config.github_branch}/{path}"
        )


_STRATEGIES: dict[str, ImageHost] = {
    "github_raw": GithubRawImageHost(),
}


def resolve_image_url(image_ref: str, config: Config) -> str:
    if not image_ref:
        raise ImageHostError("Le champ image est vide")

    strategy = _STRATEGIES.get(config.image_host)
    if strategy is None:
        known = ", ".join(sorted(_STRATEGIES))
        raise ImageHostError(
            f"Strategie d'hebergement d'image inconnue: {config.image_host!r} "
            f"(connues: {known})"
        )
    return strategy.resolve(image_ref, config)
