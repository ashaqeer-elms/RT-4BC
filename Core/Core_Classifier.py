from PySide6.QtCore import QObject, Signal
import numpy as np
import joblib
import os
import sys

class CoreClassifier(QObject):
    """Handles machine learning model loading and classification."""
    
    status_message = Signal(str, int)
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.model_path = None
    
    def load_model(self, filepath):
        """
        Load a joblib classification model with detailed error reporting.
        
        Args:
            filepath: Path to .joblib model file
            
        Returns:
            bool: True if successful, False otherwise
        """
        print("\n" + "="*60)
        print("🔍 MODEL LOADING DIAGNOSTIC")
        print("="*60)
        
        # Step 1: Check file exists
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            return False
        
        print(f"✅ File exists: {filepath}")
        
        # Step 2: Check file size
        file_size = os.path.getsize(filepath)
        print(f"✅ File size: {file_size:,} bytes ({file_size/1024:.2f} KB)")
        
        if file_size < 100:
            print("❌ File is too small - likely corrupted or empty")
            return False
        
        # Step 3: Check Python and library versions
        print(f"\n📦 Environment:")
        print(f"   Python version: {sys.version.split()[0]}")
        
        try:
            import sklearn
            print(f"   scikit-learn: {sklearn.__version__}")
        except ImportError:
            print(f"   scikit-learn: NOT INSTALLED")
        
        try:
            import xgboost
            print(f"   xgboost: {xgboost.__version__}")
        except ImportError:
            print(f"   xgboost: not installed")
        
        # Step 4: Try to load
        print(f"\n🔄 Attempting to load model...")
        
        try:
            self.model = joblib.load(filepath)
            
        except ModuleNotFoundError as e:
            print(f"\n❌ MISSING PACKAGE")
            print(f"   Error: {e}")
            missing_module = str(e).split("'")[1] if "'" in str(e) else str(e).split()[-1]
            print(f"   Missing: {missing_module}")
            print(f"\n💡 FIX: Install the missing package:")
            print(f"   pip install {missing_module}")
            return False
            
        except AttributeError as e:
            print(f"\n❌ VERSION MISMATCH")
            print(f"   Error: {e}")
            print(f"\n💡 FIX: Try updating scikit-learn:")
            print(f"   pip install --upgrade scikit-learn")
            return False
            
        except EOFError as e:
            print(f"\n❌ FILE CORRUPTED")
            print(f"   Error: {e}")
            print(f"   The .joblib file appears to be incomplete or damaged")
            return False
            
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error message: {e}")
            print(f"\n📋 Full traceback:")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 5: Validate loaded object
        print(f"\n✅ Object loaded successfully!")
        print(f"   Type: {type(self.model)}")
        print(f"   Class: {type(self.model).__name__}")
        print(f"   Module: {type(self.model).__module__}")
        
        # Step 6: Check for predict method
        if not hasattr(self.model, 'predict'):
            print(f"\n❌ INVALID MODEL")
            print(f"   The loaded object doesn't have a 'predict' method")
            print(f"   Available methods: {[m for m in dir(self.model) if not m.startswith('_')][:10]}")
            return False
        
        print(f"✅ Has 'predict' method")
        
        # Step 7: Extract model information
        print(f"\n📊 Model Information:")
        
        if hasattr(self.model, 'n_features_in_'):
            print(f"   Expected features: {self.model.n_features_in_}")
        else:
            print(f"   Expected features: Unknown (attribute not found)")
        
        if hasattr(self.model, 'classes_'):
            print(f"   Classes: {self.model.classes_}")
        else:
            print(f"   Classes: Unknown (attribute not found)")
        
        if hasattr(self.model, 'feature_names_in_'):
            print(f"   Feature names: {self.model.feature_names_in_}")
        
        # Step 8: Test prediction
        print(f"\n🧪 Testing prediction...")
        try:
            n_features = getattr(self.model, 'n_features_in_', 3)
            X_test = np.random.rand(1, n_features)
            print(f"   Test input shape: {X_test.shape}")
            
            y_pred = self.model.predict(X_test)
            print(f"✅ Prediction test successful: {y_pred}")
            
        except Exception as e:
            print(f"⚠️  Prediction test failed: {e}")
            print(f"   (This may be normal if the model expects specific preprocessing)")
        
        # Success
        self.model_path = filepath
        print(f"\n" + "="*60)
        print(f"✅ MODEL LOADED SUCCESSFULLY")
        print("="*60 + "\n")
        return True
    
    def predict_classification(self, feature_stack):
        """
        Predict classification map using loaded model.
        
        Args:
            feature_stack: numpy array of shape (num_features, H, W)
        
        Returns:
            label_map: numpy array of shape (H, W) with class labels
        """
        if self.model is None:
            print("❌ No model loaded")
            return None
        
        if feature_stack is None or feature_stack.size == 0:
            print("❌ Invalid feature stack")
            return None
        
        try:
            num_features, H, W = feature_stack.shape
            print(f"\n🔧 Prediction starting...")
            print(f"   Feature stack shape: {feature_stack.shape}")
            
            # Reshape to (H*W, num_features)
            X = feature_stack.reshape(num_features, -1).T
            print(f"   Reshaped to: {X.shape}")
            
            # Create valid pixel mask
            valid_mask = np.all(np.isfinite(X), axis=1)
            num_valid = np.sum(valid_mask)
            print(f"   Valid pixels: {num_valid:,} / {len(valid_mask):,} ({100*num_valid/len(valid_mask):.1f}%)")
            
            if num_valid == 0:
                print("❌ No valid pixels to classify")
                return None
            
            # Predict only on valid pixels
            print(f"   Running model.predict()...")
            y_pred = self.model.predict(X[valid_mask])
            print(f"   Prediction complete!")
            
            # Initialize result map with NaN
            label_map = np.full((H * W), np.nan)
            label_map[valid_mask] = y_pred
            label_map = label_map.reshape(H, W)
            
            # Summary
            unique_classes = np.unique(y_pred)
            print(f"✅ Classification successful!")
            print(f"   Unique classes: {unique_classes}")
            for cls in unique_classes:
                count = np.sum(y_pred == cls)
                print(f"   Class {cls}: {count:,} pixels ({100*count/num_valid:.1f}%)")
            
            return label_map
            
        except Exception as e:
            print(f"❌ Classification error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_model_info(self):
        """Get information about loaded model."""
        if self.model is None:
            return "No model loaded"
        
        info = f"Model: {os.path.basename(self.model_path) if self.model_path else 'Unknown'}\n"
        info += f"Type: {type(self.model).__name__}"
        
        if hasattr(self.model, 'n_features_in_'):
            info += f"\nExpected features: {self.model.n_features_in_}"
        
        if hasattr(self.model, 'classes_'):
            info += f"\nClasses: {self.model.classes_}"
        
        return info
