"""
Módulo de calibração V3 - HÍBRIDO
Combina:
- Multi-threshold OCR da versão nova
- Simplicidade e ROIs da versão antiga
- Filtros inteligentes de números
"""
import cv2
import numpy as np
import pytesseract
import re
from typing import List
from PIL import Image, ImageEnhance
try:
    from .data_types import GraphFrame, AxisCalibration
except ImportError:
    from data_types import GraphFrame, AxisCalibration


class AxisCalibratorV3:
    """Calibrador híbrido com OCR robusto"""
    
    def __init__(self, img: np.ndarray, frame: GraphFrame):
        self.img = img
        self.frame = frame
        self.h, self.w = img.shape[:2]
    
    def calibrate_x_axis(self) -> AxisCalibration:
        """Calibra eixo X com OCR multi-estratégia"""
        try:
            x1, y1 = self.frame.bottom_left
            x2, y2 = self.frame.bottom_right
            
            # ROI: ABAIXO do eixo X (onde ficam os rótulos)
            margin_v = 150  # Altura da faixa
            margin_h = 30   # Margem lateral
            
            roi = self.img[
                y2:min(y2 + margin_v, self.h),
                max(0, x1 - margin_h):min(x2 + margin_h, self.w)
            ]
            
            if roi.size == 0 or roi.shape[0] < 10 or roi.shape[1] < 10:
                raise ValueError("ROI X muito pequena")
            
            # Extrair números com múltiplas estratégias
            numbers = self._extract_numbers_robust(roi)
            
            if len(numbers) >= 2:
                min_val = min(numbers)
                max_val = max(numbers)
                
                # Detectar se há valores negativos (eixo simétrico)
                has_negative = any(n < 0 for n in numbers)
                has_positive = any(n > 0 for n in numbers)
                is_symmetric = has_negative and has_positive
                
                zero_pos = None
                if 0 in numbers or is_symmetric:
                    if min_val < 0 < max_val:
                        # Zero proporcional
                        zero_pos = abs(min_val) / (max_val - min_val)
                    elif is_symmetric:
                        zero_pos = 0.5  # Centro
                
                print(f"  ✓ Eixo X: {numbers} → [{min_val}, {max_val}]")
                return AxisCalibration(min_val, max_val, zero_pos, '', is_symmetric)
            
        except Exception as e:
            print(f"  ⚠️ Erro OCR X: {e}")
        
        print("  ⚠️ OCR X falhou, usando [0, 1]")
        return AxisCalibration(0.0, 1.0)
    
    def calibrate_y_axis(self) -> AxisCalibration:
        """Calibra eixo Y com OCR multi-estratégia"""
        try:
            x1, y1 = self.frame.top_left
            _, y2 = self.frame.bottom_left
            
            # ROI: À ESQUERDA do eixo Y
            margin_h = 200  # Largura da faixa
            margin_v = 20   # Margem vertical
            
            roi = self.img[
                max(0, y1 - margin_v):min(y2 + margin_v, self.h),
                max(0, x1 - margin_h):x1
            ]
            
            if roi.size == 0 or roi.shape[0] < 10 or roi.shape[1] < 10:
                raise ValueError("ROI Y muito pequena")
            
            numbers = self._extract_numbers_robust(roi)
            
            # Filtrar valores razoáveis para Y (tipicamente 0-120%)
            numbers = [n for n in numbers if -10 <= n <= 150]
            
            if len(numbers) >= 2:
                min_val = min(numbers)
                max_val = max(numbers)
                
                print(f"  ✓ Eixo Y: {numbers} → [{min_val}, {max_val}]")
                return AxisCalibration(min_val, max_val)
            
        except Exception as e:
            print(f"  ⚠️ Erro OCR Y: {e}")
        
        print("  ⚠️ OCR Y falhou, usando [0, 1]")
        return AxisCalibration(0.0, 1.0)
    
    def _extract_numbers_robust(self, roi: np.ndarray) -> List[float]:
        """
        Extração de números com múltiplas estratégias
        (mas mais simples que a V2 para evitar over-engineering)
        """
        if roi.size == 0 or roi.shape[0] < 10 or roi.shape[1] < 10:
            return []
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        all_numbers = []
        
        # Estratégia 1: Tesseract direto em escala de cinza
        nums1 = self._ocr_tesseract(gray)
        all_numbers.extend(nums1)
        
        # Estratégia 2: Threshold binário (branco em preto)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        nums2 = self._ocr_tesseract(binary)
        all_numbers.extend(nums2)
        
        # Estratégia 3: Threshold binário invertido (preto em branco)
        _, binary_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        nums3 = self._ocr_tesseract(binary_inv)
        all_numbers.extend(nums3)
        
        # Estratégia 4: Adaptativo Gaussiano
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        nums4 = self._ocr_tesseract(adaptive)
        all_numbers.extend(nums4)
        
        # Estratégia 5: Contraste aumentado
        enhanced = self._enhance_contrast(roi)
        nums5 = self._ocr_tesseract(enhanced)
        all_numbers.extend(nums5)
        
        # Remover duplicatas e ordenar
        unique = sorted(set(all_numbers))
        
        # Remover outliers se houver muitos valores
        if len(unique) > 4:
            unique = self._remove_outliers_iqr(unique)
        
        return unique
    
    def _ocr_tesseract(self, img) -> List[float]:
        """Executa Tesseract OCR em uma imagem"""
        try:
            # Converter para PIL
            if len(img.shape) == 2:
                pil_img = Image.fromarray(img)
            else:
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            # Resize para melhorar OCR
            w, h = pil_img.size
            if w < 600:
                scale = 600 / w
                pil_img = pil_img.resize(
                    (int(w * scale), int(h * scale)),
                    Image.Resampling.LANCZOS
                )
            
            # OCR com whitelist de caracteres numéricos
            text = pytesseract.image_to_string(
                pil_img,
                config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789.,-'
            )
            
            return self._parse_numbers(text)
            
        except Exception:
            return []
    
    def _parse_numbers(self, text: str) -> List[float]:
        """Extrai números do texto OCR"""
        # Padrões de números (do mais específico ao mais geral)
        patterns = [
            r'\b(19\d{2}|20\d{2})\b',  # Anos (ex: 2024)
            r'-?\d+[.,]\d+',             # Decimais
            r'-?\d+',                    # Inteiros
        ]
        
        numbers = []
        text_clean = text.replace(' ', '').replace('\n', ' ')
        
        for pattern in patterns:
            matches = re.findall(pattern, text_clean)
            for match in matches:
                try:
                    # Normalizar vírgula/ponto
                    num_str = match.replace(',', '.')
                    num = float(num_str)
                    
                    # Filtro básico: valores razoáveis
                    if -10000 < num < 100000:
                        numbers.append(num)
                        
                except (ValueError, IndexError):
                    continue
        
        return numbers
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Aumenta contraste da imagem"""
        if len(img.shape) == 2:
            # Já é escala de cinza
            pil_img = Image.fromarray(img)
        else:
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        enhancer = ImageEnhance.Contrast(pil_img)
        enhanced = enhancer.enhance(2.5)
        
        if len(img.shape) == 2:
            return np.array(enhanced)
        else:
            return cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
    
    def _remove_outliers_iqr(self, numbers: List[float]) -> List[float]:
        """Remove outliers usando método IQR"""
        if len(numbers) < 4:
            return numbers
        
        q1 = np.percentile(numbers, 25)
        q3 = np.percentile(numbers, 75)
        iqr = q3 - q1
        
        # Limites mais generosos (3x IQR)
        lower = q1 - 3 * iqr
        upper = q3 + 3 * iqr
        
        filtered = [n for n in numbers if lower <= n <= upper]
        
        return filtered if filtered else numbers
