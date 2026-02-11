from PySide6.QtCore import QObject, Signal
import cv2
import numpy as np
import configparser
import os

class CoreGeoTransform(QObject):
    """
    Handles geometric transformation for multi-band image alignment.
    """
    
    # ✅ Signals for status updates
    transform_completed = Signal(dict)
    error_occurred = Signal(str)
    status_message = Signal(str, int)  # (message, timeout)
    
    def __init__(self):
        super().__init__()
        
        self.homography_matrices = {
            'H_21': None,
            'H_31': None,
            'H_41': None
        }
        
        self.akaze = cv2.AKAZE_create()
        self.keypoints = {}
        self.descriptors = {}
        self.matches = {}
        
        # ✅ STATUS MESSAGE (no print)
        self.status_message.emit("CoreGeoTransform initialized", 0)
    
    def detect_features_akaze(self, images):
        """
        Detect AKAZE features in all 4 band images.
        
        Args:
            images: List of 4 grayscale images [B1, B2, B3, B4]
            
        Returns:
            dict: Keypoints and descriptors for each band
        """
        if len(images) != 4:
            self.error_occurred.emit("Expected 4 band images")
            return None
        
        results = {}
        
        for i, img in enumerate(images):
            if img is None:
                self.error_occurred.emit(f"Band {i+1} image is None")
                return None
            
            # Detect keypoints and compute descriptors
            kp, desc = self.akaze.detectAndCompute(img, None)
            
            results[f'B{i+1}'] = {
                'keypoints': kp,
                'descriptors': desc,
                'num_features': len(kp)
            }
            
            print(f"🔍 Band {i+1}: {len(kp)} features detected")
        
        self.keypoints = results
        return results
    
    def match_features(self, desc1, desc2, ratio_threshold=0.75):
        """
        Match features between two descriptor sets using BFMatcher.
        
        Args:
            desc1: Descriptors from reference image (Band 1)
            desc2: Descriptors from target image (Band 2/3/4)
            ratio_threshold: Lowe's ratio test threshold
            
        Returns:
            list: Good matches after ratio test
        """
        # Use Hamming distance for binary descriptors (AKAZE)
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        
        try:
            # Find k=2 best matches
            matches = bf.knnMatch(desc1, desc2, k=2)
            
            # Apply Lowe's ratio test
            good_matches = []
            for m_n in matches:
                if len(m_n) == 2:
                    m, n = m_n
                    if m.distance < ratio_threshold * n.distance:
                        good_matches.append(m)
            
            print(f"   ✓ {len(good_matches)} good matches (from {len(matches)} total)")
            return good_matches
            
        except Exception as e:
            print(f"   ❌ Matching error: {e}")
            return []
    
    def calculate_homography(self, kp1, kp2, matches, min_matches=10):
        """
        Calculate homography matrix from matched keypoints.
        
        Args:
            kp1: Keypoints from reference image
            kp2: Keypoints from target image
            matches: List of good matches
            min_matches: Minimum number of matches required
            
        Returns:
            numpy.ndarray: 3x3 homography matrix or None
        """
        if len(matches) < min_matches:
            print(f"   ❌ Insufficient matches: {len(matches)} < {min_matches}")
            return None
        
        # Extract matched point coordinates
        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        # Calculate homography using RANSAC
        H, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
        
        if H is None:
            print("   ❌ Homography calculation failed")
            return None
        
        # Count inliers
        inliers = np.sum(mask)
        print(f"   ✓ Homography calculated: {inliers}/{len(matches)} inliers")
        
        return H
    
    def automatic_transformation_estimation(self, images, return_matches=False):
        """
        Estimate homography using AKAZE feature detection.
        
        Args:
            images: List of 4 grayscale images (640x480)
            return_matches: If True, return keypoints and matches info
        
        Returns:
            Dictionary with homographies and optionally match info
        """
        # Create AKAZE detector
        akaze = cv2.AKAZE_create()
        
        # Reference image (Band 1)
        ref_img = images[0]
        kp_ref, des_ref = akaze.detectAndCompute(ref_img, None)
        
        results = {}
        matches_data = {}
        
        # Match each band to reference
        for i in [2, 3, 4]:
            target_img = images[i - 1]
            kp_target, des_target = akaze.detectAndCompute(target_img, None)
            
            # Match features using BFMatcher
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(des_target, des_ref, k=2)
            
            # Apply ratio test (Lowe's ratio test)
            good_matches = []
            for m_n in matches:
                if len(m_n) == 2:
                    m, n = m_n
                    if m.distance < 0.75 * n.distance:
                        good_matches.append(m)
            
            if len(good_matches) >= 4:
                # Extract matched points
                src_pts = np.float32([kp_target[m.queryIdx].pt for m in good_matches])
                dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good_matches])
                
                # Compute homography
                H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                
                results[f'H_{i}1'] = H
                
                # ✅ FIX: Store in self.homography_matrices
                self.homography_matrices[f'H_{i}1'] = H
                
                if return_matches:
                    matches_data[f'matches_{i}1'] = {
                        'keypoints1': kp_ref,
                        'keypoints2': kp_target,
                        'good_matches': good_matches,
                        'num_kp1': len(kp_ref),
                        'num_kp2': len(kp_target),
                        'num_matches': len(good_matches),
                        'num_inliers': int(mask.sum()) if mask is not None else 0
                    }
            else:
                results[f'H_{i}1'] = None
                # ✅ FIX: Also store None in self.homography_matrices
                self.homography_matrices[f'H_{i}1'] = None
                
                if return_matches:
                    matches_data[f'matches_{i}1'] = None
        
        if return_matches:
            results.update(matches_data)
        
        return results

    
    def warp_perspective(self, image, H, output_shape=None):
        """
        Warp image using homography matrix.
        
        Args:
            image: Input image to warp
            H: 3x3 homography matrix
            output_shape: (height, width) of output, defaults to input shape
            
        Returns:
            numpy.ndarray: Warped image
        """
        if H is None:
            return image
        
        if output_shape is None:
            output_shape = (image.shape[0], image.shape[1])
        
        warped = cv2.warpPerspective(image, H, (output_shape[1], output_shape[0]))
        return warped
    
    def align_all_bands(self, images):
        """
        Align all 4 bands to Band 1 using stored homography matrices.
        
        Args:
            images: List of 4 images [B1, B2, B3, B4]
            
        Returns:
            list: Aligned images [B1, B2_aligned, B3_aligned, B4_aligned]
        """
        if len(images) != 4:
            self.error_occurred.emit("Expected 4 band images")
            return None
        
        aligned_images = [images[0]]  # Band 1 is reference (no transformation)
        
        for i in [2, 3, 4]:
            H = self.homography_matrices.get(f'H_{i}1')
            if H is not None:
                aligned = self.warp_perspective(images[i-1], H)
                aligned_images.append(aligned)
                print(f"✓ Band {i} aligned")
            else:
                # No transformation available, use original
                aligned_images.append(images[i-1])
                print(f"⚠️ Band {i} not aligned (no transformation)")
        
        return aligned_images
    
    def save_config_ini(self, filepath):
        """
        Save homography matrices to INI configuration file.
        
        Args:
            filepath: Path to save .ini file
        """
        config = configparser.ConfigParser()
        
        # Save all matrices including H_11
        for key in ['H_11', 'H_21', 'H_31', 'H_41']:
            H = self.homography_matrices.get(key)
            
            if H is not None:
                # Flatten 3x3 matrix to comma-separated string
                H_flat = ','.join([str(val) for val in H.flatten()])
                config[key] = {'matrix': H_flat}
            else:
                config[key] = {'matrix': 'None'}
        
        # Write to file
        with open(filepath, 'w') as f:
            config.write(f)
        
        # ✅ STATUS MESSAGE
        self.status_message.emit(f"Configuration saved: {os.path.basename(filepath)}", 0)
    
    def load_config_ini(self, filepath):
        """
        Load homography matrices from INI configuration file.
        
        Args:
            filepath: Path to .ini file
            
        Returns:
            dict: Loaded homography matrices
        """
        if not os.path.exists(filepath):
            self.error_occurred.emit(f"File not found: {filepath}")
            return None
        
        config = configparser.ConfigParser()
        config.read(filepath)
        
        results = {}
        
        for key in ['H_21', 'H_31', 'H_41']:
            if key in config:
                matrix_str = config[key].get('matrix', 'None')
                if matrix_str == 'None':
                    results[key] = None
                    self.homography_matrices[key] = None
                else:
                    # Parse comma-separated values back to 3x3 matrix
                    values = [float(v) for v in matrix_str.split(',')]
                    H = np.array(values).reshape(3, 3)
                    results[key] = H
                    self.homography_matrices[key] = H
                    print(f"✓ Loaded {key}")
            else:
                results[key] = None
                self.homography_matrices[key] = None
        
        print(f"✅ Configuration loaded: {filepath}")
        return results
    
    def add_manual_point_pair(self, points_dict):
        """
        Add manual correspondence points for manual alignment.
        
        Args:
            points_dict: {'B1': (x,y), 'B2': (x,y), 'B3': (x,y), 'B4': (x,y)}
        """
        # Store for manual homography calculation
        # This would be implemented if manual point selection is needed
        pass
    
    def calculate_manual_homography(self, src_points, dst_points):
        """
        Calculate homography from manually selected point correspondences.
        
        Args:
            src_points: Nx2 array of source points
            dst_points: Nx2 array of destination points
            
        Returns:
            numpy.ndarray: 3x3 homography matrix
        """
        if len(src_points) < 4 or len(dst_points) < 4:
            print("❌ Need at least 4 point pairs for homography")
            return None
        
        src_pts = np.float32(src_points).reshape(-1, 1, 2)
        dst_pts = np.float32(dst_points).reshape(-1, 1, 2)
        
        H, _ = cv2.findHomography(src_pts, dst_pts, 0)
        return H
