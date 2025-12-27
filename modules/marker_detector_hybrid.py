"""
Detector Híbrido ULTIMATE
Combina:
1. Detecção de marcadores grandes por cor/contorno (versão antiga)
2. Grid de 10.000 células para curvas finas (novo)
3. Separação inteligente entre marcadores e curvas
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass


@dataclass
class Point:
    x: float
    y: float
    color: Tuple[int, int, int]
    marker_type: str = 'point'


class MarkerDetectorHybrid:
    """Detector híbrido: marcadores grandes + grid para curvas"""
    
    def __init__(self, img: np.ndarray, frame):
        self.img = img
        self.frame = frame
        self.gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    def detect_all(self, x_calib, y_calib, grid_size: int = 100):
        """
        Pipeline em 3 camadas:
        1. Marcadores grandes (círculos/quadrados destacados)
        2. Grid para curvas finas contínuas
        3. Agrupamento por cor + tipo
        """
        
        x1, y1 = self.frame.top_left
        x2, y2 = self.frame.bottom_right
        
        if x2 <= x1 or y2 <= y1:
            return {}
        
        roi = self.img[y1:y2, x1:x2].copy()
        roi_gray = self.gray[y1:y2, x1:x2]
        
        if roi.size == 0:
            return {}
        
        all_candidates = []
        
        # CAMADA 1: Marcadores grandes (círculos/quadrados)
        print("    🎯 Camada 1: Detectando marcadores grandes...")
        large_markers = self._detect_large_markers(roi, roi_gray, x1, y1)
        all_candidates.extend(large_markers)
        print(f"       Encontrados: {len(large_markers)} marcadores")
        
        # CAMADA 2: Grid para curvas finas
        print(f"    📊 Camada 2: Escaneando grid {grid_size}x{grid_size}...")
        grid_points = self._detect_curves_grid(roi, x1, y1, grid_size)
        all_candidates.extend(grid_points)
        print(f"       Encontrados: {len(grid_points)} pontos de curva")
        
        # CAMADA 3: Deduplicação e separação
        print("    🔧 Camada 3: Separando marcadores de curvas...")
        separated = self._separate_markers_and_curves(all_candidates)
        
        # Agrupar por cor
        data_points = self._group_by_color(separated, x_calib, y_calib)
        
        total = sum(len(pts) for pts in data_points.values())
        print(f"    ✅ Total: {total} pontos em {len(data_points)} séries")
        
        return data_points
    
    def _detect_large_markers(self, roi, roi_gray, offset_x, offset_y) -> List[Point]:
        """Detecta marcadores grandes usando DUAS estratégias"""
        
        markers = []
        
        # ESTRATÉGIA 1: HoughCircles (círculos grandes)
        circles = cv2.HoughCircles(
            roi_gray, cv2.HOUGH_GRADIENT,
            dp=1, minDist=10,
            param1=50, param2=25,
            minRadius=5, maxRadius=30
        )
        
        if circles is not None:
            circles = np.uint16(np.around(circles))[0]
            
            for cx, cy, r in circles:
                # Verificar se é realmente um marcador (não branco)
                if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                    # ROI inscrito
                    inner = int(r * 0.6)
                    x1_i = max(0, cx - inner)
                    y1_i = max(0, cy - inner)
                    x2_i = min(roi_gray.shape[1], cx + inner)
                    y2_i = min(roi_gray.shape[0], cy + inner)
                    
                    region = roi_gray[y1_i:y2_i, x1_i:x2_i]
                    
                    if region.size > 0:
                        darkness = np.percentile(region, 30)
                        
                        # Só aceita se suficientemente escuro (não branco)
                        if darkness < 200:
                            b, g, r_val = roi[cy, cx]
                            
                            if not self._is_white_or_gray((int(r_val), int(g), int(b))):
                                markers.append(Point(
                                    x=offset_x + cx,
                                    y=offset_y + cy,
                                    color=(int(r_val), int(g), int(b)),
                                    marker_type='circle'
                                ))
        
        # ESTRATÉGIA 2: Contornos (quadrados/triângulos)
        thresholds = [30, 50, 70, 90, 110, 130]
        
        for thresh in thresholds:
            _, binary = cv2.threshold(roi_gray, thresh, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                
                # Marcadores têm área entre 20 e 1500 pixels
                if 20 < area < 1500:
                    M = cv2.moments(cnt)
                    if M['m00'] > 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        
                        if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                            b, g, r_val = roi[cy, cx]
                            
                            if not self._is_white_or_gray((int(r_val), int(g), int(b))):
                                # Identificar forma
                                shape_type = self._identify_shape(cnt)
                                
                                markers.append(Point(
                                    x=offset_x + cx,
                                    y=offset_y + cy,
                                    color=(int(r_val), int(g), int(b)),
                                    marker_type=shape_type
                                ))
        
        # ESTRATÉGIA 3: HSV para cores específicas (da versão antiga)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        color_ranges = {
            'blue': ([100, 50, 50], [130, 255, 255]),
            'red1': ([0, 50, 50], [10, 255, 255]),
            'red2': ([170, 50, 50], [180, 255, 255]),
            'green': ([40, 50, 50], [80, 255, 255]),
            'orange': ([10, 100, 100], [25, 255, 255]),
            'yellow': ([25, 100, 100], [35, 255, 255]),
        }
        
        for color_name, (lower, upper) in color_ranges.items():
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                
                if 15 < area < 1000:
                    M = cv2.moments(cnt)
                    if M['m00'] > 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        
                        if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                            b, g, r_val = roi[cy, cx]
                            
                            markers.append(Point(
                                x=offset_x + cx,
                                y=offset_y + cy,
                                color=(int(r_val), int(g), int(b)),
                                marker_type='point'
                            ))
        
        return markers
    
    def _detect_curves_grid(self, roi, offset_x, offset_y, grid_size: int) -> List[Point]:
        """
        Grid de NxN células para detectar curvas finas
        Cada célula vota no pixel mais colorido (não branco)
        """
        
        h, w = roi.shape[:2]
        cell_h = h / grid_size
        cell_w = w / grid_size
        
        curve_points = []
        
        for row in range(grid_size):
            for col in range(grid_size):
                # Coordenadas da célula
                y1 = int(row * cell_h)
                y2 = int((row + 1) * cell_h)
                x1 = int(col * cell_w)
                x2 = int((col + 1) * cell_w)
                
                # Extrair célula
                cell = roi[y1:y2, x1:x2]
                
                if cell.size == 0:
                    continue
                
                # Encontrar pixel mais "colorido" (não branco/cinza)
                best_pixel = self._find_most_colorful_pixel(cell)
                
                if best_pixel is not None:
                    rel_y, rel_x, color = best_pixel
                    
                    # Coordenadas absolutas
                    abs_x = offset_x + x1 + rel_x
                    abs_y = offset_y + y1 + rel_y
                    
                    curve_points.append(Point(
                        x=abs_x,
                        y=abs_y,
                        color=color,
                        marker_type='curve'
                    ))
        
        return curve_points
    
    def _find_most_colorful_pixel(self, cell: np.ndarray) -> Tuple[int, int, Tuple]:
        """Encontra o pixel mais colorido (menos branco) em uma célula"""
        
        if cell.size == 0:
            return None
        
        # Converter para LAB para medir saturação
        cell_lab = cv2.cvtColor(cell, cv2.COLOR_BGR2LAB)
        
        # Canal L (luminosidade): queremos médio (não muito claro)
        # Canais A e B (cromaticidade): queremos alto
        
        best_score = -1
        best_pos = None
        best_color = None
        
        for y in range(cell.shape[0]):
            for x in range(cell.shape[1]):
                b, g, r = cell[y, x]
                
                # Filtrar branco/cinza
                if self._is_white_or_gray((int(r), int(g), int(b))):
                    continue
                
                # Score: quanto mais saturado, melhor
                L, A, B = cell_lab[y, x]
                
                # Saturação = distância de A e B do centro (128)
                saturation = np.sqrt((A - 128)**2 + (B - 128)**2)
                
                # Penalizar muito claro ou muito escuro
                lightness_penalty = abs(L - 128) / 128
                
                score = saturation * (1 - 0.5 * lightness_penalty)
                
                if score > best_score:
                    best_score = score
                    best_pos = (y, x)
                    best_color = (int(r), int(g), int(b))
        
        # Só retorna se encontrou algo razoavelmente colorido
        if best_score > 10:  # threshold mínimo de saturação
            return (best_pos[0], best_pos[1], best_color)
        
        return None
    
    def _separate_markers_and_curves(self, candidates: List[Point]) -> List[Point]:
        """
        Separa marcadores destacados de pontos de curva
        Critério: se tem muitos pontos próximos, é marcador grande
        """
        
        if len(candidates) == 0:
            return []
        
        # Separar por tipo inicial
        markers = [p for p in candidates if p.marker_type != 'curve']
        curves = [p for p in candidates if p.marker_type == 'curve']
        
        # Deduplicar marcadores (DBSCAN)
        if len(markers) > 0:
            from sklearn.cluster import DBSCAN
            
            coords = np.array([[p.x, p.y] for p in markers])
            clustering = DBSCAN(eps=8, min_samples=1).fit(coords)
            labels = clustering.labels_
            
            deduplicated_markers = []
            for label in set(labels):
                cluster = [markers[i] for i in range(len(markers)) if labels[i] == label]
                
                if len(cluster) == 1:
                    deduplicated_markers.append(cluster[0])
                else:
                    # Votação no centróide
                    cx = int(np.mean([p.x for p in cluster]))
                    cy = int(np.mean([p.y for p in cluster]))
                    
                    colors = [p.color for p in cluster]
                    color = Counter(colors).most_common(1)[0][0]
                    
                    types = [p.marker_type for p in cluster]
                    marker_type = Counter(types).most_common(1)[0][0]
                    
                    deduplicated_markers.append(Point(cx, cy, color, marker_type))
            
            markers = deduplicated_markers
        
        # Curvas: amostragem regular (não deduplicar demais)
        # Já vêm espaçadas do grid
        
        return markers + curves
    
    def _identify_shape(self, contour) -> str:
        """Identifica forma geométrica do contorno"""
        approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True)
        vertices = len(approx)
        
        if vertices == 3:
            return 'triangle'
        elif vertices == 4:
            # Verificar se é quadrado ou losango
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 1
            
            if 0.9 <= aspect_ratio <= 1.1:
                return 'square'
            else:
                return 'rectangle'
        elif vertices > 6:
            return 'circle'
        else:
            return 'polygon'
    
    def _is_white_or_gray(self, rgb: Tuple[int, int, int]) -> bool:
        """Verifica se é branco ou cinza"""
        r, g, b = rgb
        
        # Branco
        if r > 230 and g > 230 and b > 230:
            return True
        
        # Cinza (baixa saturação)
        avg = (r + g + b) / 3
        if avg > 180 and max(abs(r - avg), abs(g - avg), abs(b - avg)) < 20:
            return True
        
        return False
    
    def _group_by_color(self, markers: List[Point], x_calib, y_calib) -> Dict:
        """Agrupa por COR + TIPO (marcadores vs curvas)"""
        data_points = defaultdict(list)
        
        for marker in markers:
            color_key = self._get_color_key(marker.color)
            
            # Chave: cor + tipo
            if marker.marker_type == 'curve':
                series_key = f"{color_key}_line"
            else:
                series_key = f"{color_key}_points"
            
            # Normalizar coordenadas
            graph_x = (marker.x - self.frame.bottom_left[0]) / self.frame.width
            graph_y = 1.0 - (marker.y - self.frame.top_left[1]) / self.frame.height
            
            # Calibrar
            real_x = self._pixel_to_real_x(graph_x, x_calib)
            real_y = self._pixel_to_real_y(graph_y, y_calib)
            
            data_points[series_key].append({
                'x': real_x,
                'y': real_y,
                'type': marker.marker_type
            })
        
        return dict(data_points)
    
    def _pixel_to_real_x(self, normalized_x: float, calib) -> float:
        """Converte X normalizado para valor real"""
        if calib.zero_position is not None:
            # Eixo com zero (simétrico)
            if normalized_x < calib.zero_position:
                ratio = normalized_x / calib.zero_position
                return calib.min_value * ratio
            else:
                ratio = (normalized_x - calib.zero_position) / (1.0 - calib.zero_position)
                return calib.max_value * ratio
        else:
            # Eixo normal
            return calib.min_value + normalized_x * (calib.max_value - calib.min_value)
    
    def _pixel_to_real_y(self, normalized_y: float, calib) -> float:
        """Converte Y normalizado para valor real"""
        return calib.min_value + normalized_y * (calib.max_value - calib.min_value)
    
    def _get_color_key(self, rgb: Tuple[int, int, int]) -> str:
        """Classificação robusta de cor"""
        r, g, b = rgb
        
        # Preto (máxima prioridade)
        if max(r, g, b) < 80:
            return 'Black'
        
        # Calcular saturação
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        saturation = (max_val - min_val) / max_val if max_val > 0 else 0
        
        # Cores saturadas
        if saturation > 0.3:
            if r == max_val and r > 130:
                # Verificar se é laranja
                if g > 100 and b < 100:
                    return 'Orange'
                return 'Red'
            elif b == max_val and b > 130:
                return 'Blue'
            elif g == max_val and g > 130:
                # Verificar se é amarelo
                if r > 100 and b < 100:
                    return 'Yellow'
                return 'Green'
        
        # Cinza escuro -> preto
        if 80 <= max(r, g, b) <= 150 and saturation < 0.2:
            return 'Black'
        
        # Default: cor dominante ou preto
        if r > max(g, b):
            return 'Red'
        elif b > max(r, g):
            return 'Blue'
        elif g > max(r, b):
            return 'Green'
        
        return 'Black'
