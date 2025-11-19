# seventh_eighth_grade_functions.py

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sheets_client import get_default_client
from form_responses_functions import get_teams_by_division
from mcp.server.fastmcp import FastMCP

SEVENTH_EIGHTH_GRADE_SHEET_NAME = "7/8 Grade"

mcp = FastMCP("Seven_and_Eight_Grade_data")
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
        - Keeps only numeric characters 0–9.
        - Returns None if input is empty or contains no digits.
    """
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return digits or None


def _load_7_8_grade_values(
    range_a1: str = "A1:F100",
) -> List[List[Any]]:
    """
    Internal helper:
        Fetch raw values from the '7/8 Grade' sheet.

    Args:
        range_a1 (str):
            A1-style range to fetch. Defaults to "A1:F100".

    Returns:
        List[List[Any]]:
            Raw 2D list of values from the sheet.
    """
    client = get_default_client()
    return client.get_values(SEVENTH_EIGHTH_GRADE_SHEET_NAME, range_a1)


def _load_7_8_grade_boys_block() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Parse the 7/8 Grade Boys block.

    Layout (from CSV):

        Row 0: ['7/8 Grade Boys', '', '', '', '', '']   # label
        Row 1: ['Email', 'First Name', 'Last Name', 'Phone', 'Team Name', 'Team #']
        Row 2..10: boys teams
        Row 11: placeholder row: [NaN, NaN, NaN, NaN, NaN, '10']
        Row 12: blank row → end of boys block

    Returns:
        (headers, list_of_row_dicts)

        - headers: List[str] of column names (row 1).
        - list_of_row_dicts: each row dict maps header -> raw cell value.
    """
    values = _load_7_8_grade_values()
    if len(values) < 2:
        return [], []

    # Row 0 is label, Row 1 is header
    headers = values[1]
    data_rows = values[2:]

    records: List[Dict[str, Any]] = []
    for row in data_rows:
        # stop at the first fully empty row (spacer before girls block)
        if not any(str(c).strip() for c in row):
            break

        rec = {
            headers[i]: (row[i] if i < len(row) else None)
            for i in range(len(headers))
        }
        records.append(rec)

    return headers, records


def _load_7_8_grade_girls_block() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Parse the 7/8 Grade Girls block.

    Layout (from CSV):

        Row 13: ['7/8 Grade Girls', '', '', '', '', ''] # label
        Row 14: ['Email', 'First Name', 'Last Name', 'Phone', 'Team Name', 'Team #']
        Row 15..17: girls teams with contact info
        Row 18..24: placeholder slots (mostly only 'Team #' values 4–10)

    Behavior:
        - Includes rows that have at least one non-empty cell (so placeholders
          are kept).
        - Skips fully empty rows.

    Returns:
        (headers, list_of_row_dicts)

        - headers: List[str] of column names (girls header row).
        - list_of_row_dicts: row dicts mapping header -> raw value.
    """
    values = _load_7_8_grade_values()
    if not values:
        return [], []

    girls_label_idx: Optional[int] = None
    for idx, row in enumerate(values):
        if row and str(row[0]).strip().lower() == "7/8 grade girls":
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
        if not any(str(c).strip() for c in row):
            continue

        rec = {
            headers[i]: (row[i] if i < len(headers) else None)
            for i in range(len(headers))
        }
        records.append(rec)

    return headers, records


# ---------------------------------------------------------
# 7/8 Grade Boys functions
# ---------------------------------------------------------
@mcp.tool()
def list_7_8_grade_boys_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 7/8 Grade Boys teams with contact info and bracket team
        numbers, including placeholder slots (e.g. Team #10 with no team name).

    Args:
        None

    Returns:
        List[dict]:
            Each record:
            {
                "Email": str | None,
                "First Name": str | None,
                "Last Name": str | None,
                "Phone": str | None,       # normalized digits-only
                "Team Name": str | None,
                "Team #": int | None,
            }

    Example usage:
        >>> boys = list_7_8_grade_boys_teams()
        >>> for t in boys:
        ...     print(t["Team #"], t["Team Name"], t["First Name"], t["Email"])

    Example questions this function helps answer:
        - "Which teams are in the 7/8 Grade Boys bracket?"
        - "Who coaches 7/8 Boys Team #3?"
        - "Are there any 7/8 Boys open slots with no team assigned?"
    """
    headers, rows = _load_7_8_grade_boys_block()
    _ = headers  # kept for symmetry with other loaders
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
def get_7_8_grade_boys_team_by_number(team_number: int) -> Optional[Dict[str, Any]]:
    """
    Purpose:
        Look up a 7/8 Grade Boys team by its bracket team number.

    Args:
        team_number (int):
            The bracket slot number (e.g. 1, 2, 3...).

    Returns:
        dict | None:
            Matching team record from list_7_8_grade_boys_teams(), or None.

    Example usage:
        >>> team = get_7_8_grade_boys_team_by_number(4)
        >>> if team:
        ...     print(team["Team Name"], team["Email"])

    Example questions this function helps answer:
        - "Who is 7/8 Grade Boys Team #1?"
        - "Which team is seeded #7 in 7/8 Boys?"
    """
    boys = list_7_8_grade_boys_teams()
    for t in boys:
        if t.get("Team #") == team_number:
            return t
    return None

@mcp.tool()
def find_7_8_grade_boys_teams_by_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search 7/8 Grade Boys teams by team name (exact or substring).

    Args:
        query (str):
            Team name or substring to search for (case-insensitive).
        exact (bool):
            If True, require exact match.
            If False, allow substring match.

    Returns:
        List[dict]:
            Matching team records from list_7_8_grade_boys_teams().

    Example usage:
        >>> matches = find_7_8_grade_boys_teams_by_name("Versailles", exact=False)
        >>> for t in matches:
        ...     print(t["Team #"], t["Team Name"])

    Example questions this function helps answer:
        - "Show all 7/8 Boys teams with 'Versailles' in the name."
        - "Is there a 7/8 Boys team called 'Lake Monsters'?"
    """
    boys = list_7_8_grade_boys_teams()
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
# 7/8 Grade Girls functions
# ---------------------------------------------------------
@mcp.tool()
def list_7_8_grade_girls_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 7/8 Grade Girls teams with contact info and bracket team
        numbers, including placeholder slots that only have a team number
        (e.g. Team #4–10 with blank team names).

    Args:
        None

    Returns:
        List[dict]:
            {
                "Email": str | None,
                "First Name": str | None,
                "Last Name": str | None,
                "Phone": str | None,       # normalized digits-only
                "Team Name": str | None,
                "Team #": int | None,
            }

    Example usage:
        >>> girls = list_7_8_grade_girls_teams()
        >>> for t in girls:
        ...     print(t["Team #"], t["Team Name"], t["Email"])

    Example questions this function helps answer:
        - "Which teams are in the 7/8 Grade Girls bracket?"
        - "What 7/8 Girls team numbers are open (no team name yet)?"
        - "Who coaches 7/8 Girls Team #2?"
    """
    headers, rows = _load_7_8_grade_girls_block()
    _ = headers
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
def get_7_8_grade_girls_team_by_number(team_number: int) -> Optional[Dict[str, Any]]:
    """
    Purpose:
        Look up a 7/8 Grade Girls team by its bracket team number.

    Args:
        team_number (int):
            Bracket team number.

    Returns:
        dict | None:
            Matching record from list_7_8_grade_girls_teams(), or None.

    Example usage:
        >>> team = get_7_8_grade_girls_team_by_number(3)
        >>> if team:
        ...     print(team["Team Name"], team["Email"])

    Example questions this function helps answer:
        - "Who is 7/8 Grade Girls Team #1?"
        - "Which team is assigned to 7/8 Girls Team #3?"
    """
    girls = list_7_8_grade_girls_teams()
    for t in girls:
        if t.get("Team #") == team_number:
            return t
    return None

@mcp.tool()
def find_7_8_grade_girls_teams_by_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search 7/8 Grade Girls teams by team name.

    Args:
        query (str):
            Team name or substring to search (case-insensitive).
        exact (bool):
            If True, require exact name match.
            If False, allow substring match.

    Returns:
        List[dict]:
            Matching records from list_7_8_grade_girls_teams().

    Example usage:
        >>> matches = find_7_8_grade_girls_teams_by_name("St. Elizabeth", exact=False)
        >>> for t in matches:
        ...     print(t["Team #"], t["Team Name"])

    Example questions this function helps answer:
        - "Show all 7/8 Girls teams with 'St. Elizabeth' in the name."
        - "Is there a 7/8 Girls team called 'St. Elizabeth Hornets'?"
    """
    girls = list_7_8_grade_girls_teams()
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
# Combined 7/8 Grade helpers
# ---------------------------------------------------------
@mcp.tool()
def list_all_7_8_grade_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 7/8 grade teams (boys and girls) in a unified structure.

    Args:
        None

    Returns:
        List[dict]:
            Each record:
            {
                "division": "7/8 Boys" | "7/8 Girls",
                "team_name": str | None,
                "team_number": int | None,
                "coach_first_name": str | None,
                "coach_last_name": str | None,
                "coach_email": str | None,
                "coach_phone": str | None,
            }

    Example usage:
        >>> all_teams = list_all_7_8_grade_teams()
        >>> for t in all_teams:
        ...     print(t["division"], t["team_number"], t["team_name"])

    Example questions this function helps answer:
        - "Show all 7/8 grade teams (boys + girls) with numbers and coaches."
        - "How many total 7/8 grade teams are currently seeded?"
    """
    boys = list_7_8_grade_boys_teams()
    girls = list_7_8_grade_girls_teams()

    results: List[Dict[str, Any]] = []

    for b in boys:
        results.append(
            {
                "division": "7/8 Boys",
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
                "division": "7/8 Girls",
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
def find_7_8_grade_team_by_name_any_division(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search for a 7/8 grade team by name across both 7/8 Boys and 7/8 Girls.

    Args:
        query (str):
            Team name or substring (case-insensitive).
        exact (bool):
            If True, require exact name match.
            If False, allow substring match.

    Returns:
        List[dict]:
            Records in the same structure as list_all_7_8_grade_teams().

    Example usage:
        >>> matches = find_7_8_grade_team_by_name_any_division("Versailles", exact=False)
        >>> for t in matches:
        ...     print(t["division"], t["team_number"], t["team_name"])

    Example questions this function helps answer:
        - "Is there any 7/8 grade team named 'Versailles 7th grade' (boys or girls)?"
        - "Show all 7/8 grade teams with 'Aces' in the name."
    """
    all_teams = list_all_7_8_grade_teams()
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
def find_7_8_grade_empty_team_slots() -> List[Dict[str, Any]]:
    """
    Purpose:
        Identify 7/8 grade bracket slots that have a team number but no team
        name in either 7/8 Boys or 7/8 Girls.

        In this sheet:
        - Boys: there is a placeholder entry for Team #10 with no team name.
        - Girls: there are placeholder entries for Team #4–10 with no team name.

    Args:
        None

    Returns:
        List[dict]:
            {
                "division": "7/8 Boys" | "7/8 Girls",
                "team_number": int,
                "reason": str,   # e.g. "missing team name"
            }

    Example usage:
        >>> gaps = find_7_8_grade_empty_team_slots()
        >>> for g in gaps:
        ...     print(g["division"], g["team_number"], g["reason"])

    Example questions this function helps answer:
        - "Do we have unassigned bracket slots for 7/8 grade?"
        - "Which 7/8 Girls team numbers are placeholders only?"
    """
    results: List[Dict[str, Any]] = []

    # Boys
    boys = list_7_8_grade_boys_teams()
    for b in boys:
        num = b.get("Team #")
        name = (b.get("Team Name") or "").strip()
        if num is not None and not name:
            results.append(
                {
                    "division": "7/8 Boys",
                    "team_number": num,
                    "reason": "missing team name",
                }
            )

    # Girls
    girls = list_7_8_grade_girls_teams()
    for g in girls:
        num = g.get("Team #")
        name = (g.get("Team Name") or "").strip()
        if num is not None and not name:
            results.append(
                {
                    "division": "7/8 Girls",
                    "team_number": num,
                    "reason": "missing team name",
                }
            )

    results.sort(key=lambda x: (x["division"], x["team_number"]))
    return results


# ---------------------------------------------------------
# Cross-sheet helpers (7/8 Grade + registrations)
# ---------------------------------------------------------
@mcp.tool()
def get_7_8_grade_team_registration_details(
    team_name: str,
    division: str,
    include_waitlist: bool = True,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Link a 7/8 grade bracket team (from '7/8 Grade' sheet) back to its
        registration record(s) in 'Form Responses 1', for either "7/8 Boys"
        or "7/8 Girls" division.

    Args:
        team_name (str):
            Team name to look up (case-insensitive exact match).
        division (str):
            "7/8 Boys" or "7/8 Girls".
        include_waitlist (bool):
            If True, include waitlisted registrations.
            If False, only confirmed teams.

    Returns:
        List[dict]:
            Registration records from get_teams_by_division() matching team_name.

    Example usage:
        >>> regs = get_7_8_grade_team_registration_details(
        ...     "Lake Monsters", "7/8 Boys"
        ... )
        >>> for r in regs:
        ...     print(r["team_name"], r["contact_email"], r["is_waitlist"])

    Example questions this function helps answer:
        - "What registration info do we have for 'Lake Monsters' in 7/8 Boys?"
        - "Who is the contact for 7/8 Girls 'Versailles 7/8'?"
    """
    division = division.strip()
    if division not in ("7/8 Boys", "7/8 Girls"):
        raise ValueError("division must be '7/8 Boys' or '7/8 Girls'")

    regs = get_teams_by_division(division, include_waitlist=include_waitlist)
    q = team_name.strip().lower()
    results: List[Dict[str, Any]] = []

    for r in regs:
        name = (r.get("team_name") or "").strip().lower()
        if name == q:
            results.append(r)

    return results

@mcp.tool()
def compare_7_8_grade_boys_sheet_with_registrations() -> Dict[str, Any]:
    """
    Purpose:
        Compare the 7/8 Grade Boys bracket sheet with 'Form Responses 1'
        registrations for division "7/8 Boys" to find mismatches:

        - Teams in the bracket but not in registrations.
        - Teams in registrations but not on the bracket.

    Args:
        None

    Returns:
        dict:
            {
                "sheet_team_names": List[str],
                "registration_team_names": List[str],
                "only_in_sheet": List[str],
                "only_in_registrations": List[str],
            }

    Example usage:
        >>> diff = compare_7_8_grade_boys_sheet_with_registrations()
        >>> print("Only in sheet:", diff["only_in_sheet"])
        >>> print("Only in registrations:", diff["only_in_registrations"])

    Example questions this function helps answer:
        - "Does the 7/8 Boys bracket reflect all registered 7/8 Boys teams?"
        - "Are any registered 7/8 Boys teams missing from the bracket sheet?"
    """
    boys_sheet = list_7_8_grade_boys_teams()
    sheet_names = sorted(
        {
            (t.get("Team Name") or "").strip()
            for t in boys_sheet
            if t.get("Team Name")
        }
    )

    regs = get_teams_by_division("7/8 Boys", include_waitlist=True)
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
def compare_7_8_grade_girls_sheet_with_registrations() -> Dict[str, Any]:
    """
    Purpose:
        Compare the 7/8 Grade Girls bracket sheet with 'Form Responses 1'
        registrations for division "7/8 Girls" to spot differences.

    Args:
        None

    Returns:
        dict:
            {
                "sheet_team_names": List[str],
                "registration_team_names": List[str],
                "only_in_sheet": List[str],
                "only_in_registrations": List[str],
            }

    Example usage:
        >>> diff = compare_7_8_grade_girls_sheet_with_registrations()
        >>> print("Only in sheet:", diff["only_in_sheet"])
        >>> print("Only in registrations:", diff["only_in_registrations"])

    Example questions this function helps answer:
        - "Does the 7/8 Girls bracket include all registered 7/8 Girls teams?"
        - "Are there 7/8 Girls teams on the bracket that don't exist in registrations?"
    """
    girls_sheet = list_7_8_grade_girls_teams()
    sheet_names = sorted(
        {
            (t.get("Team Name") or "").strip()
            for t in girls_sheet
            if t.get("Team Name")
        }
    )

    regs = get_teams_by_division("7/8 Girls", include_waitlist=True)
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