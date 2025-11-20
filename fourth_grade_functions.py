# fourth_grade_functions.py

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sheets_client import get_default_client
from form_responses_functions import get_teams_by_division

from mcp.server.fastmcp import FastMCP

FOURTH_GRADE_SHEET_NAME = "4th Grade"

mcp = FastMCP("Fourth_Grade_data")

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
        Normalize phone numbers to digits-only string.

    Behavior:
        - Keeps only 0–9 characters.
        - Returns None if input is empty or contains no digits.
    """
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return digits or None


def _load_4th_grade_values(
    range_a1: str = "A1:G100",
) -> List[List[Any]]:
    """
    Internal helper:
        Fetch raw values from the '4th Grade' sheet.

    Args:
        range_a1 (str):
            A1-style range to fetch. Defaults to "A1:G100".

    Returns:
        List[List[Any]]:
            Raw 2D list of values.
    """
    client = get_default_client()
    return client.get_values(FOURTH_GRADE_SHEET_NAME, range_a1)


def _load_4th_grade_boys_block() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Parse the '4th Grade Boys' block from the '4th Grade' sheet.

    Layout:

        Row 0: label row: ['4th Grade Boys', '', ...]
        Row 1: header row
        Rows 2–N: data rows until a completely blank row.

    Returns:
        (headers, list_of_row_dicts)

        - headers: List[str] of column names (row 1).
        - list_of_row_dicts: each row dict maps header -> raw cell value.
    """
    values = _load_4th_grade_values()
    if len(values) < 2:
        return [], []

    # Row 0 is label, row 1 is header
    headers = values[1]
    data_rows = values[2:]

    records: List[Dict[str, Any]] = []
    for row in data_rows:
        # stop when hit a fully empty row
        if not any(str(c).strip() for c in row):
            break
        rec = {
            headers[i]: (row[i] if i < len(headers) else None)
            for i in range(len(headers))
        }
        records.append(rec)

    return headers, records


def _load_4th_grade_girls_block() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Parse the '4th Grade Girls' block from the '4th Grade' sheet.

    Layout (based on current sheet structure):

        Row 14: label row: ['4th Grade Girls', '', ...]
        Row 15: header row
        Rows 16–N: data rows until a blank row.

    Returns:
        (headers, list_of_row_dicts)

        - headers: List[str] of column names (row 15).
        - list_of_row_dicts: row dicts mapping header -> raw value.
    """
    values = _load_4th_grade_values()
    if len(values) < 16:
        return [], []

    headers = values[15]
    data_rows = values[16:]

    records: List[Dict[str, Any]] = []
    for row in data_rows:
        if not any(str(c).strip() for c in row):
            break
        rec = {
            headers[i]: (row[i] if i < len(headers) else None)
            for i in range(len(headers))
        }
        records.append(rec)

    return headers, records


# ---------------------------------------------------------
# 4th Grade Boys functions
# ---------------------------------------------------------
@mcp.tool()
def list_4th_grade_boys_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 4th Grade Boys teams with coach/contact info, team name,
        team number, and any bracket notes (e.g. 'Move to 5th grade division').

    Args:
        None

    Returns:
        List[dict]:
            Each record:
            {
                "Email": str | None,
                "First Name": str | None,
                "Last Name": str | None,
                "Phone": str | None,         # normalized digits-only
                "Team Name": str | None,
                "Team #": int | None,
                "is_waitlist": bool,
                "Notes": str | None,
            }

            Where:
            - 'Team #' is an integer when numeric, otherwise None.
            - 'is_waitlist' is True when the Team # cell contains 'Wait List'.

    Example usage:
        >>> boys = list_4th_grade_boys_teams()
        >>> for t in boys:
        ...     print(t["Team #"], t["Team Name"], t["First Name"], t["Notes"])

    Example questions this function helps answer:
        - "Which teams are in the 4th Grade Boys bracket?"
        - "Which 4th Boys team is marked as Wait List?"
        - "Which team is flagged 'Move to 5th grade division'?"
    """
    headers, rows = _load_4th_grade_boys_block()
    if not rows:
        return []

    results: List[Dict[str, Any]] = []
    for row in rows:
        raw_team_num = row.get("Team #")
        team_num_int = _parse_int(raw_team_num)
        is_waitlist = False
        if isinstance(raw_team_num, str) and "wait" in raw_team_num.lower():
            is_waitlist = True

        # Assume last header column contains notes (e.g. "Move to 5th grade division")
        notes = row.get(headers[-1]) if len(headers) > 6 else None

        results.append(
            {
                "Email": row.get("Email"),
                "First Name": row.get("First Name"),
                "Last Name": row.get("Last Name"),
                "Phone": _normalize_phone(row.get("Phone")),
                "Team Name": row.get("Team Name"),
                "Team #": team_num_int,
                "is_waitlist": is_waitlist,
                "Notes": notes,
            }
        )

    return results

@mcp.tool()
def get_4th_grade_boys_team_by_number(team_number: int) -> Optional[Dict[str, Any]]:
    """
    Purpose:
        Look up a 4th Grade Boys team by its bracket team number.

    Args:
        team_number (int):
            Bracket slot number, e.g. 1, 2, 3...

    Returns:
        dict | None:
            Matching team record from list_4th_grade_boys_teams(), or None.

    Example usage:
        >>> t = get_4th_grade_boys_team_by_number(2)
        >>> if t:
        ...     print(t["Team Name"], t["First Name"], t["Email"])

    Example questions this function helps answer:
        - "Who is 4th Grade Boys Team #4?"
        - "Which team is seeded #7 in 4th Boys?"
    """
    boys = list_4th_grade_boys_teams()
    for team in boys:
        if team.get("Team #") == team_number:
            return team
    return None

@mcp.tool()
def find_4th_grade_boys_teams_by_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search 4th Grade Boys bracket teams by team name.

    Args:
        query (str):
            Team name or substring to search for (case-insensitive).
        exact (bool):
            If True, require exact match.
            If False, allow substring match.

    Returns:
        List[dict]:
            Matching team records.

    Example usage:
        >>> matches = find_4th_grade_boys_teams_by_name("Lakers", exact=False)
        >>> for t in matches:
        ...     print(t["Team #"], t["Team Name"])

    Example questions this function helps answer:
        - "Find all 4th Boys teams with 'Osage' in the name."
        - "Is there a 4th Boys team named 'TNT'?"
    """
    boys = list_4th_grade_boys_teams()
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

@mcp.tool()
def list_4th_grade_boys_bracket_waitlist_entries() -> List[Dict[str, Any]]:
    """
    Purpose:
        Return any 4th Grade Boys bracket entries that are marked as
        'Wait List' in the 'Team #' column.

    Args:
        None

    Returns:
        List[dict]:
            Same structure as list_4th_grade_boys_teams(), but filtered to
            is_waitlist == True.

    Example usage:
        >>> wl = list_4th_grade_boys_bracket_waitlist_entries()
        >>> for t in wl:
        ...     print(t["Team Name"], t["Email"])

    Example questions this function helps answer:
        - "Which 4th Boys team is currently in a waitlist bracket slot?"
        - "Show all 4th Grade Boys 'Wait List' entries in the bracket."
    """
    boys = list_4th_grade_boys_teams()
    return [t for t in boys if t.get("is_waitlist")]


# ---------------------------------------------------------
# 4th Grade Girls functions
# ---------------------------------------------------------
@mcp.tool()
def list_4th_grade_girls_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 4th Grade Girls teams and their bracket team numbers.

        Note: this block only stores team names and numbers; coach/contact
        info comes from the registration sheet.

    Args:
        None

    Returns:
        List[dict]:
            {
                "Team Name": str | None,
                "Team #": int | None,
            }

    Example usage:
        >>> girls = list_4th_grade_girls_teams()
        >>> for t in girls:
        ...     print(t["Team #"], t["Team Name"])

    Example questions this function helps answer:
        - "Which teams are in the 4th Grade Girls bracket?"
        - "What is the name of 4th Girls Team #5?"
    """
    headers, rows = _load_4th_grade_girls_block()
    _ = headers  # kept for symmetry
    if not rows:
        return []

    results: List[Dict[str, Any]] = []
    for row in rows:
        results.append(
            {
                "Team Name": row.get("Team Name"),
                "Team #": _parse_int(row.get("Team #")),
            }
        )

    return results

@mcp.tool()
def get_4th_grade_girls_team_by_number(team_number: int) -> Optional[Dict[str, Any]]:
    """
    Purpose:
        Look up a 4th Grade Girls team by its bracket team number.

    Args:
        team_number (int):
            Bracket team number.

    Returns:
        dict | None:
            Matching team record from list_4th_grade_girls_teams(), or None.

    Example usage:
        >>> t = get_4th_grade_girls_team_by_number(3)
        >>> print(t)

    Example questions this function helps answer:
        - "Who is 4th Grade Girls Team #2?"
        - "Which team is seeded #7 in 4th Girls?"
    """
    girls = list_4th_grade_girls_teams()
    for t in girls:
        if t.get("Team #") == team_number:
            return t
    return None

@mcp.tool()
def find_4th_grade_girls_teams_by_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search 4th Grade Girls teams by team name.

    Args:
        query (str):
            Team name or substring to search.
        exact (bool):
            If True, require exact match.
            If False, allow partial match.

    Returns:
        List[dict]:
            Matching records from list_4th_grade_girls_teams().

    Example usage:
        >>> matches = find_4th_grade_girls_teams_by_name("Lady", exact=False)
        >>> for t in matches:
        ...     print(t["Team #"], t["Team Name"])

    Example questions this function helps answer:
        - "Show all 4th Girls teams with 'Lady' in the name."
        - "Is there a 4th Girls team called 'Iberia Lady Rangers'?"
    """
    girls = list_4th_grade_girls_teams()
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
# Combined 4th Grade helpers
# ---------------------------------------------------------
@mcp.tool()
def list_all_4th_grade_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 4th Grade teams (boys and girls) in a unified structure
        with division labels.

    Args:
        None

    Returns:
        List[dict]:
            {
                "division": "4th Boys" | "4th Girls",
                "team_name": str | None,
                "team_number": int | None,
                "coach_first_name": str | None,
                "coach_last_name": str | None,
                "coach_email": str | None,
                "coach_phone": str | None,
                "is_waitlist": bool,   # True only for 4th Boys waitlist rows
                "notes": str | None,   # notes from boys block (if any)
            }

    Example usage:
        >>> all_teams = list_all_4th_grade_teams()
        >>> for t in all_teams:
        ...     print(t["division"], t["team_number"], t["team_name"])

    Example questions this function helps answer:
        - "Show all 4th grade teams (boys + girls) with their numbers."
        - "Which 4th grade teams have waitlist flag or special notes?"
    """
    boys = list_4th_grade_boys_teams()
    girls = list_4th_grade_girls_teams()

    results: List[Dict[str, Any]] = []

    for b in boys:
        results.append(
            {
                "division": "4th Boys",
                "team_name": b.get("Team Name"),
                "team_number": b.get("Team #"),
                "coach_first_name": b.get("First Name"),
                "coach_last_name": b.get("Last Name"),
                "coach_email": b.get("Email"),
                "coach_phone": b.get("Phone"),
                "is_waitlist": b.get("is_waitlist"),
                "notes": b.get("Notes"),
            }
        )

    for g in girls:
        results.append(
            {
                "division": "4th Girls",
                "team_name": g.get("Team Name"),
                "team_number": g.get("Team #"),
                "coach_first_name": None,
                "coach_last_name": None,
                "coach_email": None,
                "coach_phone": None,
                "is_waitlist": False,
                "notes": None,
            }
        )

    results.sort(key=lambda x: (x["division"], x["team_number"] or 0))
    return results

@mcp.tool()
def find_4th_grade_team_by_name_any_division(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Search across both 4th Boys and 4th Girls for a team name.

    Args:
        query (str):
            Team name or substring.
        exact (bool):
            If True, require exact match.
            If False, allow substring match.

    Returns:
        List[dict]:
            Records from list_all_4th_grade_teams() matching the query.

    Example usage:
        >>> matches = find_4th_grade_team_by_name_any_division("Osage", exact=False)
        >>> for t in matches:
        ...     print(t["division"], t["team_number"], t["team_name"])

    Example questions this function helps answer:
        - "Find all 4th grade teams (boys or girls) with 'Osage' in the name."
        - "Does any 4th grade team use the name 'Ballistic'?"
    """
    all_teams = list_all_4th_grade_teams()
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
def find_4th_grade_empty_team_slots() -> List[Dict[str, Any]]:
    """
    Purpose:
        Identify bracket slots that have a team number but no team name
        assigned, in either 4th Boys or 4th Girls blocks.

        Example: the girls block has a row with only '10' in 'Team #' and
        no team name → open slot.

    Args:
        None

    Returns:
        List[dict]:
            {
                "division": "4th Boys" | "4th Girls",
                "team_number": int,
                "reason": str,   # e.g. "missing team name"
            }

    Example usage:
        >>> gaps = find_4th_grade_empty_team_slots()
        >>> for g in gaps:
        ...     print(g["division"], g["team_number"], g["reason"])

    Example questions this function helps answer:
        - "Which 4th grade bracket numbers are placeholders only?"
        - "Do we have open slots like '4th Girls Team #10'?"
    """
    results: List[Dict[str, Any]] = []

    # Boys
    boys = list_4th_grade_boys_teams()
    for b in boys:
        num = b.get("Team #")
        name = (b.get("Team Name") or "").strip()
        if num is not None and not name:
            results.append(
                {
                    "division": "4th Boys",
                    "team_number": num,
                    "reason": "missing team name",
                }
            )

    # Girls
    girls = list_4th_grade_girls_teams()
    for g in girls:
        num = g.get("Team #")
        name = (g.get("Team Name") or "").strip()
        if num is not None and not name:
            results.append(
                {
                    "division": "4th Girls",
                    "team_number": num,
                    "reason": "missing team name",
                }
            )

    results.sort(key=lambda x: (x["division"], x["team_number"]))
    return results


# ---------------------------------------------------------
# Cross-sheet helpers (4th Grade + registrations)
# ---------------------------------------------------------
@mcp.tool()
def get_4th_grade_team_registration_details(
    team_name: str,
    division: str,
    include_waitlist: bool = True,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Link a 4th grade bracket team (from '4th Grade' sheet) back to
        its registration record(s) in 'Form Responses 1', for either
        4th Boys or 4th Girls.

    Args:
        team_name (str):
            Team name to look up (case-insensitive exact match).
        division (str):
            "4th Boys" or "4th Girls".
        include_waitlist (bool):
            If True, include waitlisted registrations.
            If False, only confirmed teams.

    Returns:
        List[dict]:
            Registration records from get_teams_by_division() matching the team name.

    Example usage:
        >>> regs = get_4th_grade_team_registration_details(
        ...     "Sedalia Magic", "4th Boys"
        ... )
        >>> for r in regs:
        ...     print(r["team_name"], r["contact_email"], r["is_waitlist"])

    Example questions this function helps answer:
        - "What registration info do we have for 'Sedalia Magic' in 4th Boys?"
        - "Who is the contact for 4th Girls 'Iberia Lady Rangers'?"
    """
    division = division.strip()
    if division not in ("4th Boys", "4th Girls"):
        raise ValueError("division must be '4th Boys' or '4th Girls'")

    regs = get_teams_by_division(division, include_waitlist=include_waitlist)
    q = team_name.strip().lower()
    results: List[Dict[str, Any]] = []

    for r in regs:
        name = (r.get("team_name") or "").strip().lower()
        if name == q:
            results.append(r)

    return results

@mcp.tool()
def compare_4th_grade_boys_sheet_with_registrations() -> Dict[str, Any]:
    """
    Purpose:
        Compare the 4th Grade Boys bracket sheet with the 'Form Responses 1'
        registrations for division "4th Boys", to find mismatches.

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
        >>> diff = compare_4th_grade_boys_sheet_with_registrations()
        >>> print("Only in sheet:", diff["only_in_sheet"])
        >>> print("Only in registrations:", diff["only_in_registrations"])

    Example questions this function helps answer:
        - "Does the 4th Boys bracket reflect all registered teams?"
        - "Are there any extra teams in the bracket that don't exist in registrations?"
    """
    boys_sheet = list_4th_grade_boys_teams()
    sheet_names = sorted(
        {
            (t.get("Team Name") or "").strip()
            for t in boys_sheet
            if t.get("Team Name")
        }
    )

    regs = get_teams_by_division("4th Boys", include_waitlist=True)
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
def compare_4th_grade_girls_sheet_with_registrations() -> Dict[str, Any]:
    """
    Purpose:
        Compare the 4th Grade Girls bracket sheet with the 'Form Responses 1'
        registrations for division "4th Girls", to find mismatches.

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
        >>> diff = compare_4th_grade_girls_sheet_with_registrations()
        >>> print("Only in sheet:", diff["only_in_sheet"])
        >>> print("Only in registrations:", diff["only_in_registrations"])

    Example questions this function helps answer:
        - "Does the 4th Girls bracket reflect all registered teams?"
        - "Are any registered 4th Girls teams missing on the bracket sheet?"
    """
    girls_sheet = list_4th_grade_girls_teams()
    sheet_names = sorted(
        {
            (t.get("Team Name") or "").strip()
            for t in girls_sheet
            if t.get("Team Name")
        }
    )

    regs = get_teams_by_division("4th Girls", include_waitlist=True)
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