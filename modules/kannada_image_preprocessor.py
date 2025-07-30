"""
Advanced Kannada-specific image preprocessing for OCR optimization.

This module provides aggressive preprocessing specifically tuned for historical Kannada magazines
with faded scans, skewed pages, ink bleed-through, and legacy fonts. The preprocessing pipeline
is designed to maximize Google Vision OCR accuracy while preserving delicate Kannada diacritics.
"""

import cv2
import numpy as np
from PIL import Image
import logging
from typing import Tuple, Optional
import math

logger = logging.getLogger(__name__)

class KannadaImagePreprocessor:
    """
    Kannada-specific image preprocessing pipeline optimized for historical magazine scans.
    
    Key features:
    - Preserves thin vowel signs (ಿ, ೀ, ೆ, ೇ, etc.) from over-erosion
    - Handles faded/low-contrast magazine pages with CLAHE
    - Removes dark border artifacts common in old scans
    - Applies gentle deskewing to straighten tilted pages
    - Uses adaptive thresholding tuned for Kannada character recognition
    """
    
    def __init__(self):
        # Kannada-specific parameters tuned for vowel sign preservation
        self.clahe_clip_limit = 2.5  # Conservative to avoid over-enhancement
        self.clahe_grid_size = (12, 12)  # Larger grid for magazine pages
        
        # Morphological kernel sizes (small to preserve diacritics)
        self.noise_kernel_size = (2, 2)  # Minimal noise removal
        self.closing_kernel_size = (1, 2)  # Vertical emphasis for Kannada
        
        # Adaptive threshold parameters
        self.adaptive_block_size = 15  # Odd number for local adaptation
        self.adaptive_c = 4  # Conservative constant
        
        # Deskewing parameters
        self.max_skew_angle = 15.0  # Maximum correction angle
        self.min_contour_area = 100  # Minimum contour size for angle detection
        
    def preprocess_kannada_image(self, img: Image.Image) -> np.ndarray:
        """
        Main preprocessing pipeline for Kannada magazine scans.
        
        Args:
            img: PIL Image of a PDF page
            
        Returns:
            np.ndarray: High-contrast, binarized image ready for OCR
        """
        logger.debug("Starting Kannada-specific image preprocessing")
        
        try:
            # Convert PIL to OpenCV format (RGB -> BGR)
            opencv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # Step 1: Initial size optimization for memory efficiency
            processed = self._resize_if_needed(opencv_img)
            
            # Step 2: Convert to grayscale with optimal weights for text
            gray = self._convert_to_grayscale(processed)
            
            # Step 3: Remove border artifacts common in magazine scans
            bordered_removed = self._remove_dark_borders(gray)
            
            # Step 4: Apply CLAHE for contrast enhancement (gentle for magazines)
            contrast_enhanced = self._apply_clahe(bordered_removed)
            
            # Step 5: Noise reduction while preserving fine details
            denoised = self._reduce_noise_preserve_text(contrast_enhanced)
            
            # Step 6: Deskew to correct tilted scans
            deskewed = self._deskew_image(denoised)
            
            # Step 7: Adaptive thresholding tuned for Kannada
            binarized = self._adaptive_threshold_kannada(deskewed)
            
            # Step 8: Final morphological cleanup (very conservative)
            final = self._final_morphological_cleanup(binarized)
            
            logger.debug("Kannada preprocessing completed successfully")
            return final
            
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            # Return simple grayscale conversion as fallback
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    
    def _resize_if_needed(self, img: np.ndarray, max_dimension: int = 2500) -> np.ndarray:
        """
        Resize image if too large, maintaining aspect ratio.
        Magazine scans are often very high resolution but don't need to be.
        """
        height, width = img.shape[:2]
        
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Use INTER_AREA for downscaling (best quality)
            resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.debug(f"Resized from {width}x{height} to {new_width}x{new_height}")
            return resized
        
        return img
    
    def _convert_to_grayscale(self, img: np.ndarray) -> np.ndarray:
        """
        Convert to grayscale with weights optimized for text recognition.
        Standard weights work well for most text, but we can fine-tune.
        """
        if len(img.shape) == 3:
            # Use standard weights but could be tuned for Kannada magazine ink
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        return gray
    
    def _remove_dark_borders(self, img: np.ndarray) -> np.ndarray:
        """
        Remove dark border artifacts common in scanned magazines.
        Old magazine scans often have dark edges that interfere with OCR.
        """
        h, w = img.shape
        
        # Create a mask to identify potential border regions
        # Check if corners are significantly darker than center
        corner_size = min(50, h//20, w//20)
        
        # Sample corner regions
        corners = [
            img[0:corner_size, 0:corner_size],  # Top-left
            img[0:corner_size, w-corner_size:w],  # Top-right
            img[h-corner_size:h, 0:corner_size],  # Bottom-left
            img[h-corner_size:h, w-corner_size:w]  # Bottom-right
        ]
        
        # Sample center region
        center_y, center_x = h//2, w//2
        center_region = img[center_y-corner_size:center_y+corner_size, 
                          center_x-corner_size:center_x+corner_size]
        
        corner_mean = np.mean([np.mean(corner) for corner in corners])
        center_mean = np.mean(center_region)
        
        # If corners are significantly darker, apply border removal
        if corner_mean < center_mean - 20:  # Threshold for "dark border"
            logger.debug(f"Dark border detected: corner={corner_mean:.1f}, center={center_mean:.1f}")
            
            # Create a border mask (more aggressive at edges)
            border_mask = np.ones_like(img, dtype=np.uint8)
            border_width = max(5, min(h//50, w//50))
            
            # Feather the border mask for smooth transition
            border_mask[0:border_width, :] = 0
            border_mask[h-border_width:h, :] = 0
            border_mask[:, 0:border_width] = 0
            border_mask[:, w-border_width:w] = 0
            
            # Apply Gaussian blur to create smooth transition
            border_mask = cv2.GaussianBlur(border_mask.astype(np.float32), (border_width*2+1, border_width*2+1), 0)
            
            # Blend original with center-intensity background
            background = np.full_like(img, center_mean)
            result = (img * border_mask + background * (1 - border_mask)).astype(np.uint8)
            
            return result
        
        return img
    
    def _apply_clahe(self, img: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).
        This significantly improves faded magazine text while preventing over-enhancement.
        """
        clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip_limit,
            tileGridSize=self.clahe_grid_size
        )
        
        enhanced = clahe.apply(img)
        logger.debug("Applied CLAHE for contrast enhancement")
        return enhanced
    
    def _reduce_noise_preserve_text(self, img: np.ndarray) -> np.ndarray:
        """
        Reduce noise while carefully preserving thin Kannada vowel signs.
        Uses bilateral filter which smooths while preserving edges.
        """
        # Bilateral filter is excellent for text - reduces noise but preserves edges
        # Parameters: d=5 (neighborhood), sigmaColor=50, sigmaSpace=50
        denoised = cv2.bilateralFilter(img, 5, 50, 50)
        
        # Optional: Very gentle median blur for speckle noise (only if needed)
        # We skip this by default to preserve thin diacritics
        # denoised = cv2.medianBlur(denoised, 3)
        
        logger.debug("Applied noise reduction with edge preservation")
        return denoised
    
    def _deskew_image(self, img: np.ndarray) -> np.ndarray:
        """
        Detect and correct skew in scanned pages.
        Uses contour-based method that's robust for magazine layouts.
        """
        try:
            # Create binary image for contour detection
            _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Find contours (text lines/characters)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by area to get text elements
            text_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > self.min_contour_area]
            
            if len(text_contours) < 10:  # Need enough contours for reliable detection
                logger.debug("Insufficient contours for skew detection")
                return img
            
            # Calculate angles from text contours
            angles = []
            for contour in text_contours:
                # Get minimum area rectangle
                rect = cv2.minAreaRect(contour)
                angle = rect[2]
                
                # Normalize angle to [-45, 45] range
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                
                # Only consider reasonable skew angles
                if abs(angle) <= self.max_skew_angle:
                    angles.append(angle)
            
            if not angles:
                logger.debug("No valid skew angles detected")
                return img
            
            # Use median angle for robustness
            skew_angle = np.median(angles)
            
            # Only correct if angle is significant
            if abs(skew_angle) > 0.5:  # Minimum threshold for correction
                logger.debug(f"Correcting skew angle: {skew_angle:.2f} degrees")
                
                # Calculate rotation matrix
                h, w = img.shape
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
                
                # Calculate new bounding dimensions
                cos_angle = abs(rotation_matrix[0, 0])
                sin_angle = abs(rotation_matrix[0, 1])
                new_w = int((h * sin_angle) + (w * cos_angle))
                new_h = int((h * cos_angle) + (w * sin_angle))
                
                # Adjust rotation matrix for new center
                rotation_matrix[0, 2] += (new_w / 2) - center[0]
                rotation_matrix[1, 2] += (new_h / 2) - center[1]
                
                # Apply rotation
                rotated = cv2.warpAffine(
                    img, rotation_matrix, (new_w, new_h),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=255  # White background
                )
                
                return rotated
            else:
                logger.debug(f"Skew angle {skew_angle:.2f}° too small, skipping correction")
                
        except Exception as e:
            logger.warning(f"Skew correction failed: {e}")
        
        return img
    
    def _adaptive_threshold_kannada(self, img: np.ndarray) -> np.ndarray:
        """
        Apply adaptive thresholding optimized for Kannada text.
        Parameters are tuned to handle varying lighting in magazine scans.
        """
        # Adaptive threshold with Gaussian weighting
        binary = cv2.adaptiveThreshold(
            img,
            255,  # Max value
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,  # Adaptive method
            cv2.THRESH_BINARY,  # Threshold type
            self.adaptive_block_size,  # Block size (must be odd)
            self.adaptive_c  # Constant subtracted from mean
        )
        
        logger.debug("Applied adaptive thresholding for Kannada text")
        return binary
    
    def _final_morphological_cleanup(self, img: np.ndarray) -> np.ndarray:
        """
        Final morphological operations to clean up the binary image.
        Very conservative to preserve thin Kannada vowel signs.
        """
        # Small closing operation to connect broken character parts
        # Use a small vertical-oriented kernel since Kannada has vertical elements
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.closing_kernel_size)
        closed = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel_close)
        
        # Very gentle opening to remove tiny noise specks
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.noise_kernel_size)
        cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_open)
        
        logger.debug("Applied final morphological cleanup")
        return cleaned


# Convenience function for easy integration
def preprocess_kannada_image(img: Image.Image) -> np.ndarray:
    """
    Convenience function for Kannada image preprocessing.
    
    This function applies an aggressive preprocessing pipeline specifically designed
    for historical Kannada magazines with challenging scan quality.
    
    Key improvements for Kannada OCR:
    1. CLAHE contrast enhancement for faded text
    2. Bilateral filtering to reduce noise while preserving character edges
    3. Adaptive thresholding tuned for varying lighting conditions
    4. Conservative morphological operations to preserve thin vowel signs
    5. Automatic deskewing for tilted scans
    6. Dark border removal for old magazine scans
    
    Args:
        img: PIL Image object (typically from PDF page conversion)
        
    Returns:
        np.ndarray: Preprocessed grayscale image ready for OCR
        
    Example:
        from PIL import Image
        import cv2
        
        # Load your image
        img = Image.open("kannada_page.jpg")
        
        # Preprocess for OCR
        processed = preprocess_kannada_image(img)
        
        # Convert back to PIL for OCR
        processed_pil = Image.fromarray(processed)
    """
    preprocessor = KannadaImagePreprocessor()
    return preprocessor.preprocess_kannada_image(img)


# Alternative preprocessing for different scan types
def preprocess_kannada_image_aggressive(img: Image.Image) -> np.ndarray:
    """
    More aggressive preprocessing for very poor quality scans.
    Use when standard preprocessing fails to extract readable text.
    """
    preprocessor = KannadaImagePreprocessor()
    
    # More aggressive parameters
    preprocessor.clahe_clip_limit = 3.5  # Higher contrast
    preprocessor.adaptive_c = 6  # More aggressive thresholding
    preprocessor.closing_kernel_size = (2, 3)  # Stronger morphological ops
    
    return preprocessor.preprocess_kannada_image(img)


def preprocess_kannada_image_gentle(img: Image.Image) -> np.ndarray:
    """
    Gentler preprocessing for high-quality scans that might be over-processed.
    Use when standard preprocessing removes too much detail.
    """
    preprocessor = KannadaImagePreprocessor()
    
    # More conservative parameters
    preprocessor.clahe_clip_limit = 2.0  # Gentler contrast
    preprocessor.adaptive_c = 3  # More conservative thresholding
    preprocessor.closing_kernel_size = (1, 1)  # Minimal morphological ops
    
    return preprocessor.preprocess_kannada_image(img)
