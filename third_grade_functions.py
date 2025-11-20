from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sheets_client import get_default_client
from form_responses_functions import (
    get_teams_by_division,
    find_registrations_by_team_name,
)
from mcp.server.fastmcp import FastMCP
THIRD_GRADE_SHEET_NAME = "3rd Grade"
mcp = FastMCP("Third_Grade_data")

# ---------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------

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


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Internal helper:
        Normalize phone numbers by stripping non-digits and returning
        a digits-only string, or None if no digits are present.
    """
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return digits or None


def _load_3rd_grade_values(
    range_a1: str = "A1:F100",
) -> List[List[Any]]:
    """
    Internal helper:
        Fetch raw values from the '3rd Grade' sheet.

    Args:
        range_a1 (str):
            A1-style range to fetch. Defaults to "A1:F100".

    Returns:
        List[List[Any]]:
            Raw 2D list of values from the sheet.
    """
    client = get_default_client()
    return client.get_values(THIRD_GRADE_SHEET_NAME, range_a1)


def _load_3rd_grade_boys_block() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Parse the '3rd Grade Boys' block.

    Actual layout in the sheet:

        Row 0: label row:
            ['3rd Grade Boys', '', '', '', '', '']
        Row 1: header row:
            ['Email', 'First Name', 'Last Name', 'Phone', 'Team Name', 'Team #']
        Rows 2..N: data rows for 3rd Grade Boys, until a completely blank row.

    This function is robust to the possibility that the sheet might *not* have
    the label row; in that case it falls back to treating Row 0 as the header.

    Returns:
        (headers, list_of_row_dicts)
    """
    values = _load_3rd_grade_values()
    if not values:
        return [], []

    # Detect if the first row is a label like "3rd Grade Boys"
    first_cell = str(values[0][0]).strip().lower() if values[0] else ""
    if first_cell == "3rd grade boys":
        header_index = 1
    else:
        header_index = 0

    if header_index >= len(values):
        return [], []

    headers = values[header_index]
    data_rows = values[header_index + 1 :]

    rows: List[Dict[str, Any]] = []
    for row in data_rows:
        # Stop at first completely empty row (this separates boys & girls blocks)
        if not any(str(c).strip() for c in row):
            break

        row_dict = {
            headers[i]: (row[i] if i < len(row) else None)
            for i in range(len(headers))
        }
        rows.append(row_dict)

    return headers, rows


def _load_3rd_grade_girls_block() -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Internal helper:
        Parse the '3rd Grade Girls' block, which looks like:

            Row N:     ['3rd Grade Girls', '', '', '', '', '']
            Row N+1:   [None, None, None, None, 'Team Name', 'Team #']
            Row N+2+:  actual data rows, with team name & number in those columns.

        We:
            - find the row where col0 == '3rd Grade Girls'
            - take the next row as header row (we care about 'Team Name' & 'Team #')
            - parse subsequent rows until a fully blank row.

    Returns:
        (headers, list_of_row_dicts)

        For the girls block we normalize to headers:
            ["Team Name", "Team #"]
    """
    values = _load_3rd_grade_values()
    if not values:
        return [], []

    girls_label_index: Optional[int] = None
    for idx, row in enumerate(values):
        if row and str(row[0]).strip().lower() == "3rd grade girls":
            girls_label_index = idx
            break

    if girls_label_index is None:
        return [], []

    header_index = girls_label_index + 1
    if header_index >= len(values):
        return [], []

    header_row = values[header_index]
    headers = header_row

    # Identify the indices for "Team Name" and "Team #"
    team_name_idx = None
    team_num_idx = None
    for i, cell in enumerate(header_row):
        label = str(cell).strip()
        if label == "Team Name":
            team_name_idx = i
        elif label == "Team #":
            team_num_idx = i

    # If we somehow can't find the columns, bail out
    if team_name_idx is None or team_num_idx is None:
        return headers, []

    data_rows = values[header_index + 1 :]
    rows: List[Dict[str, Any]] = []

    for row in data_rows:
        # Stop at completely empty row
        if not any(str(c).strip() for c in row):
            break

        team_name = row[team_name_idx] if team_name_idx < len(row) else None
        team_num = row[team_num_idx] if team_num_idx < len(row) else None

        # Skip if both are missing / empty
        if not (str(team_name).strip() or str(team_num).strip()):
            continue

        rows.append(
            {
                "Team Name": team_name,
                "Team #": team_num,
            }
        )

    # For girls, we only really care about "Team Name" and "Team #"
    return ["Team Name", "Team #"], rows


# ---------------------------------------------------------
# Core 3rd Grade Boys functions
# ---------------------------------------------------------
@mcp.tool()
def list_3rd_grade_boys_teams() -> List[Dict[str, Any]]:
    """
    Purpose:
        List all 3rd Grade Boys teams with coach/contact information and
        team number, as stored in the '3rd Grade' sheet.
    """
    headers, rows = _load_3rd_grade_boys_block()
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
def get_3rd_grade_boys_team_by_number(
    team_number: int,
) -> Optional[Dict[str, Any]]:
    boys = list_3rd_grade_boys_teams()
    for team in boys:
        if team.get("Team #") == team_number:
            return team
    return None


@mcp.tool()
def find_3rd_grade_boys_teams_by_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    boys = list_3rd_grade_boys_teams()
    q = query.strip().lower()
    results: List[Dict[str, Any]] = []

    for team in boys:
        name = (team.get("Team Name") or "").strip().lower()
        if exact:
            if name == q:
                results.append(team)
        else:
            if q in name:
                results.append(team)

    return results


# ---------------------------------------------------------
# Core 3rd Grade Girls functions
# ---------------------------------------------------------
@mcp.tool()
def list_3rd_grade_girls_teams() -> List[Dict[str, Any]]:
    headers, rows = _load_3rd_grade_girls_block()
    _ = headers
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
def get_3rd_grade_girls_team_by_number(
    team_number: int,
) -> Optional[Dict[str, Any]]:
    girls = list_3rd_grade_girls_teams()
    for team in girls:
        if team.get("Team #") == team_number:
            return team
    return None

@mcp.tool()
def find_3rd_grade_girls_teams_by_name(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    girls = list_3rd_grade_girls_teams()
    q = query.strip().lower()
    results: List[Dict[str, Any]] = []

    for team in girls:
        name = (team.get("Team Name") or "").strip().lower()
        if exact:
            if name == q:
                results.append(team)
        else:
            if q in name:
                results.append(team)

    return results



# ---------------------------------------------------------
# Combined 3rd Grade helpers
# ---------------------------------------------------------
@mcp.tool()
def list_all_3rd_grade_teams() -> List[Dict[str, Any]]:
    boys = list_3rd_grade_boys_teams()
    girls = list_3rd_grade_girls_teams()

    results: List[Dict[str, Any]] = []

    for b in boys:
        results.append(
            {
                "division": "3rd Boys",
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
                "division": "3rd Girls",
                "team_name": g.get("Team Name"),
                "team_number": g.get("Team #"),
                "coach_first_name": None,
                "coach_last_name": None,
                "coach_email": None,
                "coach_phone": None,
            }
        )

    results.sort(key=lambda x: (x["division"], x["team_number"] or 0))
    return results

@mcp.tool()
def find_3rd_grade_team_by_name_any_division(
    query: str,
    exact: bool = False,
) -> List[Dict[str, Any]]:
    all_teams = list_all_3rd_grade_teams()
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
def find_3rd_grade_empty_team_slots() -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    # Boys: we treat missing team name as "empty" only if # is present
    boys = list_3rd_grade_boys_teams()
    for b in boys:
        tn = (b.get("Team Name") or "").strip()
        num = b.get("Team #")
        if num is not None and not tn:
            results.append(
                {
                    "division": "3rd Boys",
                    "team_number": num,
                    "reason": "missing team name",
                }
            )

    # Girls
    girls = list_3rd_grade_girls_teams()
    for g in girls:
        tn = (g.get("Team Name") or "").strip()
        num = g.get("Team #")
        if num is not None and not tn:
            results.append(
                {
                    "division": "3rd Girls",
                    "team_number": num,
                    "reason": "missing team name",
                }
            )

    results.sort(key=lambda x: (x["division"], x["team_number"]))
    return results


# ---------------------------------------------------------
# Cross-sheet helpers (3rd Grade + Registrations)
# ---------------------------------------------------------
@mcp.tool()
def get_3rd_grade_team_registration_details(
    team_name: str,
    division: str,
    include_waitlist: bool = True,
) -> List[Dict[str, Any]]:
    division = division.strip()
    if division not in ("3rd Boys", "3rd Girls"):
        raise ValueError("division must be '3rd Boys' or '3rd Girls'")

    teams = get_teams_by_division(division, include_waitlist=include_waitlist)
    q = team_name.strip().lower()
    results: List[Dict[str, Any]] = []

    for t in teams:
        name = (t.get("team_name") or "").strip().lower()
        if name == q:
            results.append(t)

    return results

@mcp.tool()
def compare_3rd_grade_boys_sheet_with_registrations() -> Dict[str, Any]:
    boys_sheet = list_3rd_grade_boys_teams()
    sheet_names = sorted(
        {
            (t.get("Team Name") or "").strip()
            for t in boys_sheet
            if t.get("Team Name")
        }
    )

    reg_teams = get_teams_by_division("3rd Boys", include_waitlist=True)
    reg_names = sorted(
        {
            (t.get("team_name") or "").strip()
            for t in reg_teams
            if t.get("team_name")
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
def compare_3rd_grade_girls_sheet_with_registrations() -> Dict[str, Any]:
    girls_sheet = list_3rd_grade_girls_teams()
    sheet_names = sorted(
        {
            (t.get("Team Name") or "").strip()
            for t in girls_sheet
            if t.get("Team Name")
        }
    )

    reg_teams = get_teams_by_division("3rd Girls", include_waitlist=True)
    reg_names = sorted(
        {
            (t.get("team_name") or "").strip()
            for t in reg_teams
            if t.get("team_name")
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