from PySide6.QtCore import QObject, QThread, Signal, QMutex, Slot
import paramiko, re, zmq, cv2, numpy as np
from Core.Core_CameraConnect import SSH_CAMERA_USER

# Globals (shared)
gain_scales = []
expo_scales = []
status_labels = []
FRAME_H = 480
FRAME_W = 640
FULL_W = FRAME_W * 4
CAM_DEVICES = [0, 2, 4, 6]
EXPO_ABS = [1, 2, 5, 10, 20, 39, 78, 156, 312, 625, 1250, 2500]
EXPO_MS = [0.04, 0.15, 0.52, 1.08, 2.24, 4.48, 9.03, 18.14, 36.04, 72.99, 146.05, 292.21]
CAMERA_IP = None
ZMQ_ADDR = None
last_fullframe = None


class CameraGainExposure(QObject):
    status_updated = Signal(int, str, str)  # cam_idx, gain_str, expo_str

    def set_camera_ip(self, ip):
        """Set global CAMERA_IP safely."""
        global CAMERA_IP
        CAMERA_IP = ip
    
    def get_camera_gains(self):
        gains = [1] * 4 if CAMERA_IP is None else []
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=CAMERA_IP, username=SSH_CAMERA_USER, timeout=5)
            for dev in CAM_DEVICES:
                _, stdout, _ = client.exec_command(f"v4l2-ctl -d{dev} -C gain")
                m = re.search(r"(\d+)", stdout.read().decode().strip())
                gains.append(int(m.group(1)) if m else 1)
            client.close()
        except Exception as e:
            print("Gain query error:", e)
            gains = [1, 1, 1, 1]
        return gains

    def get_camera_exposures(self):
        levels = [1] * 4 if CAMERA_IP is None else []
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=CAMERA_IP, username=SSH_CAMERA_USER, timeout=5)
            for dev in CAM_DEVICES:
                _, stdout, _ = client.exec_command(f"v4l2-ctl -d{dev} -C exposure_time_absolute")
                m = re.search(r"(\d+)", stdout.read().decode().strip())
                if m:
                    val = int(m.group(1))
                    diffs = [abs(val - ev) for ev in EXPO_ABS]
                    levels.append(diffs.index(min(diffs)) + 1)
                else:
                    levels.append(1)
            client.close()
        except Exception as e:
            print("Exposure query error:", e)
            levels = [1, 1, 1, 1]
        return levels

    def set_camera_gain(self, cam_index, gain_val):
        if CAMERA_IP is None: return
        try:
            dev = CAM_DEVICES[cam_index]
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=CAMERA_IP, username=SSH_CAMERA_USER, timeout=3)
            client.exec_command(f"v4l2-ctl -d{dev} -c gain={gain_val}")
            client.close()
        except Exception as e:
            print("Gain set error:", e)

    def set_camera_expo(self, cam_index, level):
        if CAMERA_IP is None: return
        try:
            level = max(1, min(12, level))
            expo_val = EXPO_ABS[level - 1]
            dev = CAM_DEVICES[cam_index]
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=CAMERA_IP, username=SSH_CAMERA_USER, timeout=3)
            client.exec_command(f"v4l2-ctl -d{dev} -c exposure_time_absolute={expo_val}")
            client.close()
        except Exception as e:
            print("Exposure set error:", e)

    @Slot(int, int)  # gain_slider.value(), expo_slider.value()
    def update_status_label(self, cam_index, g, level):
        level = max(1, min(12, level))
        ms = EXPO_MS[level - 1]
        self.status_updated.emit(cam_index, str(g), f"{ms:.2f}")

class ZMQReceiverThread(QThread):
    frame_received = Signal(object)  # np.ndarray full frame

    def __init__(self, zmq_addr):
        super().__init__()
        self.zmq_addr = zmq_addr
        self.mutex = QMutex()

    def run(self):
        context = zmq.Context()
        sock = context.socket(zmq.SUB)
        sock.setsockopt(zmq.CONFLATE, 1)
        sock.bind(self.zmq_addr)
        sock.setsockopt_string(zmq.SUBSCRIBE, "")
        while not self.isInterruptionRequested():
            try:
                data = sock.recv(flags=zmq.NOBLOCK)
                img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
                if img is not None and img.shape == (FRAME_H, FULL_W):
                    self.frame_received.emit(img.copy())
            except zmq.Again:
                self.msleep(10)
        sock.close()
        context.term()
