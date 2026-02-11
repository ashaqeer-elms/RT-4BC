from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QTableWidgetItem
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QImage, QPixmap
import numpy as np
import cv2
import os
import seaborn as sns

from UI.ui_ImageAlignment import Ui_Dialog
from Core.Core_GeoTransform import CoreGeoTransform

class ImageAlignmentDialog(QDialog):
    """
    Image alignment dialog for multi-band camera alignment.
    """
    
    # ✅ NEW: Signal for status messages (forwarded to main window)
    status_message = Signal(str, int)  # (message, timeout_ms)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        
        # Core transformation handler
        self.geo_transform = CoreGeoTransform()
        # ✅ Connect geo_transform signals
        self.geo_transform.error_occurred.connect(self.show_error_message)
        
        # Store raw band images (4 bands, 640x480 each)
        self.band_images = [None, None, None, None]
        
        # Full frame labels (one per camera)
        self.full_labels = [
            self.ui.label_2,  # CAM 1
            self.ui.label,    # CAM 2
            self.ui.label_3,  # CAM 3
            self.ui.label_4   # CAM 4
        ]
        
        # Zoom frame labels (4 separate zooms)
        self.zoom_labels = [
            self.ui.label_6,  # Band 1 zoom
            self.ui.label_5,  # Band 2 zoom
            self.ui.label_7,  # Band 3 zoom
            self.ui.label_8   # Band 4 zoom
        ]
        
        # Increase label sizes
        for label in self.full_labels:
            label.setMinimumSize(320, 240)
            label.setMaximumSize(640, 480)
            label.setScaledContents(True)
        
        for label in self.zoom_labels:
            label.setMinimumSize(250, 250)
            label.setMaximumSize(400, 400)
            label.setScaledContents(True)
        
        # Resize dialog window
        self.resize(1800, 1100)
        
        # Current bounding box center positions
        self.box_centers = [None, None, None, None]
        self.zoom_click_positions = [None, None, None, None]
        self.final_positions = [None, None, None, None]
        
        # Manual point collection
        self.manual_points = []
        
        # Zoom window size
        self.zoom_size = 100
        
        # Setup UI connections
        self.setup_connections()
        
        # Make labels clickable
        self.setup_clickable_labels()
        
        # ✅ STATUS MESSAGE instead of print
        self.status_message.emit("Image Alignment Dialog opened", 0)
    
    def show_error_message(self, error_text):
        """Show error from CoreGeoTransform as QMessageBox."""
        QMessageBox.critical(self, "Transformation Error", error_text)
    
    def setup_connections(self):
        # "Add Point" button
        self.ui.pushButton_2.clicked.connect(self.on_add_point_clicked)
        
        # Transformation buttons
        self.ui.pushButton.clicked.connect(self.automatic_transformation)
        self.ui.pushButton_3.clicked.connect(self.calculate_manual_transformation)
        
        # Load configuration
        self.ui.bg_img_open_dir.clicked.connect(self.select_config_file)
        self.ui.bg_img_load.clicked.connect(self.load_config_file)
        
        # ✅ SAVE CONFIGURATION (FIXED)
        self.ui.folder_save_open_dir_3.clicked.connect(self.select_save_folder)
        self.ui.bg_img_load_2.clicked.connect(self.save_configuration)  # This saves the config
        
        # Reset and Delete
        self.ui.pushButton_4.clicked.connect(self.on_reset_clicked)
        self.ui.pushButton_5.clicked.connect(self.on_delete_clicked)
        
        # Load Calibration Image
        self.ui.bg_img_open_dir_2.clicked.connect(self.select_calibration_image)
        self.ui.bg_img_load_3.clicked.connect(self.load_calibration_image)
        
        # Apply button
        self.ui.pushButton_6.clicked.connect(self.on_apply_clicked)

    def setup_clickable_labels(self):
        # Make each full-frame label react to mouse click
        for i, lbl in enumerate(self.full_labels):
            lbl.setMouseTracking(True)
            lbl.mousePressEvent = lambda ev, idx=i: self.on_full_frame_click(ev, idx)

        # Make each zoom label react to single-click → select coordinate
        for i, lbl in enumerate(self.zoom_labels):
            lbl.mousePressEvent = lambda ev, idx=i: self.on_zoom_click(ev, idx)

    # ---------- Loading images and initial center boxes ----------

    def load_images(self, images):
        """Load 4 band images into the dialog."""
        if len(images) != 4:
            QMessageBox.warning(self, "Error", "Expected 4 band images")
            return
        
        self.band_images = images
        
        # Initialize bounding box centers at image center
        h, w = images[0].shape[:2]
        cx, cy = w // 2, h // 2
        
        for i in range(4):
            self.box_centers[i] = (cx, cy)
            self.final_positions[i] = (cx, cy)
        
        # Draw initial boxes and zooms
        for i in range(4):
            self.update_full_frame(i)
            self.update_zoom_frame(i)
        
        # ✅ STATUS MESSAGE
        self.status_message.emit("Images loaded for alignment", 0)
   
    # ---------- Drawing full frame with box + crosshair ----------

    def update_full_frame(self, band_idx):
        img = self.band_images[band_idx]
        if img is None:
            return

        # Make RGB copy
        if img.ndim == 2:
            rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            rgb = img.copy()

        # Draw red bounding box + green crosshair at box center
        x, y = self.box_centers[band_idx]
        half = self.zoom_size // 2
        h, w = img.shape[:2]

        x1 = max(0, x - half)
        y1 = max(0, y - half)
        x2 = min(w, x + half)
        y2 = min(h, y + half)

        # Red box
        cv2.rectangle(rgb, (x1, y1), (x2 - 1, y2 - 1), (255, 0, 0), 2)
        
        # Green crosshair at final selected position (if different from center)
        if self.final_positions[band_idx] is not None:
            fx, fy = self.final_positions[band_idx]
            cv2.drawMarker(rgb, (fx, fy), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)

        # Convert to QPixmap scaled to label size
        h_rgb, w_rgb = rgb.shape[:2]
        bytes_per_line = 3 * w_rgb
        qimg = QImage(rgb.data, w_rgb, h_rgb, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.full_labels[band_idx].size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.full_labels[band_idx].setPixmap(pixmap)

    # ---------- Drawing zoom (100x100 ROI) ----------

    def update_zoom_frame(self, band_idx):
        img = self.band_images[band_idx]
        if img is None:
            return

        x, y = self.box_centers[band_idx]
        half = self.zoom_size // 2
        h, w = img.shape[:2]

        x1 = max(0, x - half)
        y1 = max(0, y - half)
        x2 = min(w, x + half)
        y2 = min(h, y + half)

        roi = img[y1:y2, x1:x2].copy()
        if roi.ndim == 2:
            rgb = cv2.cvtColor(roi, cv2.COLOR_GRAY2RGB)
        else:
            rgb = roi.copy()

        # Draw green crosshair at clicked position in zoom (if clicked)
        if self.zoom_click_positions[band_idx] is not None:
            zx, zy = self.zoom_click_positions[band_idx]
            # Ensure crosshair is within ROI bounds
            if 0 <= zx < rgb.shape[1] and 0 <= zy < rgb.shape[0]:
                cv2.drawMarker(rgb, (zx, zy), (0, 255, 0), cv2.MARKER_CROSS, 5, 1)

        h_rgb, w_rgb = rgb.shape[:2]
        bytes_per_line = 3 * w_rgb
        qimg = QImage(rgb.data, w_rgb, h_rgb, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.zoom_labels[band_idx].size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.zoom_labels[band_idx].setPixmap(pixmap)

    # ---------- Mouse interaction ----------

    def on_full_frame_click(self, event, band_idx):
        """
        Single click on a full-frame label:
        - Convert label coords → image coords
        - Move bounding box center to that point
        - Update full frame and zoom for that band
        """
        img = self.band_images[band_idx]
        if img is None:
            return

        label = self.full_labels[band_idx]
        pixmap = label.pixmap()
        if pixmap is None:
            return

        # Position in label
        lx, ly = event.pos().x(), event.pos().y()
        lw, lh = label.width(), label.height()
        pw, ph = pixmap.width(), pixmap.height()

        # Compute offsets (pixmap centered in label)
        off_x = (lw - pw) // 2
        off_y = (lh - ph) // 2

        # Position relative to pixmap
        px = lx - off_x
        py = ly - off_y

        if px < 0 or py < 0 or px >= pw or py >= ph:
            return

        ih, iw = img.shape[:2]
        scale_x = iw / pw
        scale_y = ih / ph

        orig_x = int(px * scale_x)
        orig_y = int(py * scale_y)

        # Update bounding box center for this band
        self.box_centers[band_idx] = (orig_x, orig_y)
        
        # Reset zoom click position (user needs to click zoom again)
        self.zoom_click_positions[band_idx] = None
        
        # Initialize final position at box center
        self.final_positions[band_idx] = (orig_x, orig_y)

        # Redraw box + zoom
        self.update_full_frame(band_idx)
        self.update_zoom_frame(band_idx)
        
        # print(f"👆 Band {band_idx+1} box moved to ({orig_x}, {orig_y})")

    def on_zoom_click(self, event, band_idx):
        """
        Single-click on zoom frame: select precise coordinate within zoom window.
        """
        img = self.band_images[band_idx]
        if img is None:
            return
        
        label = self.zoom_labels[band_idx]
        pixmap = label.pixmap()
        if pixmap is None:
            return
        
        # Get click position in label
        lx, ly = event.pos().x(), event.pos().y()
        lw, lh = label.width(), label.height()
        pw, ph = pixmap.width(), pixmap.height()
        
        # Compute offsets (pixmap is centered in label)
        off_x = (lw - pw) // 2
        off_y = (lh - ph) // 2
        
        # Position relative to pixmap
        px = lx - off_x
        py = ly - off_y
        
        # Check if click is within pixmap bounds
        if px < 0 or py < 0 or px >= pw or py >= ph:
            return
        
        # Get bounding box coordinates in original image
        box_x, box_y = self.box_centers[band_idx]
        half = self.zoom_size // 2
        h, w = img.shape[:2]
        
        x1 = max(0, box_x - half)
        y1 = max(0, box_y - half)
        x2 = min(w, box_x + half)
        y2 = min(h, box_y + half)
        
        # Actual zoom ROI size (might be less than 100 at edges)
        zoom_w = x2 - x1
        zoom_h = y2 - y1
        
        # ✅ FIX: Scale from PIXMAP coords → ROI coords
        # Pixmap is scaled version of ROI, so we need ROI/pixmap ratio
        scale_x = zoom_w / float(pw)
        scale_y = zoom_h / float(ph)
        
        # Convert pixmap click position to ROI coordinates
        zoom_x = int(px * scale_x)
        zoom_y = int(py * scale_y)
        
        # Clamp to ROI bounds
        zoom_x = max(0, min(zoom_x, zoom_w - 1))
        zoom_y = max(0, min(zoom_y, zoom_h - 1))
        
        # Store zoom click position (relative to zoom ROI)
        self.zoom_click_positions[band_idx] = (zoom_x, zoom_y)
        
        # Calculate final position in original image coordinates
        final_x = x1 + zoom_x
        final_y = y1 + zoom_y
        
        # Clamp to image bounds
        final_x = max(0, min(final_x, w - 1))
        final_y = max(0, min(final_y, h - 1))
        
        self.final_positions[band_idx] = (final_x, final_y)
        
        # Redraw zoom and full frame
        self.update_zoom_frame(band_idx)
        self.update_full_frame(band_idx)
        
        # Debug output (optional)
        # print(f"🎯 Band {band_idx+1}: Click ({px},{py}) → ROI ({zoom_x},{zoom_y}) → Image ({final_x},{final_y})")

    # ---------- Manual point addition ----------

    @Slot()
    def on_add_point_clicked(self):
        """Add current 4-band coordinates to the table."""
        if any(pos is None for pos in self.final_positions):
            QMessageBox.warning(
                self,
                "Incomplete Selection",
                "Please click on all 4 zoom frames to select coordinates\nbefore adding a point.",
            )
            return
        
        # Build point dict
        point = {
            "B1": self.final_positions[0],
            "B2": self.final_positions[1],
            "B3": self.final_positions[2],
            "B4": self.final_positions[3],
        }
        
        self.manual_points.append(point)
        row = len(self.manual_points) - 1
        
        # Add to table
        for col, band in enumerate(["B1", "B2", "B3", "B4"]):
            x, y = point[band]
            self.ui.tableWidget.setItem(row, col, QTableWidgetItem(f"{y} {x}"))
        
        # ✅ STATUS MESSAGE
        self.status_message.emit(f"Point {row+1} added to correspondence table", 0)
    
    @Slot()
    def automatic_transformation(self):
        """Calculate transformation using AKAZE feature detection."""
        if any(img is None for img in self.band_images):
            QMessageBox.warning(self, "No Images", "Load 4 band images first")
            return
        
        # ✅ STATUS MESSAGE
        self.status_message.emit("Calculating automatic transformation...", 0)
        
        # Run automatic estimation
        results = self.geo_transform.automatic_transformation_estimation(
            self.band_images,
            return_matches=True
        )
        
        if results is None:
            QMessageBox.critical(self, "Failed", "Automatic transformation failed")
            self.status_message.emit("Automatic transformation failed", 0)
            return
        
        # Extract homographies and matches
        homographies = {}
        matches_info = {}
        for key, value in results.items():
            if key.startswith('H_'):
                homographies[key] = value
            elif key.startswith('matches_'):
                matches_info[key] = value
        
        # Add H_11 identity matrix
        homographies['H_11'] = np.eye(3, dtype=np.float32)
        
        # Display results
        result_text = "=== Automatic Transformation Results ===\n\n"
        
        for key in ['H_11', 'H_21', 'H_31', 'H_41']:
            H = homographies.get(key)
            if H is not None:
                result_text += f"{key}:\n"
                result_text += f"{H}\n\n"
            else:
                result_text += f"{key}: FAILED\n\n"
        
        # Add match statistics
        if matches_info:
            result_text += "\n=== Feature Matching Statistics ===\n\n"
            for key, info in matches_info.items():
                if info is not None:
                    band_pair = key.replace('matches_', '')
                    result_text += f"{band_pair}:\n"
                    result_text += f"  Keypoints detected: {info.get('num_kp1', 0)} → {info.get('num_kp2', 0)}\n"
                    result_text += f"  Matches found: {info.get('num_matches', 0)}\n"
                    result_text += f"  Inliers (RANSAC): {info.get('num_inliers', 0)}\n\n"
        
        self.ui.textBrowser.setText(result_text)
        
        # Visualize feature matches
        self.visualize_feature_matches(matches_info)
        
        # ✅ STATUS MESSAGE
        self.status_message.emit("Automatic transformation complete", 0)
    
    def visualize_feature_matches(self, matches_info):
        """Visualize AKAZE feature matches on full frame labels."""
        if not matches_info:
            return
        
        # Generate distinct colors
        num_colors = 50
        colors_rgb = sns.color_palette("husl", n_colors=num_colors)
        glasbey_colors = [(int(c[2]*255), int(c[1]*255), int(c[0]*255)) for c in colors_rgb]
        
        # Process each band pair
        for band_idx in [1, 2, 3]:
            match_key = f'matches_{band_idx+1}1'
            match_data = matches_info.get(match_key)
            
            if match_data is None:
                continue
            
            kp1 = match_data.get('keypoints1', [])
            kp2 = match_data.get('keypoints2', [])
            good_matches = match_data.get('good_matches', [])
            
            if not good_matches or len(kp1) == 0 or len(kp2) == 0:
                continue
            
            # Get images
            img_ref = self.band_images[0].copy()
            img_target = self.band_images[band_idx].copy()
            
            # Convert to RGB
            if img_ref.ndim == 2:
                img_ref = cv2.cvtColor(img_ref, cv2.COLOR_GRAY2RGB)
            if img_target.ndim == 2:
                img_target = cv2.cvtColor(img_target, cv2.COLOR_GRAY2RGB)
            
            try:
                # Limit to 50 best matches
                best_matches = sorted(good_matches, key=lambda x: x.distance)[:num_colors]
                
                # Draw circles with distinct colors
                for idx, match in enumerate(best_matches):
                    if match.trainIdx < len(kp1) and match.queryIdx < len(kp2):
                        pt1 = tuple(map(int, kp1[match.trainIdx].pt))
                        pt2 = tuple(map(int, kp2[match.queryIdx].pt))
                        
                        color = glasbey_colors[idx % len(glasbey_colors)]
                        
                        cv2.circle(img_ref, pt1, 4, color, -1)
                        cv2.circle(img_target, pt2, 4, color, -1)
                        cv2.circle(img_ref, pt1, 5, (255, 255, 255), 1)
                        cv2.circle(img_target, pt2, 5, (255, 255, 255), 1)
                
                # Display images
                self.display_rgb_on_label(img_ref, self.full_labels[0])
                self.display_rgb_on_label(img_target, self.full_labels[band_idx])
                
                # ✅ STATUS MESSAGE (no print)
                self.status_message.emit(
                    f"Visualized {len(best_matches)} matches: Band 1 → Band {band_idx + 1}", 
                    0
                )
                
            except Exception as e:
                # ✅ ERROR MESSAGE
                QMessageBox.warning(
                    self,
                    "Visualization Error",
                    f"Could not visualize matches for Band {band_idx + 1}:\n{str(e)}"
                )
                continue
    
    def display_rgb_on_label(self, rgb_img, label):
        """Helper to display RGB image on a QLabel."""
        if rgb_img is None or rgb_img.size == 0:
            return
        
        h, w = rgb_img.shape[:2]
        bytes_per_line = 3 * w
        rgb_img = np.ascontiguousarray(rgb_img)
        qimg = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        label.setPixmap(pixmap)
    
    @Slot()
    def calculate_manual_transformation(self):
        """Calculate transformation from manual point correspondences."""
        if len(self.manual_points) < 4:
            QMessageBox.warning(
                self,
                "Insufficient Points",
                f"Need at least 4 point pairs.\nCurrent: {len(self.manual_points)}"
            )
            return
        
        # ✅ STATUS MESSAGE
        self.status_message.emit("Calculating manual transformation...", 0)
        
        # Extract point pairs
        b1_points = np.array([p['B1'] for p in self.manual_points], dtype=np.float32)
        results = {}
        
        # H_11 is identity
        results['H_11'] = np.eye(3, dtype=np.float32)
        self.geo_transform.homography_matrices['H_11'] = results['H_11']
        
        for i in [2, 3, 4]:
            band_points = np.array([p[f'B{i}'] for p in self.manual_points], dtype=np.float32)
            
            H, mask = cv2.findHomography(band_points, b1_points, method=cv2.RANSAC)
            
            if H is not None:
                results[f'H_{i}1'] = H
                self.geo_transform.homography_matrices[f'H_{i}1'] = H
            else:
                results[f'H_{i}1'] = None
        
        # Display results
        result_text = "=== Manual Transformation Results ===\n\n"
        result_text += f"Number of point pairs: {len(self.manual_points)}\n\n"
        
        for key in ['H_11', 'H_21', 'H_31', 'H_41']:
            H = results.get(key)
            if H is not None:
                result_text += f"{key}:\n"
                result_text += f"{H}\n\n"
            else:
                result_text += f"{key}: FAILED\n\n"
        
        self.ui.textBrowser.setText(result_text)
        
        # ✅ STATUS MESSAGE
        self.status_message.emit("Manual transformation complete", 0)
    
    @Slot()
    def on_reset_clicked(self):
        """Clear all points from table."""
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to clear all points?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.manual_points = []
            
            for row in range(self.ui.tableWidget.rowCount()):
                for col in range(self.ui.tableWidget.columnCount()):
                    self.ui.tableWidget.setItem(row, col, None)
            
            self.ui.textBrowser.clear()
            
            # ✅ STATUS MESSAGE
            self.status_message.emit("All correspondence points cleared", 0)
    
    @Slot()
    def on_delete_clicked(self):
        """Delete selected row from table."""
        current_row = self.ui.tableWidget.currentRow()
        
        if current_row < 0:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a row to delete by clicking on it."
            )
            return
        
        if current_row >= len(self.manual_points):
            QMessageBox.warning(
                self,
                "Empty Row",
                "Selected row is empty."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete point at row {current_row + 1}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.manual_points[current_row]
            
            # Clear and rebuild table
            for row in range(self.ui.tableWidget.rowCount()):
                for col in range(self.ui.tableWidget.columnCount()):
                    self.ui.tableWidget.setItem(row, col, None)
            
            for row, point in enumerate(self.manual_points):
                for col, band in enumerate(["B1", "B2", "B3", "B4"]):
                    x, y = point[band]
                    self.ui.tableWidget.setItem(row, col, QTableWidgetItem(f"{y} {x}"))
            
            # ✅ STATUS MESSAGE
            self.status_message.emit(f"Point {current_row + 1} deleted", 0)
    
    @Slot()
    def select_calibration_image(self):
        """Browse and select calibration image file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Calibration Image",
            "",
            "Image Files (*.png *.jpg *.tif *.tiff *.bmp)"
        )
        
        if filepath:
            self.ui.bg_img_dir_path_2.setText(filepath)
            # ✅ STATUS MESSAGE
            self.status_message.emit(f"Selected: {os.path.basename(filepath)}", 0)
    
    @Slot()
    def load_calibration_image(self):
        """Load calibration image and split into 4 bands."""
        filepath = self.ui.bg_img_dir_path_2.text().strip()
        
        if not filepath:
            QMessageBox.warning(self, "No File", "Please select a calibration image first")
            return
        
        if not os.path.exists(filepath):
            QMessageBox.critical(self, "File Not Found", f"File does not exist:\n{filepath}")
            return
        
        try:
            # Load image
            full_img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
            
            if full_img is None:
                QMessageBox.critical(self, "Load Error", "Failed to load image")
                return
            
            # Expected size
            expected_height = 480
            expected_width = 640 * 4
            
            if full_img.shape != (expected_height, expected_width):
                QMessageBox.warning(
                    self,
                    "Incorrect Size",
                    f"Expected image size: {expected_height} x {expected_width}\n"
                    f"Got: {full_img.shape[0]} x {full_img.shape[1]}\n\n"
                    f"Loading anyway, but results may be incorrect."
                )
            
            # Split into 4 bands
            frame_width = 640
            images = []
            
            for i in range(4):
                x_start = i * frame_width
                x_end = (i + 1) * frame_width
                
                if x_end <= full_img.shape[1]:
                    band = full_img[:, x_start:x_end]
                else:
                    band = full_img[:, x_start:]
                    if band.shape[1] < frame_width:
                        pad_width = frame_width - band.shape[1]
                        band = np.pad(band, ((0, 0), (0, pad_width)), mode='constant')
                
                if band.shape[0] != expected_height:
                    if band.shape[0] > expected_height:
                        band = band[:expected_height, :]
                    else:
                        pad_height = expected_height - band.shape[0]
                        band = np.pad(band, ((0, pad_height), (0, 0)), mode='constant')
                
                images.append(band)
            
            # Load into dialog
            self.load_images(images)
            
            # ✅ STATUS MESSAGE
            self.status_message.emit(f"Calibration image loaded: {os.path.basename(filepath)}", 0)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load calibration image:\n{str(e)}"
            )
    
    @Slot()
    def select_config_file(self):
        """Select existing .ini configuration file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Configuration File",
            "",
            "INI Files (*.ini)"
        )
        
        if filepath:
            self.ui.bg_img_dir_path.setText(filepath)
            # ✅ STATUS MESSAGE
            self.status_message.emit(f"Selected config: {os.path.basename(filepath)}", 0)
    
    @Slot()
    def load_config_file(self):
        """Load transformation from .ini file."""
        filepath = self.ui.bg_img_dir_path.text().strip()
        
        if not filepath:
            QMessageBox.warning(self, "No File", "Select a configuration file first")
            return
        
        results = self.geo_transform.load_config_ini(filepath)
        
        if results is None:
            QMessageBox.critical(self, "Failed", "Failed to load configuration")
            return
        
        # Display loaded matrices
        result_text = "=== Loaded Configuration ===\n\n"
        for key in ['H_11', 'H_21', 'H_31', 'H_41']:
            H = results.get(key)
            if H is not None:
                result_text += f"{key}:\n{H}\n\n"
            else:
                result_text += f"{key}: Not found\n\n"
        
        self.ui.textBrowser.setText(result_text)
        
        # ✅ STATUS MESSAGE
        self.status_message.emit(f"Configuration loaded: {os.path.basename(filepath)}", 0)
    
    @Slot()
    def select_save_folder(self):
        """Select folder to save configuration."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Save Folder"
        )
        
        if folder:
            self.ui.folder_save_path_3.setText(folder)
            # ✅ STATUS MESSAGE
            self.status_message.emit(f"Save folder selected", 0)

    @Slot()
    def save_configuration(self):
        """Save current transformation to .ini file."""
        folder = self.ui.folder_save_path_3.text().strip()
        
        if not folder:
            QMessageBox.warning(self, "No Folder", "Select a save folder first")
            return
        
        if not os.path.exists(folder):
            QMessageBox.critical(self, "Folder Not Found", f"Folder does not exist:\n{folder}")
            return
        
        # ✅ Check if transformations exist (including H_11)
        has_transformation = False
        for key in ['H_11', 'H_21', 'H_31', 'H_41']:
            if self.geo_transform.homography_matrices.get(key) is not None:
                has_transformation = True
                break
        
        if not has_transformation:
            QMessageBox.warning(
                self,
                "No Transformation",
                "Calculate transformation first using:\n"
                "• Automatic transformation (AKAZE), or\n"
                "• Manual transformation (point correspondences)"
            )
            return
        
        # Create filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(folder, f"alignment_{timestamp}.ini")
        
        try:
            # ✅ Make sure H_11 is set (identity matrix for Band 1)
            if self.geo_transform.homography_matrices.get('H_11') is None:
                self.geo_transform.homography_matrices['H_11'] = np.eye(3, dtype=np.float32)
            
            # Save configuration
            self.geo_transform.save_config_ini(filepath)
            
            self.status_message.emit(f"Configuration saved: {os.path.basename(filepath)}", 0)
            
        except Exception as e:
            # ✅ ERROR - Show message box
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save configuration:\n{str(e)}"
            )
    
    @Slot()
    def on_apply_clicked(self):
        """Apply transformation and close dialog."""
        # Check if transformation exists
        if all(H is None for H in self.geo_transform.homography_matrices.values()):
            QMessageBox.warning(
                self,
                "No Transformation",
                "Calculate transformation first using:\n"
                "- Automatic transformation (AKAZE), or\n"
                "- Manual transformation (point correspondences)"
            )
            return
        
        # ✅ STATUS MESSAGE
        self.status_message.emit("Transformation applied", 0)
        
        # Accept dialog (returns QDialog.Accepted)
        self.accept()