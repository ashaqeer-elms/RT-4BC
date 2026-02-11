from PySide6.QtCore import QObject
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
import cv2
import numpy as np
import os

class CoreRefRadianceEstimator(QObject):
    """Handles reference radiance estimation for calibration."""
    
    def __init__(self):
        super().__init__()
        self.ref_tiles = [None, None, None, None]
    
    def auto_load_reference(self, ref_entry, ref_labels):
        """
        On initialization, try to load the first PNG from
        Data/Calibration/Reference folder.
        
        Args:
            ref_entry: QLineEdit for file path
            ref_labels: List of 4 QLabel widgets
        """
        try:
            # Get absolute path to script directory and resolve parent
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)  # Go up one level from Core/
            
            # ✅ UPDATED PATH: Data/Calibration/Reference
            ref_dir = os.path.join(parent_dir, "Data", "Calibration", "Reference")
            
            # Normalize path to resolve any .. or . components
            ref_dir = os.path.normpath(ref_dir)
            
            if not os.path.isdir(ref_dir):
                print(f"Reference folder not found: {ref_dir}")
                return
            
            candidates = [f for f in os.listdir(ref_dir) if f.lower().endswith(".png")]
            if not candidates:
                print("No PNG files found in Reference folder")
                return
            
            ref_path = os.path.join(ref_dir, candidates[0])
            # Normalize the full path as well
            ref_path = os.path.normpath(ref_path)
            
            #print(f"Auto-loading reference: {ref_path}")
            
            # Load that image
            from Core.Core_ImageLoad import load_reference_image
            load_reference_image(
                ref_entry, ref_labels, tiles_store=self.ref_tiles, path=ref_path
            )
            
        except Exception as e:
            print(f"Auto reference load error: {e}")
    
    def estimate_reference_radiance(self, ref_entry, ref_labels, ref_cam_entries, bg_cam_entries):
        """
        Estimate reference radiance using formula:
            ref_radiance = (mean_pixel - background) / exposure_time
        
        Exposure values are parsed from filename format:
            ...YYYYMMDD_HHMMSS_exp1_exp2_exp3_exp4.png
            (where exp values are in units of ms*100, e.g., 448 = 4.48ms)
        
        Args:
            ref_entry: QLineEdit with reference image path
            ref_labels: List of 4 QLabel widgets for display
            ref_cam_entries: List of 4 QLineEdit widgets for radiance values
            bg_cam_entries: List of 4 QLineEdit widgets with background values from Tab 2
        """
        if len(ref_labels) != 4 or len(ref_cam_entries) != 4:
            print("Invalid labels or entries count")
            return
        
        # Get reference image path
        ref_path = ref_entry.text().strip()
        if not ref_path:
            QMessageBox.warning(
                None,
                "No Reference Image",
                "Please load a reference image first."
            )
            return
        
        # Parse filename for exposure values
        base = os.path.basename(ref_path)
        root_name, ext = os.path.splitext(base)
        parts = root_name.split("_")
        
        # Filename format: YYYYMMDD_HHMMSS_exp1_exp2_exp3_exp4.png
        # So we need at least 6 parts (date, time, 4 exposures)
        if len(parts) < 6:
            QMessageBox.warning(
                None,
                "Filename Error",
                "Reference filename does not contain 4 exposure values.\n"
                f"Expected format: YYYYMMDD_HHMMSS_exp1_exp2_exp3_exp4.png"
            )
            return
        
        # Last 4 parts are exposures * 100 (e.g., 448 means 4.48ms)
        try:
            expo100_vals = [int(parts[-4]), int(parts[-3]), int(parts[-2]), int(parts[-1])]
        except Exception:
            QMessageBox.warning(
                None,
                "Filename Error",
                "Failed to parse exposure values from filename."
            )
            return
        
        # Process each camera/band
        for i in range(4):
            tile = self.ref_tiles[i]
            if tile is None:
                continue
            
            h, w = tile.shape
            win_size = 100
            cx, cy = w // 2, h // 2
            
            # Calculate ROI bounds (center 100x100 pixels)
            x1 = max(0, cx - win_size // 2)
            y1 = max(0, cy - win_size // 2)
            x2 = min(w, cx + win_size // 2)
            y2 = min(h, cy + win_size // 2)
            
            roi = tile[y1:y2, x1:x2]
            
            if roi.size == 0:
                mean_val = 0.0
            else:
                mean_val = float(np.mean(roi))
            
            # print(f"🔍 BAND {i+1} - ROI mean pixel value: {mean_val:.2f}")
            
            # Background noise for this CAM from Tab 2 (fallback 0)
            try:
                bg_val = float(bg_cam_entries[i].text())
            except Exception:
                bg_val = 0.0
            
            # print(f"   Background value: {bg_val:.2f}")
            
            # Exposure in ms (divide by 100 from filename)
            exp_ms = expo100_vals[i] / 100.0 if expo100_vals[i] != 0 else 1.0
            
            # print(f"   Exposure time: {exp_ms:.2f} ms")
            
            # Reference radiance formula: (mean - background) / exposure
            ref_rad = (mean_val - bg_val) / exp_ms
            
            # print(f"   ➡️ Reference radiance: ({mean_val:.2f} - {bg_val:.2f}) / {exp_ms:.2f} = {ref_rad:.2f}\n")
            
            # Draw blue rectangle on tile to show ROI
            tile_rgb = cv2.cvtColor(tile, cv2.COLOR_GRAY2RGB)
            cv2.rectangle(tile_rgb, (x1, y1), (x2 - 1, y2 - 1), (255, 0, 0), 2)
            
            # Convert to QPixmap and display
            h_rgb, w_rgb = tile_rgb.shape[:2]
            bytes_per_line = 3 * w_rgb
            qimg = QImage(tile_rgb.data, w_rgb, h_rgb, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(
                ref_labels[i].size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            ref_labels[i].setPixmap(pixmap)
            
            # Update entry field with calculated radiance
            ref_cam_entries[i].setText(f"{ref_rad:.2f}")
        
        # print("✅ Reference radiance estimated")
