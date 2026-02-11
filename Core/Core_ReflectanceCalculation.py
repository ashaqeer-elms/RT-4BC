from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
import numpy as np

# Frame dimensions
FRAME_H = 480
FRAME_W = 640


class CoreReflectanceCalculator(QObject):
    """Handles reflectance calculation from raw camera frames."""
    
    def __init__(self):
        super().__init__()
        self.warning_invalid_params_shown = False
    
    def calculate_reflectance(self, last_fullframe, bg_tiles, expo_sliders, ref_cam_entries, EXPO_MS):
        """
        Calculate reflectance for each CAM using formula:
        reflectance_i = (CAM_i - BG_i) / exposure_i / ref_radiance_i
        
        Args:
            last_fullframe: Full camera frame (480 x 2560)
            bg_tiles: List of 4 background noise tiles
            expo_sliders: List of 4 QSlider widgets for exposure
            ref_cam_entries: List of 4 QLineEdit widgets with reference radiance values
            EXPO_MS: Exposure time lookup table
            
        Returns:
            List of 4 reflectance tiles (numpy float32 arrays) or None if error
        """
        if last_fullframe is None:
            return None
        
        reflectance_tiles = []
        
        for i in range(4):
            # Check if background tile exists
            if bg_tiles[i] is None:
                if not self.warning_invalid_params_shown:
                    QMessageBox.warning(
                        None,
                        "Missing Background",
                        "Please load and estimate background noise first (Tab 2)."
                    )
                    self.warning_invalid_params_shown = True
                return None
            
            # Extract camera tile for this band
            cam_tile = last_fullframe[:, i * FRAME_W : (i + 1) * FRAME_W].astype(np.float32)
            bg_tile = bg_tiles[i].astype(np.float32)
            
            # Get exposure time from slider
            if i < len(expo_sliders):
                level = int(expo_sliders[i].value())
                level = max(1, min(12, level))
                exp_ms = EXPO_MS[level - 1]
            else:
                exp_ms = 1.0
            
            # Get reference radiance from entry field
            try:
                ref_rad = float(ref_cam_entries[i].text())
            except Exception:
                ref_rad = 0.0
            
            # Validate parameters
            if exp_ms == 0 or ref_rad == 0:
                if not self.warning_invalid_params_shown:
                    QMessageBox.warning(
                        None,
                        "Invalid Parameters",
                        f"Exposure or reference radiance is zero for BAND {i+1}.\n"
                        f"Please set valid values in Tab 2."
                    )
                    self.warning_invalid_params_shown = True
                return None
            
            # Calculate reflectance
            numerator = cam_tile - bg_tile
            refl = numerator / exp_ms / ref_rad
            
            # print(f"🔍 BAND {i+1} reflectance: exp={exp_ms:.2f}ms, ref_rad={ref_rad:.2f}, range=[{np.min(refl):.4f}, {np.max(refl):.4f}]")
            
            reflectance_tiles.append(refl)
        
        return reflectance_tiles
