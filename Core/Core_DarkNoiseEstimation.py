from PySide6.QtCore import QObject
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt
import cv2
import numpy as np
import os

# Background noise tiles storage
bg_tiles = [None, None, None, None]

class CoreDarkNoiseEstimator(QObject):
    """Handles dark/background noise estimation for calibration."""
    
    def __init__(self):
        super().__init__()
        self.bg_tiles = [None, None, None, None]
    
    def auto_load_background(self, bg_entry, bg_labels):
        """
        On initialization, try to load the first PNG from
        Data/Calibration/Background folder and auto-estimate background noise.
        
        Args:
            bg_entry: QLineEdit for file path
            bg_labels: List of 4 QLabel widgets
        """
        try:
            # Get absolute path to script directory and resolve parent
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)  # Go up one level from Core/
            
            # ✅ UPDATED PATH: Data/Calibration/Background
            bg_dir = os.path.join(parent_dir, "Data", "Calibration", "Background")
            
            # Normalize path to resolve any .. or . components
            bg_dir = os.path.normpath(bg_dir)
            
            if not os.path.isdir(bg_dir):
                print(f"Background folder not found: {bg_dir}")
                return
            
            candidates = [f for f in os.listdir(bg_dir) if f.lower().endswith(".png")]
            if not candidates:
                print("No PNG files found in Background folder")
                return
            
            bg_path = os.path.join(bg_dir, candidates[0])
            # Normalize the full path as well
            bg_path = os.path.normpath(bg_path)
            
            # print(f"Auto-loading background: {bg_path}")
            
            # Load that image
            from Core.Core_ImageLoad import load_reference_image
            load_reference_image(
                bg_entry, bg_labels, tiles_store=self.bg_tiles, path=bg_path
            )
            
        except Exception as e:
            print(f"Auto background load error: {e}")
    
    def estimate_background_noise(self, bg_labels, bg_cam_entries):
        """
        Estimate background noise by calculating mean of center 100x100 ROI.
        Draw blue rectangle on ROI and update entry fields.
        
        Args:
            bg_labels: List of 4 QLabel widgets for display
            bg_cam_entries: List of 4 QLineEdit widgets for values
        """
        if len(bg_labels) != 4 or len(bg_cam_entries) != 4:
            print("Invalid labels or entries count")
            return
        
        for i in range(4):
            tile = self.bg_tiles[i]
            if tile is None:
                continue
            
            h, w = tile.shape
            win_size = 100
            cx, cy = w // 2, h // 2
            
            # Calculate ROI bounds
            x1 = max(0, cx - win_size // 2)
            y1 = max(0, cy - win_size // 2)
            x2 = min(w, cx + win_size // 2)
            y2 = min(h, cy + win_size // 2)
            
            roi = tile[y1:y2, x1:x2]
            
            if roi.size == 0:
                mean_val = 0.0
            else:
                mean_val = float(np.mean(roi))
            
            # Draw rectangle on tile
            tile_rgb = cv2.cvtColor(tile, cv2.COLOR_GRAY2RGB)
            cv2.rectangle(tile_rgb, (x1, y1), (x2 - 1, y2 - 1), (255, 0, 0), 2)  # Blue rectangle
            
            # Convert to QPixmap and display
            h_rgb, w_rgb = tile_rgb.shape[:2]
            bytes_per_line = 3 * w_rgb
            qimg = QImage(tile_rgb.data, w_rgb, h_rgb, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(
                bg_labels[i].size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            bg_labels[i].setPixmap(pixmap)
            
            # Update entry field
            bg_cam_entries[i].setText(f"{mean_val:.2f}")
        
        # print("✅ Background noise estimated")
