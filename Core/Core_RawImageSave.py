from PySide6.QtCore import QObject, Slot, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox
import os
from datetime import datetime
import cv2
import numpy as np

class CoreRawImageSave(QObject):
    # ✅ NEW: Signal for status bar updates
    status_message = Signal(str, int)  # (message, timeout_ms)
    
    def __init__(self):
        super().__init__()
        self.save_dir = ""
        self.exp_ms100 = [0, 0, 0, 0]
        self.save_active = False
    
    @Slot()
    def select_timestamp_folder(self, entry):
        base = QFileDialog.getExistingDirectory(None, "Select Base Folder")
        if not base:
            return
        
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = os.path.join(base, stamp)
        
        try:
            os.makedirs(target, exist_ok=False)
            entry.setText(target)
            self.save_dir = target
            # ✅ STATUS BAR
            self.status_message.emit(f"Save folder: {stamp}", 0)
        except FileExistsError:
            # ✅ QMessageBox for error
            QMessageBox.warning(
                None,
                "Folder Exists",
                f"Folder already exists: {target}\nPlease wait 1 second and try again."
            )
    
    @Slot(int)
    def toggle_save_active(self, state):
        self.save_active = bool(state)
        # ✅ STATUS BAR
        status = "ON" if self.save_active else "OFF"
        self.status_message.emit(f"Image saving: {status}", 0)
    
    def save_frame_if_active(self):
        from Core.Core_CameraView import last_fullframe
        
        if not self.save_active:
            return
        
        if last_fullframe is None:
            return
        
        if not isinstance(last_fullframe, np.ndarray) or last_fullframe.size == 0:
            return
        
        if not self.save_dir or not os.path.isdir(self.save_dir):
            return
        
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = os.path.join(
                self.save_dir,
                f"{stamp}_{self.exp_ms100[0]:04d}_{self.exp_ms100[1]:04d}_{self.exp_ms100[2]:04d}_{self.exp_ms100[3]:04d}.png"
            )
            
            success = cv2.imwrite(fname, last_fullframe)
            
            if success:
                # ✅ STATUS BAR (brief message)
                self.status_message.emit(f"Saved: {os.path.basename(fname)}", 0)
            else:
                # ✅ QMessageBox for error (but don't spam)
                if not hasattr(self, '_write_error_shown'):
                    QMessageBox.critical(
                        None,
                        "Write Failed",
                        f"Failed to write image: {fname}"
                    )
                    self._write_error_shown = True
        except Exception as e:
            # ✅ QMessageBox for error
            QMessageBox.critical(
                None,
                "Save Error",
                f"Error saving image: {str(e)}"
            )
