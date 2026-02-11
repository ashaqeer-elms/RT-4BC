from PySide6.QtWidgets import QWidget, QFileDialog
from PySide6.QtCore import Slot, QTimer, Signal

from UI.ui_Calibration import Ui_Form
from Core.Core_ImageLoad import load_reference_image
from Core.Core_DarkNoiseEstimation import CoreDarkNoiseEstimator
from Core.Core_ReferenceRadianceEstimation import CoreRefRadianceEstimator


class CalibrationTab(QWidget):

     # Signal for status messages
    status_message = Signal(str, int)  # (message, timeout_ms)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        
        # === BACKGROUND NOISE SECTION ===
        self.dark_noise_estimator = CoreDarkNoiseEstimator()
        
        # Map UI elements for background
        self.bg_labels = [
            self.ui.bg_img_5,  # BAND 1
            self.ui.bg_img_6,  # BAND 2
            self.ui.bg_img_8,  # BAND 3
            self.ui.bg_img_7   # BAND 4
        ]
        
        self.bg_cam_entries = [
            self.ui.bg_val_b1_2,
            self.ui.bg_val_b2_2,
            self.ui.bg_val_b3_2,
            self.ui.bg_val_b4_2
        ]
        
        # Connect background controls
        self.ui.bg_img_open_dir_2.clicked.connect(self.select_bg_file)
        self.ui.bg_img_load_2.clicked.connect(self.load_bg_image)
        self.ui.bg_noise_est_2.clicked.connect(self.estimate_bg_noise)
        
        # === REFERENCE RADIANCE SECTION ===
        self.ref_radiance_estimator = CoreRefRadianceEstimator()
        
        # Map UI elements for reference
        self.ref_labels = [
            self.ui.ref_img_5,  # BAND 1
            self.ui.ref_img_6,  # BAND 2
            self.ui.ref_img_8,  # BAND 3
            self.ui.ref_img_7   # BAND 4
        ]
        
        self.ref_cam_entries = [
            self.ui.ref_rad_val_b1_2,
            self.ui.ref_rad_val_b2_2,
            self.ui.ref_rad_val_b3_2,
            self.ui.ref_rad_val_b4_2
        ]
        
        # Connect reference controls
        self.ui.ref_img_open_dir_2.clicked.connect(self.select_ref_file)
        self.ui.ref_img_load_2.clicked.connect(self.load_ref_image)
        self.ui.ref_rad_est_2.clicked.connect(self.estimate_ref_radiance)
        
        # Auto-load background and reference on startup
        QTimer.singleShot(100, self.auto_load_initial_data)
    
    # ========== BACKGROUND NOISE METHODS ==========
    
    @Slot()
    def select_bg_file(self):
        """Open file dialog to select background image file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Image",
            "",
            "PNG files (*.png)"
        )
        if path:
            self.ui.bg_img_dir_path_2.setText(path)
    
    @Slot()
    def load_bg_image(self):
        """Load background image from path in entry field."""
        path = self.ui.bg_img_dir_path_2.text().strip()
        if not path:
            return
        
        load_reference_image(
            self.ui.bg_img_dir_path_2,
            self.bg_labels,
            tiles_store=self.dark_noise_estimator.bg_tiles,
            path=path
        )
    
    @Slot()
    def estimate_bg_noise(self):
        """Estimate background noise from loaded image."""
        self.dark_noise_estimator.estimate_background_noise(
            self.bg_labels,
            self.bg_cam_entries
        )
    
    # ========== REFERENCE RADIANCE METHODS ==========
    
    @Slot()
    def select_ref_file(self):
        """Open file dialog to select reference image file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Reference Image",
            "",
            "PNG files (*.png)"
        )
        if path:
            self.ui.ref_img_dir_path_2.setText(path)
    
    @Slot()
    def load_ref_image(self):
        """Load reference image from path in entry field."""
        path = self.ui.ref_img_dir_path_2.text().strip()
        if not path:
            return
        
        load_reference_image(
            self.ui.ref_img_dir_path_2,
            self.ref_labels,
            tiles_store=self.ref_radiance_estimator.ref_tiles,
            path=path
        )
    
    @Slot()
    def estimate_ref_radiance(self):
        """Estimate reference radiance from loaded image."""
        self.ref_radiance_estimator.estimate_reference_radiance(
            self.ui.ref_img_dir_path_2,
            self.ref_labels,
            self.ref_cam_entries,
            self.bg_cam_entries
        )
    
    # ========== AUTO-LOAD ==========
    
    def auto_load_initial_data(self):
        """Auto-load background and reference images on startup."""
        # Auto-load background
        self.dark_noise_estimator.auto_load_background(
            self.ui.bg_img_dir_path_2,
            self.bg_labels
        )
        
        # Auto-estimate background noise if image was loaded
        if self.dark_noise_estimator.bg_tiles[0] is not None:
            QTimer.singleShot(200, self.estimate_bg_noise)
        
        # Auto-load reference
        self.ref_radiance_estimator.auto_load_reference(
            self.ui.ref_img_dir_path_2,
            self.ref_labels
        )
        
        # Auto-estimate reference radiance if image was loaded
        if self.ref_radiance_estimator.ref_tiles[0] is not None:
            QTimer.singleShot(400, self.estimate_ref_radiance)
