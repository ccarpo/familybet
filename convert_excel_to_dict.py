"""
Convert Excel/CSV file to Python dictionary format.

Usage:
1. Save your Excel as CSV (UTF-8 encoding)
2. Run: python convert_excel_to_dict.py input.csv
3. Copy the output and paste into import_bets_from_excel.py

Expected CSV format:
Match,Philipp,Christiane,Josef,Julius,Inga,Kilian,Max,Selina
"Mexiko vs Südafrika",2:0,1:1,3:1,2:0,1:0,2:1,3:0,1:2
"Südkorea vs Tschechien",1:0,2:1,1:0,0:1,2:0,1:2,0:0,2:2
...etc...

Or with columns: Spiel, Tipper, Tipp
Spiel,Tipper,Tipp
"Mexiko vs Südafrika",Philipp,2:0
"Mexiko vs Südafrika",Christiane,1:1
...
"""

import csv
import sys


# Only import these users (exclude Philipp and Julius who are already imported)
USERS_TO_IMPORT = ['Inga', 'Josef', 'Christiane', 'Kilian', 'Max', 'Selina']


def convert_csv_to_dict_format(csv_path):
    """Convert CSV to Python dictionary string."""
    data = {}

    with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        print(f"Columns found: {headers}")

        # Check format: wide (Match + user columns) or tall (Match, User, Tip)
        if len(headers) <= 3 and 'Tipper' in headers or 'User' in headers:
            # Tall format: Spiel,Tipper,Tipp
            match_col = 'Spiel' if 'Spiel' in headers else 'Match'
            user_col = 'Tipper' if 'Tipper' in headers else 'User'
            tip_col = 'Tipp' if 'Tipp' in headers else 'Tip'

            for row in reader:
                match = row.get(match_col, '').strip()
                user = row.get(user_col, '').strip()
                tip = row.get(tip_col, '').strip()

                if match and user and tip and user in USERS_TO_IMPORT:
                    if match not in data:
                        data[match] = {}
                    data[match][user] = tip
        else:
            # Wide format: Match, User1, User2, User3...
            match_col = headers[0]  # First column is match
            user_cols = headers[1:]  # Rest are users

            for row in reader:
                match = row.get(match_col, '').strip()
                if not match:
                    continue

                data[match] = {}
                for user in user_cols:
                    if user not in USERS_TO_IMPORT:
                        continue
                    tip = row.get(user, '').strip()
                    if tip and tip not in ('-', '', 'None'):
                        data[match][user] = tip

    # Generate Python code
    lines = ['EXCEL_DATA = {']

    for match, users in data.items():
        lines.append(f'    "{match}": {{')
        for user, tip in users.items():
            lines.append(f'        "{user}": "{tip}",')
        lines.append('    },')

    lines.append('}')

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_excel_to_dict.py <csv_file>")
        print("\nExample CSV format (wide):")
        print('Match,Philipp,Christiane,Josef')
        print('"Mexiko vs Südafrika",2:0,1:1,3:1')
        print('\nExample CSV format (tall):')
        print('Spiel,Tipper,Tipp')
        print('"Mexiko vs Südafrika",Philipp,2:0')
        sys.exit(1)

    csv_file = sys.argv[1]

    if not csv_file.endswith('.csv'):
        print("⚠️ Warning: File should be a .csv file")

    try:
        result = convert_csv_to_dict_format(csv_file)
        print("\n" + "="*60)
        print("COPY THIS INTO import_bets_from_excel.py:")
        print("="*60)
        print(result)
        print("="*60)

        # Also save to file
        output_file = csv_file.replace('.csv', '_dict.py')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"\n✅ Also saved to: {output_file}")

    except FileNotFoundError:
        print(f"❌ File not found: {csv_file}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
