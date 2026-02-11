from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox, QAbstractItemView
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QImage, QPixmap, QShowEvent
import numpy as np
import cv2
import os

from UI.ui_Classification import Ui_Form
from Core.Core_Classifier import CoreClassifier
from Core.Core_RawImageSave import CoreRawImageSave

class ClassificationTab(QWidget):
    """Tab for machine learning classification using loaded models."""
    
    status_message = Signal(str, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        
        self.raster_calculation_tab = None
        self.classifier = CoreClassifier()
        self.current_classification_map = None
        
        if hasattr(self.classifier, "status_message"):
            self.classifier.status_message.connect(self.status_message)
        
        # Model loading
        self.ui.model_open_dir.clicked.connect(self.select_model_file)
        self.ui.model_load.clicked.connect(self.load_model_file)
        
        # Feature selection
        self.ui.model_input.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # Apply classification
        self.ui.model_apply.clicked.connect(self.on_apply_clicked)
        
        # Auto-classify checkbox
        self.ui.class_en_segment_2.setToolTip("Automatically reclassify when camera updates")
        
        # ✅ Colorcet Glasbey Light colormap (256 distinct colors for categorical data)
        self.glasbey_colors = self.get_glasbey_light_colors()
        
        # Save
        self.classification_saver = CoreRawImageSave()
        if hasattr(self.classification_saver, "status_message"):
            self.classification_saver.status_message.connect(self.status_message)
        
        self.ui.folder_save_open_dir_4.clicked.connect(
            lambda: self.classification_saver.select_timestamp_folder(self.ui.folder_save_path_4)
        )
        self.ui.img_save_act_4.stateChanged.connect(self.classification_saver.toggle_save_active)
    
    def get_glasbey_light_colors(self):
        """
        Returns Glasbey Light colormap - perceptually distinct colors for classification.
        256 colors optimized for categorical visualization.
        """
        try:
            import colorcet as cc
            # Get glasbey_light palette (256 RGB colors)
            colors_hex = cc.glasbey_light
            # Convert hex to BGR for OpenCV
            colors_bgr = []
            for hex_color in colors_hex:
                # Remove '#' and convert
                rgb = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
                bgr = (rgb[2], rgb[1], rgb[0])  # RGB to BGR
                colors_bgr.append(bgr)
            return colors_bgr
        except ImportError:
            print("⚠️  colorcet not installed. Using fallback colors.")
            print("   Install with: pip install colorcet")
            # Fallback: Generate distinct colors
            return self.generate_fallback_colors(256)
    
    def generate_fallback_colors(self, n=256):
        """Generate fallback distinct colors if colorcet not available."""
        colors = []
        for i in range(n):
            hue = int((i * 137.508) % 256)  # Golden angle
            sat = 200
            val = 230 if i % 2 == 0 else 180
            hsv = np.uint8([[[hue, sat, val]]])
            bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
            colors.append(tuple(map(int, bgr)))
        return colors
    
    def showEvent(self, event: QShowEvent):
        """Refresh feature list when tab becomes visible."""
        super().showEvent(event)
        self.update_feature_list()
    
    def set_tab_references(self, raster_calculation_tab):
        """Link to raster calculation tab for feature access."""
        self.raster_calculation_tab = raster_calculation_tab
        self.update_feature_list()
        
        # Connect to reflectance updates
        if hasattr(raster_calculation_tab, "reflectance_calculated"):
            # print("✅ Connecting classification to reflectance updates")
            raster_calculation_tab.reflectance_calculated.connect(self.on_reflectance_updated)
        else:
            print("⚠️  Warning: RasterCalculationTab doesn't have reflectance_calculated signal")
    
    # ========== MODEL LOADING ==========
    
    @Slot()
    def select_model_file(self):
        """Open file dialog to select .joblib model file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Classification Model", "", "Joblib files (*.joblib);;All files (*.*)"
        )
        
        if filepath:
            self.ui.model_path_dir.setText(filepath)
            self.status_message.emit(f"Model file selected: {os.path.basename(filepath)}", 0)
    
    @Slot()
    def load_model_file(self):
        """Load selected .joblib model."""
        filepath = self.ui.model_path_dir.text().strip()
        
        if not filepath:
            QMessageBox.warning(self, "No File", "Please select a model file first")
            return
        
        if not os.path.exists(filepath):
            QMessageBox.critical(self, "File Not Found", f"Model file does not exist:\n{filepath}")
            return
        
        self.status_message.emit("Loading model...", 0)
        success = self.classifier.load_model(filepath)
        
        if success:
            model_info = self.classifier.get_model_info()
            self.status_message.emit(f"Model loaded: {os.path.basename(filepath)}", 0)
            QMessageBox.information(self, "Model Loaded", f"✅ Successfully loaded model:\n\n{model_info}")
        else:
            QMessageBox.critical(self, "Load Error", "Failed to load model file.\nCheck console for details.")
            self.status_message.emit("Model load failed", 0)
    
    # ========== FEATURE SELECTION ==========
    
    def update_feature_list(self):
        """Populate feature list with R1-R4 and raster layers."""
        self.ui.model_input.clear()
        
        feature_list = ["R1", "R2", "R3", "R4"]
        self.ui.model_input.addItems(feature_list)
        
        if self.raster_calculation_tab and hasattr(self.raster_calculation_tab, "raster_calculator"):
            raster_names = self.raster_calculation_tab.raster_calculator.get_raster_list()
            self.ui.model_input.addItems(raster_names)
            feature_list.extend(raster_names)
        
        # print(f"✅ Feature list updated: {feature_list}")
        
        if len(feature_list) > 0:
            self.status_message.emit(f"Features available: {len(feature_list)}", 0)
    
    @Slot()
    def on_apply_clicked(self):
        """Apply classification with currently selected features."""
        self.apply_classification()
    
    def get_selected_features(self):
        """Get list of selected feature names from the multi-select list."""
        selected_items = self.ui.model_input.selectedItems()
        selected = [item.text() for item in selected_items]
        print(f"🔍 Selected {len(selected)} features: {selected}")
        return selected
    
    def build_feature_stack(self, selected_features):
        """Build feature stack from selected features."""
        if not self.raster_calculation_tab:
            print("❌ Raster calculation tab not available")
            return None
        
        reflectance_tiles = self.raster_calculation_tab.current_reflectance_tiles
        if reflectance_tiles is None:
            print("❌ No reflectance data available")
            return None
        
        feature_arrays = []
        
        for feature_name in selected_features:
            if feature_name == "R1":
                feature_arrays.append(reflectance_tiles[0])
            elif feature_name == "R2":
                feature_arrays.append(reflectance_tiles[1])
            elif feature_name == "R3":
                feature_arrays.append(reflectance_tiles[2])
            elif feature_name == "R4":
                feature_arrays.append(reflectance_tiles[3])
            else:
                raster_data = self.raster_calculation_tab.raster_calculator.get_raster(feature_name)
                if raster_data is not None:
                    feature_arrays.append(raster_data)
        
        if not feature_arrays:
            return None
        
        feature_stack = np.stack(feature_arrays, axis=0)
        return feature_stack
    
    # ========== AUTO-CLASSIFICATION ==========
    
    @Slot()
    def on_reflectance_updated(self):
        """Called when reflectance is recalculated. Auto-classifies if enabled."""
        if not self.ui.class_en_segment_2.isChecked():
            return
        
        if self.classifier.model is None:
            return
        
        if self.current_classification_map is None:
            return
        
        selected_features = self.get_selected_features()
        if not selected_features:
            return
        
        print("🔄 Auto-classifying new frame...")
        
        feature_stack = self.build_feature_stack(selected_features)
        if feature_stack is None:
            return
        
        label_map = self.classifier.predict_classification(feature_stack)
        if label_map is None:
            return
        
        self.current_classification_map = label_map
        self.display_classification_map(label_map)
        
        num_valid = np.sum(np.isfinite(label_map))
        unique_classes = np.unique(label_map[np.isfinite(label_map)])
        self.status_message.emit(
            f"Auto-classified: {num_valid:,} pixels, {len(unique_classes)} classes", 1500
        )
    
    # ========== CLASSIFICATION ==========
    
    @Slot()
    def apply_classification(self):
        """Apply loaded model to selected features."""
        if self.classifier.model is None:
            QMessageBox.warning(self, "No Model", "Please load a classification model first")
            return
        
        selected_features = self.get_selected_features()
        if not selected_features:
            QMessageBox.warning(
                self, "No Features",
                "Please select at least one feature from the list\n(use Ctrl+Click for multi-selection)"
            )
            return
        
        self.status_message.emit(f"Classifying with {len(selected_features)} features", 0)
        
        feature_stack = self.build_feature_stack(selected_features)
        if feature_stack is None:
            QMessageBox.critical(
                self, "Feature Error",
                "Failed to build feature stack.\nMake sure reflectance is calculated (Tab 3)."
            )
            return
        
        # Check feature count
        expected_features = getattr(self.classifier.model, "n_features_in_", None)
        if expected_features and feature_stack.shape[0] != expected_features:
            reply = QMessageBox.warning(
                self, "Feature Mismatch",
                f"⚠️ Model expects {expected_features} features, but you selected {feature_stack.shape[0]}.\n\n"
                f"Continue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        label_map = self.classifier.predict_classification(feature_stack)
        if label_map is None:
            QMessageBox.critical(self, "Classification Error", "Failed to classify image.\nCheck console for details.")
            return
        
        self.current_classification_map = label_map
        self.display_classification_map(label_map)
        
        num_valid = np.sum(np.isfinite(label_map))
        unique_classes = np.unique(label_map[np.isfinite(label_map)])
        self.status_message.emit(
            f"Classification complete: {num_valid:,} pixels, {len(unique_classes)} classes", 0
        )
        
        QMessageBox.information(
            self, "Classification Complete",
            f"✅ Classification successful!\n\nFeatures: {len(selected_features)}\nPixels: {num_valid:,}\nClasses: {unique_classes}"
        )
    
    # ========== VISUALIZATION ==========
    
    def display_classification_map(self, label_map):
        """Display classification map using Glasbey Light colormap."""
        if label_map is None:
            return
        
        h, w = label_map.shape
        valid_mask = np.isfinite(label_map)
        
        # Create RGB image
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Get unique classes
        unique_classes = np.unique(label_map[valid_mask])
        
        # Assign Glasbey colors to each class
        for cls in unique_classes:
            class_mask = (label_map == cls) & valid_mask
            color_idx = int(cls) % len(self.glasbey_colors)
            rgb[class_mask] = self.glasbey_colors[color_idx]
        
        # Convert RGB to BGR for OpenCV display
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        
        # Display
        qimg = QImage(bgr.data, w, h, 3 * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.ui.class_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.ui.class_img.setPixmap(pixmap)
        
        self.update_legend(label_map)
    
    def update_legend(self, label_map):
        """Create legend showing discrete class colors using Glasbey."""
        if label_map is None:
            return
        
        try:
            valid_mask = np.isfinite(label_map)
            unique_classes = np.unique(label_map[valid_mask])
            n_classes = len(unique_classes)
            
            if n_classes == 0:
                return
            
            # Legend dimensions
            block_height = 50
            block_width = 120
            gap = 10
            text_width = 280
            margin = 20
            
            total_width = margin + block_width + 15 + text_width + margin
            total_height = margin + n_classes * (block_height + gap) - gap + margin
            
            # Create white background
            legend_img = np.ones((total_height, total_width, 3), dtype=np.uint8) * 255
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            font_thickness = 1
            
            for i, cls in enumerate(unique_classes):
                y_start = margin + i * (block_height + gap)
                
                # Get Glasbey color for this class
                color_idx = int(cls) % len(self.glasbey_colors)
                color = self.glasbey_colors[color_idx]
                
                # Draw color block
                cv2.rectangle(
                    legend_img,
                    (margin, y_start),
                    (margin + block_width, y_start + block_height),
                    color, -1
                )
                
                # Draw border
                cv2.rectangle(
                    legend_img,
                    (margin, y_start),
                    (margin + block_width, y_start + block_height),
                    (0, 0, 0), 2
                )
                
                # Count pixels
                pixel_count = np.sum(label_map[valid_mask] == cls)
                total_valid = np.sum(valid_mask)
                percentage = (pixel_count / total_valid * 100) if total_valid > 0 else 0
                
                # Draw text
                text = f"Class {int(cls)}: {pixel_count:,} ({percentage:.1f}%)"
                text_x = margin + block_width + 15
                text_y = y_start + block_height // 2 + 8
                
                cv2.putText(legend_img, text, (text_x, text_y), font, font_scale, (0, 0, 0), font_thickness)
            
            # Display
            h, w = legend_img.shape[:2]
            qimg = QImage(legend_img.data, w, h, 3 * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(
                self.ui.img_legend.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.ui.img_legend.setPixmap(pixmap)
            
        except Exception as e:
            print(f"❌ Legend creation error: {e}")


    @Slot(str)
    def on_colormap_changed(self, colormap_name):
        """Update display when colormap changes."""
        if self.current_classification_map is not None:
            self.display_classification_map(self.current_classification_map)
            self.status_message.emit(f"Colormap: {colormap_name}", 0)

    @Slot()
    def on_vis_range_changed(self):
        """Update display when vmin/vmax changes."""
        if self.current_classification_map is not None:
            self.display_classification_map(self.current_classification_map)

    # ========== SAVE ==========

    @Slot()
    def save_classification_map(self):
        """Save classification map to file."""
        if self.current_classification_map is None:
            QMessageBox.warning(
                self, "No Classification", "Apply classification first before saving"
            )
            return

        folder = self.ui.folder_save_path_4.text().strip()
        if not folder or not os.path.exists(folder):
            QMessageBox.warning(
                self, "No Folder", "Please select a valid output folder first"
            )
            return

        classification_image = self.convert_classification_to_image(
            self.current_classification_map
        )
        if classification_image is None:
            return

        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(folder, f"classification_{timestamp}.png")

        if cv2.imwrite(filepath, classification_image):
            self.status_message.emit(
                f"Classification saved: {os.path.basename(filepath)}", 0
            )
            QMessageBox.information(
                self,
                "Saved",
                f"✅ Classification map saved:\n{os.path.basename(filepath)}",
            )
        else:
            QMessageBox.critical(self, "Save Error", "Failed to save classification")

    def convert_classification_to_image(self, label_map):
        """Convert classification map to normalized uint8 image."""
        if label_map is None:
            return None

        valid_mask = np.isfinite(label_map)
        valid_values = label_map[valid_mask]

        if valid_values.size == 0:
            return np.zeros_like(label_map, dtype=np.uint8)

        vmin, vmax = np.min(valid_values), np.max(valid_values)
        norm = (
            np.where(valid_mask, (label_map - vmin) / (vmax - vmin) * 255.0, 0)
            if vmax > vmin
            else np.zeros_like(label_map)
        )

        return norm.astype(np.uint8)
