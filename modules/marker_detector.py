"""
Módulo de detecção de marcadores
"""
import cv2
import numpy as np
from typing import List, Tuple
from collections import defaultdict
from skimage.morphology import skeletonize
from skimage import img_as_ubyte
from .data_types import Point, GraphFrame, AxisCalibration


class MarkerDetector:
    """Detecta múltiplos tipos de marcadores"""
    
    def __init__(self, img: np.ndarray, frame: GraphFrame):
        self.img = img
        self.frame = frame
        self.data_points = defaultdict(list)
    
    def detect_all(self, x_calib: AxisCalibration, y_calib: AxisCalibration):
        """Detecta todos os tipos de marcadores"""
        x1, y1 = self.frame.top_left
        x2, y2 = self.frame.bottom_right
        
        # Validar frame
        if x2 <= x1 or y2 <= y1:
            print("  ⚠️ Frame inválido")
            return {}
        
        roi = self.img[y1:y2, x1:x2].copy()
        
        # Validar ROI
        if roi.size == 0 or roi.shape[0] < 10 or roi.shape[1] < 10:
            print("  ⚠️ ROI muito pequena para processar")
            return {}
        
        all_markers = []
        
        # 1. Marcadores preenchidos
        filled = self._detect_filled_markers(roi, x1, y1)
        all_markers.extend(filled)
        print(f"  ✓ Marcadores preenchidos: {len(filled)}")
        
        # 2. Marcadores vazios
        hollow = self._detect_hollow_markers(roi, x1, y1)
        all_markers.extend(hollow)
        print(f"  ✓ Marcadores vazios: {len(hollow)}")
        
        # 3. Marcadores tipo X
        x_markers = self._detect_x_markers(roi, x1, y1)
        all_markers.extend(x_markers)
        print(f"  ✓ Marcadores tipo X: {len(x_markers)}")
        
        # 4. Curvas contínuas
        curves = self._detect_curves(roi, x1, y1)
        all_markers.extend(curves)
        print(f"  ✓ Pontos de curvas: {len(curves)}")
        
        # Agrupar por cor
        self._group_by_color(all_markers, x_calib, y_calib)
        
        total = sum(len(pts) for pts in self.data_points.values())
        print(f"\n  📊 Total: {total} pontos em {len(self.data_points)} séries")
        
        return self.data_points
    
    def _detect_filled_markers(self, roi, offset_x, offset_y) -> List[Point]:
        """Detecta marcadores preenchidos"""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        color_ranges = {
            'red': [([0, 80, 80], [10, 255, 255]), ([170, 80, 80], [180, 255, 255])],
            'green': [([40, 80, 80], [80, 255, 255])],
            'black': [([0, 0, 0], [180, 50, 60])],
            'yellow': [([20, 80, 80], [35, 255, 255])],
            'purple': [([130, 80, 80], [160, 255, 255])],
            'orange': [([10, 100, 100], [20, 255, 255])],
        }
        
        markers = []
        
        for color_name, ranges in color_ranges.items():
            combined_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            
            for lower, upper in ranges:
                mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                combined_mask = cv2.bitwise_or(combined_mask, mask)
            
            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 10 < area < 800:
                    M = cv2.moments(cnt)
                    if M['m00'] > 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        
                        if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                            b, g, r = roi[cy, cx]
                            
                            if not self._is_neutral_color((int(r), int(g), int(b))):
                                marker_type = self._identify_shape(cnt)
                                markers.append(Point(
                                    x=offset_x + cx,
                                    y=offset_y + cy,
                                    color=(int(r), int(g), int(b)),
                                    marker_type=marker_type
                                ))
        
        return markers
    
    def _detect_hollow_markers(self, roi, offset_x, offset_y) -> List[Point]:
        """Detecta marcadores vazios"""
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_roi, 50, 150)
        
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        markers = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 10 < area < 400:
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter ** 2)
                    
                    if 0.4 < circularity < 1.2:
                        M = cv2.moments(cnt)
                        if M['m00'] > 0:
                            cx = int(M['m10'] / M['m00'])
                            cy = int(M['m01'] / M['m00'])
                            
                            if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                                interior_color = gray_roi[cy, cx]
                                if interior_color > 200:
                                    b, g, r = roi[cy, cx]
                                    
                                    if not self._is_neutral_color((int(r), int(g), int(b))):
                                        markers.append(Point(
                                            x=offset_x + cx,
                                            y=offset_y + cy,
                                            color=(int(r), int(g), int(b)),
                                            marker_type='hollow'
                                        ))
        
        return markers
    
    def _detect_x_markers(self, roi, offset_x, offset_y) -> List[Point]:
        """Detecta marcadores tipo X"""
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_roi, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 20, minLineLength=5, maxLineGap=3)
        
        if lines is None:
            return []
        
        markers = []
        processed_points = set()
        
        for i, line1 in enumerate(lines):
            x1, y1, x2, y2 = line1[0]
            angle1 = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            
            for line2 in lines[i+1:]:
                x3, y3, x4, y4 = line2[0]
                angle2 = np.degrees(np.arctan2(y4 - y3, x4 - x3))
                
                angle_diff = abs(angle1 - angle2)
                if 70 < angle_diff < 110 or 160 < angle_diff < 200:
                    dist = np.sqrt((x1 - x3)**2 + (y1 - y3)**2)
                    if dist < 15:
                        cx = int((x1 + x3) / 2)
                        cy = int((y1 + y3) / 2)
                        
                        point_key = (cx, cy)
                        if point_key not in processed_points:
                            if 0 <= cy < roi.shape[0] and 0 <= cx < roi.shape[1]:
                                b, g, r = roi[cy, cx]
                                
                                if not self._is_neutral_color((int(r), int(g), int(b))):
                                    markers.append(Point(
                                        x=offset_x + cx,
                                        y=offset_y + cy,
                                        color=(int(r), int(g), int(b)),
                                        marker_type='x'
                                    ))
                                    processed_points.add(point_key)
        
        return markers
    
    def _detect_curves(self, roi, offset_x, offset_y) -> List[Point]:
        """Detecta pontos em curvas contínuas"""
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_roi, 30, 100)
        
        skeleton = skeletonize(edges > 0)
        skeleton = img_as_ubyte(skeleton)
        
        y_coords, x_coords = np.nonzero(skeleton)
        
        markers = []
        step = max(1, len(x_coords) // 200)
        
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
    
    def _identify_shape(self, contour) -> str:
        """Identifica forma do marcador"""
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
        """Verifica se a cor é neutra"""
        r, g, b = rgb
        
        if r > 240 and g > 240 and b > 240:
            return True
        
        avg = (r + g + b) / 3
        if avg > 200 and max(abs(r - avg), abs(g - avg), abs(b - avg)) < 15:
            return True
        
        return False
    
    def _group_by_color(self, markers: List[Point], x_calib: AxisCalibration, y_calib: AxisCalibration):
        """Agrupa marcadores por cor"""
        for marker in markers:
            color_key = self._get_color_key(marker.color)
            
            # Normalizar coordenadas
            graph_x = (marker.x - self.frame.bottom_left[0]) / self.frame.width
            graph_y = 1.0 - (marker.y - self.frame.top_left[1]) / self.frame.height
            
            # Aplicar calibração
            real_x = self._pixel_to_real_x(graph_x, x_calib)
            real_y = self._pixel_to_real_y(graph_y, y_calib)
            
            self.data_points[color_key].append({
                'x': real_x,
                'y': real_y,
                'type': marker.marker_type
            })
    
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
        """Gera chave de cor com tolerância para variações de compressão"""
        r, g, b = rgb
        
        # Vermelho (tolerância ±30)
        if r > 170 and g < 100 and b < 100:
            return 'Red'
        
        # Azul (tolerância ±30)
        elif r < 100 and g < 100 and b > 170:
            return 'Blue'
        
        # Verde (tolerância ±30)
        elif r < 100 and g > 170 and b < 100:
            return 'Green'
        
        # Preto/cinza escuro (todos < 80)
        elif r < 80 and g < 80 and b < 80:
            return 'Black'
        
        # Amarelo (tolerância ±30)
        elif r > 170 and g > 170 and b < 100:
            return 'Yellow'
        
        # Roxo (tolerância ±30)
        elif r > 120 and g < 100 and b > 120:
            return 'Purple'
        
        # Cinza médio (todos RGB similares, entre 80-180)
        elif 80 <= r <= 180 and 80 <= g <= 180 and 80 <= b <= 180:
            if max(abs(r-g), abs(g-b), abs(r-b)) < 30:
                return 'Black'  # Agrupar com preto
        
        # Tons claros próximos de vermelho/rosa
        elif r > 150 and g < 180 and b < 180:
            if r > g and r > b:
                return 'Red'  # Agrupar com vermelho
        
        # Outros casos: agrupar por cor dominante
        else:
            max_val = max(r, g, b)
            if max_val == r and r > 150:
                return 'Red'
            elif max_val == b and b > 150:
                return 'Blue'
            elif max_val == g and g > 150:
                return 'Green'
            else:
                return 'Black'  # Default para tons escuros/indefinidos