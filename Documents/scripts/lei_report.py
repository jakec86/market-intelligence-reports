import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import io, os, subprocess, xml.etree.ElementTree as ET

# ─── CONFIG ──────────────────────────────────────────────────────────────────
TABLEAU_SERVER     = "https://us-west-2b.online.tableau.com"
TABLEAU_SITE       = "cars"
TABLEAU_PAT_NAME   = "Claude"
TABLEAU_PAT_SECRET = subprocess.check_output(
    ["security", "find-generic-password", "-a", "jcrawley", "-s", "tableau-pat", "-w"]
).decode().strip()
LEI_VIEW_ID        = "6b8a7ea9-9ad2-4677-b044-c088c776ce23"

REPORTS = {
    "Hendricks": {
        "label":    "Hendricks - LEI Report",
        "sheet_id": "1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM",
        "gid":      565895707,
        "filter":   "Hendrick",
    },
    "Nalley": {
        "label":    "Nalley Lexus Galleria - LEI Report",
        "sheet_id": "13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8",
        "gid":      565895707,
        "filter":   "Nalley",
    },
}

SCOPES         = ["https://www.googleapis.com/auth/spreadsheets"]
TOKEN_PATH     = os.path.expanduser("~/.claude/tokens/sheets_token.json")
CLIENT_SECRETS = os.path.expanduser("~/gcp-oauth.keys.json")

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def get_sheets_client():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return gspread.Client(auth=creds)


def tableau_sign_in():
    """Sign in to Tableau with PAT and return (token, site_id)."""
    url = f"{TABLEAU_SERVER}/api/3.21/auth/signin"
    body = {
        "credentials": {
            "personalAccessTokenName": TABLEAU_PAT_NAME,
            "personalAccessTokenSecret": TABLEAU_PAT_SECRET,
            "site": {"contentUrl": TABLEAU_SITE}
        }
    }
    resp = requests.post(url, json=body)
    resp.raise_for_status()
    ns   = {"t": "http://tableau.com/api"}
    root = ET.fromstring(resp.text)
    token   = root.find(".//t:credentials", ns).get("token")
    site_id = root.find(".//t:site", ns).get("id")
    return token, site_id


def fetch_lei_csv() -> pd.DataFrame:
    token, site_id = tableau_sign_in()
    headers = {"x-tableau-auth": token}
    url = f"{TABLEAU_SERVER}/api/3.21/sites/{site_id}/views/{LEI_VIEW_ID}/data"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return pd.read_csv(io.BytesIO(resp.content))


def push_to_sheet(gc, cfg: dict, df: pd.DataFrame):
    sh = gc.open_by_key(cfg["sheet_id"])
    ws = next((w for w in sh.worksheets() if w.id == cfg["gid"]), None)
    if ws is None:
        raise ValueError(f"No tab with gid={cfg['gid']} found.")
    ws.clear()
    data = [df.columns.tolist()] + df.astype(str).values.tolist()
    ws.update(data)
    return ws.title


# ─── UI ───────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="LEI Report → Sheets", layout="wide")
st.title("LEI Report → Google Sheets")
st.caption("Source: Low Engaged Inventory Report (LEI - Local v2) · Tableau CSM Reports · Weekly Mondays")

# ── Step 1: Pull from Tableau ─────────────────────────────────────────────────
st.header("1. Pull from Tableau")

if st.button("Fetch LEI - Local v2", type="primary"):
    with st.spinner("Signing in to Tableau and downloading CSV..."):
        try:
            df = fetch_lei_csv()
            st.session_state["lei_df"] = df
            st.success(f"Fetched {len(df):,} rows · {len(df.columns)} columns")
        except Exception as e:
            st.error(f"Tableau error: {e}")

if "lei_df" not in st.session_state:
    st.info("Click above to pull the latest LEI data from Tableau.")
    st.stop()

df = st.session_state["lei_df"]

with st.expander("Raw data preview", expanded=False):
    st.dataframe(df.head(30), use_container_width=True)
    st.caption(f"Columns: {', '.join(df.columns.tolist())}")

# ── Step 2: Filter & Push ─────────────────────────────────────────────────────
st.header("2. Filter & Push to Sheets")

# Auto-detect dealer name column
dealer_col_candidates = [c for c in df.columns if any(k in c.lower() for k in ["dealer", "account", "name", "group", "customer"])]
default_idx = 0
dealer_col = st.selectbox(
    "Dealer/Account name column:",
    df.columns.tolist(),
    index=df.columns.tolist().index(dealer_col_candidates[0]) if dealer_col_candidates else 0,
)

st.divider()

for key, cfg in REPORTS.items():
    st.subheader(cfg["label"])

    filtered = df[df[dealer_col].astype(str).str.contains(cfg["filter"], case=False, na=False)]
    st.caption(f"{len(filtered):,} rows matching '{cfg['filter']}'")

    if len(filtered) == 0:
        st.warning(f"No rows found containing '{cfg['filter']}' in column '{dealer_col}'. Check column selection above.")
    else:
        st.dataframe(filtered.head(15), use_container_width=True)

    col_push, col_status = st.columns([1, 3])
    with col_push:
        if st.button(f"Push to Sheets", key=f"push_{key}", disabled=(len(filtered) == 0)):
            with st.spinner("Authorizing Google Sheets..."):
                try:
                    gc = get_sheets_client()
                    tab_name = push_to_sheet(gc, cfg, filtered)
                    with col_status:
                        st.success(f"Written {len(filtered):,} rows to tab '{tab_name}'")
                except Exception as e:
                    with col_status:
                        st.error(f"Sheets error: {e}")

    st.divider()
