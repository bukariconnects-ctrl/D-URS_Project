# server/web_service.py
# Unified Web Application with Role-Based Access Control (RBAC)
# Serves Admin Dashboard + Student Portal on a single Flask instance

import os
import sys
import socket
import ssl
import threading
import functools
import tempfile
import mimetypes
import shutil

from flask import (
    Flask, jsonify, render_template, request,
    redirect, url_for, flash, session, send_file
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from server import db_manager
from shared.security import hash_data, hash_file
from shared.config import SERVER_IP

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SERVER_DIR)
STORAGE_DIR = os.path.join(PROJECT_DIR, 'storage', 'peers')
# ── High Availability: Server-side Backup Storage ────────────────────────
# A secondary copy of every shared file is stored here, named by its
# File Handle (SHA-256 hash). If the original peer goes offline, the
# server serves the file from this backup (Replication for fault tolerance).
BACKUP_DIR = os.path.join(SERVER_DIR, 'storage', 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)
CERT_DIR = os.path.join(SERVER_DIR, 'certs')
CERT_FILE = os.path.join(CERT_DIR, 'server_cert.pem')
KEY_FILE = os.path.join(CERT_DIR, 'server_key.pem')
CHUNK_SIZE = 4096

app = Flask(
    __name__,
    template_folder=os.path.join(SERVER_DIR, 'templates'),
    static_folder=os.path.join(SERVER_DIR, 'static'),
)
app.secret_key = 'durs-unified-secret-key-2026'

# ── Virtual Peer Node Registry ──────────────────────────────────────
# Maps username -> { 'ip': ..., 'port': ..., 'thread': ... }
virtual_peers = {}


# ── SSL Certificate Generation ──────────────────────────────────────
def _generate_ssl_cert():
    """Generate a self-signed SSL cert for P2P socket transfers."""
    os.makedirs(CERT_DIR, exist_ok=True)
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u"D-URS Server"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject).issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .sign(key, hashes.SHA256())
        )
        with open(KEY_FILE, 'wb') as f:
            f.write(key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            ))
        with open(CERT_FILE, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
    except ImportError:
        os.system(
            f'openssl req -x509 -newkey rsa:2048 -keyout "{KEY_FILE}" '
            f'-out "{CERT_FILE}" -days 365 -nodes -subj "/CN=D-URS Server"'
        )


# ── Virtual Peer P2P Socket Server (per-user) ───────────────────────
def _handle_p2p_client(conn, addr, username):
    """Handle an incoming P2P file request for a virtual peer."""
    try:
        filename = conn.recv(1024).decode('utf-8').strip()
        if not filename:
            conn.close()
            return
        user_dir = os.path.join(STORAGE_DIR, username)
        file_path = os.path.join(user_dir, filename)
        if not os.path.exists(file_path):
            conn.sendall(b'ERROR: File not found')
            conn.close()
            return
        file_size = os.path.getsize(file_path)
        conn.sendall(f'OK:{file_size}'.encode('utf-8'))
        ack = conn.recv(16)
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                conn.sendall(chunk)
        print(f"[P2P Virtual:{username}] Sent '{filename}' to {addr}")
    except Exception as e:
        print(f"[P2P Virtual:{username}] Error: {e}")
    finally:
        conn.close()


def start_virtual_peer(username):
    """Spawn an SSL P2P socket server for a user. Returns (ip, port)."""
    if username in virtual_peers:
        info = virtual_peers[username]
        return info['ip'], info['port']

    _generate_ssl_cert()
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_IP, 0))
    port = server_socket.getsockname()[1]
    server_socket.listen(5)
    ssl_socket = ssl_context.wrap_socket(server_socket, server_side=True)

    def _serve():
        while True:
            try:
                conn, addr = ssl_socket.accept()
                threading.Thread(
                    target=_handle_p2p_client,
                    args=(conn, addr, username),
                    daemon=True
                ).start()
            except Exception:
                break

    t = threading.Thread(target=_serve, daemon=True)
    t.start()

    virtual_peers[username] = {'ip': SERVER_IP, 'port': port, 'thread': t}
    print(f"[VirtualPeer] Started for '{username}' on {SERVER_IP}:{port} (SSL)")
    return SERVER_IP, port


def _p2p_download(provider_ip, provider_port, filename, expected_hash, save_dir):
    """Download a file from a virtual peer over SSL TCP, verify SHA-256."""
    os.makedirs(save_dir, exist_ok=True)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = ssl_context.wrap_socket(raw_socket)
    try:
        conn.connect((provider_ip, int(provider_port)))
        conn.sendall(filename.encode('utf-8'))
        header = conn.recv(1024).decode('utf-8')
        if header.startswith('ERROR'):
            print(f"[P2P Download] Remote error: {header}")
            conn.close()
            return False
        file_size = int(header.split(':')[1])
        conn.sendall(b'READY')
        save_path = os.path.join(save_dir, filename)
        received = 0
        with open(save_path, 'wb') as f:
            while received < file_size:
                chunk = conn.recv(CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
        conn.close()
        actual_hash = hash_file(save_path)
        if actual_hash == expected_hash:
            print(f"[P2P Download] Verified: '{filename}' ({received} bytes)")
            return True
        else:
            os.remove(save_path)
            print(f"[P2P Download] Integrity FAIL: expected {expected_hash[:16]}..., got {actual_hash[:16]}...")
            return False
    except Exception as e:
        print(f"[P2P Download] Failed: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


# ── Pub/Sub Notification Helper ──────────────────────────────────────
def publish_notification_to_subscribers(topic, message, exclude_user=None):
    """Store a notification for all users subscribed to a topic."""
    subs = db_manager.get_all_subscriptions()
    notified = set()
    for s in subs:
        subscriber = s['peer_ip']  # In unified mode, peer_ip stores username
        if subscriber != exclude_user and subscriber not in notified:
            if s['topic'] == topic:
                db_manager.add_notification(subscriber, message)
                notified.add(subscriber)


# ── Decorators ───────────────────────────────────────────────────────
def login_required(f):
    """Decorator: redirect to /login if not authenticated."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to continue.', 'danger')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator: restrict access to admin role only."""
    @functools.wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    """Decorator: restrict access to student role only."""
    @functools.wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if session.get('role') != 'student':
            flash('This page is for students only.', 'danger')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated


# ── Routes ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'username' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login_page'))


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        if 'username' in session:
            return redirect(url_for('index'))
        return render_template('login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    action = request.form.get('action', 'login')

    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('login_page'))

    password_hash = hash_data(password)

    if action == 'register':
        try:
            db_manager.create_user(username, password_hash, role='student')
            flash('Account created! You can now log in.', 'success')
        except Exception as e:
            flash(str(e), 'danger')
        return redirect(url_for('login_page'))

    # Login
    try:
        token = db_manager.authenticate_user(username, password_hash)
        user = db_manager.get_user_by_username(username)
        session['username'] = username
        session['role'] = user['role']
        session['token'] = token

        # Spawn virtual peer for students
        if user['role'] == 'student':
            os.makedirs(os.path.join(STORAGE_DIR, username), exist_ok=True)
            start_virtual_peer(username)

        flash(f'Welcome, {username}!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('login_page'))


@app.route('/logout')
def logout():
    username = session.get('username')
    # Remove virtual peer so admin sees accurate online status
    if username and username in virtual_peers:
        del virtual_peers[username]
        print(f"[VirtualPeer] Stopped for '{username}' (logged out)")
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    users = db_manager.get_all_users()
    files = db_manager.get_all_files()
    subscriptions = db_manager.get_all_subscriptions()
    active_nodes = [
        {'username': u, 'ip': v['ip'], 'port': v['port']}
        for u, v in virtual_peers.items()
    ]
    topics = db_manager.get_all_topics()
    return render_template('admin.html',
                           users=users, files=files,
                           subscriptions=subscriptions,
                           active_nodes=active_nodes,
                           topics=topics)


@app.route('/admin/add_topic', methods=['POST'])
@admin_required
def admin_add_topic():
    name = request.form.get('topic_name', '').strip()
    description = request.form.get('topic_description', '').strip()
    if not name:
        flash('Topic name is required.', 'danger')
        return redirect(url_for('admin_dashboard'))
    try:
        db_manager.add_topic(name, description)
        flash(f"Topic '{name}' added successfully!", 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete_topic', methods=['POST'])
@admin_required
def admin_delete_topic():
    topic_id = request.form.get('topic_id')
    if not topic_id:
        flash('Invalid topic.', 'danger')
        return redirect(url_for('admin_dashboard'))
    db_manager.delete_topic(int(topic_id))
    flash('Topic deleted.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/dashboard')
@student_required
def student_dashboard():
    username = session['username']
    # Ensure virtual peer is running
    if username not in virtual_peers:
        os.makedirs(os.path.join(STORAGE_DIR, username), exist_ok=True)
        start_virtual_peer(username)
    peer_info = virtual_peers[username]

    all_files = db_manager.get_all_files()
    my_files = db_manager.get_files_by_owner(username)
    subscribed_topics = db_manager.get_user_subscriptions(username)
    subscribed_files = db_manager.get_files_by_topics(subscribed_topics)
    topics = db_manager.get_all_topics()

    return render_template('student.html',
                           peer_info=peer_info,
                           all_files=all_files,
                           my_files=my_files,
                           subscribed_topics=subscribed_topics,
                           subscribed_files=subscribed_files,
                           topics=topics)


@app.route('/share', methods=['POST'])
@student_required
def share_file():
    username = session['username']
    uploaded = request.files.get('file')
    topic = request.form.get('topic', '').strip()

    if not uploaded or not topic:
        flash('File and topic are required.', 'danger')
        return redirect(url_for('student_dashboard'))

    # Validate topic against approved Topics table
    if not db_manager.validate_topic(topic):
        flash(f"Invalid topic '{topic}'. Please select an approved topic.", 'danger')
        return redirect(url_for('student_dashboard'))

    # Save to user's storage folder
    user_dir = os.path.join(STORAGE_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    save_path = os.path.join(user_dir, uploaded.filename)
    uploaded.save(save_path)

    # Compute SHA-256 hash (DFS: this becomes the File Handle / GUID)
    file_hash = hash_file(save_path)

    # DFS: Auto-detect File Attributes for the Directory Service (NFS Lecture 10)
    file_size = os.path.getsize(save_path)
    mime_type, _ = mimetypes.guess_type(save_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'

    # Get virtual peer info (DFS: Flat File Server location)
    if username not in virtual_peers:
        start_virtual_peer(username)
    peer_info = virtual_peers[username]

    # Register in Directory Service with File Handle + Attributes
    db_manager.add_file_direct(
        uploaded.filename, file_hash, username,
        peer_info['ip'], peer_info['port'], topic,
        file_size=file_size, file_type=mime_type
    )

    # ── High Availability: Save a backup copy on the server ────────────
    # The backup is stored using the File Handle (hash) as filename to
    # avoid duplicates and enable direct lookup for failover downloads.
    backup_path = os.path.join(BACKUP_DIR, file_hash)
    if not os.path.exists(backup_path):
        shutil.copy2(save_path, backup_path)
        print(f"[HA Backup] Stored backup for '{uploaded.filename}' -> {file_hash[:16]}...")

    # Pub/Sub: notify subscribers of this topic
    msg = f"New file '{uploaded.filename}' shared by {username} in topic '{topic}'!"
    threading.Thread(
        target=publish_notification_to_subscribers,
        args=(topic, msg, username),
        daemon=True
    ).start()

    flash(f"File '{uploaded.filename}' shared successfully! (SHA-256: {file_hash[:16]}...)", 'success')
    return redirect(url_for('student_dashboard'))


@app.route('/delete_file', methods=['POST'])
@student_required
def delete_file():
    """Allow a student to delete their own shared file."""
    username = session['username']
    file_id = request.form.get('file_id')

    if not file_id:
        flash('Missing file identifier.', 'danger')
        return redirect(url_for('student_dashboard'))

    # Get file info before deletion (to remove physical file)
    file_info = db_manager.get_file_by_id(int(file_id))
    if file_info and file_info['owner'] != username:
        flash('Access denied: you can only delete your own files.', 'danger')
        return redirect(url_for('student_dashboard'))

    # Delete from Directory Service (DB)
    success = db_manager.delete_file_by_owner(int(file_id), username)
    if success:
        # Also remove the physical file from storage
        if file_info:
            physical_path = os.path.join(STORAGE_DIR, username, file_info['filename'])
            if os.path.exists(physical_path):
                os.remove(physical_path)
        flash(f"File '{file_info['filename']}' deleted successfully.", 'success')
    else:
        flash('Could not delete the file. You may not be the owner.', 'danger')

    return redirect(url_for('student_dashboard'))


@app.route('/subscribe', methods=['POST'])
@student_required
def subscribe():
    username = session['username']
    topic = request.form.get('topic', '').strip()
    if not topic:
        flash('Topic is required.', 'danger')
        return redirect(url_for('student_dashboard'))

    # Validate topic against approved Topics table
    if not db_manager.validate_topic(topic):
        flash(f"Invalid topic '{topic}'. Please select an approved topic.", 'danger')
        return redirect(url_for('student_dashboard'))

    db_manager.add_subscription_by_user(username, topic)
    flash(f"Subscribed to '{topic}'!", 'success')
    return redirect(url_for('student_dashboard'))


@app.route('/unsubscribe', methods=['POST'])
@student_required
def unsubscribe():
    username = session['username']
    topic = request.form.get('topic', '').strip()
    if not topic:
        flash('Topic is required.', 'danger')
        return redirect(url_for('student_dashboard'))
    db_manager.remove_subscription_by_user(username, topic)
    flash(f"Unsubscribed from '{topic}'.", 'success')
    return redirect(url_for('student_dashboard'))


@app.route('/search', methods=['POST'])
@student_required
def search():
    username = session['username']
    query = request.form.get('query', '').strip()
    search_results = db_manager.search_file_direct(query) if query else []

    # Also get full dashboard data
    if username not in virtual_peers:
        start_virtual_peer(username)
    peer_info = virtual_peers[username]
    all_files = db_manager.get_all_files()
    my_files = db_manager.get_files_by_owner(username)
    subscribed_topics = db_manager.get_user_subscriptions(username)

    topics = db_manager.get_all_topics()
    subscribed_files = db_manager.get_files_by_topics(subscribed_topics)

    return render_template('student.html',
                           peer_info=peer_info,
                           all_files=all_files,
                           my_files=my_files,
                           subscribed_topics=subscribed_topics,
                           subscribed_files=subscribed_files,
                           search_results=search_results,
                           search_query=query,
                           topics=topics)


@app.route('/download', methods=['POST'])
@student_required
def download():
    """Download a file with High Availability fallback.
    Strategy: Try P2P from the original provider first (Primary).
    If the provider is offline, transparently fall back to the
    server-side backup replica (Secondary). The transition is
    invisible to the end-user — they just click Download."""
    username = session['username']
    filename = request.form.get('filename')
    owner = request.form.get('owner')
    file_hash = request.form.get('file_hash')

    if not all([filename, owner, file_hash]):
        flash('Missing download parameters.', 'danger')
        return redirect(url_for('student_dashboard'))

    temp_dir = tempfile.mkdtemp()
    success = False
    source = 'unknown'

    # ── PRIMARY: Try P2P download from the original peer ──────────────
    if owner in virtual_peers:
        provider = virtual_peers[owner]
        try:
            success = _p2p_download(
                provider['ip'], provider['port'],
                filename, file_hash, temp_dir
            )
            if success:
                source = 'P2P'
        except Exception as e:
            print(f"[HA Download] P2P attempt failed: {e}")
            success = False

    # ── SECONDARY: Fallback to server backup replica ──────────────────
    if not success:
        print(f"[HA Download] Provider '{owner}' offline or P2P failed. Fetching from Central Backup...")
        backup_path = os.path.join(BACKUP_DIR, file_hash)
        if os.path.exists(backup_path):
            # Verify integrity of the backup copy
            backup_hash = hash_file(backup_path)
            if backup_hash == file_hash:
                dest_path = os.path.join(temp_dir, filename)
                shutil.copy2(backup_path, dest_path)
                success = True
                source = 'Server Backup'
                print(f"[HA Download] Served '{filename}' from Central Backup (integrity verified)")
            else:
                print(f"[HA Download] Backup integrity FAILED for '{filename}'")
        else:
            print(f"[HA Download] No backup found for hash {file_hash[:16]}...")

    if success:
        file_path = os.path.join(temp_dir, filename)
        flash(f"Downloaded '{filename}' (Source: {source}).", 'success')
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        flash(f"Download of '{filename}' failed. Provider offline and no backup available.", 'danger')
        return redirect(url_for('student_dashboard'))


# ── API Endpoints ────────────────────────────────────────────────────

@app.route('/api/users', methods=['GET'])
def api_users():
    """Return all registered users as JSON."""
    return jsonify(db_manager.get_all_users())


@app.route('/api/files', methods=['GET'])
def api_files():
    """Return all indexed files as JSON."""
    return jsonify(db_manager.get_all_files())


@app.route('/api/notifications')
@login_required
def api_notifications():
    """Return notifications for the logged-in user."""
    username = session['username']
    notifs = db_manager.get_notifications(username)
    return jsonify(notifs)


# ── High Availability: Backup Replication API ───────────────────────────

@app.route('/api/upload_backup', methods=['POST'])
@login_required
def api_upload_backup():
    """High Availability: Accept a file backup from a peer node.
    The file is stored using its SHA-256 hash (File Handle) as the
    filename to enable deduplication and direct lookup on failover."""
    uploaded = request.files.get('file')
    file_hash = request.form.get('file_hash', '')
    if not uploaded or not file_hash:
        return jsonify({"status": "error", "message": "File and file_hash are required."}), 400
    backup_path = os.path.join(BACKUP_DIR, file_hash)
    if not os.path.exists(backup_path):
        uploaded.save(backup_path)
        # Verify the saved backup integrity
        actual_hash = hash_file(backup_path)
        if actual_hash != file_hash:
            os.remove(backup_path)
            return jsonify({"status": "error", "message": "Integrity check failed."}), 400
        print(f"[HA Backup API] Stored backup: {file_hash[:16]}...")
    return jsonify({"status": "success", "message": "Backup stored."})


@app.route('/api/download_backup/<file_hash>', methods=['GET'])
@login_required
def api_download_backup(file_hash):
    """High Availability: Serve a backup file by its File Handle (SHA-256).
    Used as a fallback when the original peer provider is offline."""
    backup_path = os.path.join(BACKUP_DIR, file_hash)
    if not os.path.exists(backup_path):
        return jsonify({"status": "error", "message": "Backup not found."}), 404
    # Verify integrity before serving
    actual_hash = hash_file(backup_path)
    if actual_hash != file_hash:
        return jsonify({"status": "error", "message": "Backup integrity check failed."}), 500
    filename = request.args.get('filename', file_hash)
    return send_file(backup_path, as_attachment=True, download_name=filename)


# ── DFS: NFS Directory Service API (Lecture 10) ─────────────────────────
@app.route('/api/nfs/lookup', methods=['GET'])
@login_required
def api_nfs_lookup():
    """NFS Directory Service: Lookup API endpoint.
    Returns File Handle (GUID) + File Attributes for a given filename.
    Access Control: Requires authenticated session (ACL simulation)."""
    filename = request.args.get('filename', '')
    token = session.get('token', '')
    try:
        results = db_manager.nfs_lookup(token, filename)
        return jsonify({"status": "success", "results": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 403


@app.route('/api/nfs/read/<file_handle>', methods=['GET'])
@login_required
def api_nfs_read(file_handle):
    """NFS Flat File Service: Read file attributes by File Handle (GUID).
    Access Control: Requires authenticated session (ACL simulation)."""
    token = session.get('token', '')
    try:
        result = db_manager.nfs_lookup_by_handle(token, file_handle)
        if result is None:
            return jsonify({"status": "error", "message": "File Handle not found."}), 404
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 403


# ── Server Startup ───────────────────────────────────────────────────

def start_web_service(host, port):
    """Run the unified Flask web application."""
    print(f"[WebService] Unified D-URS Portal on http://{host}:{port}")
    app.run(host=host, port=port, use_reloader=False)
