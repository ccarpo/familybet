"""
Convert WM2026 Excel CSV to Python dictionary.
Specifically handles the format from "Kopie von WM2026-Familientipp.csv"
"""

import csv
import re

# Users we want to import (excluding Philipp and Julius who are already done)
USERS_TO_IMPORT = ['Inga', 'Josef', 'Christiane', 'Kilian', 'Max', 'Selina']

# User column positions - will be detected from header row
# Format: name_col -> (score1_offset, score2_offset)
# Tips are at: name_col + offset pattern
USER_OFFSETS = {
    'Inga': (-1, 1),      # score1 is 1 before name col, score2 is 1 after
    'Josef': (-1, 1),
    'Christiane': (-1, 1),
    'Philipp': (-1, 1),   # SKIP
    'Julius': (-1, 1),    # SKIP
    'Miriam': (-1, 1),    # SKIP
    'Kilian': (-1, 1),
    'Max': (-1, 1),
    'Selina': (-1, 1),
}

# Will be populated from header
USER_COLUMNS = {}


def detect_user_columns(header_rows):
    """Detect user column positions from header rows."""
    global USER_COLUMNS
    USER_COLUMNS = {}

    # Look in row 1 (index 1) for user names
    if len(header_rows) > 1:
        row = header_rows[1]
        for i, val in enumerate(row):
            val = val.strip()
            if val in USERS_TO_IMPORT:
                # Found user name, check pattern around it
                # Pattern: score1, ":", score2 at name_col-2, name_col-1, name_col+1
                # Or: points at name_col+1, then score pattern
                USER_COLUMNS[val] = i

    print(f"Detected users at columns: {USER_COLUMNS}")
    return USER_COLUMNS


# Track current group across rows
_current_group = None


def parse_match_line(row):
    """Parse a match line and extract team names and tips."""
    global _current_group

    if len(row) < 10:
        return None

    # Check for group name (column 1)
    group = row[1].strip() if len(row) > 1 else ''
    if group.startswith('Gruppe'):
        _current_group = group

    # Check if this is a match row (has teams in columns 2 and 4)
    team1 = row[2].strip() if len(row) > 2 else ''
    team2 = row[4].strip() if len(row) > 4 else ''

    # Must have teams and a valid group context
    if not team1 or not team2 or not _current_group:
        return None

    # Skip if team names look like labels (e.g., "Tabelle", empty)
    if team1 in ('', '-', 'Tabelle') or team2 in ('', '-', 'Tabelle'):
        return None

    match_key = f"{team1} vs {team2}"

    # Extract tips for each user
    tips = {}
    for user in USERS_TO_IMPORT:
        if user not in USER_COLUMNS:
            continue
        name_col = USER_COLUMNS[user]

        # Pattern: score1 at name_col-1, colon at name_col, score2 at name_col+1
        score1_col = name_col - 1
        colon_col = name_col
        score2_col = name_col + 1

        if len(row) <= score2_col:
            continue

        score1 = row[score1_col].strip()
        colon = row[colon_col].strip() if len(row) > colon_col else ''
        score2 = row[score2_col].strip()

        # Validate
        if score1.isdigit() and colon == ':' and score2.isdigit():
            tips[user] = f"{score1}:{score2}"

    return {
        'match': match_key,
        'group': _current_group,
        'tips': tips
    }


def convert_csv(csv_path):
    """Convert the WM2026 CSV to Python dict format."""
    global _current_group
    _current_group = None  # Reset group tracker
    data = {}

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=';')
        rows = list(reader)

    # First, detect user columns from header (first few rows)
    header_rows = rows[:3]
    detect_user_columns(header_rows)

    # Then process match rows
    for row in rows[3:]:
        if not row or len(row) < 5:
            continue

        # Try to parse as match line
        match_data = parse_match_line(row)
        if match_data and match_data['tips']:
            data[match_data['match']] = match_data['tips']
            print(f"✓ {match_data['match']}: {match_data['tips']}")

    return data


def generate_python_code(data):
    """Generate the EXCEL_DATA Python code."""
    lines = ['EXCEL_DATA = {']

    for match, users in sorted(data.items()):
        lines.append(f'    "{match}": {{')
        for user, tip in sorted(users.items()):
            lines.append(f'        "{user}": "{tip}",')
        lines.append('    },')

    lines.append('}')

    return '\n'.join(lines)


if __name__ == '__main__':
    import sys

    csv_file = r'd:\Temp\Kopie von WM2026-Familientipp.csv'

    if len(sys.argv) > 1:
        csv_file = sys.argv[1]

    print(f"Converting: {csv_file}")
    print("="*60)

    data = convert_csv(csv_file)

    print("\n" + "="*60)
    print(f"Found {len(data)} matches with tips")
    print("="*60)

    python_code = generate_python_code(data)

    # Save to file
    output_file = csv_file.replace('.csv', '_dict.py')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(python_code)

    print(f"\n✅ Saved to: {output_file}")
    print("\n--- CONTENT ---")
    print(python_code[:2000])  # Show first 2000 chars
    print("...")
    print(f"\nTotal length: {len(python_code)} characters")
