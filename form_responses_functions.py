# form_responses_functions.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sheets_client import get_default_client
from mcp.server.fastmcp import FastMCP
FORM_RESPONSES_SHEET_NAME = "Form Responses 1"

mcp = FastMCP("Google_ALL_sheet_data")

# ---------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------

def _load_form_responses(range_a1: str = "A1:Z1000") -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Load headers and row dictionaries from the "Form Responses 1" sheet.

    Behavior:
        - Uses the default Google Sheets client configured in sheets_client.py.
        - Reads the given A1 range and converts rows into a list of dicts
          keyed by header names.

    Args:
        range_a1 (str):
            A1 range to fetch from the "Form Responses 1" sheet.
            Defaults to "A1:Z1000".

    Returns:
        Tuple[List[str], List[dict]]:
            headers: List of column names (first row).
            rows:    List of row dictionaries {header: value}.
    """
    client = get_default_client()
    return client.get_header_and_rows(FORM_RESPONSES_SHEET_NAME, range_a1)


def _get_division_column(headers: List[str]) -> Optional[str]:
    """
    Internal helper:
        Find the division column header (starts with "Team Division(s)").
    """
    for h in headers:
        if h.startswith("Team Division(s)"):
            return h
    return None


def _get_agreement_columns(headers: List[str]) -> List[str]:
    """
    Internal helper:
        Return all headers that start with "I understand that".
    """
    return [h for h in headers if h.startswith("I understand that")]


def _parse_divisions(raw_value: Optional[str]) -> List[str]:
    """
    Internal helper:
        Parse a 'Team Division(s)' cell into normalized division names,
        stripping any '*WAITING LIST*' markers.
    """
    if not raw_value:
        return []
    divisions: List[str] = []
    for part in str(raw_value).split(","):
        clean = part.strip().replace("*WAITING LIST*", "").strip()
        if clean:
            divisions.append(clean)
    return divisions


def _is_waitlisted(raw_value: Optional[str]) -> bool:
    """
    Internal helper:
        Return True if the division cell indicates a waiting list.
    """
    if not raw_value:
        return False
    return "WAITING LIST" in str(raw_value).upper()


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Internal helper:
        Strip non-digit characters from a phone number and return digits only.
    """
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return digits or None


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """
    Internal helper:
        Parse a timestamp from the "Timestamp" column into a datetime object.
    """
    if not value:
        return None
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


# Public Functions
@mcp.tool()
def list_divisions() -> List[str]:
    """
    Purpose:
        Return all distinct divisions that appear in the "Form Responses 1" sheet.
        This ignores any '*WAITING LIST*' markers and deduplicates values.

    Args:
        None

    Returns:
        List[str]:
            A sorted list of unique division names, e.g.
            ["3rd Boys", "3rd Girls", "4th Boys", "4th Girls", "5th Boys", ...].

    Example usage:
        >>> divisions = list_divisions()
        >>> print(divisions)
        ['3rd Boys', '3rd Girls', '4th Boys', '4th Girls', ...]

    Example questions this function helps answer:
        - "What divisions are currently represented in registrations?"
        - "Which grade/gender divisions exist in this league data?"
    """
    headers, rows = _load_form_responses()
    division_col = _get_division_column(headers)
    if not division_col:
        return []

    seen: set[str] = set()
    for row in rows:
        raw = row.get(division_col)
        for d in _parse_divisions(raw):
            seen.add(d)
    return sorted(seen)

@mcp.tool()
def get_teams_by_division(
    division: str,
    include_waitlist: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Retrieve all teams that are registered in a specific division
        (e.g. "3rd Boys", "4th Girls"), optionally including those that
        are currently on a waiting list.

    Args:
        division (str):
            The exact division name to filter by, e.g. "3rd Boys".
        include_waitlist (bool):
            If True, include teams whose registration is marked as waiting list.
            If False, only include confirmed (non-waitlist) teams.

    Returns:
        List[dict]:
            A list of dictionaries, each containing key information about a team:
            {
                "team_name": str | None,
                "division": List[str],      # all divisions selected for that row
                "is_waitlist": bool,
                "contact_first_name": str | None,
                "contact_last_name": str | None,
                "contact_email": str | None,
                "contact_phone": str | None,
                "timestamp": str | None,
            }

    Example usage:
        >>> teams = get_teams_by_division("3rd Boys", include_waitlist=False)
        >>> for t in teams:
        ...     print(t["team_name"], t["contact_email"])

    Example questions this function helps answer:
        - "Show me all teams registered in 3rd Boys."
        - "Which coach contacts belong to the 5th Girls division?"
        - "Who is on the 4th Boys waiting list vs confirmed?"
    """
    headers, rows = _load_form_responses()
    division_col = _get_division_column(headers)
    if not division_col:
        return []

    results: List[Dict[str, Any]] = []
    for row in rows:
        raw_divisions = row.get(division_col)
        divisions = _parse_divisions(raw_divisions)
        if division not in divisions:
            continue

        waitlisted = _is_waitlisted(raw_divisions)
        if waitlisted and not include_waitlist:
            continue

        results.append(
            {
                "team_name": row.get("Team Name"),
                "division": divisions,
                "is_waitlist": waitlisted,
                "contact_first_name": row.get("Contact First Name"),
                "contact_last_name": row.get("Contact Last Name"),
                "contact_email": row.get("Email Address"),
                "contact_phone": row.get("Contact Phone"),
                "timestamp": row.get("Timestamp"),
            }
        )
    return results

@mcp.tool()
def get_waitlisted_teams(division: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Purpose:
        Retrieve all teams that are currently on a waiting list.
        You can optionally filter by a specific division (e.g. "3rd Boys").

    Args:
        division (str | None):
            If provided, only return waitlist entries for that division.
            If None, return waitlisted teams across all divisions.

    Returns:
        List[dict]:
            A list of team records with waitlist status set to True:
            {
                "team_name": str | None,
                "division": List[str],
                "contact_first_name": str | None,
                "contact_last_name": str | None,
                "contact_email": str | None,
                "contact_phone": str | None,
                "timestamp": str | None,
            }

    Example usage:
        >>> all_waitlist = get_waitlisted_teams()
        >>> third_boys_waitlist = get_waitlisted_teams("3rd Boys")

    Example questions this function helps answer:
        - "Which teams are on a waiting list in any division?"
        - "Who is on the 3rd Boys waiting list?"
        - "How many teams are waiting per division?"
    """
    headers, rows = _load_form_responses()
    division_col = _get_division_column(headers)
    if not division_col:
        return []

    results: List[Dict[str, Any]] = []
    for row in rows:
        raw_divisions = row.get(division_col)
        if not _is_waitlisted(raw_divisions):
            continue

        divisions = _parse_divisions(raw_divisions)
        if division and division not in divisions:
            continue

        results.append(
            {
                "team_name": row.get("Team Name"),
                "division": divisions,
                "contact_first_name": row.get("Contact First Name"),
                "contact_last_name": row.get("Contact Last Name"),
                "contact_email": row.get("Email Address"),
                "contact_phone": row.get("Contact Phone"),
                "timestamp": row.get("Timestamp"),
            }
        )
    return results

@mcp.tool()
def count_teams_by_division(include_waitlist: bool = True) -> List[Dict[str, Any]]:
    """
    Purpose:
        Produce a summary count of teams per division, including confirmed
        and optionally waitlisted teams.

    Args:
        include_waitlist (bool):
            If True, count both confirmed and waitlist teams in "total".
            If False, only count non-waitlist (confirmed) teams in "total".

    Returns:
        List[dict]:
            A list of summaries:
            {
                "division": str,
                "confirmed": int,
                "waitlist": int,
                "total": int,
            }

    Example usage:
        >>> summary = count_teams_by_division(include_waitlist=True)
        >>> for s in summary:
        ...     print(s["division"], s["confirmed"], s["waitlist"], s["total"])

    Example questions this function helps answer:
        - "How many teams are registered in each division?"
        - "Which divisions are close to capacity?"
        - "Where is the waitlist pressure highest?"
    """
    headers, rows = _load_form_responses()
    division_col = _get_division_column(headers)

    if not division_col:
        return []

    counts: Dict[str, Dict[str, int]] = {}

    for row in rows:
        raw_divisions = row.get(division_col)
        divisions = _parse_divisions(raw_divisions)
        waitlisted = _is_waitlisted(raw_divisions)

        for d in divisions:
            if d not in counts:
                counts[d] = {"confirmed": 0, "waitlist": 0}
            if waitlisted:
                counts[d]["waitlist"] += 1
            else:
                counts[d]["confirmed"] += 1

    result: List[Dict[str, Any]] = []
    for d, c in sorted(counts.items(), key=lambda x: x[0]):
        total = c["confirmed"] + (c["waitlist"] if include_waitlist else 0)
        result.append(
            {
                "division": d,
                "confirmed": c["confirmed"],
                "waitlist": c["waitlist"],
                "total": total,
            }
        )
    return result

@mcp.tool()
def list_contacts(with_teams: bool = False) -> List[Dict[str, Any]]:
    """
    Purpose:
        Generate a deduplicated list of contacts (coaches) from
        "Form Responses 1". Optionally attach the list of teams each
        contact is associated with.

    Args:
        with_teams (bool):
            If True, include a "teams" list containing all team names
            submitted by that contact.
            If False, omit "teams" from the result.

    Returns:
        List[dict]:
            Each record looks like:
            {
                "first_name": str | None,
                "last_name": str | None,
                "email": str | None,
                "phone": str | None,
                "teams": List[str] (optional if with_teams=True),
            }

    Example usage:
        >>> contacts = list_contacts(with_teams=True)
        >>> for c in contacts:
        ...     print(c["first_name"], c["email"], c.get("teams"))

    Example questions this function helps answer:
        - "Who are all the coaches in the league?"
        - "Which teams is a particular coach responsible for?"
        - "How many unique contacts do we have?"
    """
    headers, rows = _load_form_responses()
    _ = _get_division_column(headers)  # currently unused but kept for context

    key_map: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for row in rows:
        email = (row.get("Email Address") or "").strip()
        phone_norm = _normalize_phone(row.get("Contact Phone"))
        key = (email.lower(), phone_norm or "")

        if key not in key_map:
            key_map[key] = {
                "first_name": row.get("Contact First Name"),
                "last_name": row.get("Contact Last Name"),
                "email": email or None,
                "phone": phone_norm,
                "teams": [] if with_teams else None,
            }

        if with_teams:
            team_name = row.get("Team Name")
            if team_name and team_name not in key_map[key]["teams"]:
                key_map[key]["teams"].append(team_name)

    contacts = list(key_map.values())
    if not with_teams:
        for c in contacts:
            c.pop("teams", None)
    return contacts

@mcp.tool()
def find_registrations_by_email(email: str) -> List[Dict[str, Any]]:
    """
    Purpose:
        Retrieve all registration rows submitted with a particular email
        address (exact, case-insensitive match).

    Args:
        email (str):
            The email address to search for (case-insensitive).

    Returns:
        List[dict]:
            List of registration row dictionaries matching that email.

    Example usage:
        >>> regs = find_registrations_by_email("coach@example.com")
        >>> for r in regs:
        ...     print(r["Team Name"], r["Timestamp"])

    Example questions this function helps answer:
        - "Show me all teams registered by this email."
        - "Did this coach submit more than one team?"
    """
    _, rows = _load_form_responses()
    target = email.strip().lower()
    return [
        row
        for row in rows
        if (row.get("Email Address") or "").strip().lower() == target
    ]

@mcp.tool()
def find_registrations_by_team_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Find registrations whose "Team Name" matches a given string,
        either exactly or as a partial (contains) match.

    Args:
        query (str):
            The team name or substring to search for.
        exact (bool):
            If True, only return rows where Team Name equals query (case-insensitive).
            If False, return rows where Team Name contains the query substring.

    Returns:
        List[dict]:
            Matching registration rows.

    Example usage:
        >>> matches = find_registrations_by_team_name("Eldon", exact=False)
        >>> for r in matches:
        ...     print(r["Team Name"], r["Email Address"])

    Example questions this function helps answer:
        - "Is there a team called 'Eldon 3rd Grade A'?"
        - "Show all teams with 'Lakers' in the name."
    """
    _, rows = _load_form_responses()
    q = query.strip().lower()
    results: List[Dict[str, Any]] = []

    for row in rows:
        team_name = (row.get("Team Name") or "").strip()
        tn = team_name.lower()
        if exact:
            if tn == q:
                results.append(row)
        else:
            if q in tn:
                results.append(row)

    return results

@mcp.tool()
def list_duplicate_registrations() -> List[Dict[str, Any]]:
    """
    Purpose:
        Identify registration rows explicitly marked as duplicates using
        Column 1 or Column 2 when they contain the word "duplicate"
        (case-insensitive).

    Args:
        None

    Returns:
        List[dict]:
            Registration rows where Column 1 or Column 2 contains "duplicate".

    Example usage:
        >>> duplicates = list_duplicate_registrations()
        >>> for r in duplicates:
        ...     print(r["Team Name"], r["Email Address"])

    Example questions this function helps answer:
        - "Which rows have been flagged as duplicates?"
        - "Which teams may have registered twice?"
    """
    _, rows = _load_form_responses()
    results: List[Dict[str, Any]] = []

    for row in rows:
        c1 = (row.get("Column 1") or "").strip().lower()
        c2 = (row.get("Column 2") or "").strip().lower()
        if "duplicate" in c1 or "duplicate" in c2:
            results.append(row)

    return results

@mcp.tool()
def summarize_agreements() -> List[Dict[str, Any]]:
    """
    Purpose:
        Summarize how many registrations agreed vs did NOT agree to each
        of the 'I understand that...' league statements.

    Args:
        None

    Returns:
        List[dict]:
            For each agreement column:
            {
                "column": str,
                "agree_count": int,
                "other_count": int,
                "total": int,
            }

    Example usage:
        >>> summary = summarize_agreements()
        >>> for s in summary:
        ...     print(s["column"], s["agree_count"], "/", s["total"])

    Example questions this function helps answer:
        - "Did everyone agree to the liability and schedule terms?"
        - "Are there any registrations missing agreement acknowledgements?"
    """
    headers, rows = _load_form_responses()
    agreement_cols = _get_agreement_columns(headers)

    result: List[Dict[str, Any]] = []
    for col in agreement_cols:
        agree = 0
        other = 0
        for row in rows:
            val = (row.get(col) or "").strip()
            if not val:
                continue
            if val.lower() == "i agree":
                agree += 1
            else:
                other += 1
        total = agree + other
        result.append(
            {
                "column": col,
                "agree_count": agree,
                "other_count": other,
                "total": total,
            }
        )

    return result

@mcp.tool()
def get_recent_registrations(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Purpose:
        Return the most recent N registrations based on the "Timestamp" column,
        sorted from newest to oldest.

    Args:
        limit (int):
            Maximum number of latest registrations to return.
            Defaults to 10.

    Returns:
        List[dict]:
            Latest registration rows, sorted newest first.

    Example usage:
        >>> latest = get_recent_registrations(limit=5)
        >>> for r in latest:
        ...     print(r["Timestamp"], r["Team Name"])

    Example questions this function helps answer:
        - "What are the latest teams that signed up?"
        - "Who registered in the last few entries?"
    """
    _, rows = _load_form_responses()
    enriched: List[Tuple[Optional[datetime], Dict[str, Any]]] = []

    for row in rows:
        ts = _parse_timestamp(row.get("Timestamp"))
        enriched.append((ts, row))

    # Sort by timestamp, putting None at the end
    enriched.sort(key=lambda x: (x[0] is None, x[0]), reverse=True)
    return [r for _, r in enriched[:limit]]

@mcp.tool()
def search_registrations(
    query: str,
    fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Perform a simple case-insensitive search across one or more fields
        in each registration row (e.g. team name, contact name, email).

    Args:
        query (str):
            The substring to search for (case-insensitive).
        fields (List[str] | None):
            If provided, restrict search to these field names.
            If None, search common fields:
                ["Team Name", "Contact First Name", "Contact Last Name", "Email Address"].

    Returns:
        List[dict]:
            Registration rows where any of the target fields contains the query.

    Example usage:
        >>> matches = search_registrations("eagles")
        >>> for r in matches:
        ...     print(r["Team Name"])

    Example questions this function helps answer:
        - "Find any registrations with 'Eagles' in the team name."
        - "Show me all entries related to 'Kliethermes'."
    """
    _, rows = _load_form_responses()

    q = query.strip().lower()
    if not q:
        return []

    if fields is None:
        fields = [
            "Team Name",
            "Contact First Name",
            "Contact Last Name",
            "Email Address",
        ]

    results: List[Dict[str, Any]] = []
    for row in rows:
        for f in fields:
            val = (row.get(f) or "").strip().lower()
            if q in val:
                results.append(row)
                break

    return results

@mcp.tool()
def get_candidate_profiles_by_name(
    first_name: str,
    last_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Retrieve one or more "candidate" profiles (coach/contact) by their
        first and optional last name. A profile includes their contact info,
        teams they registered, and divisions for each team.

    Args:
        first_name (str):
            Contact first name to search for (case-insensitive).
        last_name (str | None):
            Optional contact last name to narrow the search (case-insensitive).

    Returns:
        List[dict]:
            A list of profiles. Each profile groups all rows that match that
            name combination. Structure example:
            {
                "first_name": "Nathanial",
                "last_name": "Caudel",
                "emails": ["nathanial@example.com"],
                "phones": ["5732308287"],
                "teams": [
                    {
                        "team_name": "Eldon 3rd Grade A",
                        "divisions": ["3rd Boys"],
                        "is_waitlist": False,
                        "timestamp": "11/5/2025 12:01:43",
                    },
                    ...
                ],
            }

    Example usage:
        >>> profiles = get_candidate_profiles_by_name("Nathanial", "Caudel")
        >>> for p in profiles:
        ...     print(p["first_name"], p["last_name"], p["emails"], p["phones"])
        ...     for t in p["teams"]:
        ...         print("  -", t["team_name"], t["divisions"])

    Example questions this function helps answer:
        - "For coach Nathanial Caudel, what teams and divisions did he register?"
        - "Show me all teams associated with a specific candidate name."
        - "Which divisions does a given coach participate in?"
    """
    headers, rows = _load_form_responses()
    division_col = _get_division_column(headers)
    if not division_col:
        return []

    fn_target = first_name.strip().lower()
    ln_target = last_name.strip().lower() if last_name else None

    profiles_map: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for row in rows:
        fn = (row.get("Contact First Name") or "").strip()
        ln = (row.get("Contact Last Name") or "").strip()

        if fn.lower() != fn_target:
            continue
        if ln_target is not None and ln.lower() != ln_target:
            continue

        email = (row.get("Email Address") or "").strip()
        phone_norm = _normalize_phone(row.get("Contact Phone"))
        raw_divisions = row.get(division_col)
        divisions = _parse_divisions(raw_divisions)
        waitlisted = _is_waitlisted(raw_divisions)

        key = (fn, ln)

        if key not in profiles_map:
            profiles_map[key] = {
                "first_name": fn or None,
                "last_name": ln or None,
                "emails": [],
                "phones": [],
                "teams": [],
            }

        profile = profiles_map[key]

        if email and email not in profile["emails"]:
            profile["emails"].append(email)
        if phone_norm and phone_norm not in profile["phones"]:
            profile["phones"].append(phone_norm)

        profile["teams"].append(
            {
                "team_name": row.get("Team Name"),
                "divisions": divisions,
                "is_waitlist": waitlisted,
                "timestamp": row.get("Timestamp"),
            }
        )

    return list(profiles_map.values())

@mcp.tool()
def get_candidate_contact_by_name(
    first_name: str,
    last_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Quickly retrieve phone number(s) and email address(es) for a candidate
        (coach/contact) by their name, without team details.

    Args:
        first_name (str):
            Contact first name (case-insensitive).
        last_name (str | None):
            Optional contact last name (case-insensitive).

    Returns:
        List[dict]:
            A list of contact entries (deduplicated by email+phone):
            {
                "first_name": str | None,
                "last_name": str | None,
                "email": str | None,
                "phone": str | None,
            }

    Example usage:
        >>> contacts = get_candidate_contact_by_name("Nathanial", "Caudel")
        >>> for c in contacts:
        ...     print(c["first_name"], c["last_name"], c["email"], c["phone"])

    Example questions this function helps answer:
        - "What is the phone number for Nathanial Caudel?"
        - "What email address does 'Aaron Kliethermes' use on his registration?"
    """
    _, rows = _load_form_responses()

    fn_target = first_name.strip().lower()
    ln_target = last_name.strip().lower() if last_name else None

    seen_keys: set[Tuple[str, str]] = set()
    results: List[Dict[str, Any]] = []

    for row in rows:
        fn = (row.get("Contact First Name") or "").strip()
        ln = (row.get("Contact Last Name") or "").strip()

        if fn.lower() != fn_target:
            continue
        if ln_target is not None and ln.lower() != ln_target:
            continue

        email = (row.get("Email Address") or "").strip()
        phone_norm = _normalize_phone(row.get("Contact Phone"))
        key = (email.lower(), phone_norm or "")

        if key in seen_keys:
            continue
        seen_keys.add(key)

        results.append(
            {
                "first_name": fn or None,
                "last_name": ln or None,
                "email": email or None,
                "phone": phone_norm,
            }
        )

    return results

@mcp.tool()
def get_candidate_agreements_by_name(
    first_name: str,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Retrieve the "I understand that..." agreement answers for a candidate.
        This returns one entry per registration row that matches the candidate,
        with all agreement columns and their values.

    Args:
        first_name (str):
            Contact first name (case-insensitive).
        last_name (str | None):
            Optional contact last name (case-insensitive).
        email (str | None):
            Optional email to narrow down matches further.

    Returns:
        List[dict]:
            One dict per matching registration row:
            {
                "first_name": str | None,
                "last_name": str | None,
                "email": str | None,
                "team_name": str | None,
                "agreements": {
                    "<agreement column name>": "<cell value>",
                    ...
                },
            }

    Example usage:
        >>> entries = get_candidate_agreements_by_name("Aaron", "Kliethermes")
        >>> for e in entries:
        ...     print(e["team_name"])
        ...     for col, val in e["agreements"].items():
        ...         print("  ", col, "=>", val)

    Example questions this function helps answer:
        - "Has this coach agreed to all the league policies?"
        - "What did 'John Doe' answer for the liability statement?"
        - "Show the agreement responses for a candidate's registrations."
    """
    headers, rows = _load_form_responses()
    agreement_cols = _get_agreement_columns(headers)

    fn_target = first_name.strip().lower()
    ln_target = last_name.strip().lower() if last_name else None
    email_target = email.strip().lower() if email else None

    results: List[Dict[str, Any]] = []

    for row in rows:
        fn = (row.get("Contact First Name") or "").strip()
        ln = (row.get("Contact Last Name") or "").strip()
        row_email = (row.get("Email Address") or "").strip().lower()

        if fn.lower() != fn_target:
            continue
        if ln_target is not None and ln.lower() != ln_target:
            continue
        if email_target is not None and row_email != email_target:
            continue

        agreements = {
            col: (row.get(col) or "").strip()
            for col in agreement_cols
        }

        results.append(
            {
                "first_name": fn or None,
                "last_name": ln or None,
                "email": row.get("Email Address") or None,
                "team_name": row.get("Team Name"),
                "agreements": agreements,
            }
        )

    return results

@mcp.tool()
def get_candidate_divisions(
    first_name: str,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
) -> List[str]:
    """
    Purpose:
        Return all distinct divisions that a particular candidate (coach/contact)
        is associated with across all their registrations.

    Args:
        first_name (str):
            Contact first name (case-insensitive).
        last_name (str | None):
            Optional contact last name (case-insensitive).
        email (str | None):
            Optional email to further narrow matches.

    Returns:
        List[str]:
            Sorted list of unique division names for this candidate.

    Example usage:
        >>> divs = get_candidate_divisions("Nathanial", "Caudel")
        >>> print(divs)
        ['3rd Boys']

    Example questions this function helps answer:
        - "Which divisions does this coach participate in?"
        - "Is this candidate coaching multiple grade levels?"
    """
    headers, rows = _load_form_responses()
    division_col = _get_division_column(headers)
    if not division_col:
        return []

    fn_target = first_name.strip().lower()
    ln_target = last_name.strip().lower() if last_name else None
    email_target = email.strip().lower() if email else None

    seen: set[str] = set()

    for row in rows:
        fn = (row.get("Contact First Name") or "").strip()
        ln = (row.get("Contact Last Name") or "").strip()
        row_email = (row.get("Email Address") or "").strip().lower()

        if fn.lower() != fn_target:
            continue
        if ln_target is not None and ln.lower() != ln_target:
            continue
        if email_target is not None and row_email != email_target:
            continue

        raw_divisions = row.get(division_col)
        for d in _parse_divisions(raw_divisions):
            seen.add(d)

    return sorted(seen)

@mcp.tool()
def get_team_details(
    team_name: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Retrieve detailed information for one or more teams based on the
        "Team Name" field. This includes team name, divisions, waitlist flag,
        candidate (coach) contact info, and agreement responses.

    Args:
        team_name (str):
            The team name or substring to search for.
        exact (bool):
            If True, only return rows with Team Name exactly equal (case-insensitive).
            If False, return rows where Team Name contains the given substring.

    Returns:
        List[dict]:
            A list of detailed team registration records:
            {
                "team_name": str | None,
                "divisions": List[str],
                "is_waitlist": bool,
                "contact_first_name": str | None,
                "contact_last_name": str | None,
                "contact_email": str | None,
                "contact_phone": str | None,
                "timestamp": str | None,
                "agreements": {
                    "<agreement column>": "<value>",
                    ...
                },
            }

    Example usage:
        >>> teams = get_team_details("Eldon 3rd Grade A", exact=True)
        >>> for t in teams:
        ...     print(t["team_name"], t["divisions"], t["contact_email"])
        ...     for col, val in t["agreements"].items():
        ...         print("  ", col, "=>", val)

    Example questions this function helps answer:
        - "Show me everything about the team 'Eldon 3rd Grade A'."
        - "Which agreements did this team acknowledge?"
        - "What divisions and contact info are linked to a team whose name contains 'Lakers'?"
    """
    headers, rows = _load_form_responses()
    division_col = _get_division_column(headers)
    agreement_cols = _get_agreement_columns(headers)
    if not division_col:
        return []

    q = team_name.strip().lower()
    results: List[Dict[str, Any]] = []

    for row in rows:
        tn = (row.get("Team Name") or "").strip()
        tn_lower = tn.lower()
        if exact:
            if tn_lower != q:
                continue
        else:
            if q not in tn_lower:
                continue

        raw_divisions = row.get(division_col)
        divisions = _parse_divisions(raw_divisions)
        waitlisted = _is_waitlisted(raw_divisions)

        agreements = {
            col: (row.get(col) or "").strip()
            for col in agreement_cols
        }

        results.append(
            {
                "team_name": tn or None,
                "divisions": divisions,
                "is_waitlist": waitlisted,
                "contact_first_name": row.get("Contact First Name"),
                "contact_last_name": row.get("Contact Last Name"),
                "contact_email": row.get("Email Address"),
                "contact_phone": _normalize_phone(row.get("Contact Phone")),
                "timestamp": row.get("Timestamp"),
                "agreements": agreements,
            }
        )

    return results

@mcp.tool()
def get_candidate_teams(
    first_name: str,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Purpose:
        Return a flat list of all team entries (one per registration row)
        associated with a given candidate, including team name, divisions,
        and waitlist status.

    Args:
        first_name (str):
            Contact first name (case-insensitive).
        last_name (str | None):
            Optional contact last name (case-insensitive).
        email (str | None):
            Optional email to narrow down matches.

    Returns:
        List[dict]:
            One dict per matching registration row:
            {
                "team_name": str | None,
                "divisions": List[str],
                "is_waitlist": bool,
                "timestamp": str | None,
            }

    Example usage:
        >>> teams = get_candidate_teams("Aaron", "Kliethermes")
        >>> for t in teams:
        ...     print(t["team_name"], t["divisions"], "waitlist:", t["is_waitlist"])

    Example questions this function helps answer:
        - "Which teams has this candidate registered?"
        - "Is this coach on a waitlist for any division?"
    """
    headers, rows = _load_form_responses()
    division_col = _get_division_column(headers)
    if not division_col:
        return []

    fn_target = first_name.strip().lower()
    ln_target = last_name.strip().lower() if last_name else None
    email_target = email.strip().lower() if email else None

    results: List[Dict[str, Any]] = []

    for row in rows:
        fn = (row.get("Contact First Name") or "").strip()
        ln = (row.get("Contact Last Name") or "").strip()
        row_email = (row.get("Email Address") or "").strip().lower()

        if fn.lower() != fn_target:
            continue
        if ln_target is not None and ln.lower() != ln_target:
            continue
        if email_target is not None and row_email != email_target:
            continue

        raw_divisions = row.get(division_col)
        divisions = _parse_divisions(raw_divisions)
        waitlisted = _is_waitlisted(raw_divisions)

        results.append(
            {
                "team_name": row.get("Team Name"),
                "divisions": divisions,
                "is_waitlist": waitlisted,
                "timestamp": row.get("Timestamp"),
            }
        )

    return results

if __name__ == "__main__":
    mcp.run(transport="stdio")