"""Google Sheets data fetching and conversion utilities."""

from typing import Optional

import gspread
import pandas as pd
import polars as pl

from utils.google_sheets_auth import authenticate_gspread


def _make_columns_unique(columns: list[str]) -> list[str]:
    """Make column names unique by appending suffixes to duplicates.

    Example: ['a', 'b', 'a', 'a'] -> ['a', 'b', 'a_1', 'a_2']
    """
    seen: dict[str, int] = {}
    unique_columns = []

    for col in columns:
        if col in seen:
            seen[col] += 1
            unique_columns.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            unique_columns.append(col)

    return unique_columns


def fetch_sheet_as_polars(
    sheet_id: str,
    client: Optional[gspread.Client] = None,
    worksheet_index: int = 0,
    worksheet_gid: Optional[int] = None,
) -> pl.DataFrame:
    """
    Fetch Google Sheet data and convert to Polars DataFrame.

    Args:
        sheet_id: Sheet ID from URL (e.g., '1MYnMn4p3nRk51T4sMYyzUrKYAcgaMJsnTvu5AGv9UBo')
        client: Authenticated gspread client (will authenticate if None)
        worksheet_index: Which worksheet tab to read (default: 0 = first tab).
            Ignored if worksheet_gid is provided.
        worksheet_gid: The gid of a specific worksheet (from URL parameter 'gid').
            Takes precedence over worksheet_index if provided.

    Returns:
        Polars DataFrame with sheet data.

    Raises:
        RuntimeError: If authentication fails.
        gspread.exceptions.SpreadsheetNotFound: If sheet doesn't exist or no access.
        gspread.exceptions.WorksheetNotFound: If worksheet index/gid doesn't exist.
        gspread.exceptions.APIError: If API rate limits or other API issues.

    Flow:
        1. Authenticate with gspread (if client not provided)
        2. Open spreadsheet by ID
        3. Get worksheet (by gid if provided, otherwise by index)
        4. Fetch all values as list of lists
        5. Convert to pandas DataFrame (headers from first row)
        6. Convert pandas -> polars
        7. Return polars DataFrame
    """
    # Authenticate if client not provided
    if client is None:
        client = authenticate_gspread()

    # Open spreadsheet
    print(f"Opening Google Sheet: {sheet_id}")
    try:
        spreadsheet = client.open_by_key(sheet_id)
    except gspread.exceptions.SpreadsheetNotFound as e:
        raise gspread.exceptions.SpreadsheetNotFound(
            f"Spreadsheet not found: {sheet_id}\n\n"
            "Possible causes:\n"
            "1. The sheet ID is incorrect\n"
            "2. The sheet is not shared with your Google account\n"
            "3. The sheet has been deleted\n\n"
            "To fix:\n"
            "1. Verify the sheet ID in the URL\n"
            "2. Ask the sheet owner to share it with your email"
        ) from e

    # Get worksheet (by gid if provided, otherwise by index)
    try:
        if worksheet_gid is not None:
            worksheet = spreadsheet.get_worksheet_by_id(worksheet_gid)
        else:
            worksheet = spreadsheet.get_worksheet(worksheet_index)
    except gspread.exceptions.WorksheetNotFound as e:
        available_sheets = [(ws.title, ws.id) for ws in spreadsheet.worksheets()]
        if worksheet_gid is not None:
            raise gspread.exceptions.WorksheetNotFound(
                f"Worksheet gid {worksheet_gid} not found.\n\n"
                f"Available worksheets (title, gid): {available_sheets}\n\n"
                "Use worksheet_gid parameter with a valid gid."
            ) from e
        else:
            raise gspread.exceptions.WorksheetNotFound(
                f"Worksheet index {worksheet_index} not found.\n\n"
                f"Available worksheets (title, gid): {available_sheets}\n\n"
                "Use worksheet_index or worksheet_gid parameter to select a different tab."
            ) from e

    if worksheet is None:
        available_sheets = [(ws.title, ws.id) for ws in spreadsheet.worksheets()]
        raise RuntimeError(
            f"Worksheet not found.\n\n"
            f"Available worksheets (title, gid): {available_sheets}\n\n"
            "Use worksheet_index or worksheet_gid parameter to select a different tab."
        )

    print(f"Reading worksheet: '{worksheet.title}'")

    # Fetch all values as list of lists
    try:
        all_values = worksheet.get_all_values()
    except gspread.exceptions.APIError as e:
        raise gspread.exceptions.APIError(
            f"Google Sheets API error: {e}\n\n"
            "Possible causes:\n"
            "1. API rate limit exceeded (100 requests per 100 seconds)\n"
            "2. Google Sheets API not enabled in your project\n"
            "3. Temporary API outage\n\n"
            "To fix:\n"
            "1. Wait a few seconds and try again\n"
            "2. Enable Google Sheets API in Google Cloud Console"
        ) from e

    if not all_values:
        raise RuntimeError(
            f"Sheet '{worksheet.title}' is empty.\n\n"
            "The worksheet contains no data. Please check:\n"
            "1. You're reading the correct worksheet tab\n"
            "2. The data hasn't been moved or deleted"
        )

    # Convert to pandas DataFrame (first row = headers)
    raw_headers = all_values[0]
    headers = _make_columns_unique(raw_headers)
    data_rows = all_values[1:]

    # Warn about duplicate columns
    if len(headers) != len(set(raw_headers)):
        duplicates = [h for h in raw_headers if raw_headers.count(h) > 1]
        print(f"Warning: Found duplicate column names: {set(duplicates)}. Suffixes added to make unique.")

    df_pandas = pd.DataFrame(data_rows, columns=headers)

    # Convert pandas -> polars
    df_polars = pl.from_pandas(df_pandas)

    print(f"Successfully loaded {len(df_polars)} rows, {len(df_polars.columns)} columns")
    return df_polars
