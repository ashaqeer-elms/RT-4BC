from PySide6.QtWidgets import QWidget, QMessageBox, QListWidgetItem
from PySide6.QtCore import Qt, QTimer, Slot, QStringListModel, Signal
from PySide6.QtGui import QImage, QPixmap
import numpy as np
import cv2

from UI.ui_RasterCalculation import Ui_Form
from Core.Core_ReflectanceCalculation import CoreReflectanceCalculator
from Core.Core_RasterCalculation import CoreRasterCalculator
from Core.Core_RawImageSave import CoreRawImageSave

class RasterCalculationTab(QWidget):
    """
    Tab for reflectance calculation and raster operations.
    - Top: 4 reflectance images (R1-R4)
    - Bottom: Raster calculation with expression editor
    """
    
    # ✅ NEW: Signal for status messages
    status_message = Signal(str, int)  # (message, timeout_ms)
    features_update = Signal()
    reflectance_calculated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        
        # Tab references (set by main window)
        self.camera_viewer_tab = None
        self.calibration_tab = None
        
        # === REFLECTANCE CALCULATION ===
        self.reflectance_calculator = CoreReflectanceCalculator()
        self.current_reflectance_tiles = None
        
        # Reflectance save setup
        self.reflectance_saver = CoreRawImageSave()
        # ✅ Forward save status messages
        if hasattr(self.reflectance_saver, 'status_message'):
            self.reflectance_saver.status_message.connect(self.status_message)
        
        # Map reflectance image labels
        self.refl_labels = [
            self.ui.refl_img_1,  # R1 (BAND 1)
            self.ui.refl_img_2,  # R2 (BAND 2)
            self.ui.refl_img_3,  # R3 (BAND 3)
            self.ui.refl_img_4   # R4 (BAND 4)
        ]
        
        # Connect reflectance button
        self.ui.refl_val_est.clicked.connect(self.calculate_and_display_reflectance)
        
        # Reflectance save setup
        self.ui.folder_save_open_dir_2.clicked.connect(
            lambda: self.reflectance_saver.select_timestamp_folder(self.ui.folder_save_path_2)
        )
        self.ui.img_save_act_2.stateChanged.connect(self.reflectance_saver.toggle_save_active)
        
        # === SHOW RASTER CALCULATION SECTION ===
        self.ui.ras_est.setVisible(True)
        
        # === RASTER CALCULATION ===
        self.raster_calculator = CoreRasterCalculator()
        self.current_displayed_raster = None
        
        # Populate raster band list (R1-R4)
        self.setup_raster_band_list()
        
        # Connect raster controls
        self.ui.ras_check_func.clicked.connect(self.check_raster_expression)
        self.ui.ras_reset_func.clicked.connect(self.reset_raster_expression)
        self.ui.ras_apply_func.clicked.connect(self.apply_raster_expression)
        
        # Calculated raster dropdown
        self.ui.ras_calc_list.currentIndexChanged.connect(self.on_raster_selection_changed)
        
        # Setup colormap dropdown
        colormaps = ['Jet', 'Viridis', 'Hot', 'Cool', 'Gray', 'Plasma', 'Inferno', 'Turbo']
        self.ui.vis_colormap_list.addItems(colormaps)
        self.ui.vis_colormap_list.setCurrentText('Jet')
        self.ui.vis_colormap_list.currentTextChanged.connect(self.on_colormap_changed)
        
        # === VISUALIZATION SETTINGS (vmin/vmax) ===
        self.ui.vis_vmin_val.setRange(-1000.0, 1000.0)
        self.ui.vis_vmin_val.setValue(0.0)
        self.ui.vis_vmin_val.setDecimals(3)
        self.ui.vis_vmin_val.setSingleStep(0.1)
        
        self.ui.vis_vmax_val.setRange(-1000.0, 1000.0)
        self.ui.vis_vmax_val.setValue(1.0)
        self.ui.vis_vmax_val.setDecimals(3)
        self.ui.vis_vmax_val.setSingleStep(0.1)
        
        # Connect vmin/vmax changes to update display
        self.ui.vis_vmin_val.valueChanged.connect(self.on_vis_range_changed)
        self.ui.vis_vmax_val.valueChanged.connect(self.on_vis_range_changed)
        
        # Raster save setup (separate saver for raster)
        self.raster_saver = CoreRawImageSave()
        # ✅ Forward save status messages
        if hasattr(self.raster_saver, 'status_message'):
            self.raster_saver.status_message.connect(self.status_message)
        
        self.ui.folder_save_open_dir_3.clicked.connect(
            lambda: self.raster_saver.select_timestamp_folder(self.ui.folder_save_path_3)
        )
        self.ui.img_save_act_3.stateChanged.connect(self.raster_saver.toggle_save_active)
        
        # === PERIODIC UPDATE TIMERS ===
        # Reflectance update (NO STATUS MESSAGES - automatic)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_reflectance_display)
        self.update_timer.start(500)
        
        # Reflectance save (NO STATUS MESSAGES - automatic)
        self.refl_save_timer = QTimer()
        self.refl_save_timer.timeout.connect(self.save_reflectance_if_active)
        self.refl_save_timer.start(1000)
        
        # Raster save (NO STATUS MESSAGES - automatic)
        self.raster_save_timer = QTimer()
        self.raster_save_timer.timeout.connect(self.save_raster_if_active)
        self.raster_save_timer.start(1000)
    
    def set_tab_references(self, camera_viewer_tab, calibration_tab):
        """Link to other tabs for data access."""
        self.camera_viewer_tab = camera_viewer_tab
        self.calibration_tab = calibration_tab
    
    # ========== REFLECTANCE METHODS ==========
    
    @Slot()
    def calculate_and_display_reflectance(self):
        """Manually trigger reflectance calculation."""
        # ✅ STATUS MESSAGE (manual action)
        self.status_message.emit("Calculating reflectance...", 0)
        self.update_reflectance_display()
        
        if self.current_reflectance_tiles is not None:
            # ✅ STATUS MESSAGE (success)
            self.status_message.emit("Reflectance calculated successfully", 0)
    
    def update_reflectance_display(self):
        """Periodically calculate and display reflectance tiles (NO STATUS MESSAGE)."""
        if self.camera_viewer_tab is None or self.calibration_tab is None:
            return
        
        try:
            from Core.Core_CameraView import last_fullframe, EXPO_MS
            
            if last_fullframe is None:
                return
            
            # Use aligned frame from camera_viewer if alignment is enabled
            frame_to_use = last_fullframe
            if (hasattr(self.camera_viewer_tab, 'alignment_enabled') and
                self.camera_viewer_tab.alignment_enabled and
                hasattr(self.camera_viewer_tab, 'last_aligned_frame') and
                self.camera_viewer_tab.last_aligned_frame is not None):
                frame_to_use = self.camera_viewer_tab.last_aligned_frame
            
            bg_tiles = self.calibration_tab.dark_noise_estimator.bg_tiles
            expo_sliders = self.camera_viewer_tab.expo_sliders
            ref_cam_entries = self.calibration_tab.ref_cam_entries
            
            # Calculate reflectance
            tiles = self.reflectance_calculator.calculate_reflectance(
                frame_to_use,
                bg_tiles,
                expo_sliders,
                ref_cam_entries,
                EXPO_MS
            )
            
            if tiles is None:
                return
            
            # Store for raster calculation
            self.current_reflectance_tiles = tiles
            
            # Display each tile
            for i in range(4):
                self.display_normalized_image(tiles[i], self.refl_labels[i])
            
            # Auto-create overlay if it doesn't exist (NO STATUS MESSAGE)
            self.ensure_overlay_raster()
            
            # Auto-update all calculated rasters (NO STATUS MESSAGE)
            self.update_all_rasters()

            self.current_reflectance_tiles = tiles
        
            # ✅ EMIT SIGNAL at the end
            self.reflectance_calculated.emit()
                
        except Exception as e:
            # Silent fail for automatic updates
            pass

    def display_normalized_image(self, data, label):
        """Normalize and display a numpy array as image (grayscale)."""
        if data is None:
            return
        
        # Normalize to 0-255
        t_min, t_max = np.min(data), np.max(data)
        if t_max > t_min:
            norm = (data - t_min) / (t_max - t_min) * 255.0
        else:
            norm = np.zeros_like(data)
        
        norm_u8 = norm.astype(np.uint8)
        rgb = cv2.cvtColor(norm_u8, cv2.COLOR_GRAY2RGB)
        
        # Convert to QPixmap
        h, w = rgb.shape[:2]
        bytes_per_line = 3 * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        label.setPixmap(pixmap)
    
    @Slot()
    def save_reflectance_if_active(self):
        """Save reflectance combined image (NO STATUS MESSAGE - automatic)."""
        if self.current_reflectance_tiles is None:
            return
        
        # Combine reflectance tiles horizontally (480x2560)
        combined = self.combine_tiles_to_image(self.current_reflectance_tiles)
        if combined is None:
            return
        
        # Use CoreRawImageSave
        import Core.Core_CameraView as ccv
        original = ccv.last_fullframe
        try:
            ccv.last_fullframe = combined
            self.reflectance_saver.save_frame_if_active()
        finally:
            ccv.last_fullframe = original
    
    # ========== RASTER CALCULATION METHODS ==========
    
    def setup_raster_band_list(self):
        """Setup band list showing R1-R4 reflectance bands."""
        model = QStringListModel(["R1", "R2", "R3", "R4"])
        self.ui.ras_band_list.setModel(model)
        # Double-click to insert into expression
        self.ui.ras_band_list.doubleClicked.connect(self.insert_band_to_expression)
    
    @Slot()
    def insert_band_to_expression(self):
        """Insert selected band into expression text."""
        index = self.ui.ras_band_list.currentIndex()
        if index.isValid():
            band = index.data()
            current_text = self.ui.ras_func_txt.toPlainText()
            self.ui.ras_func_txt.setPlainText(current_text + band)
            
            # ✅ STATUS MESSAGE (manual action)
            self.status_message.emit(f"Inserted {band} into expression", 0)
    
    @Slot()
    def check_raster_expression(self):
        """Validate the raster expression."""
        expression = self.ui.ras_func_txt.toPlainText().strip()
        is_valid, error_msg = self.raster_calculator.validate_expression(expression)
        
        if is_valid:
            # ✅ STATUS MESSAGE + Dialog (manual action)
            self.status_message.emit(f"Expression valid: {expression}", 0)
            QMessageBox.information(self, "Valid", "✅ Expression syntax is valid!")
        else:
            # ✅ ERROR - QMessageBox only
            QMessageBox.warning(self, "Invalid", f"❌ {error_msg}")
    
    @Slot()
    def reset_raster_expression(self):
        """Clear expression and all calculated rasters."""
        reply = QMessageBox.question(
            self,
            "Reset",
            "Clear expression and all calculated rasters?",
            QMessageBox.Yes | QMessageBox.No,
        )
        
        if reply == QMessageBox.Yes:
            self.ui.ras_func_txt.clear()
            self.raster_calculator.clear_all_rasters()
            self.ui.ras_calc_list.clear()
            self.ui.ras_img.clear()
            self.ui.img_leg.clear()
            self.current_displayed_raster = None
            
            # ✅ STATUS MESSAGE (manual action)
            self.status_message.emit("All rasters cleared", 0)
    
    @Slot()
    def apply_raster_expression(self):
        """Apply expression to create new calculated raster."""
        expression = self.ui.ras_func_txt.toPlainText().strip()
        
        # Validate
        is_valid, error_msg = self.raster_calculator.validate_expression(expression)
        if not is_valid:
            QMessageBox.warning(self, "Invalid", f"❌ {error_msg}")
            return
        
        # Check if reflectance is available
        if self.current_reflectance_tiles is None:
            QMessageBox.warning(
                self, "No Data", "Calculate reflectance first (top section)"
            )
            return
        
        # ✅ STATUS MESSAGE (manual action - processing)
        self.status_message.emit(f"Calculating: {expression}", 0)
        
        # Evaluate expression
        result = self.raster_calculator.evaluate_expression(
            expression, self.current_reflectance_tiles
        )
        
        if result is None:
            QMessageBox.critical(self, "Error", "Failed to evaluate expression")
            self.status_message.emit("Raster calculation failed", 0)
            return
        
        raster_name = self.raster_calculator.add_calculated_raster(expression, result)
        self.ui.ras_calc_list.addItem(raster_name)
        self.ui.ras_calc_list
        
        # Display immediately
        self.display_raster(result)
        
        # ✅ STATUS MESSAGE (manual action - success)
        vmin = np.min(result)
        vmax = np.max(result)
        self.status_message.emit(
            f"{raster_name} created: range [{vmin:.3f}, {vmax:.3f}]", 
            0
        )
    
    @Slot(int)
    def on_raster_selection_changed(self, index):
        """Display selected raster when dropdown changes."""
        raster_name = self.ui.ras_calc_list.currentText()
        if not raster_name:
            return
        
        raster_data = self.raster_calculator.get_raster(raster_name)
        if raster_data is not None:
            self.display_raster(raster_data)
            
            # ✅ STATUS MESSAGE (manual action)
            vmin = np.min(raster_data)
            vmax = np.max(raster_data)
            self.status_message.emit(
                f"Displaying {raster_name}: range [{vmin:.3f}, {vmax:.3f}]", 
                0
            )
    
    @Slot(str)
    def on_colormap_changed(self, colormap_name):
        """Update raster display when colormap changes."""
        if self.current_displayed_raster is not None:
            self.display_raster(self.current_displayed_raster)
            
            # ✅ STATUS MESSAGE (manual action)
            self.status_message.emit(f"Colormap changed to: {colormap_name}", 0)
    
    def display_raster(self, raster_data):
        """Display raster result in ras_img with colormap and update legend."""
        self.current_displayed_raster = raster_data
        if raster_data is None:
            return
        
        # Get colormap (convert to lowercase for consistent matching)
        colormap_name = self.ui.vis_colormap_list.currentText().lower()
        
        # Get fixed vmin/vmax from spinboxes
        vmin = self.ui.vis_vmin_val.value()
        vmax = self.ui.vis_vmax_val.value()
        
        # Ensure vmax > vmin
        if vmax <= vmin:
            vmax = vmin + 0.001
        
        # Clip data to vmin/vmax range and normalize
        clipped_data = np.clip(raster_data, vmin, vmax)
        norm = (clipped_data - vmin) / (vmax - vmin) * 255.0
        norm_u8 = norm.astype(np.uint8)
        
        # Apply colormap
        colormap_dict = {
            'viridis': cv2.COLORMAP_VIRIDIS,
            'jet': cv2.COLORMAP_JET,
            'hot': cv2.COLORMAP_HOT,
            'cool': cv2.COLORMAP_COOL,
            'gray': -1,
            'plasma': cv2.COLORMAP_PLASMA,
            'inferno': cv2.COLORMAP_INFERNO,
            'turbo': cv2.COLORMAP_TURBO
        }
        
        cmap = colormap_dict.get(colormap_name, cv2.COLORMAP_JET)
        if cmap == -1:
            rgb = cv2.cvtColor(norm_u8, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.applyColorMap(norm_u8, cmap)
        
        # Convert to QPixmap
        h, w = rgb.shape[:2]
        bytes_per_line = 3 * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.ui.ras_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.ui.ras_img.setPixmap(pixmap)
        
        # Update legend with FIXED vmin/vmax
        self.update_colorbar_legend(raster_data, vmin, vmax, colormap_name)
    
    def update_all_rasters(self):
        """
        Recalculate ALL stored rasters using new reflectance data.
        (NO STATUS MESSAGE - automatic process)
        """
        if self.current_reflectance_tiles is None:
            return
        
        # Get list of all raster names
        raster_names = self.raster_calculator.get_raster_list()
        
        for raster_name in raster_names:
            expression = self.raster_calculator.raster_expressions.get(raster_name)
            if not expression:
                continue
            
            try:
                # Re-evaluate expression
                result = self.raster_calculator.evaluate_expression(
                    expression, self.current_reflectance_tiles
                )
                
                if result is not None:
                    # Update stored raster
                    self.raster_calculator.calculated_rasters[raster_name] = result
            except Exception:
                # Silent fail for automatic updates
                pass
        
        # Refresh display of current raster
        current_raster = self.ui.ras_calc_list.currentText()
        if current_raster:
            raster_data = self.raster_calculator.get_raster(current_raster)
            if raster_data is not None:
                self.display_raster(raster_data)
    
    def ensure_overlay_raster(self):
        """Auto-create 'Overlay' raster if it doesn't exist (NO STATUS MESSAGE)."""
        if self.current_reflectance_tiles is None:
            return
        
        overlay_expr = "R1//4 + R2//4 + R3//4 + R4//4"
        
        if "Overlay" not in self.raster_calculator.calculated_rasters:
            result = self.raster_calculator.evaluate_expression(
                overlay_expr, self.current_reflectance_tiles
            )
            
            if result is not None:
                self.raster_calculator.calculated_rasters["Overlay"] = result
                self.raster_calculator.raster_expressions["Overlay"] = overlay_expr
                
                # Add to top of dropdown
                if self.ui.ras_calc_list.findText("Overlay") == -1:
                    self.ui.ras_calc_list.insertItem(0, "Overlay")
    
    def update_colorbar_legend(self, raster_data, vmin, vmax, colormap_name):
        """
        Create gradient colorbar with FIXED min/max scale values.
        
        Args:
            raster_data: numpy array of raster values (for reference only)
            vmin: FIXED minimum value for scale
            vmax: FIXED maximum value for scale
            colormap_name: name of colormap to use (already lowercase)
        """
        if raster_data is None:
            return
        
        try:
            # Create a vertical gradient (650 pixels tall, 80 wide)
            height = 650
            width = 80
            gradient = np.linspace(255, 0, height).reshape(-1, 1)
            gradient = np.tile(gradient, (1, width)).astype(np.uint8)
            
            # Apply same colormap as raster (all lowercase)
            colormap_dict = {
                'viridis': cv2.COLORMAP_VIRIDIS,
                'jet': cv2.COLORMAP_JET,
                'hot': cv2.COLORMAP_HOT,
                'cool': cv2.COLORMAP_COOL,
                'gray': -1,
                'plasma': cv2.COLORMAP_PLASMA,
                'inferno': cv2.COLORMAP_INFERNO,
                'turbo': cv2.COLORMAP_TURBO
            }
            
            cmap = colormap_dict.get(colormap_name, cv2.COLORMAP_JET)
            if cmap == -1:
                gradient_rgb = cv2.cvtColor(gradient, cv2.COLOR_GRAY2RGB)
            else:
                gradient_rgb = cv2.applyColorMap(gradient, cmap)
            
            # Add white border
            gradient_rgb = cv2.copyMakeBorder(
                gradient_rgb, 30, 30, 15, 15,
                cv2.BORDER_CONSTANT, value=[255, 255, 255]
            )
            
            # Add text labels for FIXED min/max/mid
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1
            color = (0, 0, 0)
            thickness = 1
            
            # Max value at top (FIXED)
            max_text = f"{vmax:.3f}"
            cv2.putText(gradient_rgb, max_text, (10, 25), font, font_scale, color, thickness)
            
            # Min value at bottom (FIXED)
            min_text = f"{vmin:.3f}"
            text_y = height + 25
            cv2.putText(gradient_rgb, min_text, (10, text_y), font, font_scale, color, thickness)
            
            # Middle value (FIXED)
            mid_val = (vmin + vmax) / 2
            mid_text = f"{mid_val:.3f}"
            mid_y = height // 2 + 30
            cv2.putText(gradient_rgb, mid_text, (10, mid_y), font, font_scale, color, thickness)
            
            # Convert to QPixmap
            h, w = gradient_rgb.shape[:2]
            bytes_per_line = 3 * w
            qimg = QImage(gradient_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(
                self.ui.img_leg.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.ui.img_leg.setPixmap(pixmap)
            
        except Exception as e:
            # Silent fail for legend errors
            pass
    
    @Slot()
    def on_vis_range_changed(self):
        """Update raster display when vmin/vmax changes (manual action)."""
        if self.current_displayed_raster is not None:
            self.display_raster(self.current_displayed_raster)
            
            # ✅ STATUS MESSAGE (manual action)
            vmin = self.ui.vis_vmin_val.value()
            vmax = self.ui.vis_vmax_val.value()
            self.status_message.emit(f"Display range: [{vmin:.3f}, {vmax:.3f}]", 0)
    
    @Slot()
    def save_raster_if_active(self):
        """Save currently displayed raster as single 640x480 frame (NO STATUS MESSAGE)."""
        if self.current_displayed_raster is None:
            return
        
        # Convert single raster to 640x480 uint8 image
        raster_image = self.convert_raster_to_image(self.current_displayed_raster)
        if raster_image is None:
            return
        
        # Temporarily replace last_fullframe with single raster image
        import Core.Core_CameraView as ccv
        original = ccv.last_fullframe
        try:
            ccv.last_fullframe = raster_image
            self.raster_saver.save_frame_if_active()
        finally:
            ccv.last_fullframe = original
    
    # ========== HELPER METHODS ==========
    
    def combine_tiles_to_image(self, tiles):
        """Combine 4 reflectance tiles into 480x2560 image."""
        if tiles is None or len(tiles) != 4:
            return None
        
        combined_list = []
        for tile in tiles:
            t_min, t_max = np.min(tile), np.max(tile)
            if t_max > t_min:
                norm = (tile - t_min) / (t_max - t_min) * 255.0
            else:
                norm = np.zeros_like(tile)
            combined_list.append(norm.astype(np.uint8))
        
        return np.hstack(combined_list)
    
    def convert_raster_to_image(self, raster):
        """Convert single raster (480x640) to normalized uint8 image."""
        if raster is None:
            return None
        
        # Normalize to 0-255
        t_min, t_max = np.min(raster), np.max(raster)
        if t_max > t_min:
            norm = (raster - t_min) / (t_max - t_min) * 255.0
        else:
            norm = np.zeros_like(raster)
        
        return norm.astype(np.uint8)
