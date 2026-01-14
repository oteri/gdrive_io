# google-drive-access

This document explains how to access a Google Sheets file stored in Google Drive.

## Prerequisites: Install required Python packages

Make sure the following Python packages are installed in your environment:

* `gspread`
* `google-auth`
* `google-auth-oauthlib`
* `google-auth-httplib2`

You can install them using `pip`:

```bash
pip install \
  "gspread>=6.1.4" \
  "google-auth>=2.35.0" \
  "google-auth-oauthlib>=1.2.1" \
  "google-auth-httplib2>=0.2.0"
```

If you are using a virtual environment (recommended), ensure it is activated before running the command.


## A. Create the credentials

 Step 1: Create Google Cloud Project
 1. Go to https://console.cloud.google.com/
 2. Create a new project (e.g., "Your-project")
 Step 2: Enable Google Sheets API
 1. Navigate to "APIs & Services" > "Library"
 2. Search for "Google Sheets API"
 3. Click "Enable"
 Step 3: Create OAuth2 Credentials
 1. Go to "APIs & Services" > "Credentials"
 2. Click "Create Credentials" > "OAuth client ID"
 3. If prompted, configure consent screen:
   - User type: Internal (company workspace)
   - App name: "Your App Name"
   - Scopes: Add https://www.googleapis.com/auth/spreadsheets.readonly
 4. Application type: "Desktop app"
 5. Name: "Your Client"
 6. Click "Create"
 7. Download the JSON file to `$HOME/.config/gspread/client_secrets.json`

---

## B. Retrieve spreadsheet identifiers

You need two pieces of information from the Google Sheets URL:

* **SHEET_ID**: the spreadsheet identifier
* **WORKSHEET_GID**: the identifier of the worksheet (tab) inside the spreadsheet

### Example

If the Google Sheets URL is:

```
https://docs.google.com/spreadsheets/d/XXXXX/edit?gid=1234567890
```

Then:

```text
SHEET_ID = "XXXXX"  # Spreadsheet ID
WORKSHEET_GID = 1234567890  # Worksheet (tab) ID
```

You will use these values in your code.

---

## C. Access the data using Python

Below is an example of Python code that loads data from Google Sheets into a Polars DataFrame:

```python
import sys
import polars as pl

sys.path.insert(0, "src")  # If files are not accessible via the default PYTHONPATH
from google_sheets_data import fetch_sheet_as_polars

# Google Sheet configuration
SHEET_ID = "XXXXX"  # Spreadsheet ID
WORKSHEET_GID = 1234567890  # Worksheet (tab) ID

print("Loading curated dataset from Google Sheets...")

# Load data from Google Sheets (raises an exception on failure)
curated_df = fetch_sheet_as_polars(SHEET_ID, worksheet_gid=WORKSHEET_GID)
```

---

## D. OAuth authentication flow

When you run the code for the first time, you will see output similar to the following:

```text
Loading curated dataset from Google Sheets...

======================================================================
OAUTH2 AUTHENTICATION REQUIRED
======================================================================

SSH PORT FORWARDING REQUIRED!
If not already done, reconnect with:
  ssh -L 8080:localhost:8080 user@server

A URL will be printed below. Copy it and open it in your LOCAL browser.
After granting access, the browser redirects and authentication completes.

======================================================================

Copy this URL and open it in your browser:

https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=blablabla

Waiting for authentication...
```

---

## E. Required authentication steps

Two steps are critical for authentication:

### Step 1: SSH port forwarding (if needed)

If the notebook is running on a remote server and your browser is on a different machine, you must forward port `8080` before starting authentication:

```bash
ssh -L 8080:localhost:8080 user@server
```

This is required because the OAuth flow redirects authentication data back to the server via the local port.

### Step 2: Complete authentication in the browser

1. Copy the authentication URL printed in the terminal.
2. Paste it into your browser (an incognito/private window may be required).
3. Grant access when prompted.

---

## F. Completion

Once authentication completes successfully, the data will be loaded and displayed in your environment.
