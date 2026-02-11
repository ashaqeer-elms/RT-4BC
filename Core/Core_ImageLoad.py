from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt
import cv2
import numpy as np

# Frame dimensions
FRAME_H = 480
FRAME_W = 640
FULL_W = FRAME_W * 4


def load_reference_image(entry, ref_labels_local, tiles_store=None, path=None):
    """
    Load a reference/background image, split into 4 tiles, and display.
    
    Args:
        entry: QLineEdit widget to display file path
        ref_labels_local: List of 4 QLabel widgets for displaying tiles
        tiles_store: Optional list to store raw numpy arrays
        path: Optional path to load directly (for auto-load)
    """
    # If path is not provided, use file dialog (manual mode)
    if path is None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Select Reference Image",
            "",
            "PNG files (*.png)"
        )
    
    if not path:
        return
    
    entry.setText(path)
    
    # Load image as grayscale
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        QMessageBox.critical(None, "Load Error", "Failed to load image as grayscale.")
        return
    
    # Validate shape
    if img.shape != (FRAME_H, FULL_W):
        QMessageBox.critical(
            None,
            "Shape Error",
            f"Expected shape (480, {FULL_W}), got {img.shape}."
        )
        return
    
    # Split into 4 tiles and display
    for i in range(4):
        tile = img[:, i * FRAME_W : (i + 1) * FRAME_W]
        
        # Store raw tile if requested
        if tiles_store is not None:
            tiles_store[i] = tile.copy()
        
        # Convert to RGB for display
        tile_rgb = cv2.cvtColor(tile, cv2.COLOR_GRAY2RGB)
        
        # Convert to QPixmap
        h, w = tile_rgb.shape[:2]
        bytes_per_line = 3 * w
        qimg = QImage(tile_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            ref_labels_local[i].size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        ref_labels_local[i].setPixmap(pixmap)
