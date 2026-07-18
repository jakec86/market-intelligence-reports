"""
One-time OAuth flow for Google Slides + Drive write access.
Saves credentials to ~/.claude/tokens/slides_credentials.json

Usage:
    python3 ~/Documents/scripts/slides_auth.py
"""

import json
import urllib.parse
import urllib.request
import http.server
import threading
import webbrowser
import os

CLIENT_SECRETS = os.path.expanduser("~/gcp-oauth.keys.json")
TOKEN_PATH = os.path.expanduser("~/.claude/tokens/slides_credentials.json")
REDIRECT_URI = "http://localhost:3501"
SCOPES = " ".join([
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
])

with open(CLIENT_SECRETS) as f:
    creds = json.load(f)["installed"]
    CLIENT_ID = creds["client_id"]
    CLIENT_SECRET = creds["client_secret"]

auth_code = None

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        auth_code = params.get("code")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Google Slides auth complete! Return to terminal.</h2>")
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
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    })
)

print("Opening browser for Google Slides + Drive auth...")
print(f"\nIf browser doesn't open, visit:\n{auth_url}\n")
webbrowser.open(auth_url)
thread.join()

if not auth_code:
    print("ERROR: No auth code received.")
    exit(1)

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

tokens["client_id"] = CLIENT_ID
tokens["client_secret"] = CLIENT_SECRET

os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
with open(TOKEN_PATH, "w") as f:
    json.dump(tokens, f, indent=2)

print(f"\nCredentials saved to {TOKEN_PATH}")
print("You can now use create_deck.py to generate Google Slides.")
