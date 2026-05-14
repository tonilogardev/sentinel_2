"""Copernicus DataSpace OData API client."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests


BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"


@dataclass
class TokenManager:
    username: str
    password: str
    _token: dict[str, Any] = field(default_factory=dict)

    def _request_token(self, data: dict[str, str]) -> dict[str, Any]:
        r = requests.post(AUTH_URL, data=data, timeout=30)
        r.raise_for_status()
        token = r.json()
        token["t0"] = time.time()
        return token

    def get_access_token(self) -> str:
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "client_id": "cdse-public",
        }
        self._token = self._request_token(data)
        return self._token["access_token"]

    def refresh_token(self) -> str:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._token["refresh_token"],
            "client_id": "cdse-public",
        }
        self._token = self._request_token(data)
        return self._token["access_token"]

    @property
    def access_token(self) -> str:
        return self._token.get("access_token", "")

    @property
    def is_expired(self) -> bool:
        if not self._token:
            return True
        elapsed = time.time() - self._token["t0"]
        return elapsed >= self._token.get("expires_in", 0) - 60


@dataclass
class DataSpaceClient:
    username: str
    password: str
    base_url: str = BASE_URL

    def __post_init__(self) -> None:
        self._token_mgr = TokenManager(self.username, self.password)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "DataSpaceClient":
        creds = config.get("_credentials", {})
        api = config.get("api", {})
        return cls(
            username=creds.get("username", ""),
            password=creds.get("password", ""),
            base_url=api.get("downloadURL", BASE_URL),
        )

    def _ensure_token(self) -> str:
        mgr = self._token_mgr
        if not mgr.access_token:
            return mgr.get_access_token()

        elapsed = time.time() - mgr._token["t0"]
        expires_in = mgr._token.get("expires_in", 3600)
        refresh_expires_in = mgr._token.get("refresh_expires_in", 86400)

        if elapsed < expires_in - 60:
            return mgr.access_token

        if elapsed < refresh_expires_in - 60:
            print("  Token expired — refreshing...")
            return mgr.refresh_token()

        print("  Refresh token expired — re-authenticating...")
        return mgr.get_access_token()

    def search(
        self,
        *,
        date: str,
        orbit: str,
        polygon_wkt: str,
        product_type: str = "MSIL1C",
        cloud_cover: float | None = None,
        top: int = 500,
    ) -> list[dict[str, Any]]:
        token = self._ensure_token()
        filters = [
            f"contains(Name,'{product_type}')",
            f"contains(Name,'{orbit}')",
            f"ContentDate/Start ge {date}T00:00:00.000Z",
            f"ContentDate/End le {date}T23:59:59.000Z",
            f"OData.CSC.Intersects(area=geography'SRID=4326;{polygon_wkt}')",
        ]
        if cloud_cover is not None:
            filters.append(
                f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
                f"and att/OData.CSC.DoubleAttribute/Value lt {cloud_cover})"
            )

        url = f"{self.base_url}odata/v1/Products?$filter={' and '.join(filters)}&$top={top}&$expand=Attributes"
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        r.raise_for_status()
        return r.json().get("value", [])

    def get_checksum(self, product_id: str) -> str | None:
        token = self._ensure_token()
        url = f"{self.base_url}odata/v1/Products?$filter=Id eq '{product_id}'"
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        r.raise_for_status()
        for c in r.json().get("value", [{}])[0].get("Checksum", []):
            if c.get("Algorithm") == "MD5":
                return c.get("Value")
        return None

    def get_download_url(self, product_id: str) -> str:
        return f"{self.base_url}odata/v1/Products({product_id})/$value"
