from google_auth_oauthlib.flow import InstalledAppFlow
import json

flow = InstalledAppFlow.from_client_secrets_file(
    '/Users/jcrawley/gcp-oauth.keys.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
)
creds = flow.run_local_server(port=8099)
token_data = {
    'access_token': creds.token,
    'refresh_token': creds.refresh_token,
    'scope': ' '.join(creds.scopes),
    'token_type': 'Bearer',
}
with open('/Users/jcrawley/.claude/tokens/gsheets_credentials.json', 'w') as f:
    json.dump(token_data, f)
print('Saved write-capable token to gsheets_credentials.json')
