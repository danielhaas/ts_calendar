import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from api._teamsnap_client import TeamSnapClient, _parse_collection_items, BASE_URL

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TeamSnap Calendar Feed</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 480px; margin: 60px auto; padding: 0 20px; color: #333; }
  h1 { font-size: 1.4em; }
  select { width: 100%; padding: 10px; font-size: 16px; margin: 12px 0; }
  #result { display: none; margin-top: 20px; }
  .url-box { background: #f4f4f4; padding: 12px; border-radius: 6px;
             word-break: break-all; font-family: monospace; font-size: 14px;
             margin: 10px 0; }
  button { background: #0070f3; color: white; border: none; padding: 10px 20px;
           border-radius: 6px; font-size: 14px; cursor: pointer; }
  button:hover { background: #005cc5; }
  .hint { color: #666; font-size: 13px; margin-top: 8px; }
</style>
</head>
<body>
<h1>TEAM_NAME</h1>
<p>Select your name to get a calendar subscription URL that shows only events you've RSVP'd Yes or Maybe to.</p>

<select id="member" onchange="showLink()">
  <option value="">-- Select your name --</option>
  MEMBER_OPTIONS
</select>

<div id="result">
  <p><strong>Your calendar feed URL:</strong></p>
  <div class="url-box" id="url"></div>
  <button onclick="copyUrl()">Copy URL</button>
  <span id="copied" style="display:none; color:#0a0; margin-left:8px;">Copied!</span>
  <p class="hint">Add this URL as a calendar subscription in Google Calendar, Apple Calendar, or Outlook.</p>
</div>

<script>
var baseUrl = location.origin + "/api/calendar?team_id=TEAM_ID&key=FEED_KEY";
function showLink() {
  var mid = document.getElementById("member").value;
  var el = document.getElementById("result");
  if (!mid) { el.style.display = "none"; return; }
  var url = baseUrl + "&member_id=" + mid;
  document.getElementById("url").textContent = url;
  el.style.display = "block";
  document.getElementById("copied").style.display = "none";
}
function copyUrl() {
  navigator.clipboard.writeText(document.getElementById("url").textContent);
  document.getElementById("copied").style.display = "inline";
  setTimeout(function(){ document.getElementById("copied").style.display = "none"; }, 2000);
}
</script>
<footer style="margin-top:40px; padding-top:16px; border-top:1px solid #eee; font-size:12px; color:#999;">
  <a href="https://github.com/danielhaas/ts_calendar" style="color:#999;">Source on GitHub</a>
</footer>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        password = os.environ.get("FEED_PASSWORD", "")
        if password:
            key = params.get("key", [None])[0]
            if key != password:
                self.send_response(403)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Forbidden: invalid key")
                return

        team_id = params.get("team_id", [None])[0]
        if not team_id:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Missing required query parameter: team_id")
            return

        try:
            client = TeamSnapClient()

            # Fetch team name
            team_data = client._get(f"{BASE_URL}/teams/{team_id}")
            team_items = _parse_collection_items(team_data)
            team_name = team_items[0].get("name", "TeamSnap") if team_items else "TeamSnap"

            data = client._get(f"{BASE_URL}/members/search", params={
                "team_id": team_id,
            })
            members = _parse_collection_items(data)
            members_list = [
                {
                    "member_id": m.get("id"),
                    "name": f"{m.get('first_name', '')} {m.get('last_name', '')}".strip(),
                }
                for m in members
            ]
            members_list.sort(key=lambda m: m["name"])

            options = "\n  ".join(
                f'<option value="{m["member_id"]}">{m["name"]}</option>'
                for m in members_list
            )
            html = HTML_TEMPLATE.replace("TEAM_NAME", team_name)
            html = html.replace("MEMBER_OPTIONS", options)
            html = html.replace("TEAM_ID", str(team_id))
            html = html.replace("FEED_KEY", password)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())
