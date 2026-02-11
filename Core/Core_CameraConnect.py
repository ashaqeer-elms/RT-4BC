# PySide6 essentials
from PySide6.QtCore import (Signal,QObject)
import socket
import paramiko
import threading
import re

# Constants (exact from original)
SSH_ROUTER_IP = "192.168.2.1"
SSH_ROUTER_USER = "root"
SSH_CAMERA_USER = "pi"

CAMERA_IP = None
ZMQ_ADDR = None

class CoreCameraConnect(QObject):
    """
    Complete camera connection manager - exact port of original tkinter code.
    Handles: IP detection via router, SSH verification, ZMQ address setup.
    """
    
    # Signals for UI updates (thread-safe)
    camera_ip_detected = Signal(str)    # IP found from nslookup
    camera_connected = Signal(str)      # SSH verified, ZMQ ready
    ssh_error = Signal(str)             # Any SSH failure
    
    def __init__(self):
        super().__init__()
        self.camera_ip = None
        self.zmq_addr = None

    def get_lan_ip(self):
        """Get local LAN IP (exact original)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "Unknown"

    def detect_camera_ip(self):
        """Detect camera IP via router (EXACT original logic)."""
        def run_detection():
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    hostname=SSH_ROUTER_IP,
                    username=SSH_ROUTER_USER,
                    password="admin",  # Original hardcoded
                    timeout=5,
                )
                _, stdout, _ = client.exec_command("nslookup qbc.lan")
                output = stdout.read().decode()
                client.close()

                ips = re.findall(r"Address:\s+(\d+\.\d+\.\d+\.\d+)", output)

                if not ips:
                    raise RuntimeError("Camera IP not found in nslookup output")

                # EXACT: Use last IP (ips[-1])
                detected_ip = ips[-1]
                self.camera_ip_detected.emit(detected_ip)

            except Exception as e:
                self.ssh_error.emit(str(e))

        # Threaded (daemon = auto-cleanup)
        threading.Thread(target=run_detection, daemon=True).start()

    def ssh_check_camera(self, ip):
        """SSH verify camera (EXACT original logic)."""
        def run_ssh_check():
            global CAMERA_IP  # Match original global pattern
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(hostname=ip, username=SSH_CAMERA_USER, timeout=5)
                client.close()
                
                self.camera_ip = ip
                self.zmq_addr = f"tcp://{self.get_lan_ip()}:5555"
                self.camera_connected.emit(ip)
                
            except Exception as e:
                self.ssh_error.emit(str(e))

        threading.Thread(target=run_ssh_check, daemon=True).start()

    # Properties for ZMQ address access
    @property
    def zmq_address(self):
        return self.zmq_addr

    
