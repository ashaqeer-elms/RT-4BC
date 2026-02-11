from PySide6.QtCore import QObject, Signal
import numpy as np
import re

class CoreRasterCalculator(QObject):
    """Handles raster calculation with multiple stored rasters."""
    
    # ✅ NEW: Signals for status updates
    status_message = Signal(str, int)  # (message, timeout)
    
    def __init__(self):
        super().__init__()
        self.calculated_rasters = {}
        self.raster_expressions = {}
        self.raster_counter = 0
    
    def validate_expression(self, expression):
        """
        Validate raster expression for safety.
        
        Returns:
            (bool, str): (is_valid, error_message)
        """
        if not expression.strip():
            return False, "Expression is empty"
        
        # ✅ FIX: Allow parentheses and operators (removed extra backslashes)
        allowed = re.compile(r"^[\w\s\+\-\*\/\%\(\)\.]+$")
        
        if not allowed.match(expression):
            return False, "Expression contains invalid characters"
        
        # Check for band references
        if not any(band in expression for band in ["R1", "R2", "R3", "R4"]):
            return False, "Expression must reference at least one band (R1-R4)"
        
        return True, ""
    
    def evaluate_expression(self, expression, reflectance_tiles):
        """
        Evaluate raster expression on reflectance tiles.
        
        Args:
            expression: String expression like "(R1 - R2) / (R1 + R2)"
            reflectance_tiles: List of 4 numpy arrays
        
        Returns:
            numpy array result or None if error
        """
        if reflectance_tiles is None or len(reflectance_tiles) != 4:
            return None
        
        # Create namespace with band references
        namespace = {
            "R1": reflectance_tiles[0],
            "R2": reflectance_tiles[1],
            "R3": reflectance_tiles[2],
            "R4": reflectance_tiles[3],
            "np": np,
        }
        
        try:
            # ✅ SIMPLEST FIX: Just use eval with namespace
            result = eval(expression, namespace)
            
            # Ensure result is numpy array
            if not isinstance(result, np.ndarray):
                result = np.array(result)
            
            return result
            
        except Exception as e:
            print(f"❌ Raster eval error: {e}")
            print(f"   Expression: {expression}")
            return None
    
    def add_calculated_raster(self, expression, result):
        """Store a newly calculated raster (NO PRINT - handled by Lib)."""
        self.raster_counter += 1
        raster_name = f"Raster {self.raster_counter}"
        self.calculated_rasters[raster_name] = result
        self.raster_expressions[raster_name] = expression
        return raster_name

    def get_raster_list(self):
        """Get list of all calculated raster names."""
        return list(self.calculated_rasters.keys())
    
    def get_raster(self, raster_name):
        """Get a specific calculated raster by name."""
        return self.calculated_rasters.get(raster_name)
    

    
    def clear_all_rasters(self):
        """Clear all calculated rasters (NO PRINT - handled by Lib)."""
        self.calculated_rasters.clear()
        self.raster_expressions.clear()
        self.raster_counter = 0
