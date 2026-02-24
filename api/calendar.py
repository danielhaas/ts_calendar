import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from api._ical_generator import generate_ical
from api._teamsnap_client import TeamSnapClient

# In-memory cache for warm serverless instances
_cache = {}
CACHE_TTL = 300  # 5 minutes


def _get_cached(team_id):
    entry = _cache.get(team_id)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL:
        return entry["data"]
    return None


def _set_cached(team_id, data):
    _cache[team_id] = {"data": data, "ts": time.time()}


def _build_feed(team_id, member_id=None):
    client = TeamSnapClient()

    # 1. Get member_id — use provided one, or look up current user's
    if not member_id:
        member_id = client.get_member_id(team_id)

    # 2. Fetch events, availabilities, locations, and opponents
    events = client.get_events(team_id)
    availabilities = client.get_availabilities(team_id, member_id)
    locations_list = client.get_locations(team_id)
    opponents_list = client.get_opponents(team_id)

    # 3. Build lookup maps
    avail_by_event = {a["event_id"]: a for a in availabilities}
    locations_by_id = {loc["id"]: loc for loc in locations_list}
    opponents_by_id = {opp["id"]: opp for opp in opponents_list}

    # 4. Filter to Yes (1) or Maybe (2)
    filtered = []
    for ev in events:
        avail = avail_by_event.get(ev["id"])
        if avail and avail.get("status_code") in (1, 2):
            filtered.append(ev)

    # 5. Generate iCal
    return generate_ical(filtered, locations_by_id, opponents_by_id)


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

        member_id = params.get("member_id", [None])[0]

        # Check cache (keyed by team_id + member_id)
        cache_key = f"{team_id}:{member_id or 'me'}"
        ical_data = _get_cached(cache_key)
        if not ical_data:
            try:
                ical_data = _build_feed(team_id, member_id)
                _set_cached(cache_key, ical_data)
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
