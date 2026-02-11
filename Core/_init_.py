"""
Global imports for Lib modules - reduces repetition.
Usage: from Lib import *
"""

# Core libs (always needed)
import os
import re
import socket
import threading
import time
from datetime import datetime
from pathlib import Path

# Computer vision
import cv2
import numpy as np

# Networking/SSH
import paramiko
import zmq

# PySide6 essentials
from PySide6.QtCore import (Signal, Slot, QObject, QTimer, QEvent, Qt)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QFileDialog, QMessageBox, QWidget)

# Constants (global access)
SSH_ROUTER_IP = "192.168.2.1"
SSH_ROUTER_USER = "root"
SSH_CAMERA_USER = "pi"
FRAME_H = 480
FRAME_W = 640
FULL_W = FRAME_W * 4
CAM_DEVICES = ['/dev/video0', '/dev/video2', '/dev/video4', '/dev/video6']
EXPO_ABS = [1, 2, 5, 10, 20, 39, 78, 156, 312, 625, 1250, 2500]
EXPO_MS = [0.04, 0.15, 0.52, 1.08, 2.24, 4.48, 9.03, 18.14, 36.04, 72.99, 146.05, 292.21]
