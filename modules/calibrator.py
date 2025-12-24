"""
Módulo de calibração de eixos usando OCR inteligente
"""
import cv2
import numpy as np
import pytesseract
import re
from typing import List, Tuple, Optional
from PIL import Image, ImageEnhance
from .data_types import GraphFrame, AxisCalibration


class AxisCalibrator:
    """Calibra eixos usando OCR inteligente"""
    
    def __init__(self, img: np.ndarray, frame: GraphFrame):
        self.img = img
        self.frame = frame
        self.h, self.w = img.shape[:2]
    
    def calibrate_x_axis(self) -> AxisCalibration:
        """Calibra eixo horizontal (X) com OCR inteligente"""
        try:
            # Região MUITO expandida para capturar todos os rótulos
            x1, y1 = self.frame.bottom_left
            x2, y2 = self.frame.bottom_right
            
            # Pegar região abaixo E acima do eixo
            margin = 250
            roi_below = self.img[
                max(0, y2 - 50):min(y2 + margin, self.h),
                max(0, x1 - 100):min(x2 + 100, self.w)
            ]
            
            # Preprocessar para melhor OCR
            numbers = self._extract_numbers_smart(roi_below)
            
            if len(numbers) >= 2:
                min_val = min(numbers)
                max_val = max(numbers)
                
                # Verificar se é simétrico
                has_negative = any(n < 0 for n in numbers)
                has_positive = any(n > 0 for n in numbers)
                is_symmetric = has_negative and has_positive
                
                zero_pos = None
                if 0 in numbers or is_symmetric:
                    if min_val < 0 < max_val:
                        zero_pos = abs(min_val) / (max_val - min_val)
                    elif is_symmetric:
                        zero_pos = 0.5
                
                print(f"  ✓ Eixo X detectado: {numbers}")
                return AxisCalibration(min_val, max_val, zero_pos, '', is_symmetric)
            
        except Exception as e:
            print(f"  ⚠️ Erro OCR eixo X: {e}")
        
        print("  ⚠️ OCR do eixo X falhou, usando valores padrão")
        return AxisCalibration(0.0, 1.0)
    
    def calibrate_y_axis(self) -> AxisCalibration:
        """Calibra eixo vertical (Y) com OCR inteligente"""
        try:
            x1, y1 = self.frame.top_left
            _, y2 = self.frame.bottom_left
            
            # Região MUITO expandida à esquerda
            margin = 300
            roi_left = self.img[
                max(0, y1 - 100):min(y2 + 100, self.h),
                max(0, x1 - margin):x1 + 50
            ]
            
            # Preprocessar para melhor OCR
            numbers = self._extract_numbers_smart(roi_left)
            
            if len(numbers) >= 2:
                min_val = min(numbers)
                max_val = max(numbers)
                
                print(f"  ✓ Eixo Y detectado: {numbers}")
                return AxisCalibration(min_val, max_val)
            
        except Exception as e:
            print(f"  ⚠️ Erro OCR eixo Y: {e}")
        
        print("  ⚠️ OCR do eixo Y falhou, usando valores padrão")
        return AxisCalibration(0.0, 1.0)
    
    def _extract_numbers_smart(self, roi: np.ndarray) -> List[float]:
        """Extrai números com preprocessamento inteligente"""
        if roi.size == 0 or roi.shape[0] < 10 or roi.shape[1] < 10:
            return []
        
        numbers_all = []
        
        # Estratégia 1: OCR direto
        numbers_all.extend(self._ocr_image(roi))
        
        # Estratégia 2: Binarização adaptativa
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        numbers_all.extend(self._ocr_image(binary, is_gray=True))
        
        # Estratégia 3: Inversão de cores
        inverted = cv2.bitwise_not(gray)
        numbers_all.extend(self._ocr_image(inverted, is_gray=True))
        
        # Estratégia 4: Aumento de contraste
        enhanced = self._enhance_contrast(roi)
        numbers_all.extend(self._ocr_image(enhanced))
        
        # Limpar e retornar números únicos
        unique_numbers = sorted(set(numbers_all))
        
        # Filtrar outliers (valores muito discrepantes)
        if len(unique_numbers) > 3:
            unique_numbers = self._remove_outliers(unique_numbers)
        
        return unique_numbers
    
    def _ocr_image(self, img, is_gray=False) -> List[float]:
        """Executa OCR em uma imagem"""
        try:
            if is_gray:
                if len(img.shape) == 2:
                    pil_img = Image.fromarray(img)
                else:
                    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            else:
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            # Aumentar tamanho para melhor OCR
            width, height = pil_img.size
            if width < 500:
                scale = 500 / width
                new_size = (int(width * scale), int(height * scale))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            
            # OCR com configuração otimizada
            text = pytesseract.image_to_string(
                pil_img, 
                config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789.,-'
            )
            
            return self._parse_numbers(text)
            
        except Exception:
            return []
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Aumenta contraste da imagem"""
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Contrast(pil_img)
        enhanced = enhancer.enhance(2.5)
        return cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
    
    def _parse_numbers(self, text: str) -> List[float]:
        """Extrai números de texto com padrões avançados"""
        patterns = [
            r'\b(19\d{2}|20\d{2})\b',              # Anos: 1900-2099
            r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\b',  # Números com separadores
            r'-?\d+[.,]\d+',                        # Decimais
            r'-?\d+',                               # Inteiros
        ]
        
        numbers = []
        text_clean = text.replace(' ', '').replace('\n', ' ')
        
        for pattern in patterns:
            matches = re.findall(pattern, text_clean)
            for match in matches:
                try:
                    # Normalizar separadores (vírgula -> ponto)
                    num_str = match.replace(',', '.')
                    # Remover pontos de milhar (ex: 1.000 -> 1000)
                    parts = num_str.split('.')
                    if len(parts) > 2:
                        # Tem pontos de milhar
                        num_str = ''.join(parts[:-1]) + '.' + parts[-1]
                    elif len(parts) == 2 and len(parts[1]) == 3 and '.' not in match:
                        # 1.000 é milhar, não decimal
                        num_str = parts[0] + parts[1]
                    
                    num = float(num_str)
                    
                    # Validar range razoável
                    if -10000 < num < 100000:
                        numbers.append(num)
                        
                except (ValueError, IndexError):
                    continue
        
        return numbers
    
    def _remove_outliers(self, numbers: List[float]) -> List[float]:
        """Remove outliers usando IQR"""
        if len(numbers) < 4:
            return numbers
        
        q1 = np.percentile(numbers, 25)
        q3 = np.percentile(numbers, 75)
        iqr = q3 - q1
        
        lower = q1 - 3 * iqr
        upper = q3 + 3 * iqr
        
        filtered = [n for n in numbers if lower <= n <= upper]
        
        return filtered if filtered else numbers
