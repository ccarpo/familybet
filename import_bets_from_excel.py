"""
Import bets from Excel/CSV data.
Run: python import_bets_from_excel.py

Expected data format (CSV or Python dict):
- Rows: Matches (format: "Team1 vs Team2")
- Columns: Users (Philipp, Christiane, Josef, Julius, Inga, Kilian, Max, Selina)
- Cells: Tips in format "1:0", "2:1", etc. or "-" for no tip
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Match, Bet
from datetime import datetime


# Only import these users (Philipp and Julius already have bets)
USERS_TO_IMPORT = ['Inga', 'Josef', 'Christiane', 'Kilian', 'Max', 'Selina']


def parse_tip(tip_str):
    """Parse tip string like '1:0' or '2:1' into (score1, score2)."""
    if not tip_str or tip_str.strip() in ('-', '', 'None', None):
        return None, None
    try:
        parts = tip_str.strip().split(':')
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        pass
    return None, None


def find_match(team1_name, team2_name, matches):
    """Find match by team names (fuzzy match)."""
    for match in matches:
        # Direct match
        if (match.team1_name == team1_name and match.team2_name == team2_name):
            return match
        # Reversed match (in case Excel has different order)
        if (match.team2_name == team1_name and match.team1_name == team2_name):
            return match
        # Partial match for team names
        t1_lower = team1_name.lower()
        t2_lower = team2_name.lower()
        m1_lower = match.team1_name.lower()
        m2_lower = match.team2_name.lower()
        if (t1_lower in m1_lower or m1_lower in t1_lower) and \
           (t2_lower in m2_lower or m2_lower in t2_lower):
            return match
    return None


def import_bets(data_dict):
    """
    Import bets from dictionary.

    Example data_dict:
    {
        "Mexiko vs Südafrika": {
            "Philipp": "2:0",
            "Christiane": "1:1",
            "Josef": "3:1",
            ...
        },
        ...
    }
    """
    app = create_app()

    with app.app_context():
        # Load all users
        users = {u.name: u for u in User.query.all()}
        print(f"Found users: {list(users.keys())}")

        # Load all matches
        matches = Match.query.all()
        print(f"Found {len(matches)} matches")

        imported_count = 0
        skipped_count = 0

        for match_key, user_tips in data_dict.items():
            # Parse match key
            if ' vs ' in match_key:
                parts = match_key.split(' vs ')
                team1, team2 = parts[0].strip(), parts[1].strip()
            elif ' - ' in match_key:
                parts = match_key.split(' - ')
                team1, team2 = parts[0].strip(), parts[1].strip()
            else:
                print(f"⚠️ Cannot parse match: {match_key}")
                continue

            # Find match in database
            match = find_match(team1, team2, matches)
            if not match:
                print(f"⚠️ Match not found: {team1} vs {team2}")
                continue

            print(f"\n🎯 {match.team1_name} vs {match.team2_name} (ID: {match.id})")

            for user_name, tip_str in user_tips.items():
                # Skip if not in whitelist
                if user_name not in USERS_TO_IMPORT:
                    continue

                # Find user
                user = users.get(user_name)
                if not user:
                    print(f"   ⚠️ User not found: {user_name}")
                    continue

                # Parse tip
                score1, score2 = parse_tip(tip_str)
                if score1 is None:
                    print(f"   ⏭️ {user_name}: no tip ('{tip_str}')")
                    continue

                # Check for existing bet
                existing = Bet.query.filter_by(
                    user_id=user.id,
                    match_id=match.id
                ).first()

                if existing:
                    # Update existing bet
                    existing.team1_score_pred = score1
                    existing.team2_score_pred = score2
                    existing.updated_at = datetime.utcnow()
                    print(f"   ✏️ {user_name}: updated to {score1}:{score2}")
                else:
                    # Create new bet
                    new_bet = Bet(
                        user_id=user.id,
                        match_id=match.id,
                        team1_score_pred=score1,
                        team2_score_pred=score2
                    )
                    db.session.add(new_bet)
                    print(f"   ✨ {user_name}: new tip {score1}:{score2}")

                imported_count += 1

        # Commit all changes
        db.session.commit()
        print(f"\n✅ Done! Imported {imported_count} bets, skipped {skipped_count}")


# DATA FROM YOUR EXCEL
# Copy-paste your data here or read from CSV
EXCEL_DATA = {
    "Algerien vs Österreich": {
        "Christiane": "1:2",
        "Inga": "1:3",
        "Josef": "1:1",
        "Kilian": "1:2",
        "Max": "1:2",
        "Selina": "1:2",
    },
    "Argentinien vs Algerien": {
        "Christiane": "3:1",
        "Inga": "4:2",
        "Josef": "3:1",
        "Kilian": "2:1",
        "Max": "2:1",
        "Selina": "2:1",
    },
    "Argentinien vs Österreich": {
        "Christiane": "2:1",
        "Inga": "2:2",
        "Josef": "3:1",
        "Kilian": "1:1",
        "Max": "2:1",
        "Selina": "3:1",
    },
    "Australien vs Türkei": {
        "Christiane": "0:1",
        "Inga": "2:2",
        "Josef": "1:2",
        "Kilian": "0:2",
        "Max": "1:2",
        "Selina": "0:2",
    },
    "Belgien vs Iran": {
        "Christiane": "2:0",
        "Inga": "1:3",
        "Josef": "3:0",
        "Kilian": "3:1",
        "Max": "2:0",
        "Selina": "2:1",
    },
    "Belgien vs Ägypten": {
        "Christiane": "2:1",
        "Inga": "1:1",
        "Josef": "2:1",
        "Kilian": "2:0",
        "Max": "3:1",
        "Selina": "2:0",
    },
    "Bosnien-Herz. vs Katar": {
        "Christiane": "2:0",
        "Inga": "2:1",
        "Josef": "0:1",
        "Kilian": "2:1",
        "Max": "1:0",
        "Selina": "2:0",
    },
    "Brasilien vs Haiti": {
        "Christiane": "3:0",
        "Inga": "5:1",
        "Josef": "4:0",
        "Kilian": "2:1",
        "Max": "5:0",
        "Selina": "4:1",
    },
    "Brasilien vs Marokko": {
        "Christiane": "1:1",
        "Inga": "1:0",
        "Josef": "3:1",
        "Kilian": "3:0",
        "Max": "1:2",
        "Selina": "2:1",
    },
    "Curacao vs Elfenbeinküste": {
        "Christiane": "0:2",
        "Inga": "0:0",
        "Josef": "0:6",
        "Kilian": "0:2",
        "Max": "0:2",
        "Selina": "0:2",
    },
    "DR Kongo vs Usbekistan": {
        "Christiane": "1:1",
        "Inga": "0:0",
        "Josef": "3:1",
        "Kilian": "1:1",
        "Max": "1:0",
        "Selina": "1:1",
    },
    "Deutschland vs Curacao": {
        "Christiane": "3:1",
        "Inga": "3:0",
        "Josef": "4:0",
        "Kilian": "2:0",
        "Max": "3:0",
        "Selina": "4:0",
    },
    "Deutschland vs Elfenbeinküste": {
        "Christiane": "2:1",
        "Inga": "5:2",
        "Josef": "1:1",
        "Kilian": "1:0",
        "Max": "2:2",
        "Selina": "2:2",
    },
    "Ecuador vs Curacao": {
        "Christiane": "2:0",
        "Inga": "2:1",
        "Josef": "4:0",
        "Kilian": "2:1",
        "Max": "2:0",
        "Selina": "3:1",
    },
    "Ecuador vs Deutschland": {
        "Christiane": "1:1",
        "Inga": "2:3",
        "Josef": "1:2",
        "Kilian": "2:2",
        "Max": "1:2",
        "Selina": "1:2",
    },
    "Elfenbeinküste vs Ecuador": {
        "Christiane": "0:1",
        "Inga": "1:1",
        "Josef": "3:2",
        "Kilian": "1:2",
        "Max": "2:1",
        "Selina": "2:3",
    },
    "England vs Ghana": {
        "Christiane": "3:1",
        "Inga": "4:1",
        "Josef": "3:0",
        "Kilian": "2:1",
        "Max": "1:1",
        "Selina": "2:0",
    },
    "England vs Kroatien": {
        "Christiane": "2:1",
        "Inga": "2:2",
        "Josef": "2:1",
        "Kilian": "1:1",
        "Max": "2:1",
        "Selina": "3:1",
    },
    "Frankreich vs Irak": {
        "Christiane": "3:0",
        "Inga": "3:1",
        "Josef": "3:1",
        "Kilian": "3:0",
        "Max": "3:1",
        "Selina": "3:1",
    },
    "Frankreich vs Senegal": {
        "Christiane": "2:1",
        "Inga": "3:2",
        "Josef": "2:1",
        "Kilian": "3:1",
        "Max": "2:0",
        "Selina": "2:1",
    },
    "Ghana vs Panama": {
        "Christiane": "2:0",
        "Inga": "0:0",
        "Josef": "2:0",
        "Kilian": "2:1",
        "Max": "2:1",
        "Selina": "1:2",
    },
    "Haiti vs Schottland": {
        "Christiane": "0:2",
        "Inga": "0:3",
        "Josef": "0:2",
        "Kilian": "0:1",
        "Max": "0:2",
        "Selina": "0:2",
    },
    "Irak vs Norwegen": {
        "Christiane": "0:3",
        "Inga": "0:1",
        "Josef": "0:3",
        "Kilian": "0:2",
        "Max": "0:2",
        "Selina": "0:2",
    },
    "Iran vs Neuseeland": {
        "Christiane": "2:0",
        "Inga": "2:1",
        "Josef": "0:2",
        "Kilian": "2:0",
        "Max": "1:2",
        "Selina": "1:0",
    },
    "Japan vs Schweden": {
        "Christiane": "2:1",
        "Inga": "1:1",
        "Josef": "1:2",
        "Kilian": "2:1",
        "Max": "2:2",
        "Selina": "2:1",
    },
    "Jordanien vs Algerien": {
        "Christiane": "0:1",
        "Inga": "1:1",
        "Josef": "2:3",
        "Kilian": "0:2",
        "Max": "0:1",
        "Selina": "0:2",
    },
    "Jordanien vs Argentinien": {
        "Christiane": "0:3",
        "Inga": "2:3",
        "Josef": "1:2",
        "Kilian": "0:3",
        "Max": "0:3",
        "Selina": "0:3",
    },
    "Kanada vs Bosnien-Herz.": {
        "Christiane": "2:1",
        "Inga": "1:1",
        "Josef": "1:2",
        "Kilian": "1:1",
        "Max": "2:0",
        "Selina": "2:1",
    },
    "Kanada vs Katar": {
        "Christiane": "2:0",
        "Inga": "3:0",
        "Josef": "2:2",
        "Kilian": "1:1",
        "Max": "2:1",
        "Selina": "2:1",
    },
    "Kap Verde vs Saudi-Arabien": {
        "Christiane": "1:2",
        "Inga": "1:1",
        "Josef": "1:4",
        "Kilian": "0:1",
        "Max": "0:1",
        "Selina": "0:1",
    },
    "Katar vs Schweiz": {
        "Christiane": "0:2",
        "Inga": "1:3",
        "Josef": "0:2",
        "Kilian": "0:1",
        "Max": "0:3",
        "Selina": "0:2",
    },
    "Kolumbien vs DR Kongo": {
        "Christiane": "2:0",
        "Inga": "1:1",
        "Josef": "3:0",
        "Kilian": "3:1",
        "Max": "2:1",
        "Selina": "2:1",
    },
    "Kolumbien vs Portugal": {
        "Christiane": "1:1",
        "Inga": "2:2",
        "Josef": "2:4",
        "Kilian": "1:2",
        "Max": "1:2",
        "Selina": "2:3",
    },
    "Kroatien vs Ghana": {
        "Christiane": "1:1",
        "Inga": "1:1",
        "Josef": "1:0",
        "Kilian": "2:1",
        "Max": "2:1",
        "Selina": "2:1",
    },
    "Marokko vs Haiti": {
        "Christiane": "2:1",
        "Inga": "0:0",
        "Josef": "3:0",
        "Kilian": "3:1",
        "Max": "4:0",
        "Selina": "3:0",
    },
    "Mexiko vs Südafrika": {
        "Christiane": "2:1",
        "Inga": "3:1",
        "Josef": "2:0",
        "Kilian": "2:0",
        "Max": "2:1",
        "Selina": "2:0",
    },
    "Mexiko vs Südkorea": {
        "Christiane": "1:1",
        "Inga": "3:3",
        "Josef": "3:1",
        "Kilian": "1:1",
        "Max": "1:1",
        "Selina": "3:1",
    },
    "Neuseeland vs Belgien": {
        "Christiane": "0:3",
        "Inga": "1:0",
        "Josef": "0:2",
        "Kilian": "0:3",
        "Max": "0:2",
        "Selina": "0:3",
    },
    "Neuseeland vs Ägypten": {
        "Christiane": "1:2",
        "Inga": "2:0",
        "Josef": "0:1",
        "Kilian": "0:2",
        "Max": "1:1",
        "Selina": "1:2",
    },
    "Niederlande vs Japan": {
        "Christiane": "1:1",
        "Inga": "3:3",
        "Josef": "2:0",
        "Kilian": "2:1",
        "Max": "2:1",
        "Selina": "2:2",
    },
    "Niederlande vs Schweden": {
        "Christiane": "2:1",
        "Inga": "3:3",
        "Josef": "3:2",
        "Kilian": "2:1",
        "Max": "2:1",
        "Selina": "1:0",
    },
    "Norwegen vs Frankreich": {
        "Christiane": "1:2",
        "Inga": "3:3",
        "Josef": "1:2",
        "Kilian": "1:2",
        "Max": "1:2",
        "Selina": "1:2",
    },
    "Norwegen vs Senegal": {
        "Christiane": "1:1",
        "Inga": "2:0",
        "Josef": "2:1",
        "Kilian": "2:2",
        "Max": "1:2",
        "Selina": "2:1",
    },
    "Panama vs England": {
        "Christiane": "0:3",
        "Inga": "0:1",
        "Josef": "0:5",
        "Kilian": "0:3",
        "Max": "0:2",
        "Selina": "0:2",
    },
    "Panama vs Kroatien": {
        "Christiane": "0:2",
        "Inga": "2:2",
        "Josef": "0:2",
        "Kilian": "0:2",
        "Max": "0:2",
        "Selina": "1:2",
    },
    "Paraguay vs Australien": {
        "Christiane": "1:1",
        "Inga": "0:2",
        "Josef": "1:2",
        "Kilian": "2:1",
        "Max": "2:2",
        "Selina": "2:1",
    },
    "Portugal vs DR Kongo": {
        "Christiane": "2:0",
        "Inga": "3:1",
        "Josef": "4:1",
        "Kilian": "3:0",
        "Max": "2:0",
        "Selina": "3:0",
    },
    "Portugal vs Usbekistan": {
        "Christiane": "2:0",
        "Inga": "2:0",
        "Josef": "3:1",
        "Kilian": "2:0",
        "Max": "2:0",
        "Selina": "2:0",
    },
    "Saudi-Arabien vs Uruguay": {
        "Christiane": "1:2",
        "Inga": "1:1",
        "Josef": "2:4",
        "Kilian": "0:3",
        "Max": "1:4",
        "Selina": "1:2",
    },
    "Schottland vs Brasilien": {
        "Christiane": "1:2",
        "Inga": "3:2",
        "Josef": "1:3",
        "Kilian": "0:2",
        "Max": "0:3",
        "Selina": "1:3",
    },
    "Schottland vs Marokko": {
        "Christiane": "0:2",
        "Inga": "1:1",
        "Josef": "1:2",
        "Kilian": "1:2",
        "Max": "1:1",
        "Selina": "0:1",
    },
    "Schweden vs Tunesien": {
        "Christiane": "2:0",
        "Inga": "4:2",
        "Josef": "1:1",
        "Kilian": "3:0",
        "Max": "2:1",
        "Selina": "2:1",
    },
    "Schweiz vs Bosnien-Herz.": {
        "Christiane": "2:1",
        "Inga": "2:2",
        "Josef": "3:1",
        "Kilian": "2:1",
        "Max": "2:1",
        "Selina": "3:1",
    },
    "Schweiz vs Kanada": {
        "Christiane": "1:1",
        "Inga": "1:1",
        "Josef": "1:0",
        "Kilian": "1:0",
        "Max": "1:1",
        "Selina": "1:0",
    },
    "Senegal vs Irak": {
        "Christiane": "2:0",
        "Inga": "0:0",
        "Josef": "3:1",
        "Kilian": "2:0",
        "Max": "1:1",
        "Selina": "2:0",
    },
    "Spanien vs Kap Verde": {
        "Christiane": "3:0",
        "Inga": "3:1",
        "Josef": "5:0",
        "Kilian": "3:0",
        "Max": "5:0",
        "Selina": "4:0",
    },
    "Spanien vs Saudi-Arabien": {
        "Christiane": "2:0",
        "Inga": "3:2",
        "Josef": "3:1",
        "Kilian": "2:0",
        "Max": "3:0",
        "Selina": "2:0",
    },
    "Südafrika vs Südkorea": {
        "Christiane": "0:2",
        "Inga": "0:2",
        "Josef": "2:1",
        "Kilian": "1:2",
        "Max": "0:1",
        "Selina": "0:2",
    },
    "Südkorea vs Tschechien": {
        "Christiane": "1:1",
        "Inga": "2:0",
        "Josef": "0:1",
        "Kilian": "1:1",
        "Max": "2:0",
        "Selina": "2:1",
    },
    "Tschechien vs Mexiko": {
        "Christiane": "1:2",
        "Inga": "1:2",
        "Josef": "1:1",
        "Kilian": "1:1",
        "Max": "1:3",
        "Selina": "1:2",
    },
    "Tschechien vs Südafrika": {
        "Christiane": "2:0",
        "Inga": "2:2",
        "Josef": "2:2",
        "Kilian": "2:1",
        "Max": "2:1",
        "Selina": "1:0",
    },
    "Tunesien vs Japan": {
        "Christiane": "0:2",
        "Inga": "0:2",
        "Josef": "2:1",
        "Kilian": "0:2",
        "Max": "1:2",
        "Selina": "0:2",
    },
    "Tunesien vs Niederlande": {
        "Christiane": "0:3",
        "Inga": "0:2",
        "Josef": "1:2",
        "Kilian": "0:2",
        "Max": "1:2",
        "Selina": "1:3",
    },
    "Türkei vs Paraguay": {
        "Christiane": "2:1",
        "Inga": "3:0",
        "Josef": "1:1",
        "Kilian": "1:1",
        "Max": "2:1",
        "Selina": "3:1",
    },
    "Türkei vs USA": {
        "Christiane": "1:1",
        "Inga": "2:2",
        "Josef": "1:1",
        "Kilian": "0:1",
        "Max": "1:1",
        "Selina": "2:2",
    },
    "USA vs Australien": {
        "Christiane": "3:0",
        "Inga": "1:2",
        "Josef": "2:0",
        "Kilian": "1:1",
        "Max": "2:2",
        "Selina": "1:0",
    },
    "USA vs Paraguay": {
        "Christiane": "2:1",
        "Inga": "1:0",
        "Josef": "2:1",
        "Kilian": "2:1",
        "Max": "2:1",
        "Selina": "2:1",
    },
    "Uruguay vs Kap Verde": {
        "Christiane": "2:0",
        "Inga": "0:0",
        "Josef": "4:0",
        "Kilian": "2:0",
        "Max": "4:0",
        "Selina": "3:1",
    },
    "Uruguay vs Spanien": {
        "Christiane": "1:1",
        "Inga": "0:3",
        "Josef": "1:2",
        "Kilian": "1:1",
        "Max": "2:3",
        "Selina": "1:2",
    },
    "Usbekistan vs Kolumbien": {
        "Christiane": "1:2",
        "Inga": "1:1",
        "Josef": "1:3",
        "Kilian": "0:2",
        "Max": "0:2",
        "Selina": "0:2",
    },
    "Ägypten vs Iran": {
        "Christiane": "1:1",
        "Inga": "2:2",
        "Josef": "2:0",
        "Kilian": "2:1",
        "Max": "1:0",
        "Selina": "1:0",
    },
    "Österreich vs Jordanien": {
        "Christiane": "2:0",
        "Inga": "3:0",
        "Josef": "2:0",
        "Kilian": "2:0",
        "Max": "2:0",
        "Selina": "2:0",
    },
}


def read_from_csv(csv_file_path):
    """Read data from CSV file."""
    import csv
    data = {}
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            match_key = row.get('Match', row.get('Spiel', ''))
            if match_key:
                data[match_key] = {k: v for k, v in row.items() if k not in ('Match', 'Spiel') and v}
    return data


if __name__ == '__main__':
    # Option 1: Use hardcoded data above
    if EXCEL_DATA:
        print("Importing from EXCEL_DATA constant...")
        import_bets(EXCEL_DATA)

    # Option 2: Read from CSV file
    # csv_path = input("Enter CSV file path (or press Enter to skip): ").strip()
    # if csv_path and os.path.exists(csv_path):
    #     data = read_from_csv(csv_path)
    #     import_bets(data)
    else:
        print("\n⚠️ EXCEL_DATA is empty!")
        print("Please fill the EXCEL_DATA dictionary with your data.")
        print("\nExample format:")
        print('"Mexiko vs Südafrika": {')
        print('    "Philipp": "2:0",')
        print('    "Christiane": "1:1",')
        print('    ...')
        print('}')
