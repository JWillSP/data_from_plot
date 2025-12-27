"""
Módulo de detecção de marcadores - V3 HÍBRIDO
Combina:
- Detecção HSV robusta da versão antiga
- Grid de 10.000 células para curvas contínuas
- Separação clara entre marcadores e curvas
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict
from collections import defaultdict, Counter
try:
    from .data_types import Point, GraphFrame, AxisCalibration
except ImportError:
    from data_types import Point, GraphFrame, AxisCalibration


class MarkerDetectorV3:
    """Detector híbrido: HSV para marcadores + Grid para curvas"""
    
    def __init__(self, img: np.ndarray, frame: GraphFrame):
        self.img = img
        self.frame = frame
        self.gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
    def detect_all(self, x_calib: AxisCalibration, y_calib: AxisCalibration):
        """Pipeline híbrido: marcadores destacados + grid para curvas"""
        x1, y1 = self.frame.top_left
        x2, y2 = self.frame.bottom_right
        
        if x2 <= x1 or y2 <= y1:
            return {}
        
        roi = self.img[y1:y2, x1:x2].copy()
        
        if roi.size == 0:
            return {}
        
        # ETAPA 1: Detectar marcadores GRANDES (círculos/quadrados) via HSV
        print("  Camada 1: Detectando marcadores destacados (HSV)...")
        markers = self._detect_highlighted_markers_hsv(roi, x1, y1)
        print(f"    ✓ {len(markers)} marcadores destacados")
        
        # ETAPA 2: Detectar curvas FINAS via Grid 100x100 = 10.000 células
        print("  Camada 2: Detectando curvas via grid 100x100...")
        curves = self._detect_curves_with_grid(roi, x1, y1, grid_size=100)
        print(f"    ✓ {len(curves)} pontos em curvas")
        
        # ETAPA 3: Separar por cor E tipo (não misturar marcadores com curvas)
        all_points = markers + curves
        data_points = self._group_by_color_and_type(all_points, x_calib, y_calib)
        
        total = sum(len(pts) for pts in data_points.values())
        print(f"  🎯 Total: {total} pontos em {len(data_points)} séries")
        
        return data_points
    
    def _detect_highlighted_markers_hsv(self, roi, offset_x, offset_y) -> List[Point]:
        """
        Detecta marcadores DESTACADOS (círculos, quadrados) usando HSV + contornos
        Baseado na versão antiga que funcionava bem
        """
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Ranges de cor em HSV (versão antiga)
        color_ranges = {
            'blue': ([100, 50, 50], [130, 255, 255]),
            'red1': ([0, 50, 50], [10, 255, 255]),      # Vermelho parte 1
            'red2': ([170, 50, 50], [180, 255, 255]),   # Vermelho parte 2
            'green': ([40, 50, 50], [80, 255, 255]),
            'orange': ([10, 100, 100], [25, 255, 255]),  # Laranja
            'black': ([0, 0, 0], [180, 255, 50])
        }
        
        detected = []
        
        for color_name, (lower, upper) in color_ranges.items():
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            
            # Encontrar contornos
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Área entre 10 e 1000 pixels (marcadores grandes)
                if 10 < area < 1000:
                    M = cv2.moments(contour)
                    if M['m00'] > 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        
                        # Verificar se está dentro do ROI
                        if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                            b, g, r = roi[cy, cx]
                            
                            # Criar ponto
                            detected.append(Point(
                                x=offset_x + cx,
                                y=offset_y + cy,
                                color=(int(r), int(g), int(b)),
                                marker_type='marker'  # Marcador destacado
                            ))
        
        return detected
    
    def _detect_curves_with_grid(self, roi, offset_x, offset_y, grid_size=100) -> List[Point]:
        """
        Grid de 100x100 = 10.000 células detectoras
        Detecta curvas FINAS escaneando cada célula
        """
        h, w = roi.shape[:2]
        cell_h = h / grid_size
        cell_w = w / grid_size
        
        # Criar máscara de bordas para curvas finas
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_roi, 30, 100)
        
        # Dilatar levemente para conectar linhas finas
        kernel = np.ones((2, 2), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        detected_curve_points = []
        
        # Escanear grid 100x100
        for i in range(grid_size):
            for j in range(grid_size):
                # Coordenadas da célula
                y_start = int(i * cell_h)
                y_end = int((i + 1) * cell_h)
                x_start = int(j * cell_w)
                x_end = int((j + 1) * cell_w)
                
                # ROI da célula
                cell = edges[y_start:y_end, x_start:x_end]
                
                # Se há pixels de borda na célula
                if np.any(cell > 0):
                    # Centro da célula
                    cy = (y_start + y_end) // 2
                    cx = (x_start + x_end) // 2
                    
                    if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                        b, g, r = roi[cy, cx]
                        
                        # Filtrar branco/cinza claro
                        if not self._is_neutral_color((int(r), int(g), int(b))):
                            detected_curve_points.append(Point(
                                x=offset_x + cx,
                                y=offset_y + cy,
                                color=(int(r), int(g), int(b)),
                                marker_type='curve'  # Ponto de curva
                            ))
        
        return detected_curve_points
    
    def _is_neutral_color(self, rgb: Tuple[int, int, int]) -> bool:
        """Filtra cores neutras (branco/cinza)"""
        r, g, b = rgb
        
        # Branco
        if r > 240 and g > 240 and b > 240:
            return True
        
        # Cinza (baixa saturação)
        avg = (r + g + b) / 3
        if avg > 200 and max(abs(r - avg), abs(g - avg), abs(b - avg)) < 15:
            return True
        
        return False
    
    def _group_by_color_and_type(self, points: List[Point], 
                                   x_calib: AxisCalibration, 
                                   y_calib: AxisCalibration) -> Dict:
        """
        Agrupa pontos por COR + TIPO
        Marcadores e curvas da mesma cor ficam em séries SEPARADAS
        """
        data_points = defaultdict(list)
        
        for point in points:
            # Classificar cor
            color_name = self._classify_color(point.color)
            
            # Chave: cor + tipo (separar marcadores de curvas)
            if point.marker_type == 'marker':
                series_key = f"{color_name}_points"
            else:  # curve
                series_key = f"{color_name}_line"
            
            # Normalizar coordenadas (0-1)
            norm_x = (point.x - self.frame.bottom_left[0]) / self.frame.width
            norm_y = 1.0 - (point.y - self.frame.top_left[1]) / self.frame.height
            
            # Aplicar calibração
            real_x = self._pixel_to_real_x(norm_x, x_calib)
            real_y = self._pixel_to_real_y(norm_y, y_calib)
            
            data_points[series_key].append({
                'x': real_x,
                'y': real_y,
                'type': point.marker_type
            })
        
        return dict(data_points)
    
    def _classify_color(self, rgb: Tuple[int, int, int]) -> str:
        """Classificação robusta de cores"""
        r, g, b = rgb
        
        # Preto (prioridade)
        if max(r, g, b) < 80:
            return 'Black'
        
        # Calcular saturação
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        saturation = (max_val - min_val) / max_val if max_val > 0 else 0
        
        # Cores saturadas
        if saturation > 0.3:
            if r == max_val:
                # Verificar se é laranja vs vermelho
                if g > 100 and g > b:
                    return 'Orange'
                elif r > 150:
                    return 'Red'
            elif b == max_val and b > 150:
                return 'Blue'
            elif g == max_val and g > 150:
                return 'Green'
        
        # Cinza escuro → Preto
        if max_val < 180 and saturation < 0.2:
            return 'Black'
        
        # Default
        return 'Black'
    
    def _pixel_to_real_x(self, normalized_x: float, calib: AxisCalibration) -> float:
        """Converte X normalizado para valor real (com suporte a zero)"""
        if calib.zero_position is not None:
            if normalized_x < calib.zero_position:
                ratio = normalized_x / calib.zero_position
                return calib.min_value * ratio
            else:
                ratio = (normalized_x - calib.zero_position) / (1.0 - calib.zero_position)
                return calib.max_value * ratio
        else:
            return calib.min_value + normalized_x * (calib.max_value - calib.min_value)
    
    def _pixel_to_real_y(self, normalized_y: float, calib: AxisCalibration) -> float:
        """Converte Y normalizado para valor real"""
        return calib.min_value + normalized_y * (calib.max_value - calib.min_value)
