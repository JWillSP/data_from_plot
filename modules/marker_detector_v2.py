"""
Módulo de detecção de marcadores - V2
Arquitetura em camadas com júri de decisão
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict
from collections import defaultdict, Counter
from sklearn.cluster import DBSCAN
from .data_types import Point, GraphFrame, AxisCalibration


class MarkerDetectorV2:
    """Detecta marcadores usando arquitetura hierárquica"""
    
    def __init__(self, img: np.ndarray, frame: GraphFrame):
        self.img = img
        self.frame = frame
        self.gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
    def detect_all(self, x_calib: AxisCalibration, y_calib: AxisCalibration):
        """Pipeline em 3 camadas + júri"""
        x1, y1 = self.frame.top_left
        x2, y2 = self.frame.bottom_right
        
        if x2 <= x1 or y2 <= y1:
            return {}
        
        roi = self.img[y1:y2, x1:x2].copy()
        roi_gray = self.gray[y1:y2, x1:x2]
        
        if roi.size == 0:
            return {}
        
        all_candidates = []
        
        # Camada 1: Círculos grandes (maior prioridade)
        circles = self._detect_large_circles(roi, roi_gray, x1, y1)
        all_candidates.extend(circles)
        print(f"  ✓ Camada 1 (círculos): {len(circles)}")
        
        # Camada 2: Formas definidas (média prioridade)
        shapes = self._detect_defined_shapes(roi, roi_gray, x1, y1)
        all_candidates.extend(shapes)
        print(f"  ✓ Camada 2 (formas): {len(shapes)}")
        
        # Camada 3: Curvas finas (SEMPRE ativa para linhas contínuas)
        curves = self._detect_curves(roi, x1, y1)
        all_candidates.extend(curves)
        print(f"  ✓ Camada 3 (curvas): {len(curves)}")
        
        # Júri: deduplicar e agrupar
        final = self._jury_decision(all_candidates)
        print(f"  📊 Júri: {len(final)} pontos únicos")
        
        # Agrupar por cor
        data_points = self._group_by_color(final, x_calib, y_calib)
        
        total = sum(len(pts) for pts in data_points.values())
        print(f"  🎯 Total: {total} pontos em {len(data_points)} séries")
        
        return data_points
    
    def _detect_large_circles(self, roi, roi_gray, offset_x, offset_y) -> List[Point]:
        """Camada 1: HoughCircles com diâmetro modal"""
        circles = cv2.HoughCircles(
            roi_gray, cv2.HOUGH_GRADIENT, 
            dp=1, minDist=15,
            param1=50, param2=30,
            minRadius=8, maxRadius=50
        )
        
        if circles is None:
            return []
        
        circles = np.uint16(np.around(circles))[0]
        
        # Calcular diâmetro modal
        radii = circles[:, 2]
        radius_counts = Counter(radii)
        modal_radius = radius_counts.most_common(1)[0][0] if radius_counts else None
        
        if modal_radius is None:
            return []
        
        # Filtrar por raio próximo ao modal (±30%)
        tolerance = modal_radius * 0.3
        valid_circles = [
            c for c in circles 
            if abs(c[2] - modal_radius) < tolerance
        ]
        
        markers = []
        for cx, cy, r in valid_circles:
            # ROI inscrito 70%
            inner = int(r * 0.7)
            x1_i = max(0, cx - inner)
            y1_i = max(0, cy - inner)
            x2_i = min(roi_gray.shape[1], cx + inner)
            y2_i = min(roi_gray.shape[0], cy + inner)
            
            region = roi_gray[y1_i:y2_i, x1_i:x2_i]
            
            if region.size > 0:
                # Percentil 20 (mais robusto)
                darkness = np.percentile(region, 20)
                
                # Só aceita se escuro
                if darkness < 150:
                    if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                        b, g, r_val = roi[cy, cx]
                        
                        markers.append(Point(
                            x=offset_x + cx,
                            y=offset_y + cy,
                            color=(int(r_val), int(g), int(b)),
                            marker_type='circle'
                        ))
        
        return markers
    
    def _detect_defined_shapes(self, roi, roi_gray, offset_x, offset_y) -> List[Point]:
        """Camada 2: Contornos com múltiplos thresholds - FOCO EM QUADRADOS"""
        markers = []
        
        # Thresholds menores para detectar quadrados pretos preenchidos
        thresholds = [30, 50, 70, 90, 110]
        
        for thresh in thresholds:
            _, binary = cv2.threshold(roi_gray, thresh, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                # Aumentar range de área (quadrados podem ser maiores)
                if 10 < area < 1000:
                    M = cv2.moments(cnt)
                    if M['m00'] > 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        
                        if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                            # ROI inscrito
                            r = int(np.sqrt(area / np.pi))
                            inner = int(r * 0.7)
                            
                            x1_i = max(0, cx - inner)
                            y1_i = max(0, cy - inner)
                            x2_i = min(roi_gray.shape[1], cx + inner)
                            y2_i = min(roi_gray.shape[0], cy + inner)
                            
                            region = roi_gray[y1_i:y2_i, x1_i:x2_i]
                            
                            if region.size > 0:
                                darkness = np.percentile(region, 20)
                                
                                if darkness < 150:
                                    b, g, r_val = roi[cy, cx]
                                    
                                    if not self._is_neutral_color((int(r_val), int(g), int(b))):
                                        shape_type = self._identify_shape(cnt)
                                        
                                        markers.append(Point(
                                            x=offset_x + cx,
                                            y=offset_y + cy,
                                            color=(int(r_val), int(g), int(b)),
                                            marker_type=shape_type
                                        ))
        
        return markers
    
    def _detect_curves(self, roi, offset_x, offset_y) -> List[Point]:
        """Camada 3: Skeleton para curvas finas"""
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_roi, 30, 100)
        
        from skimage.morphology import skeletonize
        from skimage import img_as_ubyte
        
        skeleton = skeletonize(edges > 0)
        skeleton = img_as_ubyte(skeleton)
        
        y_coords, x_coords = np.nonzero(skeleton)
        
        if len(x_coords) == 0:
            return []
        
        markers = []
        step = max(1, len(x_coords) // 100)  # Reduzido de 200
        
        for i in range(0, len(x_coords), step):
            cx = x_coords[i]
            cy = y_coords[i]
            
            if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                b, g, r = roi[cy, cx]
                
                if not self._is_neutral_color((int(r), int(g), int(b))):
                    markers.append(Point(
                        x=offset_x + cx,
                        y=offset_y + cy,
                        color=(int(r), int(g), int(b)),
                        marker_type='curve'
                    ))
        
        return markers
    
    def _jury_decision(self, candidates: List[Point]) -> List[Point]:
        """Deduplicação com DBSCAN + votação (separa curvas de marcadores)"""
        if len(candidates) == 0:
            return []
        
        # Separar curvas de marcadores ANTES do clustering
        curves = [p for p in candidates if p.marker_type == 'curve']
        markers = [p for p in candidates if p.marker_type != 'curve']
        
        final = []
        
        # Deduplica APENAS marcadores (quadrados/círculos)
        if len(markers) > 0:
            coords = np.array([[p.x, p.y] for p in markers])
            clustering = DBSCAN(eps=5, min_samples=1).fit(coords)
            labels = clustering.labels_
            
            for label in set(labels):
                cluster_points = [markers[i] for i in range(len(markers)) if labels[i] == label]
                
                if len(cluster_points) == 1:
                    final.append(cluster_points[0])
                else:
                    # Votação
                    cx = int(np.mean([p.x for p in cluster_points]))
                    cy = int(np.mean([p.y for p in cluster_points]))
                    
                    colors = [p.color for p in cluster_points]
                    color = Counter(colors).most_common(1)[0][0]
                    
                    types = [p.marker_type for p in cluster_points]
                    marker_type = Counter(types).most_common(1)[0][0]
                    
                    final.append(Point(cx, cy, color, marker_type))
        
        # Curvas: amostragem sem deduplicação (já são espaçadas)
        final.extend(curves)
        
        return final
    
    def _identify_shape(self, contour) -> str:
        """Identifica forma geométrica"""
        approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True)
        vertices = len(approx)
        
        if vertices == 3:
            return 'triangle'
        elif vertices == 4:
            return 'square'
        elif vertices > 6:
            return 'circle'
        else:
            return 'point'
    
    def _is_neutral_color(self, rgb: Tuple[int, int, int]) -> bool:
        """Filtra branco/cinza"""
        r, g, b = rgb
        
        if r > 240 and g > 240 and b > 240:
            return True
        
        avg = (r + g + b) / 3
        if avg > 200 and max(abs(r - avg), abs(g - avg), abs(b - avg)) < 15:
            return True
        
        return False
    
    def _group_by_color(self, markers: List[Point], x_calib: AxisCalibration, y_calib: AxisCalibration) -> Dict:
        """Agrupa por COR + TIPO (separa curvas de marcadores)"""
        data_points = defaultdict(list)
        
        for marker in markers:
            color_key = self._get_color_key(marker.color)
            
            # CHAVE: cor + tipo (curva vs marcador)
            if marker.marker_type == 'curve':
                series_key = f"{color_key}_line"
            else:
                series_key = f"{color_key}_points"
            
            # Normalizar
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
    
    def _pixel_to_real_x(self, normalized_x: float, calib: AxisCalibration) -> float:
        """Converte X normalizado para valor real"""
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
    
    def _get_color_key(self, rgb: Tuple[int, int, int]) -> str:
        """Classificação de cor melhorada"""
        r, g, b = rgb
        
        # Preto (prioridade máxima para evitar falsos positivos)
        if max(r, g, b) < 100 and (r + g + b) / 3 < 80:
            return 'Black'
        
        # Cores saturadas
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        saturation = (max_val - min_val) / max_val if max_val > 0 else 0
        
        if saturation > 0.3:  # Cor saturada
            if r == max_val and r > 150:
                return 'Red'
            elif b == max_val and b > 150:
                return 'Blue'
            elif g == max_val and g > 150:
                return 'Green'
        
        # Cinza escuro -> agrupar com preto
        if 80 <= max(r, g, b) <= 180 and max(abs(r-g), abs(g-b), abs(r-b)) < 30:
            return 'Black'
        
        # Default: cor dominante fraca = preto
        return 'Black'