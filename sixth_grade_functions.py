# sixth_grade_functions.py

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sheets_client import get_default_client
from form_responses_functions import get_teams_by_division
from mcp.server.fastmcp import FastMCP

SIXTH_GRADE_SHEET_NAME = "6th Grade"

mcp = FastMCP("Sixth_Grade_data")


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

    This makes it easier to compare or display phones consistently.
    """
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return digits or None


def _load_6th_grade_values(
    range_a1: str = "A1:F100",
) -> List[List[Any]]:
    """
    Internal helper:
        Fetch raw values from the '6th Grade' sheet.

    Args:
        range_a1 (str):
            A1-style range to fetch. Defaults to "A1:F100".

    Returns:
        List[List[Any]]:
            Raw 2D list of values from the sheet.
    """
    client = get_default_client()
    return client.get_values(SIXTH_GRADE_SHEET_NAME, range_a1)


def _load_6th_grade_boys_block() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Parse the 6th Grade Boys block.

        Layout:

            Row 0: ['6th Grade Boys', '', '', '', '', '']   # label
            Row 1: ['Email', 'First Name', 'Last Name', 'Phone', 'Team Name', 'Team #']
            Row 2..N: boys data rows
            Row N+1: blank row → end of boys block

    Returns:
        (headers, list_of_row_dicts)

        - headers: List[str] of column names.
        - list_of_row_dicts: each row dict maps header -> raw cell value.
    """
    values = _load_6th_grade_values()
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


def _load_6th_grade_girls_block() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Parse the 6th Grade Girls block.

        Layout:

            Row K:  ['6th Grade Girls', '', '', '', '', '']   # label
            Row K+1: ['Email', 'First Name', 'Last Name', 'Phone', 'Team Name', 'Team #']
            Row K+2..N: girls teams and placeholder rows
                        (some rows may only have Team # filled, e.g. 6..10)

        Behavior:
            - Includes rows that have at least one non-empty cell, so that
              placeholder slots (only Team # filled) are included.
            - Skips fully empty rows.

        Returns:
            (headers, list_of_row_dicts)
    """
    values = _load_6th_grade_values()
    if not values:
        return [], []

    girls_label_idx: Optional[int] = None
    for idx, row in enumerate(values):
        if row and str(row[0]).strip().lower() == "6th grade girls":
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
        # keep rows that have at least one non-empty cell
        if not any(str(c).strip() for c in row):
            continue
        rec = {
            headers[i]: (row[i] if i < len(row) else None)
            for i in range(len(headers))
        }
        records.append(rec)

    return headers, records


# ---------------------------------------------------------
# 6th Grade Boys functions
# ---------------------------------------------------------
@mcp.tool()
def list_6th_grade_boys_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 6th Grade Boys teams, with coach/contact info and bracket
        team numbers.

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
        >>> boys = list_6th_grade_boys_teams()
        >>> for t in boys:
        ...     print(t["Team #"], t["Team Name"], t["First Name"], t["Email"])

    Example questions this function helps answer:
        - "Which teams are in the 6th Grade Boys bracket?"
        - "Who coaches 6th Boys Team #3?"
        - "What are the contact emails for all 6th Boys teams?"
    """
    headers, rows = _load_6th_grade_boys_block()
    _ = headers  # kept for symmetry and potential future use
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
def get_6th_grade_boys_team_by_number(team_number: int) -> Optional[Dict[str, Any]]:
    """
    Purpose:
        Look up a 6th Grade Boys team by its bracket team number.

    Args:
        team_number (int):
            The bracket slot number (e.g. 1, 2, 3...).

    Returns:
        dict | None:
            Matching team record from list_6th_grade_boys_teams(), or None.

    Example usage:
        >>> team = get_6th_grade_boys_team_by_number(4)
        >>> if team:
        ...     print(team["Team Name"], team["Email"])

    Example questions this function helps answer:
        - "Who is 6th Grade Boys Team #1?"
        - "Which team is seeded #7 in 6th Boys?"
    """
    boys = list_6th_grade_boys_teams()
    for t in boys:
        if t.get("Team #") == team_number:
            return t
    return None

@mcp.tool()
def find_6th_grade_boys_teams_by_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search 6th Grade Boys teams by team name (exact or substring).

    Args:
        query (str):
            Team name or substring to search for (case-insensitive).
        exact (bool):
            If True, require exact match.
            If False, allow substring match.

    Returns:
        List[dict]:
            Matching team records from list_6th_grade_boys_teams().

    Example usage:
        >>> matches = find_6th_grade_boys_teams_by_name("Osage", exact=False)
        >>> for t in matches:
        ...     print(t["Team #"], t["Team Name"])

    Example questions this function helps answer:
        - "Show all 6th Boys teams with 'Osage' in the name."
        - "Is there a 6th Boys team called 'Boone Boyz'?"
    """
    boys = list_6th_grade_boys_teams()
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
# 6th Grade Girls functions
# ---------------------------------------------------------
@mcp.tool()
def list_6th_grade_girls_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 6th Grade Girls teams with contact info and bracket team
        numbers, including placeholder slots that only have a team number.

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
        >>> girls = list_6th_grade_girls_teams()
        >>> for t in girls:
        ...     print(t["Team #"], t["Team Name"], t["Email"])

    Example questions this function helps answer:
        - "Which teams are in the 6th Grade Girls bracket?"
        - "What 6th Girls team numbers are open (no team name yet)?"
        - "Who coaches 6th Girls Team #2?"
    """
    headers, rows = _load_6th_grade_girls_block()
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
def get_6th_grade_girls_team_by_number(team_number: int) -> Optional[Dict[str, Any]]:
    """
    Purpose:
        Look up a 6th Grade Girls team by bracket team number.

    Args:
        team_number (int):
            The bracket slot number.

    Returns:
        dict | None:
            Matching record from list_6th_grade_girls_teams(), or None.

    Example usage:
        >>> team = get_6th_grade_girls_team_by_number(3)
        >>> if team:
        ...     print(team["Team Name"], team["Email"])

    Example questions this function helps answer:
        - "Who is 6th Grade Girls Team #1?"
        - "Which team is assigned to 6th Girls Team #4?"
    """
    girls = list_6th_grade_girls_teams()
    for t in girls:
        if t.get("Team #") == team_number:
            return t
    return None

@mcp.tool()
def find_6th_grade_girls_teams_by_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search 6th Grade Girls teams by team name.

    Args:
        query (str):
            Team name or substring to search (case-insensitive).
        exact (bool):
            If True, require exact name match.
            If False, allow substring match.

    Returns:
        List[dict]:
            Matching records from list_6th_grade_girls_teams().

    Example usage:
        >>> matches = find_6th_grade_girls_teams_by_name("Lady", exact=False)
        >>> for t in matches:
        ...     print(t["Team #"], t["Team Name"])

    Example questions this function helps answer:
        - "Show all 6th Girls teams with 'Lady' in the name."
        - "Is there a 6th Girls team called 'Lady Mustangs'?"
    """
    girls = list_6th_grade_girls_teams()
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
# Combined 6th Grade helpers
# ---------------------------------------------------------
@mcp.tool()
def list_all_6th_grade_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 6th Grade teams (boys and girls) in a unified structure.

    Args:
        None

    Returns:
        List[dict]:
            Each record:
            {
                "division": "6th Boys" | "6th Girls",
                "team_name": str | None,
                "team_number": int | None,
                "coach_first_name": str | None,
                "coach_last_name": str | None,
                "coach_email": str | None,
                "coach_phone": str | None,
            }

    Example usage:
        >>> all_teams = list_all_6th_grade_teams()
        >>> for t in all_teams:
        ...     print(t["division"], t["team_number"], t["team_name"])

    Example questions this function helps answer:
        - "Show all 6th grade teams (boys + girls) and their seed numbers."
        - "How many 6th grade teams are currently seeded?"
    """
    boys = list_6th_grade_boys_teams()
    girls = list_6th_grade_girls_teams()

    results: List[Dict[str, Any]] = []

    for b in boys:
        results.append(
            {
                "division": "6th Boys",
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
                "division": "6th Girls",
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
def find_6th_grade_team_by_name_any_division(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search for a 6th grade team by name across both 6th Boys and 6th Girls.

    Args:
        query (str):
            Team name or substring (case-insensitive).
        exact (bool):
            If True, require exact name match.
            If False, allow substring match.

    Returns:
        List[dict]:
            Records in the same structure as list_all_6th_grade_teams().

    Example usage:
        >>> matches = find_6th_grade_team_by_name_any_division("Pintos", exact=False)
        >>> for t in matches:
        ...     print(t["division"], t["team_number"], t["team_name"])

    Example questions this function helps answer:
        - "Is there any 6th grade team named 'Pintos' (boys or girls)?"
        - "Show all 6th grade teams with 'Osage' in the name."
    """
    all_teams = list_all_6th_grade_teams()
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
def find_6th_grade_empty_team_slots() -> List[Dict[str, Any]]:
    """
    Purpose:
        Identify 6th grade bracket slots that have a team number but no
        team name in either 6th Boys or 6th Girls.

        For example, in the 6th Girls block, Team #6–10 rows may only have
        a team number set with all other fields blank.

    Args:
        None

    Returns:
        List[dict]:
            {
                "division": "6th Boys" | "6th Girls",
                "team_number": int,
                "reason": str,   # e.g. "missing team name"
            }

    Example usage:
        >>> gaps = find_6th_grade_empty_team_slots()
        >>> for g in gaps:
        ...     print(g["division"], g["team_number"], g["reason"])

    Example questions this function helps answer:
        - "Do we have unassigned bracket slots for 6th grade?"
        - "Which 6th Girls team numbers are placeholders only?"
    """
    results: List[Dict[str, Any]] = []

    # Boys
    boys = list_6th_grade_boys_teams()
    for b in boys:
        num = b.get("Team #")
        name = (b.get("Team Name") or "").strip()
        if num is not None and not name:
            results.append(
                {
                    "division": "6th Boys",
                    "team_number": num,
                    "reason": "missing team name",
                }
            )

    # Girls
    girls = list_6th_grade_girls_teams()
    for g in girls:
        num = g.get("Team #")
        name = (g.get("Team Name") or "").strip()
        if num is not None and not name:
            results.append(
                {
                    "division": "6th Girls",
                    "team_number": num,
                    "reason": "missing team name",
                }
            )

    results.sort(key=lambda x: (x["division"], x["team_number"]))
    return results


# ---------------------------------------------------------
# Cross-sheet helpers (6th Grade + registrations)
# ---------------------------------------------------------
@mcp.tool()
def get_6th_grade_team_registration_details(
    team_name: str,
    division: str,
    include_waitlist: bool = True,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Link a 6th grade bracket team (from '6th Grade' sheet) back to its
        registration record(s) in 'Form Responses 1', for either "6th Boys"
        or "6th Girls" division.

    Args:
        team_name (str):
            Team name to look up (case-insensitive exact match).
        division (str):
            "6th Boys" or "6th Girls".
        include_waitlist (bool):
            If True, include waitlisted registrations.
            If False, only confirmed teams.

    Returns:
        List[dict]:
            Registration records from get_teams_by_division() matching team_name.

    Example usage:
        >>> regs = get_6th_grade_team_registration_details(
        ...     "Camdenton Lakers", "6th Boys"
        ... )
        >>> for r in regs:
        ...     print(r["team_name"], r["contact_email"], r["is_waitlist"])

    Example questions this function helps answer:
        - "What registration info do we have for 'Camdenton Lakers' in 6th Boys?"
        - "Who is the contact for 6th Girls 'Lady Mustangs'?"
    """
    division = division.strip()
    if division not in ("6th Boys", "6th Girls"):
        raise ValueError("division must be '6th Boys' or '6th Girls'")

    regs = get_teams_by_division(division, include_waitlist=include_waitlist)
    q = team_name.strip().lower()
    results: List[Dict[str, Any]] = []

    for r in regs:
        name = (r.get("team_name") or "").strip().lower()
        if name == q:
            results.append(r)

    return results

@mcp.tool()
def compare_6th_grade_boys_sheet_with_registrations() -> Dict[str, Any]:
    """
    Purpose:
        Compare the 6th Grade Boys bracket sheet with 'Form Responses 1'
        registrations for division "6th Boys" to find mismatches:

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
        >>> diff = compare_6th_grade_boys_sheet_with_registrations()
        >>> print("Only in sheet:", diff["only_in_sheet"])
        >>> print("Only in registrations:", diff["only_in_registrations"])

    Example questions this function helps answer:
        - "Does the 6th Boys bracket reflect all registered 6th Boys teams?"
        - "Are any registered 6th Boys teams missing from the bracket sheet?"
    """
    boys_sheet = list_6th_grade_boys_teams()
    sheet_names = sorted(
        {
            (t.get("Team Name") or "").strip()
            for t in boys_sheet
            if t.get("Team Name")
        }
    )

    regs = get_teams_by_division("6th Boys", include_waitlist=True)
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
def compare_6th_grade_girls_sheet_with_registrations() -> Dict[str, Any]:
    """
    Purpose:
        Compare the 6th Grade Girls bracket sheet with 'Form Responses 1'
        registrations for division "6th Girls" to spot differences.

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
        >>> diff = compare_6th_grade_girls_sheet_with_registrations()
        >>> print("Only in sheet:", diff["only_in_sheet"])
        >>> print("Only in registrations:", diff["only_in_registrations"])

    Example questions this function helps answer:
        - "Does the 6th Girls bracket include all registered 6th Girls teams?"
        - "Are there 6th Girls teams on the bracket that don't exist in registrations?"
    """
    girls_sheet = list_6th_grade_girls_teams()
    sheet_names = sorted(
        {
            (t.get("Team Name") or "").strip()
            for t in girls_sheet
            if t.get("Team Name")
        }
    )

    regs = get_teams_by_division("6th Girls", include_waitlist=True)
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