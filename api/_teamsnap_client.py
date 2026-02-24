import os
from datetime import datetime, timedelta, timezone

import requests

BASE_URL = "https://api.teamsnap.com/v3"
TOKEN_URL = "https://auth.teamsnap.com/oauth/token"


def _parse_collection_items(response_json):
    """Convert Collection+JSON items to list of flat dicts."""
    items = response_json.get("collection", {}).get("items", [])
    result = []
    for item in items:
        obj = {entry["name"]: entry["value"] for entry in item.get("data", [])}
        result.append(obj)
    return result


class TeamSnapClient:
    def __init__(self):
        self.access_token = os.environ["TEAMSNAP_ACCESS_TOKEN"]
        self.refresh_token = os.environ.get("TEAMSNAP_REFRESH_TOKEN", "")
        self.client_id = os.environ.get("TEAMSNAP_CLIENT_ID", "")
        self.client_secret = os.environ.get("TEAMSNAP_CLIENT_SECRET", "")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/vnd.collection+json",
        }

    def _refresh_access_token(self):
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise RuntimeError("Cannot refresh token: missing credentials")
        resp = requests.post(TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        if "refresh_token" in data:
            self.refresh_token = data["refresh_token"]

    def _get(self, url, params=None):
        resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
        if resp.status_code == 401:
            self._refresh_access_token()
            resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_user_id(self):
        data = self._get(f"{BASE_URL}/me")
        items = _parse_collection_items(data)
        return items[0]["id"]

    def get_member_id(self, team_id):
        user_id = self.get_user_id()
        data = self._get(f"{BASE_URL}/members/search", params={
            "team_id": team_id,
            "user_id": user_id,
        })
        items = _parse_collection_items(data)
        if not items:
            raise ValueError(f"No member found for user {user_id} on team {team_id}")
        return items[0]["id"]

    def get_events(self, team_id):
        started_after = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        data = self._get(f"{BASE_URL}/events/search", params={
            "team_id": team_id,
            "started_after": started_after,
        })
        return _parse_collection_items(data)

    def get_availabilities(self, team_id, member_id):
        data = self._get(f"{BASE_URL}/availabilities/search", params={
            "team_id": team_id,
            "member_id": member_id,
        })
        return _parse_collection_items(data)

    def get_locations(self, team_id):
        data = self._get(f"{BASE_URL}/locations/search", params={
            "team_id": team_id,
        })
        return _parse_collection_items(data)

    def get_opponents(self, team_id):
        data = self._get(f"{BASE_URL}/opponents/search", params={
            "team_id": team_id,
        })
        return _parse_collection_items(data)
