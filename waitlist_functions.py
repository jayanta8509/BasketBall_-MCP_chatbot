from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sheets_client import get_default_client
from form_responses_functions import get_waitlisted_teams, list_divisions
from mcp.server.fastmcp import FastMCP

WAITLIST_SHEET_NAME = "Waitlist"

mcp = FastMCP("Waitlist_data")

# ---------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------

def _load_waitlist_sheet(
    range_a1: str = "A1:G500",
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Load the "Waitlist" sheet with the correct header row.

    The sheet structure looks like:

        Row 0: ["Waiting List Teams", "Unnamed: 1", ..., "Unnamed: 6"]
        Row 1: ["Email", "First Name", "Last Name", "Phone",
                "Divison", "Team Name", "Notes"]
        Row 2+: actual data rows

    So we:
        - use row index 1 (second row) as headers
        - rows from index 2 onward as data

    Args:
        range_a1 (str):
            Range to read from the "Waitlist" sheet.

    Returns:
        (headers, records)
    """
    client = get_default_client()
    values = client.get_values(WAITLIST_SHEET_NAME, range_a1)
    if len(values) < 2:
        return [], []

    headers = values[1]
    data_rows = values[2:]

    records: List[Dict[str, Any]] = []
    for row in data_rows:
        # Skip completely empty rows
        if not any(str(cell).strip() for cell in row):
            continue
        row_dict = {
            headers[i]: (row[i] if i < len(row) else None)
            for i in range(len(headers))
        }
        records.append(row_dict)

    return headers, records


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Internal helper:
        Normalize a phone value to a digits-only string, or None.
    """
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return digits or None


# ---------------------------------------------------------
# Core waitlist-only functions
# ---------------------------------------------------------
@mcp.tool()
def list_waitlist_entries() -> List[Dict[str, Any]]:
    """
    Purpose:
        Return all entries from the "Waitlist" sheet as a list of dicts.
        Each entry corresponds to a single team on the manual waitlist.

    Args:
        None

    Returns:
        List[dict]:
            Each record looks like:
            {
                "Email": str | None,
                "First Name": str | None,
                "Last Name": str | None,
                "Phone": str | None,
                "Divison": str | None,
                "Team Name": str | None,
                "Notes": str | None,
            }

    Example usage:
        >>> entries = list_waitlist_entries()
        >>> for e in entries:
        ...     print(e["Team Name"], e["Divison"], e["Email"])

    Example questions this function helps answer:
        - "Show me everyone on the manual waitlist."
        - "Which teams are listed in the Waitlist sheet?"
    """
    _, rows = _load_waitlist_sheet()
    return rows

@mcp.tool()
def list_waitlist_divisions() -> List[str]:
    """
    Purpose:
        Return a sorted list of distinct divisions that appear in the
        "Waitlist" sheet.

    Args:
        None

    Returns:
        List[str]:
            Unique division values from the 'Divison' column, sorted.

    Example usage:
        >>> divs = list_waitlist_divisions()
        >>> print(divs)
        ['3rd Boys', '4th Boys', '7/8 Girls', ...]

    Example questions this function helps answer:
        - "Which divisions currently have a manual waitlist?"
        - "Are there any waitlist entries for 7/8 divisions?"
    """
    _, rows = _load_waitlist_sheet()
    seen: set[str] = set()
    for row in rows:
        div = (row.get("Divison") or "").strip()
        if div:
            seen.add(div)
    return sorted(seen)

@mcp.tool()
def get_waitlist_for_division(
    division: str,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Get all waitlist entries from the "Waitlist" sheet for a specific
        division (e.g. "3rd Boys").

    Args:
        division (str):
            Division name to filter by (case-insensitive comparison).

    Returns:
        List[dict]:
            One dict per team on that division's waitlist:
            {
                "Email": str | None,
                "First Name": str | None,
                "Last Name": str | None,
                "Phone": str | None,
                "Divison": str | None,
                "Team Name": str | None,
                "Notes": str | None,
                "position": int,   # 1-based index within that division in sheet order
            }

    Example usage:
        >>> wait_3rd_boys = get_waitlist_for_division("3rd Boys")
        >>> for w in wait_3rd_boys:
        ...     print(w["position"], w["Team Name"], w["Email"])

    Example questions this function helps answer:
        - "Who is on the 3rd Boys waitlist and in what order?"
        - "Show me the detailed waitlist for 4th Boys."
    """
    _, rows = _load_waitlist_sheet()
    results: List[Dict[str, Any]] = []

    pos = 0
    target_div = division.strip().lower()
    for row in rows:
        div = (row.get("Divison") or "").strip()
        if not div:
            continue
        if div.strip().lower() != target_div:
            continue
        pos += 1
        entry = dict(row)
        entry["position"] = pos
        results.append(entry)

    return results

@mcp.tool()
def get_waitlist_for_email(
    email: str,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Retrieve all waitlist entries (possibly multiple teams/divisions) for
        a given email address from the "Waitlist" sheet.

    Args:
        email (str):
            Email address to match (case-insensitive exact match).

    Returns:
        List[dict]:
            All waitlist entries that use this email.

    Example usage:
        >>> entries = get_waitlist_for_email("nntimmerman@gmail.com")
        >>> for e in entries:
        ...     print(e["Team Name"], e["Divison"])

    Example questions this function helps answer:
        - "Which waitlist teams belong to this coach's email?"
        - "Is this email on any waitlist, and in which divisions?"
    """
    _, rows = _load_waitlist_sheet()
    target = email.strip().lower()
    results: List[Dict[str, Any]] = []

    for row in rows:
        row_email = (row.get("Email") or "").strip().lower()
        if row_email == target:
            results.append(row)

    return results

@mcp.tool()
def get_waitlist_for_candidate_by_name(
    first_name: str,
    last_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Retrieve all waitlist entries for a candidate (contact) based on
        first name and optional last name from the "Waitlist" sheet.

    Args:
        first_name (str):
            First name to match (case-insensitive).
        last_name (str | None):
            Optional last name to match (case-insensitive). If None, only
            the first name is used.

    Returns:
        List[dict]:
            Matching waitlist entries, one per row.

    Example usage:
        >>> entries = get_waitlist_for_candidate_by_name("Nathan", "Timmerman")
        >>> for e in entries:
        ...     print(e["Team Name"], e["Divison"])

    Example questions this function helps answer:
        - "Is Nathan Timmerman on any waitlists and for which teams?"
        - "Show all waitlist entries for a given coach name."
    """
    _, rows = _load_waitlist_sheet()

    fn_target = first_name.strip().lower()
    ln_target = last_name.strip().lower() if last_name else None

    results: List[Dict[str, Any]] = []

    for row in rows:
        fn = (row.get("First Name") or "").strip()
        ln = (row.get("Last Name") or "").strip()

        if fn.lower() != fn_target:
            continue
        if ln_target is not None and ln.lower() != ln_target:
            continue

        results.append(row)

    return results

@mcp.tool()
def get_waitlist_for_team_name(
    team_name: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Find waitlist entries where 'Team Name' matches or contains a given
        string.

    Args:
        team_name (str):
            Team name or substring to search for (case-insensitive).
        exact (bool):
            If True, 'Team Name' must be exactly equal (case-insensitive).
            If False, 'Team Name' may simply contain the given substring.

    Returns:
        List[dict]:
            Matching waitlist entries.

    Example usage:
        >>> entries = get_waitlist_for_team_name("Falcons", exact=False)
        >>> for e in entries:
        ...     print(e["Team Name"], e["Divison"])

    Example questions this function helps answer:
        - "Is 'Falcons Green' on any waitlist?"
        - "Show me all waitlist entries for teams containing 'Falcons'."
    """
    _, rows = _load_waitlist_sheet()
    q = team_name.strip().lower()
    results: List[Dict[str, Any]] = []

    for row in rows:
        tn = (row.get("Team Name") or "").strip()
        tn_lower = tn.lower()
        if exact:
            if tn_lower == q:
                results.append(row)
        else:
            if q in tn_lower:
                results.append(row)

    return results

@mcp.tool()
def get_waitlist_positions_by_division() -> List[Dict[str, Any]]:
    """
    Purpose:
        Return a structured view of the waitlist positions per division,
        based on row order in the "Waitlist" sheet.

    Args:
        None

    Returns:
        List[dict]:
            Each record contains:
            {
                "division": str,
                "team_name": str | None,
                "first_name": str | None,
                "last_name": str | None,
                "email": str | None,
                "phone": str | None,
                "position": int,   # 1-based position in that division's queue
            }

    Example usage:
        >>> positions = get_waitlist_positions_by_division()
        >>> for p in positions:
        ...     print(p["division"], p["position"], p["team_name"])

    Example questions this function helps answer:
        - "What is the waitlist order across all divisions?"
        - "Who is first/second/etc. on the 3rd Boys waitlist?"
    """
    _, rows = _load_waitlist_sheet()
    counters: Dict[str, int] = {}
    results: List[Dict[str, Any]] = []

    for row in rows:
        div = (row.get("Divison") or "").strip()
        if not div:
            continue

        key = div.lower()
        counters.setdefault(key, 0)
        counters[key] += 1
        position = counters[key]

        results.append(
            {
                "division": div,
                "team_name": row.get("Team Name"),
                "first_name": row.get("First Name"),
                "last_name": row.get("Last Name"),
                "email": row.get("Email"),
                "phone": _normalize_phone(row.get("Phone")),
                "position": position,
            }
        )

    return results


def get_waitlist_position_for_team(
    division: str,
    team_name: str,
    exact: bool = True,
) -> Optional[int]:
    """
    Purpose:
        Get the numeric position (1-based) of a team on the manual waitlist
        for a given division.

    Args:
        division (str):
            Division name (case-insensitive).
        team_name (str):
            Team name to match (case-insensitive).
        exact (bool):
            If True, require exact match of team name.
            If False, any entry where team name contains the given substring
            is considered a match (returns the first matching position).

    Returns:
        int | None:
            The position (1-based) in that division's waitlist queue,
            or None if not found.

    Example usage:
        >>> pos = get_waitlist_position_for_team("3rd Boys", "Falcons Green")
        >>> print(pos)
        1

    Example questions this function helps answer:
        - "What position is 'Falcons Green' in on the 3rd Boys waitlist?"
        - "Is this team near the top of the waitlist?"
    """
    entries = get_waitlist_for_division(division)
    q = team_name.strip().lower()

    for e in entries:
        tn = (e.get("Team Name") or "").strip().lower()
        if exact:
            if tn == q:
                return e.get("position")
        else:
            if q in tn:
                return e.get("position")

    return None

@mcp.tool()
def get_waitlist_summary_by_division() -> List[Dict[str, Any]]:
    """
    Purpose:
        Provide a simple count of how many manual waitlist entries exist
        per division, based solely on the "Waitlist" sheet.

    Args:
        None

    Returns:
        List[dict]:
            Sorted by division name:
            {
                "division": str,
                "count": int,
            }

    Example usage:
        >>> summary = get_waitlist_summary_by_division()
        >>> for s in summary:
        ...     print(s["division"], "=>", s["count"], "entries")

    Example questions this function helps answer:
        - "How many teams are on the waitlist for each division?"
        - "Where is demand highest on the manual waitlist?"
    """
    _, rows = _load_waitlist_sheet()
    counts: Dict[str, int] = {}

    for row in rows:
        div = (row.get("Divison") or "").strip()
        if not div:
            continue
        key = div
        counts[key] = counts.get(key, 0) + 1

    result = [
        {"division": d, "count": c}
        for d, c in sorted(counts.items(), key=lambda x: x[0])
    ]
    return result

@mcp.tool()
def search_waitlist(
    query: str,
    fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Perform a simple case-insensitive search across one or more fields
        in the "Waitlist" sheet (e.g., team name, candidate name, email).

    Args:
        query (str):
            Substring to search for.
        fields (List[str] | None):
            If provided, restrict search to these column names (e.g.
            ["Team Name", "First Name", "Last Name"]).
            If None, default to:
            ["Team Name", "First Name", "Last Name", "Email", "Divison"].

    Returns:
        List[dict]:
            All rows where any target field contains the query.

    Example usage:
        >>> matches = search_waitlist("Falcons")
        >>> for m in matches:
        ...     print(m["Team Name"], m["Divison"])

    Example questions this function helps answer:
        - "Are there any waitlist entries with 'Falcons' in the name?"
        - "Find any waitlist entries related to a specific last name."
    """
    _, rows = _load_waitlist_sheet()
    q = query.strip().lower()
    if not q:
        return []

    if fields is None:
        fields = ["Team Name", "First Name", "Last Name", "Email", "Divison"]

    results: List[Dict[str, Any]] = []

    for row in rows:
        for f in fields:
            val = (row.get(f) or "").strip().lower()
            if q in val:
                results.append(row)
                break

    return results


# ---------------------------------------------------------
# Cross-sheet helpers: Waitlist + Form Responses
# ---------------------------------------------------------
@mcp.tool()
def get_combined_waitlist_for_division(
    division: str,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Combine waitlist information for a division from:
        - Sheet1: 'Form Responses 1' (teams marked as *WAITING LIST*)
        - Sheet3: 'Waitlist' (manual queue)
        into a unified list.

    Args:
        division (str):
            Division name, e.g. "3rd Boys".

    Returns:
        List[dict]:
            Combined entries with a "source" field indicating where the
            waitlist entry comes from:
            {
                "source": "form_responses" | "waitlist_sheet",
                "division": str,
                "team_name": str | None,
                "contact_first_name": str | None,
                "contact_last_name": str | None,
                "email": str | None,
                "phone": str | None,
                "position": int | None,   # position from Waitlist sheet if available
                "notes": str | None,
            }

    Example usage:
        >>> combined = get_combined_waitlist_for_division("3rd Boys")
        >>> for c in combined:
        ...     print(c["source"], c["team_name"], c["email"], c["position"])

    Example questions this function helps answer:
        - "For 3rd Boys, show all waitlisted teams from both sheets."
        - "Is there anyone on the manual waitlist that isn't in Form Responses yet?"
    """
    # From Sheet1 (Form Responses 1)
    fr_wait = get_waitlisted_teams(division)

    combined: List[Dict[str, Any]] = []

    for row in fr_wait:
        combined.append(
            {
                "source": "form_responses",
                "division": division,
                "team_name": row.get("team_name"),
                "contact_first_name": row.get("contact_first_name"),
                "contact_last_name": row.get("contact_last_name"),
                "email": row.get("contact_email"),
                "phone": row.get("contact_phone"),
                "position": None,
                "notes": None,
            }
        )

    # From Waitlist sheet
    wl_entries = get_waitlist_for_division(division)
    for e in wl_entries:
        combined.append(
            {
                "source": "waitlist_sheet",
                "division": division,
                "team_name": e.get("Team Name"),
                "contact_first_name": e.get("First Name"),
                "contact_last_name": e.get("Last Name"),
                "email": e.get("Email"),
                "phone": _normalize_phone(e.get("Phone")),
                "position": e.get("position"),
                "notes": e.get("Notes"),
            }
        )

    return combined

@mcp.tool()
def get_combined_waitlist_summary() -> List[Dict[str, Any]]:
    """
    Purpose:
        Produce a combined summary of waitlist counts per division, merging:
        - 'Form Responses 1' waitlist teams (Sheet1)
        - 'Waitlist' sheet manual entries (Sheet3)

    Args:
        None

    Returns:
        List[dict]:
            For each division that appears in either source:
            {
                "division": str,
                "form_responses_waitlist_count": int,
                "manual_waitlist_count": int,
                "combined_waitlist_count": int,
            }

    Example usage:
        >>> summary = get_combined_waitlist_summary()
        >>> for s in summary:
        ...     print(s["division"], s["combined_waitlist_count"])

    Example questions this function helps answer:
        - "Across both sheets, how many teams are on the waitlist per division?"
        - "Are there divisions where the manual waitlist is much larger than the auto one?"
    """
    divisions_from_sheet1 = list_divisions()
    divisions_from_waitlist = list_waitlist_divisions()

    all_divs = sorted(set(divisions_from_sheet1) | set(divisions_from_waitlist))

    results: List[Dict[str, Any]] = []

    for div in all_divs:
        fr_entries = get_waitlisted_teams(div)
        fr_count = len(fr_entries)

        wl_entries = get_waitlist_for_division(div)
        wl_count = len(wl_entries)

        results.append(
            {
                "division": div,
                "form_responses_waitlist_count": fr_count,
                "manual_waitlist_count": wl_count,
                "combined_waitlist_count": fr_count + wl_count,
            }
        )

    return results

@mcp.tool()
def is_candidate_on_any_waitlist(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Purpose:
        Check if a candidate (coach/contact) appears on any waitlist, across
        BOTH:
            - Sheet1: 'Form Responses 1' waitlisted teams
            - Sheet3: 'Waitlist' manual entries

        It returns a structured object describing where and how many times
        the candidate appears.

    Args:
        first_name (str | None):
            Optional first name to match (case-insensitive).
        last_name (str | None):
            Optional last name to match (case-insensitive).
        email (str | None):
            Optional email to match (case-insensitive).

            At least one of (first_name, last_name, email) should be provided.

    Returns:
        dict:
            {
                "query": {
                    "first_name": str | None,
                    "last_name": str | None,
                    "email": str | None,
                },
                "form_responses_matches": List[dict],  # from get_waitlisted_teams per division
                "waitlist_sheet_matches": List[dict],  # from Waitlist sheet
                "is_on_any_waitlist": bool,
            }

    Example usage:
        >>> status = is_candidate_on_any_waitlist(
        ...     first_name="Nathan", last_name="Timmerman"
        ... )
        >>> print(status["is_on_any_waitlist"])
        True
        >>> print(len(status["form_responses_matches"]))
        1
        >>> print(len(status["waitlist_sheet_matches"]))
        2

    Example questions this function helps answer:
        - "Is this coach on any waitlist at all?"
        - "Across both sheets, where does this candidate appear on waitlists?"
    """
    if not (first_name or last_name or email):
        raise ValueError("At least one of first_name, last_name, or email must be provided")

    # Normalize query fields
    fn_q = first_name.strip().lower() if first_name else None
    ln_q = last_name.strip().lower() if last_name else None
    email_q = email.strip().lower() if email else None

    # 1) From Form Responses 1 (Sheet1) via get_waitlisted_teams per division
    fr_matches: List[Dict[str, Any]] = []

    for div in list_divisions():
        entries = get_waitlisted_teams(div)
        for e in entries:
            fn = (e.get("contact_first_name") or "").strip().lower()
            ln = (e.get("contact_last_name") or "").strip().lower()
            em = (e.get("contact_email") or "").strip().lower()

            if fn_q and fn_q != fn:
                continue
            if ln_q and ln_q != ln:
                continue
            if email_q and email_q != em:
                continue

            fr_matches.append(
                {
                    "division": div,
                    "team_name": e.get("team_name"),
                    "contact_first_name": e.get("contact_first_name"),
                    "contact_last_name": e.get("contact_last_name"),
                    "email": e.get("contact_email"),
                    "phone": e.get("contact_phone"),
                }
            )

    # 2) From Waitlist sheet (Sheet3)
    wl_matches: List[Dict[str, Any]] = []
    _, rows = _load_waitlist_sheet()

    for row in rows:
        fn = (row.get("First Name") or "").strip().lower()
        ln = (row.get("Last Name") or "").strip().lower()
        em = (row.get("Email") or "").strip().lower()

        if fn_q and fn_q != fn:
            continue
        if ln_q and ln_q != ln:
            continue
        if email_q and email_q != em:
            continue

        wl_matches.append(
            {
                "division": row.get("Divison"),
                "team_name": row.get("Team Name"),
                "first_name": row.get("First Name"),
                "last_name": row.get("Last Name"),
                "email": row.get("Email"),
                "phone": _normalize_phone(row.get("Phone")),
                "notes": row.get("Notes"),
            }
        )

    is_on_any = bool(fr_matches or wl_matches)

    return {
        "query": {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        },
        "form_responses_matches": fr_matches,
        "waitlist_sheet_matches": wl_matches,
        "is_on_any_waitlist": is_on_any,
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")