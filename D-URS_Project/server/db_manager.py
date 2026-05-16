# server/db_manager.py
# SQLite logic for the Central Index Server

import sqlite3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.security import generate_token

DB_PATH = os.path.join(os.path.dirname(__file__), 'server_index.db')


def get_connection():
    """Return a connection to the server index database."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the database tables if they do not already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            session_token TEXT
        )
    ''')

    # Add 'role' column to existing tables that lack it
    try:
        cursor.execute('ALTER TABLE Users ADD COLUMN role TEXT NOT NULL DEFAULT "student"')
    except sqlite3.OperationalError:
        pass  # Column already exists

    # ── DFS: Directory Service Schema (NFS Lecture 10) ──────────────────
    # The Files table acts as the Directory Service, storing File Handles
    # (file_hash = GUID) and File Attributes (size, type, timestamps).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            owner TEXT NOT NULL DEFAULT '',
            provider_ip TEXT NOT NULL,
            provider_port INTEGER NOT NULL,
            topic TEXT,
            file_size INTEGER NOT NULL DEFAULT 0,
            file_type TEXT NOT NULL DEFAULT 'application/octet-stream',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Add 'owner' column to existing tables that lack it
    try:
        cursor.execute('ALTER TABLE Files ADD COLUMN owner TEXT NOT NULL DEFAULT ""')
    except sqlite3.OperationalError:
        pass  # Column already exists

    # DFS migrations: add file_size, file_type, created_at to existing DBs
    try:
        cursor.execute('ALTER TABLE Files ADD COLUMN file_size INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE Files ADD COLUMN file_type TEXT NOT NULL DEFAULT "application/octet-stream"')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE Files ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except sqlite3.OperationalError:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            peer_ip TEXT NOT NULL,
            peer_port INTEGER NOT NULL,
            topic TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT ''
        )
    ''')

    conn.commit()
    conn.close()

    # Seed a default admin account if no admin exists yet
    _seed_default_admin()


def _seed_default_admin():
    """Create a default admin account (admin / admin123) if none exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Users WHERE role = 'admin'")
    if cursor.fetchone() is None:
        from shared.security import hash_data
        try:
            cursor.execute(
                'INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)',
                ('admin', hash_data('admin123'), 'admin')
            )
            conn.commit()
            print("[DB] Default admin created — username: admin / password: admin123")
        except sqlite3.IntegrityError:
            pass  # Admin already exists
    conn.close()


def create_user(username, password_hash, role='student'):
    """Register a new user. Returns True on success, raises on duplicate."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)',
            (username, password_hash, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        raise Exception(f"Username '{username}' already exists.")
    finally:
        conn.close()


def authenticate_user(username, password_hash):
    """Validate credentials and return a new session token."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id FROM Users WHERE username = ? AND password_hash = ?',
        (username, password_hash)
    )
    user = cursor.fetchone()
    if user is None:
        conn.close()
        raise Exception("Invalid username or password.")
    token = generate_token()
    cursor.execute(
        'UPDATE Users SET session_token = ? WHERE id = ?',
        (token, user['id'])
    )
    conn.commit()
    conn.close()
    return token


def get_user_by_username(username):
    """Return user dict (id, username, role) or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, role FROM Users WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def verify_token(token):
    """Check whether a session token is valid. Returns True or False."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id FROM Users WHERE session_token = ?',
        (token,)
    )
    user = cursor.fetchone()
    conn.close()
    return user is not None


def add_file(token, filename, file_hash, provider_ip, provider_port, topic,
             owner='', file_size=0, file_type='application/octet-stream'):
    """Register a file in the Directory Service. Requires a valid session token.
    DFS: This is analogous to creating an entry in the NFS Directory Service."""
    if not verify_token(token):
        raise Exception("Authentication failed: invalid session token.")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO Files (filename, file_hash, owner, provider_ip, provider_port, topic, file_size, file_type) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (filename, file_hash, owner, provider_ip, provider_port, topic, file_size, file_type)
    )
    conn.commit()
    conn.close()
    return True


def add_file_direct(filename, file_hash, owner, provider_ip, provider_port, topic,
                    file_size=0, file_type='application/octet-stream'):
    """Register a file in the Directory Service (unified web app, no token).
    DFS: Stores the File Handle (hash) and File Attributes (size, type)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO Files (filename, file_hash, owner, provider_ip, provider_port, topic, file_size, file_type) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (filename, file_hash, owner, provider_ip, provider_port, topic, file_size, file_type)
    )
    conn.commit()
    conn.close()
    return True


def search_file(token, filename):
    """Search for providers of a file by name. Requires a valid session token."""
    if not verify_token(token):
        raise Exception("Authentication failed: invalid session token.")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT filename, file_hash, owner, provider_ip, provider_port, topic, '
        'file_size, file_type, created_at FROM Files WHERE filename LIKE ?',
        (f'%{filename}%',)
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def search_file_direct(query):
    """Search files without token (used by unified web app).
    DFS: This is the Directory Service lookup returning File Handles + Attributes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, filename, file_hash, owner, provider_ip, provider_port, topic, '
        'file_size, file_type, created_at FROM Files WHERE filename LIKE ?',
        (f'%{query}%',)
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_files_by_owner(username):
    """Return files shared by a specific user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, filename, file_hash, provider_ip, provider_port, topic, '
        'file_size, file_type, created_at FROM Files WHERE owner = ?',
        (username,)
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def add_subscription(peer_ip, peer_notify_port, topic):
    """Save a peer's subscription to a topic."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO Subscriptions (peer_ip, peer_port, topic) VALUES (?, ?, ?)',
        (peer_ip, peer_notify_port, topic)
    )
    conn.commit()
    conn.close()
    return True


def add_subscription_by_user(username, topic):
    """Save a user subscription (uses username as peer_ip for unified web app)."""
    conn = get_connection()
    cursor = conn.cursor()
    # Avoid duplicates
    cursor.execute(
        'SELECT id FROM Subscriptions WHERE peer_ip = ? AND topic = ?',
        (username, topic)
    )
    if cursor.fetchone() is None:
        cursor.execute(
            'INSERT INTO Subscriptions (peer_ip, peer_port, topic) VALUES (?, ?, ?)',
            (username, 0, topic)
        )
        conn.commit()
    conn.close()
    return True


def remove_subscription_by_user(username, topic):
    """Remove a user's subscription to a topic."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM Subscriptions WHERE peer_ip = ? AND topic = ?',
        (username, topic)
    )
    conn.commit()
    conn.close()
    return True


def get_user_subscriptions(username):
    """Return list of topics a user is subscribed to."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT topic FROM Subscriptions WHERE peer_ip = ?', (username,))
    results = [row['topic'] for row in cursor.fetchall()]
    conn.close()
    return results


def get_files_by_topics(topic_list):
    """Return all files whose topic is in the given list."""
    if not topic_list:
        return []
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ','.join('?' for _ in topic_list)
    cursor.execute(
        f'SELECT id, filename, file_hash, owner, provider_ip, provider_port, topic, '
        f'file_size, file_type, created_at FROM Files WHERE topic IN ({placeholders})',
        topic_list
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_subscribers(topic):
    """Return a list of (peer_ip, peer_port) tuples for all subscribers of a topic."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT peer_ip, peer_port FROM Subscriptions WHERE topic = ?',
        (topic,)
    )
    results = [(row['peer_ip'], row['peer_port']) for row in cursor.fetchall()]
    conn.close()
    return results


def add_notification(username, message):
    """Store a notification for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO Notifications (username, message) VALUES (?, ?)',
        (username, message)
    )
    conn.commit()
    conn.close()


def get_notifications(username):
    """Return all notifications for a user, newest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, message, created_at FROM Notifications WHERE username = ? ORDER BY id DESC',
        (username,)
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_all_users():
    """Return a list of all users (id, username, role — no sensitive data)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, role FROM Users')
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_all_files():
    """Return a list of all indexed files.
    DFS: This returns the full Directory Service listing with File Attributes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, filename, file_hash, owner, provider_ip, provider_port, topic, '
        'file_size, file_type, created_at FROM Files'
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_all_subscriptions():
    """Return a list of all subscriptions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, peer_ip, peer_port, topic FROM Subscriptions')
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def add_topic(name, description=''):
    """Add an approved topic/category (admin use). Returns True or raises on duplicate."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO Topics (name, description) VALUES (?, ?)',
            (name.strip(), description.strip())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        raise Exception(f"Topic '{name}' already exists.")
    finally:
        conn.close()


def get_all_topics():
    """Return a list of all approved topics."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, description FROM Topics ORDER BY name')
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def delete_topic(topic_id):
    """Delete a topic by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Topics WHERE id = ?', (topic_id,))
    conn.commit()
    conn.close()
    return True


def validate_topic(topic_name):
    """Check whether a topic name exists in the approved Topics table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM Topics WHERE name = ?', (topic_name,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


# ── File Management: Owner-based CRUD Operations ────────────────────────────

def delete_file_by_owner(file_id, owner):
    """Delete a file from the Directory Service only if the requester is the owner.
    DFS: Simulates access control — only the file owner can remove directory entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM Files WHERE id = ? AND owner = ?', (file_id, owner))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return False
    cursor.execute('DELETE FROM Files WHERE id = ? AND owner = ?', (file_id, owner))
    conn.commit()
    conn.close()
    return True


def get_file_by_id(file_id):
    """Return a single file record by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, filename, file_hash, owner, provider_ip, provider_port, topic, '
        'file_size, file_type, created_at FROM Files WHERE id = ?',
        (file_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ── DFS: NFS-Inspired Directory Service Operations ──────────────────────────
# The following functions simulate the NFS Directory Service API (Lecture 10).
# - nfs_lookup: Maps filename → File Handle (GUID) + File Attributes
# - Access Control: Only authenticated users can perform lookups (ACL simulation)

def nfs_lookup(token, filename):
    """NFS Directory Service: Lookup operation.
    Given a filename, returns the File Handle (SHA-256 hash = GUID) and
    File Attributes (size, type, owner, creation time) as per NFS Lecture 10.
    Access Control: Requires a valid session token (ACL check)."""
    if not verify_token(token):
        raise Exception("Access Denied: Invalid session token (ACL check failed).")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT file_hash, filename, owner, provider_ip, provider_port, topic, '
        'file_size, file_type, created_at FROM Files WHERE filename LIKE ?',
        (f'%{filename}%',)
    )
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        r = dict(row)
        # DFS: The file_hash serves as the unique File Handle (GUID)
        results.append({
            "file_handle": r['file_hash'],       # NFS File Handle (GUID)
            "attributes": {                      # NFS File Attributes (fattr)
                "filename": r['filename'],
                "owner": r['owner'],
                "file_size": r['file_size'],
                "file_type": r['file_type'],
                "created_at": r['created_at'],
                "topic": r['topic'],
            },
            "location": {                        # Flat File Service address
                "provider_ip": r['provider_ip'],
                "provider_port": r['provider_port'],
            }
        })
    return results


def nfs_lookup_by_handle(token, file_handle):
    """NFS Flat File Service: Read operation by File Handle.
    Given a File Handle (SHA-256 GUID), returns the file's attributes and location.
    Access Control: Requires a valid session token (ACL check)."""
    if not verify_token(token):
        raise Exception("Access Denied: Invalid session token (ACL check failed).")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT file_hash, filename, owner, provider_ip, provider_port, topic, '
        'file_size, file_type, created_at FROM Files WHERE file_hash = ?',
        (file_handle,)
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    r = dict(row)
    return {
        "file_handle": r['file_hash'],
        "attributes": {
            "filename": r['filename'],
            "owner": r['owner'],
            "file_size": r['file_size'],
            "file_type": r['file_type'],
            "created_at": r['created_at'],
            "topic": r['topic'],
        },
        "location": {
            "provider_ip": r['provider_ip'],
            "provider_port": r['provider_port'],
        }
    }


if __name__ == '__main__':
    init_db()
    print(f"Server database initialized at {DB_PATH}")
