import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from api._teamsnap_client import TeamSnapClient, _parse_collection_items, BASE_URL


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        team_id = params.get("team_id", [None])[0]
        if not team_id:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Missing required query parameter: team_id")
            return

        try:
            client = TeamSnapClient()
            data = client._get(f"{BASE_URL}/members/search", params={
                "team_id": team_id,
            })
            members = _parse_collection_items(data)
            result = [
                {
                    "member_id": m.get("id"),
                    "name": f"{m.get('first_name', '')} {m.get('last_name', '')}".strip(),
                }
                for m in members
            ]
            result.sort(key=lambda m: m["name"])

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())
