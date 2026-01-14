"""Google Sheets OAuth2 authentication utilities."""

from pathlib import Path
from typing import Optional
import pickle

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def get_credentials_path() -> Path:
    """
    Get path to gspread credentials directory.

    Returns ~/.config/gspread/ directory path.
    """
    return Path.home() / ".config" / "gspread"


def authenticate_gspread() -> gspread.Client:
    """
    Authenticate with Google Sheets using OAuth2 flow.

    Returns:
        gspread.Client: Authenticated client for Google Sheets API.

    Raises:
        RuntimeError: If authentication fails (missing credentials, user cancellation, etc.)

    Flow:
        1. Check for cached credentials at ~/.config/gspread/token.pickle
        2. If exists and valid -> use cached credentials
        3. If expired -> refresh tokens automatically
        4. If not found -> run OAuth2 browser flow
        5. Save tokens for future use
    """
    creds_dir = get_credentials_path()
    token_file = creds_dir / "token.pickle"
    client_secrets_file = creds_dir / "client_secrets.json"

    # Check if client_secrets.json exists
    if not client_secrets_file.exists():
        raise RuntimeError(
            f"OAuth2 credentials file not found at: {client_secrets_file}\n\n"
            "To set up Google Sheets access:\n"
            "1. Run: ./scripts/setup_gcloud_oauth.sh\n"
            "2. Or manually download OAuth2 credentials from Google Cloud Console\n"
            "3. Save as: ~/.config/gspread/client_secrets.json\n"
            "4. Set permissions: chmod 600 ~/.config/gspread/client_secrets.json"
        )

    creds: Optional[Credentials] = None

    # Try to load cached credentials
    if token_file.exists():
        with open(token_file, "rb") as token:
            creds = pickle.load(token)

    # If no valid credentials, run OAuth2 flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            try:
                creds.refresh(Request())
            except Exception as e:
                raise RuntimeError(
                    f"Failed to refresh OAuth2 credentials: {e}\n\n"
                    "Try deleting the token file and re-authenticating:\n"
                    f"  rm {token_file}\n"
                    "Then run the notebook again."
                ) from e
        else:
            print("")
            print("=" * 70)
            print("OAUTH2 AUTHENTICATION REQUIRED")
            print("=" * 70)
            print("")
            print("SSH PORT FORWARDING REQUIRED!")
            print("If not already done, reconnect with:")
            print("  ssh -L 8080:localhost:8080 user@server")
            print("")
            print("A URL will be printed below. Copy it and open in your LOCAL browser.")
            print("After granting access, the browser redirects and auth completes.")
            print("")
            print("=" * 70)
            print("")

            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_file), SCOPES
            )

            try:
                creds = flow.run_local_server(
                    port=8080,
                    open_browser=False,
                    authorization_prompt_message=(
                        "\nCopy this URL and open in your browser:\n\n{url}\n\n"
                        "Waiting for authentication...\n"
                    ),
                    success_message=(
                        "Authentication successful! You can close this browser tab."
                    ),
                )
            except Exception as e:
                raise RuntimeError(
                    f"OAuth2 authentication failed: {e}\n\n"
                    "Possible causes:\n"
                    "1. Port 8080 is already in use on the server\n"
                    "2. SSH port forwarding not set up\n"
                    "3. User cancelled authentication\n"
                    "4. Invalid client_secrets.json file\n\n"
                    "For SSH connections, reconnect with port forwarding:\n"
                    "  ssh -L 8080:localhost:8080 user@server"
                ) from e

        # Save credentials for next time
        creds_dir.mkdir(parents=True, exist_ok=True)
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)
        print(f"Credentials saved to {token_file}")

    # Create and return gspread client
    client = gspread.authorize(creds)
    print("Google Sheets authentication successful!")
    return client
