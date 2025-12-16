"""Script to migrate data from CSV to Cloudflare D1 database.

Usage:
    wrangler d1 execute qanda-questions --file=schema.sql
    python migrate_to_d1.py
"""
import csv
from pathlib import Path
import sqlite3
import sys

def migrate_csv_to_d1(csv_loc):
    """Migrate CSV data to D1 database (local development version)."""
    # For local development, D1 uses SQLite
    db_path = '.wrangler/state/d1/DB.db'

    if not Path(csv_loc).exists():
        print(f"Error: CSV file not found: {csv_loc}")
        sys.exit(1)

    if not Path(db_path).exists():
        print("""Error: D1 database not found.
        Run 'wrangler d1 execute qanda-questions --file=schema.sql' first""")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(csv_loc, newline='', encoding='utf-8') as fh:
        reader = csv.reader(fh)
        # Skip header if it exists
        try:
            first_row = next(reader)
            # If first column isn't an ID number, assume it's a header
            if not first_row[0].isdigit():
                print("Skipping header row")
            else:
                # It was data, insert it
                cursor.execute(
                    'INSERT INTO questions (question, answer) VALUES (?, ?)',
                    (first_row[1], first_row[2])
                )
        except StopIteration:
            print("Warning: Empty CSV file")
            return

        # Process remaining rows
        for row in reader:
            if len(row) >= 3:  # Ensure we have ID, question, and answer
                cursor.execute(
                    'INSERT INTO questions (question, answer) VALUES (?, ?)',
                    (row[1], row[2])
                )

    conn.commit()
    print("""Migration complete.
    Run 'wrangler d1 execute qanda-questions --command=\"SELECT * FROM questions;\"' to verify.""")

if __name__ == '__main__':
    csv_path = Path(__file__).parent / 'QandA.csv'
    migrate_csv_to_d1(csv_path)
