from __future__ import annotations

import re
from typing import Any, List, Tuple, Optional  # <-- add Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES_READONLY = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SCOPES_READWRITE = ["https://www.googleapis.com/auth/spreadsheets"]


def extract_spreadsheet_id_from_url(url: str) -> str:
    """
    Helper: given a Google Sheets URL, extract the spreadsheet ID.
    """
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        raise ValueError(f"Could not extract spreadsheet ID from URL: {url}")
    return match.group(1)


class GoogleSheetsClient:
    """
    Simple wrapper around the Google Sheets API using a Service Account.
    """

    def __init__(
        self,
        spreadsheet_id: str,
        credentials_file: str,
        read_only: bool = True,
    ) -> None:
        scopes = SCOPES_READONLY if read_only else SCOPES_READWRITE

        self.spreadsheet_id = spreadsheet_id
        creds = Credentials.from_service_account_file(
            credentials_file,
            scopes=scopes,
        )
        self.service = build("sheets", "v4", credentials=creds)

    def list_sheets(self) -> List[str]:
        metadata = (
            self.service.spreadsheets()
            .get(spreadsheetId=self.spreadsheet_id)
            .execute()
        )
        sheets = metadata.get("sheets", [])
        names: List[str] = []
        for s in sheets:
            props = s.get("properties", {})
            title = props.get("title")
            if title:
                names.append(title)
        return names

    def get_values(
        self,
        sheet_name: str,
        range_a1: str = "A1:Z1000",
    ) -> List[List[Any]]:
        range_name = f"'{sheet_name}'!{range_a1}"
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=range_name)
            .execute()
        )
        return result.get("values", [])

    def get_header_and_rows(
        self,
        sheet_name: str,
        range_a1: str = "A1:Z1000",
    ) -> Tuple[List[str], List[dict]]:
        values = self.get_values(sheet_name, range_a1)
        if not values:
            return [], []

        headers = values[0]
        rows = values[1:]

        records: List[dict] = []
        for row in rows:
            row_dict = {
                headers[i]: (row[i] if i < len(row) else None)
                for i in range(len(headers))
            }
            records.append(row_dict)

        return headers, records


SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "17naV22wjmcj_s5M2o_v5NoUq4dqXGSvrZ4CIRMpmZyQ/"
    "edit?gid=519694341#gid=519694341"
)

_SPREADSHEET_ID = extract_spreadsheet_id_from_url(SHEET_URL)
_default_client: Optional[GoogleSheetsClient] = None


def get_default_client(read_only: bool = True) -> GoogleSheetsClient:
    """
    Return a lazily-created singleton GoogleSheetsClient based on the
    global SERVICE_ACCOUNT_FILE + SHEET_URL config.

    Args:
        read_only (bool):
            Whether the client should use read-only or read-write scopes.
            (Most of your current functions will use read_only=True.)

    Returns:
        GoogleSheetsClient:
            Shared client instance.
    """
    global _default_client
    if _default_client is None:
        # In future, if you need write operations, you can add logic to choose scopes
        _default_client = GoogleSheetsClient(
            spreadsheet_id=_SPREADSHEET_ID,
            credentials_file=SERVICE_ACCOUNT_FILE,
            read_only=read_only,
        )
    return _default_client
