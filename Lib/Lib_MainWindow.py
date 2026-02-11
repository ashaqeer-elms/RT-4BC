import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Slot
from UI.ui_MainWindow import Ui_MainWindow
from Lib.Lib_CameraViewer import CameraViewerTab
from Lib.Lib_Calibration import CalibrationTab
from Lib.Lib_RasterCalculation import RasterCalculationTab
from Lib.Lib_Classification import ClassificationTab
import os

def ensure_data_folders():
    """Create Data folder structure if it doesn't exist."""
    
    # ✅ FIX: Handle both script and exe modes
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)  # Go up from Lib/ to project root
    
    data_base = os.path.join(base_dir, "Data")
    
    # Create main data folders
    os.makedirs(os.path.join(data_base, "Raw"), exist_ok=True)
    os.makedirs(os.path.join(data_base, "Raster"), exist_ok=True)
    os.makedirs(os.path.join(data_base, "Classification"), exist_ok=True)
    
    # Create Calibration folder with subfolders
    calibration_base = os.path.join(data_base, "Calibration")
    os.makedirs(os.path.join(calibration_base, "Background"), exist_ok=True)
    os.makedirs(os.path.join(calibration_base, "Reference"), exist_ok=True)
    os.makedirs(os.path.join(calibration_base, "Transformation"), exist_ok=True)
    
    # Create Raster folder with subfolders
    raster_base = os.path.join(data_base, "Raster")
    os.makedirs(os.path.join(raster_base, "Raster"), exist_ok=True)
    os.makedirs(os.path.join(raster_base, "Reflectance"), exist_ok=True)
    
    return data_base


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # ✅ ENSURE DATA FOLDERS EXIST FIRST
        try:
            data_path = ensure_data_folders()
            print()
        except Exception as e:
            print(f"⚠ Warning: Could not create Data folders: {e}")
        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # ✅ SET WINDOW TITLE
        self.setWindowTitle("nBC-RT Viewer")
        
        # ✅ INITIALIZE STATUS BAR
        self.statusBar().showMessage("Initializing...", 0)
        
        # Replace empty tabs
        self.ui.main_tab.removeTab(0)
        self.camera_tab = CameraViewerTab(self.ui.main_tab)
        self.ui.main_tab.insertTab(0, self.camera_tab, "Camera View")
        
        self.ui.main_tab.removeTab(1)
        self.calibration_tab = CalibrationTab(self.ui.main_tab)
        self.ui.main_tab.insertTab(1, self.calibration_tab, "Calibration")
        
        self.ui.main_tab.removeTab(2)
        self.raster_tab = RasterCalculationTab(self.ui.main_tab)
        self.ui.main_tab.insertTab(2, self.raster_tab, "Reflectance Calculation")
        
        self.ui.main_tab.removeTab(3)
        self.classification_tab = ClassificationTab(self.ui.main_tab)
        self.ui.main_tab.insertTab(3, self.classification_tab, "Classification")
        
        # ✅ START AT FIRST TAB
        self.ui.main_tab.setCurrentIndex(0)
        
        # === LINK TABS FOR DATA SHARING ===
        self.raster_tab.set_tab_references(self.camera_tab, self.calibration_tab)
        
        # ✅ CRITICAL: Link classification tab to raster tab
        self.classification_tab.set_tab_references(self.raster_tab)
        
        if hasattr(self.raster_tab, 'reflectance_updated'):
            self.raster_tab.reflectance_updated.connect(
                self.classification_tab.auto_reclassify_if_active
            )
            
        # ✅ CONNECT ALL TAB STATUS SIGNALS TO STATUS BAR
        self.camera_tab.status_message.connect(self.update_status_bar)
        self.calibration_tab.status_message.connect(self.update_status_bar)
        self.raster_tab.status_message.connect(self.update_status_bar)
        self.classification_tab.status_message.connect(self.update_status_bar)
        
        # ✅ STATUS BAR: Ready message
        self.statusBar().showMessage("Ready", 0)
    
    @Slot(str, int)
    def update_status_bar(self, message, timeout):
        """
        Update main window status bar from any tab.
        
        Args:
            message: Status message to display
            timeout: Display duration in milliseconds (0 = permanent)
        """
        self.statusBar().showMessage(message, timeout)
