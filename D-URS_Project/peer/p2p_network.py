# peer/p2p_network.py
# P2P Socket networking: SSL-wrapped TCP server and client for file transfer
# DFS Architecture: This module implements the Flat File Service (NFS Lecture 10).
# The Peer node stores actual file content and serves it based on filename requests.
# File integrity is verified using the File Handle (SHA-256 GUID) after each transfer.

import socket
import ssl
import threading
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.security import hash_file
from peer import local_db

CHUNK_SIZE = 4096
CERT_DIR = os.path.join(os.path.dirname(__file__), 'certs')
CERT_FILE = os.path.join(CERT_DIR, 'peer_cert.pem')
KEY_FILE = os.path.join(CERT_DIR, 'peer_key.pem')


def generate_self_signed_cert(cert_path=CERT_FILE, key_path=KEY_FILE):
    """Generate a self-signed certificate and private key for local SSL testing."""
    os.makedirs(os.path.dirname(cert_path), exist_ok=True)

    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u"D-URS Peer"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .sign(key, hashes.SHA256())
        )

        with open(key_path, 'wb') as f:
            f.write(key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            ))
        with open(cert_path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

    except ImportError:
        # Fallback: use OpenSSL CLI if cryptography lib not available
        os.system(
            f'openssl req -x509 -newkey rsa:2048 -keyout "{key_path}" '
            f'-out "{cert_path}" -days 365 -nodes '
            f'-subj "/CN=D-URS Peer"'
        )

    return cert_path, key_path


def _handle_client(conn, addr):
    """Handle an incoming P2P file request on the server side."""
    try:
        filename = conn.recv(1024).decode('utf-8').strip()
        if not filename:
            conn.close()
            return

        file_path = local_db.get_local_file_path(filename)
        if file_path is None or not os.path.exists(file_path):
            conn.sendall(b'ERROR: File not found')
            conn.close()
            return

        file_size = os.path.getsize(file_path)
        conn.sendall(f'OK:{file_size}'.encode('utf-8'))

        # Wait for client ready signal
        ack = conn.recv(16)

        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                conn.sendall(chunk)

        print(f"[P2P Server] Sent '{filename}' to {addr}")
    except Exception as e:
        print(f"[P2P Server] Error handling {addr}: {e}")
    finally:
        conn.close()


def start_p2p_server(host, port):
    """Start an SSL-wrapped TCP server to serve files to peers. Runs in a daemon thread."""
    cert_path, key_path = generate_self_signed_cert()

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)

    ssl_socket = ssl_context.wrap_socket(server_socket, server_side=True)
    print(f"[P2P Server] Listening on {host}:{port} (SSL)")

    def _serve():
        while True:
            try:
                conn, addr = ssl_socket.accept()
                thread = threading.Thread(target=_handle_client, args=(conn, addr), daemon=True)
                thread.start()
            except Exception as e:
                print(f"[P2P Server] Accept error: {e}")
                break

    server_thread = threading.Thread(target=_serve, daemon=True)
    server_thread.start()
    return server_thread


def download_file(peer_ip, peer_port, filename, expected_hash, save_dir=None):
    """Download a file from a peer over SSL TCP, then verify its SHA-256 hash."""
    if save_dir is None:
        save_dir = os.path.join(os.path.dirname(__file__), 'downloads')
    os.makedirs(save_dir, exist_ok=True)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = ssl_context.wrap_socket(raw_socket)

    try:
        conn.connect((peer_ip, int(peer_port)))

        # Send requested filename
        conn.sendall(filename.encode('utf-8'))

        # Receive header: "OK:<size>" or "ERROR:..."
        header = conn.recv(1024).decode('utf-8')
        if header.startswith('ERROR'):
            print(f"[P2P Client] Remote error: {header}")
            conn.close()
            return False

        file_size = int(header.split(':')[1])

        # Signal ready
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

        # Integrity check
        actual_hash = hash_file(save_path)
        if actual_hash == expected_hash:
            print(f"[P2P Client] Download Success & Verified: '{filename}' ({received} bytes)")
            return True
        else:
            os.remove(save_path)
            print(f"[P2P Client] Security Warning: File tampered or corrupted! "
                  f"Expected {expected_hash}, got {actual_hash}")
            return False

    except Exception as e:
        print(f"[P2P Client] Download failed: {e}")
        conn.close()
        return False
