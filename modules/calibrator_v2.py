"""
Módulo de calibração com multi-threshold OCR
"""
import cv2
import numpy as np
import pytesseract
import re
from typing import List
from PIL import Image, ImageEnhance
from .data_types import GraphFrame, AxisCalibration


class AxisCalibratorV2:
    """Calibra eixos com OCR robusto"""
    
    def __init__(self, img: np.ndarray, frame: GraphFrame):
        self.img = img
        self.frame = frame
        self.h, self.w = img.shape[:2]
    
    def calibrate_x_axis(self) -> AxisCalibration:
        """Calibra eixo X focando em números horizontais"""
        try:
            x1, y1 = self.frame.bottom_left
            x2, y2 = self.frame.bottom_right
            
            # ROI ABAIXO do eixo (onde ficam rótulos de X)
            margin_v = 200  # vertical
            margin_h = 50   # horizontal
            
            roi = self.img[
                y2:min(y2 + margin_v, self.h),  # SÓ abaixo
                max(0, x1 - margin_h):min(x2 + margin_h, self.w)
            ]
            
            if roi.size == 0:
                raise ValueError("ROI vazia")
            
            numbers = self._extract_numbers_multithreshold(roi)
            
            if len(numbers) >= 2:
                min_val = min(numbers)
                max_val = max(numbers)
                
                has_negative = any(n < 0 for n in numbers)
                has_positive = any(n > 0 for n in numbers)
                is_symmetric = has_negative and has_positive
                
                zero_pos = None
                if 0 in numbers or is_symmetric:
                    if min_val < 0 < max_val:
                        zero_pos = abs(min_val) / (max_val - min_val)
                    elif is_symmetric:
                        zero_pos = 0.5
                
                print(f"  ✓ Eixo X: {numbers}")
                return AxisCalibration(min_val, max_val, zero_pos, '', is_symmetric)
            
        except Exception as e:
            print(f"  ⚠️ Erro OCR X: {e}")
        
        print("  ⚠️ OCR X falhou, usando [0, 1]")
        return AxisCalibration(0.0, 1.0)
    
    def calibrate_y_axis(self) -> AxisCalibration:
        """Calibra eixo Y focando em números verticais à esquerda"""
        try:
            x1, y1 = self.frame.top_left
            _, y2 = self.frame.bottom_left
            
            # ROI À ESQUERDA do eixo (onde ficam rótulos de Y)
            margin_h = 250  # horizontal
            margin_v = 30   # vertical
            
            roi = self.img[
                max(0, y1 - margin_v):min(y2 + margin_v, self.h),
                max(0, x1 - margin_h):x1  # SÓ à esquerda
            ]
            
            if roi.size == 0:
                raise ValueError("ROI vazia")
            
            numbers = self._extract_numbers_multithreshold(roi)
            
            # Filtrar valores razoáveis para Y
            numbers = [n for n in numbers if 0 <= n <= 2.0]
            
            if len(numbers) >= 2:
                min_val = min(numbers)
                max_val = max(numbers)
                
                print(f"  ✓ Eixo Y: {numbers}")
                return AxisCalibration(min_val, max_val)
            
        except Exception as e:
            print(f"  ⚠️ Erro OCR Y: {e}")
        
        print("  ⚠️ OCR Y falhou, usando [0, 1]")
        return AxisCalibration(0.0, 1.0)
    
    def _extract_numbers_multithreshold(self, roi: np.ndarray) -> List[float]:
        """Multi-threshold OCR (técnica do gabarito)"""
        if roi.size == 0 or roi.shape[0] < 10 or roi.shape[1] < 10:
            return []
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        all_numbers = []
        
        # Estratégia 1: Múltiplos thresholds
        thresholds = [50, 70, 90, 110, 130, 150, 180]
        
        for thresh in thresholds:
            _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
            nums = self._ocr_image(binary, is_gray=True)
            all_numbers.extend(nums)
            
            # Também inverso
            _, binary_inv = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY_INV)
            nums_inv = self._ocr_image(binary_inv, is_gray=True)
            all_numbers.extend(nums_inv)
        
        # Estratégia 2: Adaptativo
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        all_numbers.extend(self._ocr_image(adaptive, is_gray=True))
        
        # Estratégia 3: Contraste aumentado
        enhanced = self._enhance_contrast(roi)
        all_numbers.extend(self._ocr_image(enhanced))
        
        # Limpar
        unique = sorted(set(all_numbers))
        
        if len(unique) > 3:
            unique = self._remove_outliers(unique)
        
        return unique
    
    def _ocr_image(self, img, is_gray=False) -> List[float]:
        """Executa OCR"""
        try:
            if is_gray:
                if len(img.shape) == 2:
                    pil_img = Image.fromarray(img)
                else:
                    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            else:
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            # Resize para OCR
            width, height = pil_img.size
            if width < 600:
                scale = 600 / width
                new_size = (int(width * scale), int(height * scale))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            
            text = pytesseract.image_to_string(
                pil_img,
                config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789.,-'
            )
            
            return self._parse_numbers(text)
            
        except Exception:
            return []
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Aumenta contraste"""
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Contrast(pil_img)
        enhanced = enhancer.enhance(2.5)
        return cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
    
    def _parse_numbers(self, text: str) -> List[float]:
        """Extrai números do texto"""
        patterns = [
            r'\b(19\d{2}|20\d{2})\b',
            r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\b',
            r'-?\d+[.,]\d+',
            r'-?\d+',
        ]
        
        numbers = []
        text_clean = text.replace(' ', '').replace('\n', ' ')
        
        for pattern in patterns:
            matches = re.findall(pattern, text_clean)
            for match in matches:
                try:
                    num_str = match.replace(',', '.')
                    parts = num_str.split('.')
                    if len(parts) > 2:
                        num_str = ''.join(parts[:-1]) + '.' + parts[-1]
                    elif len(parts) == 2 and len(parts[1]) == 3 and '.' not in match:
                        num_str = parts[0] + parts[1]
                    
                    num = float(num_str)
                    
                    if -10000 < num < 100000:
                        numbers.append(num)
                        
                except (ValueError, IndexError):
                    continue
        
        return numbers
    
    def _remove_outliers(self, numbers: List[float]) -> List[float]:
        """Remove outliers com IQR"""
        if len(numbers) < 4:
            return numbers
        
        q1 = np.percentile(numbers, 25)
        q3 = np.percentile(numbers, 75)
        iqr = q3 - q1
        
        lower = q1 - 3 * iqr
        upper = q3 + 3 * iqr
        
        filtered = [n for n in numbers if lower <= n <= upper]
        
        return filtered if filtered else numbers
