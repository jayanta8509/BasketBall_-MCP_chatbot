from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sheets_client import get_default_client
from form_responses_functions import count_teams_by_division
from mcp.server.fastmcp import FastMCP

COUNT_SHEET_NAME = "Count"
mcp = FastMCP("Count_all_data")

# ---------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------

def _load_count_sheet(
    range_a1: str = "A1:E20",
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Load headers and row dictionaries from the "Count" sheet.

    Behavior:
        - Uses the default Google Sheets client configured in sheets_client.py.
        - Reads the given A1 range and converts rows into a list of dicts
          keyed by header names.

    Args:
        range_a1 (str):
            A1 range to fetch from the "Count" sheet.
            Defaults to "A1:E20".

    Returns:
        Tuple[List[str], List[dict]]:
            headers: List of column names (first row).
            rows:    List of row dictionaries {header: value}.
    """
    client = get_default_client()
    return client.get_header_and_rows(COUNT_SHEET_NAME, range_a1)


def _parse_int(value: Any) -> Optional[int]:
    """
    Internal helper:
        Safely parse an integer from a cell; return None if not possible.
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


def _parse_currency(value: Any) -> Optional[float]:
    """
    Internal helper:
        Parse a currency string like "$19,350.00" into a float (19350.00).
        Return None if it cannot be parsed.
    """
    if value is None:
        return None
    s = str(value).strip().replace(",", "").replace("$", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _is_division_row(row: Dict[str, Any]) -> bool:
    """
    Internal helper:
        Return True if this row looks like a division (e.g., "3rd Boys",
        "4th Girls"), and False for summary rows like "Total Teams" or
        "Revenue".
    """
    div = (row.get("Division") or "").strip()
    if not div:
        return False
    if div in ("Total Teams", "Revenue"):
        return False
    return True


# Public functions
@mcp.tool()
def get_division_summary(division: str) -> Optional[Dict[str, Any]]:
    """
    Purpose:
        Retrieve the summary row for a single division from the "Count" sheet,
        including number of teams, needed slots, host teams, and status flags
        like FULL or Wait List.

    Args:
        division (str):
            Division name to search for, e.g. "3rd Boys", "5th Girls".

    Returns:
        dict | None:
            A dictionary with parsed values, or None if the division is not found:
            {
                "division": str,
                "teams": int | None,
                "needed_raw": str | None,
                "needed": int | None,
                "needed_is_waitlist": bool,
                "host_teams": int | None,
                "is_full": bool,
            }

    Example usage:
        >>> info = get_division_summary("3rd Boys")
        >>> print(info)
        {'division': '3rd Boys', 'teams': 10, 'needed_raw': 'Wait List',
         'needed': None, 'needed_is_waitlist': True, 'host_teams': 5,
         'is_full': True}

    Example questions this function helps answer:
        - "How many teams are in 3rd Boys, and is it full?"
        - "For 7/8 Girls, how many teams do we still need?"
        - "Is 4th Boys already on a waitlist?"
    """
    headers, rows = _load_count_sheet()
    _ = headers  # currently unused, kept for symmetry

    results: List[Dict[str, Any]] = []

    for row in rows:
        div = (row.get("Division") or "").strip()
        if div.lower() != division.strip().lower():
            continue

        teams = _parse_int(row.get("# of Teams"))
        needed_raw = row.get("Needed")
        needed = _parse_int(needed_raw)
        host_teams = _parse_int(row.get("Host Teams"))
        status = (row.get("Unnamed: 4") or "").strip()

        results.append(
            {
                "division": div,
                "teams": teams,
                "needed_raw": needed_raw,
                "needed": needed,
                "needed_is_waitlist": isinstance(needed_raw, str)
                and "wait list" in needed_raw.lower(),
                "host_teams": host_teams,
                "is_full": status.upper() == "FULL",
            }
        )

    if not results:
        return None
    # If somehow multiple, return the first
    return results[0]

@mcp.tool()
def list_division_summaries() -> List[Dict[str, Any]]:
    """
    Purpose:
        Return a structured summary for all division rows (3rd Boys, 3rd Girls,
        ..., 7/8 Girls) in the "Count" sheet.

    Args:
        None

    Returns:
        List[dict]:
            Each entry has the same structure as get_division_summary(), e.g.:
            {
                "division": "3rd Boys",
                "teams": 10,
                "needed_raw": "Wait List",
                "needed": None,
                "needed_is_waitlist": True,
                "host_teams": 5,
                "is_full": True,
            }

    Example usage:
        >>> summaries = list_division_summaries()
        >>> for s in summaries:
        ...     print(s["division"], s["teams"], "FULL?", s["is_full"])

    Example questions this function helps answer:
        - "Give me a one-line summary for each division."
        - "Which divisions have how many teams, hosts, and remaining needed slots?"
    """
    _, rows = _load_count_sheet()
    results: List[Dict[str, Any]] = []

    for row in rows:
        if not _is_division_row(row):
            continue

        div = (row.get("Division") or "").strip()
        teams = _parse_int(row.get("# of Teams"))
        needed_raw = row.get("Needed")
        needed = _parse_int(needed_raw)
        host_teams = _parse_int(row.get("Host Teams"))
        status = (row.get("Unnamed: 4") or "").strip()

        results.append(
            {
                "division": div,
                "teams": teams,
                "needed_raw": needed_raw,
                "needed": needed,
                "needed_is_waitlist": isinstance(needed_raw, str)
                and "wait list" in needed_raw.lower(),
                "host_teams": host_teams,
                "is_full": status.upper() == "FULL",
            }
        )

    return results

@mcp.tool()
def list_full_divisions() -> List[str]:
    """
    Purpose:
        Return a list of all divisions whose status is marked as FULL in the
        "Count" sheet.

    Args:
        None

    Returns:
        List[str]:
            A list of division names that are FULL.

    Example usage:
        >>> full_divisions = list_full_divisions()
        >>> print(full_divisions)
        ['3rd Boys', '4th Boys', '5th Boys', '6th Boys']

    Example questions this function helps answer:
        - "Which divisions are already full and closed for registration?"
        - "Where are we no longer taking teams?"
    """
    summaries = list_division_summaries()
    return [s["division"] for s in summaries if s.get("is_full")]

@mcp.tool()
def list_divisions_with_waitlist() -> List[str]:
    """
    Purpose:
        Return a list of all divisions that are currently on a waiting list,
        according to the 'Needed' column containing 'Wait List' in the
        "Count" sheet.

    Args:
        None

    Returns:
        List[str]:
            Division names where 'Needed' indicates a waitlist.

    Example usage:
        >>> waitlist_divs = list_divisions_with_waitlist()
        >>> print(waitlist_divs)
        ['3rd Boys', '4th Boys']

    Example questions this function helps answer:
        - "Which divisions are already in waitlist mode?"
        - "Do any divisions have more teams than planned capacity?"
    """
    summaries = list_division_summaries()
    return [
        s["division"]
        for s in summaries
        if s.get("needed_is_waitlist")
    ]

@mcp.tool()
def list_divisions_still_needing_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all divisions that still require additional teams (where 'Needed'
        is a positive integer), ordered by how many teams they still need.

    Args:
        None

    Returns:
        List[dict]:
            Entries with at least 1 needed team, e.g.:
            {
                "division": "3rd Girls",
                "teams": 8,
                "needed": 2,
                "host_teams": 4,
            }

    Example usage:
        >>> open_divisions = list_divisions_still_needing_teams()
        >>> for d in open_divisions:
        ...     print(d["division"], "needs", d["needed"], "more teams")

    Example questions this function helps answer:
        - "Which divisions are not full yet and how many teams do they need?"
        - "Where can we still place new registrations?"
    """
    summaries = list_division_summaries()
    results: List[Dict[str, Any]] = []

    for s in summaries:
        needed = s.get("needed")
        if needed is not None and needed > 0:
            results.append(
                {
                    "division": s["division"],
                    "teams": s.get("teams"),
                    "needed": needed,
                    "host_teams": s.get("host_teams"),
                }
            )

    # sort descending by needed teams
    results.sort(key=lambda x: x["needed"], reverse=True)
    return results

@mcp.tool()
def get_overall_team_totals() -> Dict[str, Any]:
    """
    Purpose:
        Retrieve the overall totals from the "Total Teams" row of the "Count"
        sheet, including total number of teams and total host teams.

    Args:
        None

    Returns:
        dict:
            {
                "total_teams": int | None,
                "total_host_teams": int | None,
            }

    Example usage:
        >>> totals = get_overall_team_totals()
        >>> print(totals)
        {'total_teams': 79, 'total_host_teams': 36}

    Example questions this function helps answer:
        - "How many total teams are registered in the league?"
        - "How many of those are host teams?"
    """
    _, rows = _load_count_sheet()

    total_teams: Optional[int] = None
    total_host_teams: Optional[int] = None

    for row in rows:
        div = (row.get("Division") or "").strip()
        if div == "Total Teams":
            total_teams = _parse_int(row.get("# of Teams"))
            # 'Needed' column text: 'Total Host Teams', so use Host Teams column
            total_host_teams = _parse_int(row.get("Host Teams"))
            break

    return {
        "total_teams": total_teams,
        "total_host_teams": total_host_teams,
    }

@mcp.tool()
def get_revenue_summary() -> Dict[str, Optional[float]]:
    """
    Purpose:
        Parse the "Revenue" row from the "Count" sheet and return numeric
        revenue values for non-host, host, and total revenue.

    Args:
        None

    Returns:
        dict:
            {
                "non_host_revenue": float | None,
                "host_revenue": float | None,
                "total_revenue": float | None,
            }

            For the sheet example:
            {
                "non_host_revenue": 19350.00,
                "host_revenue": 8100.00,
                "total_revenue": 27450.00,
            }

    Example usage:
        >>> rev = get_revenue_summary()
        >>> print(rev)
        {'non_host_revenue': 19350.0, 'host_revenue': 8100.0, 'total_revenue': 27450.0}

    Example questions this function helps answer:
        - "What is the total projected revenue from registrations?"
        - "How much revenue comes from host vs non-host teams?"
    """
    _, rows = _load_count_sheet()

    non_host: Optional[float] = None
    host: Optional[float] = None
    total: Optional[float] = None

    for row in rows:
        div = (row.get("Division") or "").strip()
        if div == "Revenue":
            non_host = _parse_currency(row.get("Needed"))
            host = _parse_currency(row.get("Host Teams"))
            total = _parse_currency(row.get("Unnamed: 4"))
            break

    return {
        "non_host_revenue": non_host,
        "host_revenue": host,
        "total_revenue": total,
    }


# Cross-sheet consistency checks with Sheet 1
@mcp.tool()
def compare_division_team_counts_with_registrations() -> List[Dict[str, Any]]:
    """
    Purpose:
        Compare the "# of Teams" per division in the "Count" sheet with the
        actual number of team registrations in Sheet 1 ("Form Responses 1"),
        using the count_teams_by_division() helper.

        This is a validation tool to detect mismatches between the summary
        sheet and the raw registration data.

    Args:
        None

    Returns:
        List[dict]:
            One entry per division that appears in *either* sheet, with:
            {
                "division": str,
                "count_sheet_teams": int | None,
                "form_responses_teams_confirmed": int | None,
                "form_responses_teams_waitlist": int | None,
                "difference": int | None,  # count_sheet_teams - form_responses_confirmed
            }

            Only rows where at least one side has data are included. You can
            filter difference != 0 to find actual mismatches.

    Example usage:
        >>> discrepancies = compare_division_team_counts_with_registrations()
        >>> for d in discrepancies:
        ...     print(d["division"], "sheet:", d["count_sheet_teams"],
        ...           "registrations:", d["form_responses_teams_confirmed"])

    Example questions this function helps answer:
        - "Does the 'Count' sheet match the actual registration counts?"
        - "Where are our summary numbers out of sync with Sheet 1?"
    """
    # From Count sheet
    summaries = list_division_summaries()
    count_map: Dict[str, int] = {
        s["division"]: (s.get("teams") or 0) for s in summaries
    }

    # From Form Responses (Sheet 1)
    fr_counts = count_teams_by_division()
    fr_map: Dict[str, Dict[str, int]] = {
        row["division"]: {
            "confirmed": row["confirmed"],
            "waitlist": row["waitlist"],
        }
        for row in fr_counts
    }

    # Combine keys from both sources
    all_divisions = sorted(set(count_map.keys()) | set(fr_map.keys()))
    results: List[Dict[str, Any]] = []

    for div in all_divisions:
        sheet_count = count_map.get(div)
        fr_info = fr_map.get(div, {"confirmed": None, "waitlist": None})
        confirmed = fr_info["confirmed"]
        waitlist = fr_info["waitlist"]

        difference: Optional[int] = None
        if sheet_count is not None and confirmed is not None:
            difference = sheet_count - confirmed

        results.append(
            {
                "division": div,
                "count_sheet_teams": sheet_count,
                "form_responses_teams_confirmed": confirmed,
                "form_responses_teams_waitlist": waitlist,
                "difference": difference,
            }
        )

    return results

@mcp.tool()
def compare_total_teams_with_registrations() -> Dict[str, Any]:
    """
    Purpose:
        Compare the "Total Teams" value from the "Count" sheet with the sum of
        confirmed teams across all divisions in the "Form Responses 1" sheet.

    Args:
        None

    Returns:
        dict:
            {
                "total_teams_count_sheet": int | None,
                "total_confirmed_from_form_responses": int,
                "difference": int | None,  # count_sheet - confirmed
            }

    Example usage:
        >>> total_check = compare_total_teams_with_registrations()
        >>> print(total_check)
        {'total_teams_count_sheet': 79,
         'total_confirmed_from_form_responses': 79,
         'difference': 0}

    Example questions this function helps answer:
        - "Is the overall team count in the 'Count' sheet correct?"
        - "Are we missing any teams in our summary?"
    """
    totals = get_overall_team_totals()
    total_sheet = totals.get("total_teams")

    fr_counts = count_teams_by_division()
    total_confirmed = sum(row["confirmed"] for row in fr_counts)

    difference: Optional[int] = None
    if total_sheet is not None:
        difference = total_sheet - total_confirmed

    return {
        "total_teams_count_sheet": total_sheet,
        "total_confirmed_from_form_responses": total_confirmed,
        "difference": difference,
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")