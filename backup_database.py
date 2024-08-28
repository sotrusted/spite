import os
import sqlite3
from datetime import datetime

def backup_database(db_path, backup_dir):
    # Ensure the backup directory exists
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Get the current date and time for the backup file name
    now = datetime.now()
    backup_file = os.path.join(backup_dir, f"backup_{now.strftime('%Y%m%d_%H%M%S')}.db")

    # Connect to the source database
    conn = sqlite3.connect(db_path)

    # Use the SQLite backup API to create a backup
    with sqlite3.connect(backup_file) as backup_conn:
        conn.backup(backup_conn)

    dump_file = os.path.join(backup_dir, f"backup_{now.strftime('%Y%m%d_%H%M%S')}.sql")

    # Dump the database schema and data
    command = f"sqlite3 {db_path} .dump > {dump_file}"
    subprocess.run(command, shell=True, check=True)

    print(f"Backup created: {backup_file}")

if __name__ == "__main__":
    # Path to your SQLite database
    db_path = '/home/sargent/spite/db.sqlite3'
    # Directory where you want to store the backups
    backup_dir = '/home/sargent/spite/backups/db/'

    backup_database(db_path, backup_dir)
