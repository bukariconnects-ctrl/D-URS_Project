# peer/peer_node.py
# Main entry point for the Student Peer Node (RPC Client + TCP Socket)
# DFS Architecture: This module acts as the NFS Client + Flat File Server (Lecture 10)

import os
import sys
import socket
import threading
import mimetypes
import urllib.request
import urllib.error
from xmlrpc.client import ServerProxy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.config import SERVER_IP, SERVER_RPC_PORT, SERVER_WEB_PORT
from shared.security import hash_data, hash_file
from peer import p2p_network, local_db, web_app

PEER_P2P_PORT = 9000


def _find_free_port():
    """Find and return a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


class PeerNode:
    """RPC client that communicates with the Central Index Server."""

    def __init__(self, peer_ip='127.0.0.1', peer_port=None, web_port=5001):
        self.server = ServerProxy(f'http://{SERVER_IP}:{SERVER_RPC_PORT}', allow_none=True)
        self.token = None
        self.peer_ip = peer_ip
        self.peer_port = peer_port if peer_port else _find_free_port()
        self.web_port = web_port

        # Initialize the local database
        local_db.init_db()

        # Start the P2P file server in a daemon thread
        p2p_network.start_p2p_server(self.peer_ip, self.peer_port)
        print(f"[PeerNode] P2P server started on {self.peer_ip}:{self.peer_port}")

        # Start the notification listener in a daemon thread
        self.notify_port = self.start_notification_listener()
        print(f"[PeerNode] Notification listener on {self.peer_ip}:{self.notify_port}")

        # Register this node with the web app and start the web portal
        web_app.set_peer_node(self)
        threading.Thread(
            target=web_app.start_web_app,
            args=(self.peer_ip, self.web_port),
            daemon=True
        ).start()

    def start_notification_listener(self):
        """Start a TCP listener for push notifications from the broker."""
        notify_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        notify_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        notify_socket.bind((self.peer_ip, 0))
        notify_port = notify_socket.getsockname()[1]
        notify_socket.listen(5)

        def _listen():
            while True:
                try:
                    conn, addr = notify_socket.accept()
                    data = conn.recv(4096).decode('utf-8')
                    if data:
                        print(f"[NOTIFICATION] {data}")
                        web_app.notifications.append(data)
                    conn.close()
                except Exception:
                    break

        thread = threading.Thread(target=_listen, daemon=True)
        thread.start()
        return notify_port

    def subscribe_to_topic(self, topic):
        """Subscribe to a topic to receive push notifications."""
        if self.token is None:
            print("[Subscribe] Error: You must log in first.")
            return {"status": "error", "message": "Not logged in."}
        response = self.server.subscribe(self.token, topic, self.peer_ip, self.notify_port)
        print(f"[Subscribe] {response['message'] if 'message' in response else response}")
        return response

    def register(self, username, password):
        """Register a new account on the central server."""
        password_hash = hash_data(password)
        response = self.server.register_user(username, password_hash)
        print(f"[Register] {response['message'] if 'message' in response else response}")
        return response

    def login(self, username, password):
        """Log in to the central server and store the session token."""
        password_hash = hash_data(password)
        response = self.server.login(username, password_hash)
        if response['status'] == 'success':
            self.token = response['token']
            print(f"[Login] Success. Token stored.")
        else:
            print(f"[Login] Failed: {response['message']}")
        return response

    def publish_file_to_server(self, filename, filepath, topic):
        """Hash a file and register it on the central index server.
        DFS: The Peer acts as the Flat File Server (Lecture 10).
        Before registering, we auto-detect File Attributes (size, MIME type)
        to store in the Directory Service."""
        if self.token is None:
            print("[Publish] Error: You must log in first.")
            return {"status": "error", "message": "Not logged in."}
        abs_path = os.path.abspath(filepath)
        file_hash = hash_file(abs_path)

        # DFS: Auto-detect File Attributes for the Directory Service
        file_size = os.path.getsize(abs_path)
        mime_type, _ = mimetypes.guess_type(abs_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        # Register in the local DB so the P2P server can serve it
        local_db.add_local_file(filename, file_hash, abs_path)
        # DFS: Register File Handle + Attributes in the Directory Service
        response = self.server.register_file(
            self.token, filename, file_hash,
            self.peer_ip, self.peer_port, topic,
            file_size, mime_type
        )
        print(f"[Publish] {response['message'] if 'message' in response else response}")

        # ── High Availability: Upload a backup copy to the Central Server ──
        # This ensures the file remains downloadable even if this peer goes
        # offline (Server-side Backup Replication for fault tolerance).
        self._upload_backup(abs_path, file_hash)

        return response

    def search_for_file(self, filename):
        """Search the central index for providers of a file."""
        if self.token is None:
            print("[Search] Error: You must log in first.")
            return {"status": "error", "message": "Not logged in."}
        response = self.server.lookup_file(self.token, filename)
        if response['status'] == 'success':
            print(f"[Search] Found {len(response['results'])} result(s):")
            for r in response['results']:
                print(f"  - {r['filename']} | {r['provider_ip']}:{r['provider_port']} | hash={r['file_hash']}")
        else:
            print(f"[Search] Failed: {response['message']}")
        return response

    # ── DFS: NFS Client Operations (Lecture 10) ──────────────────────────
    def nfs_lookup(self, filename):
        """NFS Client: Lookup a filename via the Directory Service.
        Returns the File Handle (GUID) and File Attributes."""
        if self.token is None:
            print("[NFS Lookup] Error: You must log in first.")
            return {"status": "error", "message": "Not logged in."}
        response = self.server.nfs_lookup(self.token, filename)
        if response['status'] == 'success':
            print(f"[NFS Lookup] Found {len(response['results'])} result(s):")
            for r in response['results']:
                attrs = r['attributes']
                print(f"  - Handle: {r['file_handle'][:16]}...")
                print(f"    Name: {attrs['filename']} | Size: {attrs['file_size']} | Type: {attrs['file_type']}")
        else:
            print(f"[NFS Lookup] Failed: {response['message']}")
        return response


    def _upload_backup(self, filepath, file_hash):
        """High Availability: Upload a backup copy of the file to the Central Server."""
        try:
            import http.client
            import io
            boundary = '----DURSBackupBoundary'
            filename = os.path.basename(filepath)
            with open(filepath, 'rb') as f:
                file_data = f.read()
            body = (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="file_hash"\r\n\r\n'
                f'{file_hash}\r\n'
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f'Content-Type: application/octet-stream\r\n\r\n'
            ).encode('utf-8') + file_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')
            conn = http.client.HTTPConnection(SERVER_IP, SERVER_WEB_PORT, timeout=10)
            conn.request('POST', '/api/upload_backup', body=body,
                         headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
            resp = conn.getresponse()
            if resp.status == 200:
                print(f"[HA Backup] Backup uploaded successfully for {file_hash[:16]}...")
            else:
                print(f"[HA Backup] Backup upload returned status {resp.status}")
            conn.close()
        except Exception as e:
            print(f"[HA Backup] Failed to upload backup: {e}")

    def _download_from_server_backup(self, file_hash, filename, save_dir):
        """High Availability: Download a file from the Central Server backup.
        Used as a fallback when the original peer provider is offline."""
        try:
            os.makedirs(save_dir, exist_ok=True)
            url = f'http://{SERVER_IP}:{SERVER_WEB_PORT}/api/download_backup/{file_hash}?filename={filename}'
            save_path = os.path.join(save_dir, filename)
            urllib.request.urlretrieve(url, save_path)
            # Verify SHA-256 integrity
            from shared.security import hash_file as verify_hash
            actual_hash = verify_hash(save_path)
            if actual_hash == file_hash:
                print(f"[HA Download] Verified backup download: '{filename}' ({os.path.getsize(save_path)} bytes)")
                return True
            else:
                os.remove(save_path)
                print(f"[HA Download] Backup integrity FAIL: expected {file_hash[:16]}..., got {actual_hash[:16]}...")
                return False
        except Exception as e:
            print(f"[HA Download] Backup download failed: {e}")
            return False

    def request_and_download(self, filename):
        """Lookup a file and download with High Availability fallback.
        Strategy: Try P2P first (Primary), then Central Backup (Secondary)."""
        if self.token is None:
            print("[Download] Error: You must log in first.")
            return {"status": "error", "message": "Not logged in."}
        response = self.server.lookup_file(self.token, filename)
        if response['status'] != 'success' or not response['results']:
            print(f"[Download] File '{filename}' not found on the network.")
            return {"status": "error", "message": "File not found."}
        # Use the first available provider
        provider = response['results'][0]
        peer_ip = provider['provider_ip']
        peer_port = provider['provider_port']
        expected_hash = provider['file_hash']
        save_dir = os.path.join(os.path.dirname(__file__), 'downloads')

        # ── PRIMARY: Try P2P download from the original peer ──────────────
        try:
            print(f"[Download] Trying P2P from {peer_ip}:{peer_port}...")
            success = p2p_network.download_file(peer_ip, peer_port, filename, expected_hash, save_dir)
        except (ConnectionError, socket.error) as e:
            print(f"[Download] P2P failed: {e}")
            success = False

        # ── SECONDARY: Fallback to Central Server backup ──────────────────
        if not success:
            print("[Download] Original provider offline. Fetching from Central Backup...")
            success = self._download_from_server_backup(expected_hash, filename, save_dir)

        return {"status": "success" if success else "error"}


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='D-URS Peer Node')
    parser.add_argument('--web-port', type=int, default=5001, help='Port for the web portal (default: 5001)')
    parser.add_argument('--p2p-port', type=int, default=None, help='Port for the P2P file server')
    parser.add_argument('--cli', action='store_true', help='Run in CLI mode instead of web mode')
    args = parser.parse_args()

    peer = PeerNode(peer_port=args.p2p_port, web_port=args.web_port)
    print(f"\n===== D-URS Peer Node =====")
    print(f"  Student Portal: http://127.0.0.1:{args.web_port}")
    print(f"  P2P Server:     port {peer.peer_port}")
    print(f"  Notifications:  port {peer.notify_port}")

    if args.cli:
        while True:
            print("\n--- Menu ---")
            print("1. Register User")
            print("2. Login")
            print("3. Subscribe to Topic")
            print("4. Publish/Share a File")
            print("5. Search and Download a File")
            print("6. Exit")

            choice = input("Select an option: ").strip()

            if choice == '1':
                username = input("Username: ").strip()
                password = input("Password: ").strip()
                peer.register(username, password)
            elif choice == '2':
                username = input("Username: ").strip()
                password = input("Password: ").strip()
                peer.login(username, password)
            elif choice == '3':
                topic = input("Topic to subscribe to: ").strip()
                peer.subscribe_to_topic(topic)
            elif choice == '4':
                filename = input("File name (as it will appear on the network): ").strip()
                filepath = input("Full path to the file: ").strip()
                topic = input("Topic/Category: ").strip()
                peer.publish_file_to_server(filename, filepath, topic)
            elif choice == '5':
                filename = input("File name to search for: ").strip()
                peer.request_and_download(filename)
            elif choice == '6':
                print("Goodbye!")
                break
            else:
                print("Invalid option. Please try again.")
    else:
        print("\nPress Ctrl+C to stop the peer node.")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            print("\n[PeerNode] Shutting down.")
