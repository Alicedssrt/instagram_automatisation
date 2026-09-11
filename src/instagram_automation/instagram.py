"""Client minimal pour l'Instagram Graph API (Meta) -- publication d'un post image.

Flux de publication (cf. documentation Meta "Content Publishing") :
1. POST /{ig-user-id}/media          -> cree un conteneur media (image_url, caption)
2. GET  /{container-id}?fields=status_code -> attendre que le conteneur soit pret
3. POST /{ig-user-id}/media_publish  -> publie le conteneur (creation_id)
"""

from __future__ import annotations

import time

import requests

from .config import Config

STATUS_FINISHED = "FINISHED"
STATUS_ERROR = "ERROR"
STATUS_EXPIRED = "EXPIRED"

TOKEN_ERROR_CODE = 190


class InstagramAPIError(RuntimeError):
    """Erreur retournee par l'Instagram Graph API."""


class InstagramClient:
    def __init__(self, config: Config, session: requests.Session | None = None):
        self._config = config
        self._session = session or requests.Session()
        self._base_url = f"https://graph.facebook.com/{config.graph_api_version}"

    def publish_post(self, image_url: str, caption: str) -> str:
        """Enchaine creation du conteneur, attente, puis publication. Retourne le media_id."""
        container_id = self.create_container(image_url, caption)
        self.wait_until_ready(container_id)
        return self.publish_container(container_id)

    def create_container(self, image_url: str, caption: str) -> str:
        url = f"{self._base_url}/{self._config.ig_user_id}/media"
        response = self._session.post(
            url,
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": self._config.ig_access_token,
            },
            timeout=30,
        )
        data = self._check(response)
        container_id = data.get("id")
        if not container_id:
            raise InstagramAPIError(f"Reponse inattendue (pas d'id de conteneur): {data}")
        return container_id

    def wait_until_ready(self, container_id: str, timeout: int = 60, interval: int = 5) -> None:
        url = f"{self._base_url}/{container_id}"
        deadline = time.monotonic() + timeout
        while True:
            response = self._session.get(
                url,
                params={
                    "fields": "status_code",
                    "access_token": self._config.ig_access_token,
                },
                timeout=30,
            )
            data = self._check(response)
            status = data.get("status_code")

            if status == STATUS_FINISHED:
                return
            if status in (STATUS_ERROR, STATUS_EXPIRED):
                raise InstagramAPIError(
                    f"Le conteneur media {container_id} est en erreur (status={status})"
                )
            if time.monotonic() >= deadline:
                raise InstagramAPIError(
                    f"Timeout en attendant que le conteneur media {container_id} soit pret "
                    f"(dernier status={status})"
                )
            time.sleep(interval)

    def publish_container(self, container_id: str) -> str:
        url = f"{self._base_url}/{self._config.ig_user_id}/media_publish"
        response = self._session.post(
            url,
            data={
                "creation_id": container_id,
                "access_token": self._config.ig_access_token,
            },
            timeout=30,
        )
        data = self._check(response)
        media_id = data.get("id")
        if not media_id:
            raise InstagramAPIError(f"Reponse inattendue (pas d'id de media): {data}")
        return media_id

    @staticmethod
    def _check(response: requests.Response) -> dict:
        try:
            data = response.json()
        except ValueError:
            data = {}

        error = data.get("error") if isinstance(data, dict) else None
        if error:
            message = error.get("message", "Erreur inconnue")
            code = error.get("code")
            if code == TOKEN_ERROR_CODE:
                raise InstagramAPIError(
                    f"Token d'acces Meta invalide ou expire (code {code}): {message}"
                )
            raise InstagramAPIError(f"Erreur Instagram Graph API (code {code}): {message}")

        if not response.ok:
            raise InstagramAPIError(
                f"Requete Instagram Graph API echouee (HTTP {response.status_code}): "
                f"{response.text[:500]}"
            )

        return data
