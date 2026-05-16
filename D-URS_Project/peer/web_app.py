# peer/web_app.py
# Flask-based Student Portal for the Peer Node

import os
import sys
import threading

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

PEER_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(PEER_DIR, 'templates'),
    static_folder=os.path.join(PEER_DIR, 'static'),
)
app.secret_key = 'durs-peer-secret-key'

# Global reference to the PeerNode instance (set at startup)
_peer_node = None
# Global list for notifications received via Pub/Sub
notifications = []
# Track subscribed topics for display
subscribed_topics = []


def set_peer_node(node):
    """Set the global PeerNode instance used by Flask routes."""
    global _peer_node
    _peer_node = node


@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    action = request.form.get('action', 'login')

    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('login_page'))

    if action == 'register':
        resp = _peer_node.register(username, password)
        if resp['status'] == 'success':
            flash('Account created! You can now log in.', 'success')
        else:
            flash(resp.get('message', 'Registration failed.'), 'danger')
        return redirect(url_for('login_page'))

    # Login
    resp = _peer_node.login(username, password)
    if resp['status'] == 'success':
        session['username'] = username
        flash(f'Welcome back, {username}!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash(resp.get('message', 'Login failed.'), 'danger')
        return redirect(url_for('login_page'))


@app.route('/logout')
def logout():
    session.clear()
    _peer_node.token = None
    return redirect(url_for('login_page'))


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login_page'))

    # Fetch all network files from the central server via RPC
    all_files = []
    if _peer_node.token:
        try:
            resp = _peer_node.server.lookup_file(_peer_node.token, '')
            if resp['status'] == 'success':
                all_files = resp['results']
        except Exception:
            pass

    return render_template(
        'dashboard.html',
        username=session['username'],
        peer_port=_peer_node.peer_port,
        all_files=all_files,
        subscribed_topics=subscribed_topics,
    )


@app.route('/share', methods=['POST'])
def share_file():
    if 'username' not in session or not _peer_node.token:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login_page'))

    uploaded = request.files.get('file')
    topic = request.form.get('topic', '').strip()

    if not uploaded or not topic:
        flash('File and topic are required.', 'danger')
        return redirect(url_for('dashboard'))

    # Save the uploaded file to shared_files/
    shared_dir = os.path.join(PEER_DIR, 'shared_files')
    os.makedirs(shared_dir, exist_ok=True)
    save_path = os.path.join(shared_dir, uploaded.filename)
    uploaded.save(save_path)

    resp = _peer_node.publish_file_to_server(uploaded.filename, save_path, topic)
    if resp['status'] == 'success':
        flash(f"File '{uploaded.filename}' shared successfully!", 'success')
    else:
        flash(resp.get('message', 'Failed to share file.'), 'danger')

    return redirect(url_for('dashboard'))


@app.route('/subscribe', methods=['POST'])
def subscribe():
    if 'username' not in session or not _peer_node.token:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login_page'))

    topic = request.form.get('topic', '').strip()
    if not topic:
        flash('Topic is required.', 'danger')
        return redirect(url_for('dashboard'))

    resp = _peer_node.subscribe_to_topic(topic)
    if resp['status'] == 'success':
        if topic not in subscribed_topics:
            subscribed_topics.append(topic)
        flash(f"Subscribed to '{topic}'!", 'success')
    else:
        flash(resp.get('message', 'Subscription failed.'), 'danger')

    return redirect(url_for('dashboard'))


@app.route('/search', methods=['POST'])
def search():
    if 'username' not in session or not _peer_node.token:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login_page'))

    query = request.form.get('query', '').strip()
    search_results = []
    all_files = []

    if query:
        try:
            resp = _peer_node.server.lookup_file(_peer_node.token, query)
            if resp['status'] == 'success':
                search_results = resp['results']
        except Exception:
            flash('Search failed.', 'danger')

    # Also fetch all files for the main table
    try:
        resp = _peer_node.server.lookup_file(_peer_node.token, '')
        if resp['status'] == 'success':
            all_files = resp['results']
    except Exception:
        pass

    return render_template(
        'dashboard.html',
        username=session['username'],
        peer_port=_peer_node.peer_port,
        all_files=all_files,
        subscribed_topics=subscribed_topics,
        search_results=search_results,
    )


@app.route('/download', methods=['POST'])
def download():
    if 'username' not in session or not _peer_node.token:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login_page'))

    filename = request.form.get('filename')
    provider_ip = request.form.get('provider_ip')
    provider_port = request.form.get('provider_port')
    file_hash = request.form.get('file_hash')

    if not all([filename, provider_ip, provider_port, file_hash]):
        flash('Missing download parameters.', 'danger')
        return redirect(url_for('dashboard'))

    from peer import p2p_network
    save_dir = os.path.join(PEER_DIR, 'downloads')
    success = p2p_network.download_file(provider_ip, int(provider_port), filename, file_hash, save_dir)

    if success:
        flash(f"'{filename}' downloaded and verified successfully!", 'success')
    else:
        flash(f"Download of '{filename}' failed or integrity check failed.", 'danger')

    return redirect(url_for('dashboard'))


@app.route('/api/notifications')
def api_notifications():
    """Endpoint polled by JavaScript to fetch new notifications."""
    return jsonify(notifications)


def start_web_app(host, port):
    """Run the peer Flask web app."""
    print(f"[PeerWeb] Student Portal running on http://{host}:{port}")
    app.run(host=host, port=port, use_reloader=False)
