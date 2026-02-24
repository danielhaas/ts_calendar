#!/usr/bin/env python3
"""Local test server for the calendar feed."""

import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Load .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

from api._teamsnap_client import TeamSnapClient
from api._ical_generator import generate_ical
from api.calendar import _build_feed, _get_cached, _set_cached


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path not in ("/api/calendar", "/api/calendar/"):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found. Use /api/calendar?team_id=YOUR_TEAM_ID")
            return

        params = parse_qs(parsed.query)
        team_id = params.get("team_id", [None])[0]

        if not team_id:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Missing required query parameter: team_id")
            return

        ical_data = _get_cached(team_id)
        if not ical_data:
            try:
                ical_data = _build_feed(team_id)
                _set_cached(team_id, ical_data)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode())
                return

        self.send_response(200)
        self.send_header("Content-Type", "text/calendar; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(ical_data)


if __name__ == "__main__":
    port = 3000
    server = HTTPServer(("", port), Handler)
    print(f"Serving on http://localhost:{port}")
    print(f"Test: curl http://localhost:{port}/api/calendar?team_id=YOUR_TEAM_ID")
    server.serve_forever()
