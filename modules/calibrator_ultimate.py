"""
Calibrador de Eixos ULTIMATE - OCR Multi-estratégia
Combina OCR robusto + fallback inteligente
"""
import cv2
import numpy as np
import pytesseract
import re
from typing import List, Optional
from PIL import Image, ImageEnhance
from dataclasses import dataclass


@dataclass
class AxisCalibration:
    min_value: float
    max_value: float
    zero_position: Optional[float] = None
    unit: str = ''
    is_symmetric: bool = False


class AxisCalibratorUltimate:
    """Calibrador com múltiplas estratégias de OCR"""
    
    def __init__(self, img: np.ndarray, frame):
        self.img = img
        self.frame = frame
        self.h, self.w = img.shape[:2]
    
    def calibrate_x_axis(self) -> AxisCalibration:
        """Calibra eixo X com múltiplas estratégias"""
        print("  🔍 Calibrando eixo X...")
        
        # ROI abaixo do frame
        x1, y1 = self.frame.bottom_left
        x2, y2 = self.frame.bottom_right
        
        # Região ABAIXO + margens laterais
        margin_v = min(250, self.h - y2)
        margin_h = 80
        
        roi = self.img[
            y2:min(y2 + margin_v, self.h),
            max(0, x1 - margin_h):min(x2 + margin_h, self.w)
        ]
        
        if roi.size == 0:
            print("    ⚠️  ROI vazia, usando [0, 1]")
            return AxisCalibration(0.0, 1.0)
        
        # Tentar extrair números
        numbers = self._extract_numbers_ultimate(roi, axis='x')
        
        if len(numbers) >= 2:
            numbers = sorted(set(numbers))
            min_val = min(numbers)
            max_val = max(numbers)
            
            # Detectar simetria
            has_negative = any(n < 0 for n in numbers)
            has_positive = any(n > 0 for n in numbers)
            is_symmetric = has_negative and has_positive
            
            zero_pos = None
            if 0 in numbers or is_symmetric:
                if min_val < 0 < max_val:
                    zero_pos = abs(min_val) / (max_val - min_val)
                elif is_symmetric:
                    zero_pos = 0.5
            
            print(f"    ✅ X: {numbers} → [{min_val}, {max_val}]")
            if zero_pos:
                print(f"       Zero em: {zero_pos:.1%}")
            
            return AxisCalibration(min_val, max_val, zero_pos, '', is_symmetric)
        
        print("    ⚠️  OCR falhou, usando [0, 1]")
        return AxisCalibration(0.0, 1.0)
    
    def calibrate_y_axis(self) -> AxisCalibration:
        """Calibra eixo Y com múltiplas estratégias"""
        print("  🔍 Calibrando eixo Y...")
        
        # ROI à ESQUERDA do frame
        x1, y1 = self.frame.top_left
        x2, y2 = self.frame.bottom_left
        
        # Região À ESQUERDA + margens verticais
        margin_h = min(300, x1)
        margin_v = 50
        
        roi = self.img[
            max(0, y1 - margin_v):min(y2 + margin_v, self.h),
            max(0, x1 - margin_h):x1
        ]
        
        if roi.size == 0:
            print("    ⚠️  ROI vazia, usando [0, 1]")
            return AxisCalibration(0.0, 1.0)
        
        # Tentar extrair números
        numbers = self._extract_numbers_ultimate(roi, axis='y')
        
        # Filtrar valores razoáveis para Y (0 a 200 geralmente)
        numbers = [n for n in numbers if 0 <= n <= 200]
        
        if len(numbers) >= 2:
            numbers = sorted(set(numbers))
            min_val = min(numbers)
            max_val = max(numbers)
            
            print(f"    ✅ Y: {numbers} → [{min_val}, {max_val}]")
            return AxisCalibration(min_val, max_val)
        
        print("    ⚠️  OCR falhou, usando [0, 1]")
        return AxisCalibration(0.0, 1.0)
    
    def _extract_numbers_ultimate(self, roi: np.ndarray, axis: str) -> List[float]:
        """Extração ULTIMATE com 5 estratégias diferentes"""
        
        if roi.size == 0 or roi.shape[0] < 10 or roi.shape[1] < 10:
            return []
        
        all_numbers = []
        
        # Converter para grayscale
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi.copy()
        
        # ESTRATÉGIA 1: Múltiplos thresholds fixos
        thresholds = [30, 50, 70, 90, 110, 130, 150, 170, 190, 210]
        
        for thresh in thresholds:
            # Binário normal
            _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
            nums = self._ocr_image(binary, is_gray=True)
            all_numbers.extend(nums)
            
            # Binário invertido
            _, binary_inv = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY_INV)
            nums_inv = self._ocr_image(binary_inv, is_gray=True)
            all_numbers.extend(nums_inv)
        
        # ESTRATÉGIA 2: Threshold adaptativo
        adaptive_mean = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY, 15, 5
        )
        all_numbers.extend(self._ocr_image(adaptive_mean, is_gray=True))
        
        adaptive_gauss = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 15, 5
        )
        all_numbers.extend(self._ocr_image(adaptive_gauss, is_gray=True))
        
        # ESTRATÉGIA 3: OTSU
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        all_numbers.extend(self._ocr_image(otsu, is_gray=True))
        
        # ESTRATÉGIA 4: Contraste aumentado
        enhanced = self._enhance_contrast(roi)
        all_numbers.extend(self._ocr_image(enhanced))
        
        # ESTRATÉGIA 5: Morfologia para limpar ruído
        kernel = np.ones((2, 2), np.uint8)
        morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        _, morph_bin = cv2.threshold(morph, 127, 255, cv2.THRESH_BINARY)
        all_numbers.extend(self._ocr_image(morph_bin, is_gray=True))
        
        # Remover duplicatas e ordenar
        unique = sorted(set(all_numbers))
        
        # Filtrar outliers se tiver muitos números
        if len(unique) > 4:
            unique = self._remove_outliers(unique)
        
        return unique
    
    def _ocr_image(self, img, is_gray=False) -> List[float]:
        """Executa OCR em uma imagem"""
        try:
            # Converter para PIL
            if is_gray:
                if len(img.shape) == 2:
                    pil_img = Image.fromarray(img)
                else:
                    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            else:
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            # Resize para melhorar OCR (pelo menos 800px de largura)
            width, height = pil_img.size
            if width < 800:
                scale = 800 / width
                new_size = (int(width * scale), int(height * scale))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Múltiplos configs de tesseract
            configs = [
                '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789.,-',
                '--psm 11 --oem 3 -c tessedit_char_whitelist=0123456789.,-',
                '--psm 12 --oem 3 -c tessedit_char_whitelist=0123456789.,-',
            ]
            
            numbers = []
            for config in configs:
                try:
                    text = pytesseract.image_to_string(pil_img, config=config)
                    numbers.extend(self._parse_numbers(text))
                except:
                    continue
            
            return numbers
            
        except Exception:
            return []
    
    def _parse_numbers(self, text: str) -> List[float]:
        """Extrai números do texto com regex inteligente"""
        
        # Padrões em ordem de prioridade
        patterns = [
            # Anos (1900-2099)
            r'\b(19\d{2}|20\d{2})\b',
            # Números com separadores de milhar e decimais
            r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\b',
            # Decimais simples
            r'-?\d+[.,]\d+',
            # Inteiros (incluindo negativos)
            r'-?\d+',
        ]
        
        numbers = []
        text_clean = text.replace(' ', '').replace('\n', ' ')
        
        for pattern in patterns:
            matches = re.findall(pattern, text_clean)
            
            for match in matches:
                try:
                    num_str = match.replace(',', '.')
                    
                    # Lidar com separadores de milhar
                    parts = num_str.split('.')
                    
                    if len(parts) > 2:
                        # Múltiplos pontos: assumir que últimos são decimais
                        num_str = ''.join(parts[:-1]) + '.' + parts[-1]
                    elif len(parts) == 2:
                        # Dois pontos: verificar se é separador de milhar ou decimal
                        if len(parts[1]) == 3 and '.' not in match:
                            # Separador de milhar (ex: 1.000)
                            num_str = parts[0] + parts[1]
                    
                    num = float(num_str)
                    
                    # Filtro de valores razoáveis
                    if -10000 < num < 100000:
                        numbers.append(num)
                        
                except (ValueError, IndexError):
                    continue
        
        return numbers
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Aumenta contraste da imagem"""
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        # Contraste
        enhancer = ImageEnhance.Contrast(pil_img)
        enhanced = enhancer.enhance(2.5)
        
        # Brilho
        enhancer = ImageEnhance.Brightness(enhanced)
        enhanced = enhancer.enhance(1.2)
        
        return cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
    
    def _remove_outliers(self, numbers: List[float]) -> List[float]:
        """Remove outliers usando IQR"""
        if len(numbers) < 4:
            return numbers
        
        q1 = np.percentile(numbers, 25)
        q3 = np.percentile(numbers, 75)
        iqr = q3 - q1
        
        # Limites mais permissivos (3x IQR)
        lower = q1 - 3 * iqr
        upper = q3 + 3 * iqr
        
        filtered = [n for n in numbers if lower <= n <= upper]
        
        return filtered if filtered else numbers
