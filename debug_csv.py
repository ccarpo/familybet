import csv
with open(r'd:\Temp\Kopie von WM2026-Familientipp.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f, delimiter=';')
    rows = list(reader)
    # Check row 3 (first match)
    row = rows[3]
    print('Row 3 (Mexiko vs Südafrika):')
    # Inga at col 12, so check cols 10, 11, 12, 13
    for i in range(10, 15):
        print(f'  {i}: "{row[i]}"')
    print()
    # Josef at col 16
    for i in range(14, 19):
        print(f'  {i}: "{row[i]}"')
    print()
    # Check if any of these are digits
    print(f"10 is digit: {row[10].strip().isdigit()}")
    print(f"11 is colon: {row[11].strip() == ':'}")
    print(f"13 is digit: {row[13].strip().isdigit()}")
