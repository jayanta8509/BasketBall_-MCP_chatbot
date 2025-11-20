from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sheets_client import get_default_client
from form_responses_functions import get_teams_by_division
from mcp.server.fastmcp import FastMCP


FIFTH_GRADE_SHEET_NAME = "5th Grade"
mcp = FastMCP("Fifth_Grade_data")

# ---------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------

def _parse_int(value: Any) -> Optional[int]:
    """
    Internal helper:
        Safely parse an integer from a cell; return None if not possible.

    Behavior:
        - Accepts any value (string, number, None).
        - Strips commas and whitespace.
        - Returns int on success, None on failure.
    """
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Internal helper:
        Normalize phone numbers to a digits-only string.

    Behavior:
        - Keeps only 0–9 characters.
        - Returns None if input is empty or contains no digits.
    """
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return digits or None


def _load_5th_grade_values(
    range_a1: str = "A1:F100",
) -> List[List[Any]]:
    """
    Internal helper:
        Fetch raw values from the '5th Grade' sheet.

    Args:
        range_a1 (str):
            A1 range to fetch. Defaults to "A1:F100".

    Returns:
        List[List[Any]]:
            Raw 2D list of values (no header/row dict mapping).
    """
    client = get_default_client()
    return client.get_values(FIFTH_GRADE_SHEET_NAME, range_a1)


def _load_5th_grade_boys_block() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Parse the 5th Grade Boys block from the '5th Grade' sheet.

    Actual layout in the sheet / CSV:

        Row 0: label row:
            ['5th Grade Boys', '', '', '', '', '']

        Row 1: header row:
            ['Email', 'First Name', 'Last Name', 'Phone', 'Team Name', 'Team #']

        Rows 2..N: data rows for 5th Grade Boys teams

        Next row: blank row (all empty) → end of boys block.

    Returns:
        (headers, list_of_row_dicts)

        - headers: List[str] of column names.
        - list_of_row_dicts: each row dict maps header -> raw cell value.
    """
    values = _load_5th_grade_values()
    if len(values) < 2:
        return [], []

    # Row 0 = label, Row 1 = actual headers
    headers = values[1]
    data_rows = values[2:]

    records: List[Dict[str, Any]] = []
    for row in data_rows:
        # End at first fully-empty row (spacer before girls block)
        if not any(str(c).strip() for c in row):
            break
        rec = {
            headers[i]: (row[i] if i < len(headers) else None)
            for i in range(len(headers))
        }
        records.append(rec)

    return headers, records


def _load_5th_grade_girls_block() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Parse the 5th Grade Girls block from the '5th Grade' sheet.

    Layout:

        Row K:   ['5th Grade Girls', '', '', '', '', '']
        Row K+1: header row:
                 ['Email', 'First Name', 'Last Name', 'Phone', 'Team Name', 'Team #']
        Row K+2..N: data rows for 5th Grade Girls

        The last few rows may be placeholder slots with just 'Team #' values
        and empty team/contact info (e.g. Team #6-10).

    Returns:
        (headers, list_of_row_dicts)

        - headers: List[str]
        - list_of_row_dicts: row dicts with header -> raw value
    """
    values = _load_5th_grade_values()
    if not values:
        return [], []

    girls_label_idx: Optional[int] = None
    for idx, row in enumerate(values):
        if row and str(row[0]).strip().lower() == "5th grade girls":
            girls_label_idx = idx
            break

    if girls_label_idx is None:
        return [], []

    header_idx = girls_label_idx + 1
    if header_idx >= len(values):
        return [], []

    headers = values[header_idx]
    data_rows = values[header_idx + 1 :]

    records: List[Dict[str, Any]] = []
    for row in data_rows:
        # Include placeholder rows that may have only Team # filled;
        # skip rows that are entirely empty.
        if not any(str(c).strip() for c in row):
            continue

        rec = {
            headers[i]: (row[i] if i < len(headers) else None)
            for i in range(len(headers))
        }
        records.append(rec)

    return headers, records


# ---------------------------------------------------------
# 5th Grade Boys functions
# ---------------------------------------------------------
@mcp.tool()
def list_5th_grade_boys_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 5th Grade Boys teams with contact info and bracket team numbers.

    Args:
        None

    Returns:
        List[dict]:
            Each record:
            {
                "Email": str | None,
                "First Name": str | None,
                "Last Name": str | None,
                "Phone": str | None,      # normalized digits-only
                "Team Name": str | None,
                "Team #": int | None,
            }
    """
    headers, rows = _load_5th_grade_boys_block()
    _ = headers  # kept for symmetry; not used directly here
    if not rows:
        return []

    results: List[Dict[str, Any]] = []
    for row in rows:
        results.append(
            {
                "Email": row.get("Email"),
                "First Name": row.get("First Name"),
                "Last Name": row.get("Last Name"),
                "Phone": _normalize_phone(row.get("Phone")),
                "Team Name": row.get("Team Name"),
                "Team #": _parse_int(row.get("Team #")),
            }
        )

    return results

@mcp.tool()
def get_5th_grade_boys_team_by_number(team_number: int) -> Optional[Dict[str, Any]]:
    """
    Purpose:
        Look up a 5th Grade Boys team by bracket team number.
    """
    boys = list_5th_grade_boys_teams()
    for t in boys:
        if t.get("Team #") == team_number:
            return t
    return None

@mcp.tool()
def find_5th_grade_boys_teams_by_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search 5th Grade Boys teams by team name (exact or substring).
    """
    boys = list_5th_grade_boys_teams()
    q = query.strip().lower()
    results: List[Dict[str, Any]] = []

    for t in boys:
        name = (t.get("Team Name") or "").strip().lower()
        if exact:
            if name == q:
                results.append(t)
        else:
            if q in name:
                results.append(t)

    return results


# ---------------------------------------------------------
# 5th Grade Girls functions
# ---------------------------------------------------------
@mcp.tool()
def list_5th_grade_girls_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 5th Grade Girls teams with contact info and bracket
        team numbers, including placeholder slots that only have a
        team number (no team name yet).
    """
    headers, rows = _load_5th_grade_girls_block()
    _ = headers  # kept for symmetry
    if not rows:
        return []

    results: List[Dict[str, Any]] = []
    for row in rows:
        results.append(
            {
                "Email": row.get("Email"),
                "First Name": row.get("First Name"),
                "Last Name": row.get("Last Name"),
                "Phone": _normalize_phone(row.get("Phone")),
                "Team Name": row.get("Team Name"),
                "Team #": _parse_int(row.get("Team #")),
            }
        )

    return results

@mcp.tool()
def get_5th_grade_girls_team_by_number(team_number: int) -> Optional[Dict[str, Any]]:
    """
    Purpose:
        Look up a 5th Grade Girls team by its bracket team number.
    """
    girls = list_5th_grade_girls_teams()
    for t in girls:
        if t.get("Team #") == team_number:
            return t
    return None

@mcp.tool()
def find_5th_grade_girls_teams_by_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search 5th Grade Girls teams by team name.
    """
    girls = list_5th_grade_girls_teams()
    q = query.strip().lower()
    results: List[Dict[str, Any]] = []

    for t in girls:
        name = (t.get("Team Name") or "").strip().lower()
        if exact:
            if name == q:
                results.append(t)
        else:
            if q in name:
                results.append(t)

    return results


# ---------------------------------------------------------
# Combined 5th Grade helpers
# ---------------------------------------------------------
@mcp.tool()
def list_all_5th_grade_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 5th Grade teams (boys and girls) in a unified structure.
    """
    boys = list_5th_grade_boys_teams()
    girls = list_5th_grade_girls_teams()

    results: List[Dict[str, Any]] = []

    for b in boys:
        results.append(
            {
                "division": "5th Boys",
                "team_name": b.get("Team Name"),
                "team_number": b.get("Team #"),
                "coach_first_name": b.get("First Name"),
                "coach_last_name": b.get("Last Name"),
                "coach_email": b.get("Email"),
                "coach_phone": b.get("Phone"),
            }
        )

    for g in girls:
        results.append(
            {
                "division": "5th Girls",
                "team_name": g.get("Team Name"),
                "team_number": g.get("Team #"),
                "coach_first_name": g.get("First Name"),
                "coach_last_name": g.get("Last Name"),
                "coach_email": g.get("Email"),
                "coach_phone": g.get("Phone"),
            }
        )

    results.sort(key=lambda x: (x["division"], x["team_number"] or 0))
    return results

@mcp.tool()
def find_5th_grade_team_by_name_any_division(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search for a 5th grade team by name across both 5th Boys and
        5th Girls blocks.
    """
    all_teams = list_all_5th_grade_teams()
    q = query.strip().lower()
    results: List[Dict[str, Any]] = []

    for t in all_teams:
        name = (t.get("team_name") or "").strip().lower()
        if exact:
            if name == q:
                results.append(t)
        else:
            if q in name:
                results.append(t)

    return results

@mcp.tool()
def find_5th_grade_empty_team_slots() -> List[Dict[str, Any]]:
    """
    Purpose:
        Identify 5th grade bracket slots with a team number but no team name
        in either 5th Boys or 5th Girls sections.
    """
    results: List[Dict[str, Any]] = []

    # Boys
    boys = list_5th_grade_boys_teams()
    for b in boys:
        num = b.get("Team #")
        name = (b.get("Team Name") or "").strip()
        if num is not None and not name:
            results.append(
                {
                    "division": "5th Boys",
                    "team_number": num,
                    "reason": "missing team name",
                }
            )

    # Girls
    girls = list_5th_grade_girls_teams()
    for g in girls:
        num = g.get("Team #")
        name = (g.get("Team Name") or "").strip()
        if num is not None and not name:
            results.append(
                {
                    "division": "5th Girls",
                    "team_number": num,
                    "reason": "missing team name",
                }
            )

    results.sort(key=lambda x: (x["division"], x["team_number"]))
    return results


# ---------------------------------------------------------
# Cross-sheet helpers (5th Grade + registrations)
# ---------------------------------------------------------
@mcp.tool()
def get_5th_grade_team_registration_details(
    team_name: str,
    division: str,
    include_waitlist: bool = True,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Link a 5th grade bracket team (from '5th Grade' sheet) back to its
        registrations in 'Form Responses 1', for either "5th Boys" or
        "5th Girls" division.
    """
    division = division.strip()
    if division not in ("5th Boys", "5th Girls"):
        raise ValueError("division must be '5th Boys' or '5th Girls'")

    regs = get_teams_by_division(division, include_waitlist=include_waitlist)
    q = team_name.strip().lower()
    results: List[Dict[str, Any]] = []

    for r in regs:
        name = (r.get("team_name") or "").strip().lower()
        if name == q:
            results.append(r)

    return results

@mcp.tool()
def compare_5th_grade_boys_sheet_with_registrations() -> Dict[str, Any]:
    """
    Purpose:
        Compare the 5th Grade Boys bracket sheet with 'Form Responses 1'
        registrations for division "5th Boys" to identify any mismatch.
    """
    boys_sheet = list_5th_grade_boys_teams()
    sheet_names = sorted(
        {
            (t.get("Team Name") or "").strip()
            for t in boys_sheet
            if t.get("Team Name")
        }
    )

    regs = get_teams_by_division("5th Boys", include_waitlist=True)
    reg_names = sorted(
        {
            (r.get("team_name") or "").strip()
            for r in regs
            if r.get("team_name")
        }
    )

    only_in_sheet = sorted(set(sheet_names) - set(reg_names))
    only_in_regs = sorted(set(reg_names) - set(sheet_names))

    return {
        "sheet_team_names": sheet_names,
        "registration_team_names": reg_names,
        "only_in_sheet": only_in_sheet,
        "only_in_registrations": only_in_regs,
    }

@mcp.tool()
def compare_5th_grade_girls_sheet_with_registrations() -> Dict[str, Any]:
    """
    Purpose:
        Compare the 5th Grade Girls bracket sheet with 'Form Responses 1'
        registrations for division "5th Girls" to spot differences.
    """
    girls_sheet = list_5th_grade_girls_teams()
    sheet_names = sorted(
        {
            (t.get("Team Name") or "").strip()
            for t in girls_sheet
            if t.get("Team Name")
        }
    )

    regs = get_teams_by_division("5th Girls", include_waitlist=True)
    reg_names = sorted(
        {
            (r.get("team_name") or "").strip()
            for r in regs
            if r.get("team_name")
        }
    )

    only_in_sheet = sorted(set(sheet_names) - set(reg_names))
    only_in_regs = sorted(set(reg_names) - set(sheet_names))

    return {
        "sheet_team_names": sheet_names,
        "registration_team_names": reg_names,
        "only_in_sheet": only_in_sheet,
        "only_in_registrations": only_in_regs,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")