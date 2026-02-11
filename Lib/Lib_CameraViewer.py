from PySide6.QtWidgets import QMessageBox, QWidget, QFileDialog
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QTimer, Slot, Signal
from UI.ui_CameraView import Ui_Form
from Core.Core_CameraConnect import CoreCameraConnect
from Core.Core_CameraView import (
    CAMERA_IP,
    ZMQ_ADDR,
    CameraGainExposure,
    ZMQReceiverThread,
    FRAME_W,
    EXPO_MS,
)
from Core.Core_RawImageSave import CoreRawImageSave
import cv2
import os
from datetime import datetime
import numpy as np

class CameraViewerTab(QWidget):
    # ✅ NEW: Signal to update main window status bar
    status_message = Signal(str, int)  # (message, timeout_ms)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        
        # === CAMERA CONNECT ===
        lan_ip = CoreCameraConnect().get_lan_ip()
        self.ui.router_ip_add_in_2.setText(lan_ip)
        
        self.camera_connector = CoreCameraConnect()
        self.ui.detect_2.clicked.connect(self.camera_connector.detect_camera_ip)
        self.ui.connect_2.clicked.connect(self.on_connect_clicked)
        
        self.camera_connector.camera_ip_detected.connect(
            self.ui.cam_ip_add_in_2.setText
        )
        self.camera_connector.camera_ip_detected.connect(
            lambda ip: self.status_message.emit(f"Camera IP detected: {ip}", 0)
        )
        self.camera_connector.camera_connected.connect(self.on_camera_ready)
        self.camera_connector.ssh_error.connect(self.show_ssh_error)
        
        # === GAIN/EXPO CONTROLLER ===
        self.gain_expo = CameraGainExposure()
        self.gain_expo.status_updated.connect(self.on_status_update)
        
        # === CAM 1-4 MAPPING (exact UI names) ===
        self.cam_images = [
            self.ui.cam_image_2,    # CAM 1
            self.ui.cam_image_10,   # CAM 2
            self.ui.cam_image_14,   # CAM 3
            self.ui.cam_image_15,   # CAM 4
        ]
        
        self.gain_sliders = [
            self.ui.gain_slide_2,
            self.ui.gain_slide_10,
            self.ui.gain_slide_14,
            self.ui.gain_slide_15,
        ]
        
        self.expo_sliders = [
            self.ui.exp_slide_2,
            self.ui.exp_slide_10,
            self.ui.exp_slide_14,
            self.ui.exp_slide_15,
        ]
        
        self.gain_status_labels = [
            self.ui.gain_status_2,
            self.ui.gain_status_10,
            self.ui.gain_status_14,
            self.ui.gain_status_15,
        ]
        
        self.expo_status_labels = [
            self.ui.exp_status_2,
            self.ui.exp_status_10,
            self.ui.exp_status_14,
            self.ui.exp_status_15,
        ]
        
        # Connect ALL sliders (cam 0-3)
        for i in range(4):
            cam_idx = i
            self.gain_sliders[i].valueChanged.connect(
                lambda v, idx=cam_idx: self.on_gain_changed(idx, v)
            )
            self.expo_sliders[i].valueChanged.connect(
                lambda v, idx=cam_idx: self.on_expo_changed(idx, v)
            )
        
        # === IMAGE ALIGNMENT ===
        self.ui.img_overlay_open_2.clicked.connect(self.open_image_alignment)
        self.ui.img_overlay_act_2.stateChanged.connect(self.toggle_image_alignment)
        self.alignment_enabled = False
        self.geo_transform = None
        
        # === IMAGE SAVE ===
        self.raw_save = CoreRawImageSave()
        self.raw_save.status_message.connect(self.status_message)  # ✅ Forward status
        
        self.ui.folder_save_open_dir_5.clicked.connect(
            lambda: self.raw_save.select_timestamp_folder(self.ui.folder_save_path_5)
        )
        self.ui.img_save_act_5.stateChanged.connect(self.raw_save.toggle_save_active)
        
        # === ZMQ + SAVE TIMERS ===
        self.zmq_thread = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frames)
        
        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self.save_if_active)
        self.save_timer.start(1000)
        
        self.last_aligned_frame = None
        
    def on_connect_clicked(self):
        ip = self.ui.cam_ip_add_in_2.text().strip()
        if not ip:
            QMessageBox.warning(self, "No IP", "Detect or enter Camera IP")
            return
        
        self.status_message.emit("Connecting to camera...", 0)
        self.camera_connector.ssh_check_camera(ip)
    
    @Slot(str)
    def on_camera_ready(self, ip):
        global CAMERA_IP, ZMQ_ADDR
        CAMERA_IP = ip
        self.gain_expo.set_camera_ip(ip)
        ZMQ_ADDR = self.camera_connector.zmq_address
        
        # ✅ STATUS BAR instead of print
        self.status_message.emit(f"Camera connected: {ip}", 0)
        
        # Query + set initial sliders
        gains = self.gain_expo.get_camera_gains()
        expos = self.gain_expo.get_camera_exposures()
        
        for i in range(4):
            self.gain_sliders[i].setValue(gains[i])
            self.expo_sliders[i].setValue(expos[i])
        
        self.start_zmq_streaming()
    
    def show_ssh_error(self, msg):
        # ✅ QMessageBox for errors
        QMessageBox.critical(self, "SSH Connection Failed", msg)
    
    @Slot(int, str, str)
    def on_status_update(self, idx, gain_str, expo_str):
        self.gain_status_labels[idx].setText(gain_str)
        self.expo_status_labels[idx].setText(expo_str)
    
    @Slot(int, int)
    def on_gain_changed(self, cam_idx, gain_val):
        self.gain_expo.set_camera_gain(cam_idx, gain_val)
        expo_val = self.expo_sliders[cam_idx].value()
        self.gain_expo.update_status_label(cam_idx, gain_val, expo_val)
    
    @Slot(int, int)
    def on_expo_changed(self, cam_idx, expo_val):
        self.gain_expo.set_camera_expo(cam_idx, expo_val)
        gain_val = self.gain_sliders[cam_idx].value()
        self.gain_expo.update_status_label(cam_idx, gain_val, expo_val)
    
    def start_zmq_streaming(self):
        if self.zmq_thread and self.zmq_thread.isRunning():
            self.zmq_thread.requestInterruption()
            self.zmq_thread.wait()
        
        self.zmq_thread = ZMQReceiverThread(ZMQ_ADDR)
        self.zmq_thread.frame_received.connect(self.on_frame_received)
        self.zmq_thread.start()
        self.update_timer.start(33)
        
        # ✅ STATUS BAR
        self.status_message.emit("ZMQ streaming started", 0)
    
    @Slot(object)
    def on_frame_received(self, full_frame):
        import Core.Core_CameraView as ccv
        ccv.last_fullframe = full_frame
    
    @Slot()
    def update_frames(self):
        from Core.Core_CameraView import last_fullframe
        
        if last_fullframe is None:
            return
        
        # Update current expo for filename every frame
        self.update_expo_for_save()
        
        # Apply alignment if enabled
        aligned_frame = last_fullframe
        if self.alignment_enabled and self.geo_transform is not None:
            aligned_frame = self.apply_alignment(last_fullframe)
        
        self.last_aligned_frame = aligned_frame if self.alignment_enabled else None
        
        for i in range(4):
            tile = aligned_frame[:, i * FRAME_W : (i + 1) * FRAME_W]
            tile_rgb = cv2.cvtColor(tile, cv2.COLOR_GRAY2RGB)
            
            # Highlight overexposure in red
            mask = tile >= 255
            tile_rgb[mask] = [255, 0, 0]
            
            h, w = tile_rgb.shape[:2]
            bytes_per_line = 3 * w
            qimg = QImage(tile_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(
                self.cam_images[i].size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.cam_images[i].setPixmap(pixmap)
    
    def apply_alignment(self, full_frame):
        """Apply geometric transformation to align all bands to Band 1."""
        bands = [
            full_frame[:, 0:640],
            full_frame[:, 640:1280],
            full_frame[:, 1280:1920],
            full_frame[:, 1920:2560],
        ]
        
        aligned_bands = [bands[0]]
        
        for i in [2, 3, 4]:
            H_key = f"H_{i}1"
            H = self.geo_transform.homography_matrices.get(H_key)
            
            if H is not None:
                aligned = cv2.warpPerspective(
                    bands[i - 1],
                    H,
                    (640, 480),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=0,
                )
                aligned_bands.append(aligned)
            else:
                # ✅ QMessageBox for error (only first time)
                if not hasattr(self, f'_warned_{H_key}'):
                    QMessageBox.warning(
                        self,
                        "Missing Transformation",
                        f"Transformation matrix {H_key} not found. Using original band."
                    )
                    setattr(self, f'_warned_{H_key}', True)
                aligned_bands.append(bands[i - 1])
        
        aligned_frame = np.hstack(aligned_bands)
        return aligned_frame
    
    def update_expo_for_save(self):
        """Update saver with current slider exposures (for filename)."""
        exp_ms100 = []
        for slider in self.expo_sliders:
            level = max(1, min(12, slider.value()))
            ms = EXPO_MS[level - 1]
            exp_ms100.append(int(round(ms * 100)))
        self.raw_save.exp_ms100 = exp_ms100
    
    @Slot()
    def save_if_active(self):
        """Periodic check and save frame if checkbox is enabled."""
        self.raw_save.save_frame_if_active()
    
    @Slot()
    def open_image_alignment(self):
        """Open image alignment dialog with current frame."""
        from Core.Core_CameraView import last_fullframe
        from Lib.Lib_ImageAlignment import ImageAlignmentDialog
        from PySide6.QtWidgets import QDialog
        
        if last_fullframe is None:
            QMessageBox.warning(
                self,
                "No Frame",
                "Start camera streaming first to capture images for alignment.",
            )
            return
        
        # Split frame into 4 bands
        images = [
            last_fullframe[:, 0 * FRAME_W : 1 * FRAME_W],
            last_fullframe[:, 1 * FRAME_W : 2 * FRAME_W],
            last_fullframe[:, 2 * FRAME_W : 3 * FRAME_W],
            last_fullframe[:, 3 * FRAME_W : 4 * FRAME_W],
        ]
        
        dlg = ImageAlignmentDialog(self)
        
        # ✅ Connect dialog status to main window
        dlg.status_message.connect(self.status_message)
        
        dlg.load_images(images)
        
        result = dlg.exec()
        
        if result == QDialog.Accepted:
            self.geo_transform = dlg.geo_transform
            self.status_message.emit("Transformation matrices loaded", 0)
        
    @Slot(int)
    def toggle_image_alignment(self, state):
        """Toggle real-time image alignment on/off."""
        self.alignment_enabled = bool(state)
        
        if self.alignment_enabled:
            if self.geo_transform is None:
                QMessageBox.warning(
                    self,
                    "No Transformation",
                    "Please calculate transformation matrices first using\n"
                    "'Image Alignment Settings' button",
                )
                self.ui.img_overlay_act_2.setChecked(False)
                self.alignment_enabled = False
                return
            # ✅ STATUS BAR
            self.status_message.emit("Image alignment enabled", 0)
        else:
            # ✅ STATUS BAR
            self.status_message.emit("Image alignment disabled", 0)
