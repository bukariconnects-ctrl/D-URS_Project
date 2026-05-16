# peer/local_db.py
# SQLite logic for the Peer Node

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'peer_local.db')


def get_connection():
    """Return a connection to the peer local database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the database tables if they do not already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MyFiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            file_path TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def add_local_file(filename, file_hash, file_path):
    """Save a shared file record to the local database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO MyFiles (filename, file_hash, file_path) VALUES (?, ?, ?)',
        (filename, file_hash, file_path)
    )
    conn.commit()
    conn.close()
    return True


def get_local_file_path(filename):
    """Return the absolute path of a file if it exists in the local DB, else None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT file_path FROM MyFiles WHERE filename = ?',
        (filename,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['file_path']
    return None


if __name__ == '__main__':
    init_db()
    print(f"Peer database initialized at {DB_PATH}")
