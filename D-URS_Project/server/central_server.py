# server/central_server.py
# Main entry point for the Central Index Server (RPC + Flask + Pub/Sub)
# DFS Architecture: This module implements the Directory Service (NFS Lecture 10)

import os
import sys
import socket
import threading
from xmlrpc.server import SimpleXMLRPCServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.config import SERVER_IP, SERVER_RPC_PORT, SERVER_WEB_PORT
from server import db_manager
from server import web_service


class IndexServer:
    """RPC-exposed methods for the Central Index Server.
    DFS: Acts as the NFS Directory Service + Mount Service (Lecture 10).
    Provides nfs_lookup (name → File Handle + Attributes) and
    register_file (creates directory entries in the central index)."""

    def register_user(self, username, password_hash):
        """Register a new user account."""
        try:
            db_manager.create_user(username, password_hash)
            return {"status": "success", "message": f"User '{username}' registered."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def login(self, username, password_hash):
        """Authenticate a user and return a session token."""
        try:
            token = db_manager.authenticate_user(username, password_hash)
            return {"status": "success", "token": token}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def register_file(self, token, filename, file_hash, provider_ip, provider_port, topic,
                       file_size=0, file_type='application/octet-stream'):
        """Register a shared file in the Directory Service (requires valid token).
        DFS: Creates an entry in the NFS Directory Service with File Handle + Attributes.
        After success, asynchronously notifies all subscribers of the topic."""
        try:
            db_manager.add_file(token, filename, file_hash, provider_ip, provider_port, topic,
                               owner='', file_size=file_size, file_type=file_type)
            # Asynchronous multicast notification to subscribers
            if topic:
                msg = f"New file '{filename}' available in topic '{topic}'!"
                threading.Thread(target=publish_notification, args=(topic, msg), daemon=True).start()
            return {"status": "success", "message": f"File '{filename}' registered."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def subscribe(self, token, topic, peer_ip, notify_port):
        """Subscribe a peer to a topic for push notifications (requires valid token)."""
        try:
            if not db_manager.verify_token(token):
                return {"status": "error", "message": "Authentication failed: invalid session token."}
            db_manager.add_subscription(peer_ip, notify_port, topic)
            return {"status": "success", "message": f"Subscribed to topic '{topic}'."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def lookup_file(self, token, filename):
        """Search for providers of a file (requires valid token)."""
        try:
            results = db_manager.search_file(token, filename)
            return {"status": "success", "results": results}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── DFS: NFS Directory Service Lookup (Lecture 10) ──────────────────
    def nfs_lookup(self, token, filename):
        """NFS Directory Service: Lookup operation (Lecture 10, Slide 7).
        Maps a filename to a File Handle (GUID = SHA-256 hash) and returns
        the file's attributes (size, type, owner, creation time).
        Access Control: Simulates the ACL check (Slide 9) via token verification."""
        try:
            results = db_manager.nfs_lookup(token, filename)
            return {"status": "success", "results": results}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def nfs_read_by_handle(self, token, file_handle):
        """NFS Flat File Service: Read attributes by File Handle (GUID).
        Given a File Handle, returns the file's metadata and provider location.
        The actual file content is retrieved via P2P from the Flat File Server (Peer)."""
        try:
            result = db_manager.nfs_lookup_by_handle(token, file_handle)
            if result is None:
                return {"status": "error", "message": "File Handle not found."}
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}


def publish_notification(topic, message):
    """Send a notification message to all subscribers of a topic via TCP."""
    subscribers = db_manager.get_subscribers(topic)
    for peer_ip, peer_port in subscribers:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((peer_ip, int(peer_port)))
            sock.sendall(message.encode('utf-8'))
            sock.close()
            print(f"[Broker] Notified {peer_ip}:{peer_port} -> {message}")
        except Exception:
            # Ignore offline or unreachable peers
            pass


def start_server():
    """Start the XML-RPC server on the configured IP and port."""
    db_manager.init_db()

    # Start the Flask Web Service in a daemon thread
    threading.Thread(target=web_service.start_web_service, args=(SERVER_IP, SERVER_WEB_PORT), daemon=True).start()

    server = SimpleXMLRPCServer((SERVER_IP, SERVER_RPC_PORT), allow_none=True, logRequests=True)
    server.register_instance(IndexServer())
    print(f"[IndexServer] RPC server running on {SERVER_IP}:{SERVER_RPC_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[IndexServer] Shutting down.")


if __name__ == '__main__':
    start_server()
