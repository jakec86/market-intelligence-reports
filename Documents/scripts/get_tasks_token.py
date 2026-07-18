"""
Run this once to get a Google Tasks refresh token.
After completing the OAuth flow, it prints the refresh token.
Then paste it into ~/.claude/settings.json under google-tasks > env > REFRESH_TOKEN.

Usage:
    python3 ~/Desktop/get_tasks_token.py
"""

import json
import urllib.parse
import urllib.request
import http.server
import threading
import webbrowser
import os

CLIENT_SECRETS = os.path.expanduser("~/gcp-oauth.keys.json")
with open(CLIENT_SECRETS) as f:
    _creds = json.load(f)["installed"]
    CLIENT_ID = _creds["client_id"]
    CLIENT_SECRET = _creds["client_secret"]
REDIRECT_URI = "http://localhost:3501"
SCOPE = "https://www.googleapis.com/auth/tasks"

auth_code = None

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        auth_code = params.get("code")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Auth complete! Return to terminal.</h2>")
    def log_message(self, *args):
        pass

server = http.server.HTTPServer(("localhost", 3501), Handler)
thread = threading.Thread(target=server.handle_request)
thread.start()

auth_url = (
    "https://accounts.google.com/o/oauth2/v2/auth?"
    + urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
)

print("Opening browser for Google Tasks auth...")
print(f"\nIf browser doesn't open, visit:\n{auth_url}\n")
webbrowser.open(auth_url)
thread.join()

# Exchange code for tokens
data = urllib.parse.urlencode({
    "code": auth_code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
}).encode()

req = urllib.request.Request(
    "https://oauth2.googleapis.com/token",
    data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
with urllib.request.urlopen(req) as resp:
    tokens = json.loads(resp.read())

refresh_token = tokens.get("refresh_token")
print(f"\nRefresh token:\n{refresh_token}")
print("\nAdd this to ~/.claude/settings.json under google-tasks > env > REFRESH_TOKEN")
