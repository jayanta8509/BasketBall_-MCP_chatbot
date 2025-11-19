# 🏀 Basketball League Management MCP Server

An AI-powered basketball league management system built with MCP (Model Context Protocol) servers that provides comprehensive team registration, bracket management, and waitlist functionality for youth basketball leagues.

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Setup and Installation](#-setup-and-installation)
- [Available Data Sources](#-available-data-sources)
- [API Usage](#-api-usage)
- [MCP Tools Reference](#-mcp-tools-reference)
- [Example Queries](#-example-queries)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)

## 🎯 Overview

This system manages youth basketball league operations including:
- Team registrations across multiple grade divisions
- Automatic bracket assignments
- Waitlist management (manual and automatic)
- Coach and contact information management
- Revenue tracking and reporting
- Division capacity management

## ✨ Features

### 📊 Registration Management
- **Grade-Based Divisions**: 3rd-8th grade (Boys & Girls)
- **Team Registration**: Automated team assignment and capacity management
- **Contact Management**: Coach and parent contact information
- **Revenue Tracking**: $150 per team registration fee

### 🏀 Bracket Management
- **Automatic Assignment**: Teams assigned to brackets based on registration
- **Grade-Specific Brackets**: Separate brackets for each grade level
- **Position Tracking**: Track team positions within brackets
- **Division Comparison**: Compare registration counts with bracket assignments

### ⏳ Waitlist Management
- **Manual Waitlist**: Priority-based manual waitlist positions
- **Automatic Waitlist**: Teams waitlisted when divisions are full
- **Position Tracking**: Real-time waitlist position updates
- **Division-Specific Waitlists**: Separate waitlists for each division

### 📈 Analytics & Reporting
- **Division Summaries**: Comprehensive overview of all divisions
- **Team Counts**: Real-time team registration tracking
- **Revenue Reports**: Financial overview of registrations
- **Capacity Analysis**: Division capacity and availability tracking

## 🏗️ Architecture

### MCP Servers
The system consists of multiple MCP servers, each handling specific data sources:

| Server Name | Function | Data Source |
|-------------|----------|-------------|
| `Google_ALL_sheet_data` | Form Responses Management | `form_responses_functions.py` |
| `Third_Grade_data` | 3rd Grade Bracket Management | `third_grade_functions.py` |
| `Fourth_Grade_data` | 4th Grade Bracket Management | `fourth_grade_functions.py` |
| `Fifth_Grade_data` | 5th Grade Bracket Management | `fifth_grade_functions.py` |
| `Sixth_Grade_data` | 6th Grade Bracket Management | `sixth_grade_functions.py` |
| `Seventh_Eight_Grade_data` | 7th/8th Grade Bracket Management | `seventh_eighth_grade_functions.py` |
| `Waitlist_data` | Waitlist Management | `waitlist_functions.py` |
| `Count_all_data` | Summary & Analytics | `count_functions.py` |

### Frontend Applications
- **FastAPI Web App** (`app.py`): RESTful API for web integration
- **CLI Client** (`client.py`): Interactive command-line interface

## 🚀 Setup and Installation

### Prerequisites
- Python 3.8+
- MCP server runtime
- Google Sheets API access
- Environment variables configured

### Environment Variables
Create a `.env` file in the root directory:

```bash
# Google Sheets Configuration
GOOGLE_SHEETS_CREDS_JSON=path/to/credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id

# MCP Configuration
MCP_SERVER_CONFIG=server_config.json

# API Configuration
API_PORT=8032
API_HOST=0.0.0.0
```

### Installation Steps

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Basketball-MCP-chatbot
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure MCP servers**:
```bash
# Setup MCP server configuration
mcp setup
```

4. **Start the applications**:

**Option A: FastAPI Web Server**
```bash
python app.py
```
The API will be available at `http://localhost:8032`

**Option B: Interactive CLI Client**
```bash
python client.py
```

## 📚 Available Data Sources

### 📋 Form Responses (Google_ALL_sheet_data)
- **Description**: Primary team registration data
- **Fields**: Team Name, Coach Name, Email, Phone, Division, Payment Status
- **Functions**: `get_teams_by_division`, `find_registrations_by_email`, `list_contacts`

### 🏀 Grade-Specific Brackets
Each grade level (3rd-8th) has dedicated bracket management:
- **Teams**: Assigned to specific bracket positions
- **Divisions**: Separate Boys and Girls divisions
- **Functions**: `list_*_grade_*_teams`, `get_*_grade_*_team_by_number`

### ⏳ Waitlist Management (Waitlist_data)
- **Manual Waitlist**: Priority-based positioning
- **Automatic Waitlist**: Overflow team management
- **Functions**: `list_waitlist_entries`, `get_waitlist_for_division`, `get_waitlist_position_for_team`

### 📊 Summary & Analytics (Count_all_data)
- **Division Summaries**: Status overview
- **Team Totals**: Overall registration counts
- **Revenue Tracking**: Financial summary
- **Capacity Analysis**: Available spots per division

## 🔌 API Usage

### Base URL
```
http://localhost:8032
```

### Endpoints

#### Ask Question
**POST** `/api/v1/basketball/ask-question`

**Request Body**:
```json
{
  "question": "How many teams are registered in 3rd Boys?",
  "division_filter": "3rd Boys"
}
```

**Response**:
```json
{
  "answer": "There are currently 8 teams registered in the 3rd Boys division...",
  "question": "How many teams are registered in 3rd Boys?",
  "division_filter": "3rd Boys"
}
```

#### Health Check
**GET** `/health`

**Response**:
```json
{
  "status": "healthy",
  "service": "Basketball League Management API",
  "version": "1.0.0"
}
```

#### API Information
**GET** `/`

Returns comprehensive API information including available divisions and example questions.

## 🛠️ MCP Tools Reference

### 📋 Registration Tools
- `get_teams_by_division(division_name: str)`: Get all teams in a specific division
- `find_registrations_by_email(email: str)`: Find registrations by email address
- `get_waitlisted_teams(division_name: str)`: Get waitlisted teams for a division
- `list_contacts()`: Get all contact information
- `count_teams_by_division(division_name: str)`: Count teams in a division

### 🏀 Bracket Management Tools
- `list_[grade]_grade_[gender]_teams()`: List teams in specific bracket
- `get_[grade]_grade_[gender]_team_by_number(team_number: int)`: Get specific team
- `find_[grade]_grade_[gender]_teams_by_name(team_name: str)`: Find teams by name
- `compare_[grade]_grade_[gender]_sheet_with_registrations()`: Compare bracket vs registration

### ⏳ Waitlist Tools
- `list_waitlist_entries()`: Get all waitlist entries
- `get_waitlist_for_division(division_name: str)`: Division-specific waitlist
- `get_combined_waitlist_for_division(division_name: str)`: Combined waitlist data
- `get_waitlist_position_for_team(team_name: str)`: Get waitlist position

### 📊 Summary & Analytics Tools
- `get_division_summary(division_name: str)`: Get division status summary
- `list_division_summaries()`: Get all division summaries
- `get_overall_team_totals()`: Get total team counts
- `get_revenue_summary()`: Get revenue information
- `list_full_divisions()`: List full divisions
- `list_divisions_still_needing_teams()`: List divisions with openings

### 👥 Contact Management Tools
- `get_candidate_contact_by_name(candidate_name: str)`: Get contact info
- `get_candidate_profiles_by_name(candidate_name: str)`: Get detailed profiles
- `get_candidate_teams(candidate_name: str)`: Get teams for candidate
- `is_candidate_on_any_waitlist(candidate_name: str)`: Check waitlist status

## 💬 Example Queries

### Team Registration Queries
```
How many teams are registered in 3rd Boys?
Show me all teams in 5th Girls division
Which divisions have the most teams registered?
```

### Waitlist Management
```
Who is on the manual waitlist for 4th Boys?
What position is 'Eldon 3rd Grade A' on the waitlist?
Show me all waitlisted teams across all divisions
```

### Coach & Contact Information
```
What's the contact info for coach Aaron Kliethermes?
Find teams registered by coach 'John Smith'
Get phone numbers for all 6th Grade Boys coaches
```

### Division Status & Capacity
```
Which divisions are currently full?
How many more spots are available in 7th Boys?
Compare registration counts with bracket assignments
Show me divisions that still need more teams
```

### Revenue & Financial
```
What's the total revenue from registrations?
How much revenue from 4th Grade divisions?
Calculate total teams and expected revenue
```

### Comprehensive Reports
```
Generate a complete league status report
Give me a summary of all registered teams by division
Show me the bracket assignments for 5th Grade Boys
Compare registration across all divisions
```

## ⚙️ Configuration

### MCP Server Configuration
Update `mcp_config.json` with your server details:

```json
{
  "servers": {
    "Google_ALL_sheet_data": {
      "command": "python",
      "args": ["-m", "form_responses_functions"],
      "env": {
        "GOOGLE_SHEETS_SPREADSHEET_ID": "your_sheet_id"
      }
    },
    "Third_Grade_data": {
      "command": "python",
      "args": ["-m", "third_grade_functions"]
    }
    // ... other servers
  }
}
```

### Division Naming Convention
- **Format**: `{Grade} {Gender}`
- **Grades**: 3rd, 4th, 5th, 6th, 7/8
- **Genders**: Boys, Girls
- **Examples**: "3rd Boys", "4th Girls", "7/8 Boys"

## 🔧 Troubleshooting

### Common Issues

#### MCP Server Connection Failed
**Problem**: Unable to connect to MCP servers
**Solution**:
1. Check server configuration in `mcp_config.json`
2. Verify Python dependencies are installed
3. Ensure Google Sheets credentials are valid

#### Google Sheets Access Denied
**Problem**: Unable to access Google Sheets data
**Solution**:
1. Verify `GOOGLE_SHEETS_SPREADSHEET_ID` is correct
2. Check Google Sheets API permissions
3. Ensure credentials file has proper access

#### API Not Responding
**Problem**: FastAPI server not responding
**Solution**:
1. Check if port 8032 is available
2. Verify all dependencies are installed
3. Check application logs for errors

#### Waitlist Position Not Found
**Problem**: `get_waitlist_position_for_team` returns no results
**Solution**:
1. Verify team name matches exactly (case-sensitive)
2. Check if team is actually on waitlist
3. Use `list_waitlist_entries` to verify team exists

### Debug Mode
Enable debug logging by setting:
```bash
export DEBUG=true
python app.py
```

### Support
For additional support:
1. Check the application logs
2. Verify MCP server status
3. Test individual MCP functions
4. Review Google Sheets API permissions

---

## 📞 Contact Information

Jayanta Roy

---

**Version**: 1.0.0
**Last Updated**: 2025-11-19
**System**: Basketball League Management MCP Server