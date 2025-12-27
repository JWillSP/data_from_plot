"""
Módulo de detecção de eixos
"""
import cv2
import numpy as np
from typing import List, Optional
try:
    from .data_types import GraphAxis, GraphFrame
except ImportError:
    from data_types import GraphAxis, GraphFrame


class AxisDetector:
    """Detecta eixos do gráfico de forma robusta"""
    
    def __init__(self, img: np.ndarray):
        self.img = img
        self.gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.h, self.w = img.shape[:2]
    
    def detect_axes(self) -> List[GraphAxis]:
        """Detecta eixos usando múltiplas estratégias"""
        all_lines = []
        
        # Estratégia 1: Detecção de bordas padrão
        edges1 = cv2.Canny(cv2.GaussianBlur(self.gray, (5, 5), 0), 50, 150)
        lines1 = cv2.HoughLinesP(edges1, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        if lines1 is not None:
            all_lines.extend(lines1)
        
        # Estratégia 2: Morfologia para preencher gaps
        kernel = np.ones((3, 3), np.uint8)
        edges2 = cv2.dilate(edges1, kernel, iterations=2)
        edges2 = cv2.erode(edges2, kernel, iterations=2)
        lines2 = cv2.HoughLinesP(edges2, 1, np.pi/180, 80, minLineLength=80, maxLineGap=20)
        if lines2 is not None:
            all_lines.extend(lines2)
        
        # Estratégia 3: Detecção em regiões de baixa variância
        _, binary = cv2.threshold(self.gray, 200, 255, cv2.THRESH_BINARY)
        lines3 = cv2.HoughLinesP(binary, 1, np.pi/180, 100, minLineLength=100, maxLineGap=15)
        if lines3 is not None:
            all_lines.extend(lines3)
        
        if not all_lines:
            print("⚠️ Nenhum eixo detectado, usando bordas da imagem")
            return self._use_image_borders()
        
        # Filtrar e categorizar linhas
        h_lines, v_lines = self._categorize_lines(all_lines)
        
        # Agrupar linhas similares
        h_lines = self._merge_similar_axes(h_lines, True)
        v_lines = self._merge_similar_axes(v_lines, False)
        
        print(f"  ✓ Eixos detectados: {len(h_lines)} horizontal, {len(v_lines)} vertical")
        
        return h_lines + v_lines
    
    def _categorize_lines(self, lines: List) -> tuple:
        """Categoriza linhas em horizontais e verticais"""
        h_lines, v_lines = [], []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            
            # Linhas horizontais
            if (angle < 5 or angle > 175) and length > 0.5 * self.w:
                h_lines.append(GraphAxis(x1, y1, x2, y2, True))
            
            # Linhas verticais
            elif 85 < angle < 95 and length > 0.5 * self.h:
                v_lines.append(GraphAxis(x1, y1, x2, y2, False))
        
        return h_lines, v_lines
    
    def _merge_similar_axes(self, axes: List[GraphAxis], is_horizontal: bool, threshold: int = 10) -> List[GraphAxis]:
        """Agrupa eixos muito próximos"""
        if not axes:
            return []
        
        # Ordenar por posição
        if is_horizontal:
            axes.sort(key=lambda a: (a.y1 + a.y2) / 2)
        else:
            axes.sort(key=lambda a: (a.x1 + a.x2) / 2)
        
        merged = [axes[0]]
        
        for axis in axes[1:]:
            last = merged[-1]
            
            if is_horizontal:
                dist = abs((axis.y1 + axis.y2) / 2 - (last.y1 + last.y2) / 2)
            else:
                dist = abs((axis.x1 + axis.x2) / 2 - (last.x1 + last.x2) / 2)
            
            if dist < threshold:
                # Mesclar (usar o mais longo)
                if axis.length() > last.length():
                    merged[-1] = axis
            else:
                merged.append(axis)
        
        return merged
    
    def _use_image_borders(self) -> List[GraphAxis]:
        """Fallback: usa as bordas da imagem como eixos"""
        margin = int(0.1 * min(self.h, self.w))
        
        return [
            GraphAxis(margin, self.h - margin, self.w - margin, self.h - margin, True),
            GraphAxis(margin, margin, margin, self.h - margin, False),
        ]
    
    def find_frame(self, axes: List[GraphAxis]) -> Optional[GraphFrame]:
        """Encontra o frame do gráfico a partir dos eixos"""
        h_axes = [a for a in axes if a.is_horizontal]
        v_axes = [a for a in axes if not a.is_horizontal]
        
        if len(h_axes) >= 2 and len(v_axes) >= 2:
            h_axes.sort(key=lambda a: min(a.y1, a.y2))
            v_axes.sort(key=lambda a: min(a.x1, a.x2))
            
            # Usar apenas os 2 primeiros eixos horizontais (ignora bordas externas/legendas)
            h_top = h_axes[0]
            h_bottom = h_axes[1] if len(h_axes) > 1 else h_axes[0]
            
            frame = GraphFrame(
                top_left=(min(v_axes[0].x1, v_axes[0].x2), min(h_top.y1, h_top.y2)),
                top_right=(max(v_axes[-1].x1, v_axes[-1].x2), min(h_top.y1, h_top.y2)),
                bottom_left=(min(v_axes[0].x1, v_axes[0].x2), max(h_bottom.y1, h_bottom.y2)),
                bottom_right=(max(v_axes[-1].x1, v_axes[-1].x2), max(h_bottom.y1, h_bottom.y2)),
                width=max(v_axes[-1].x1, v_axes[-1].x2) - min(v_axes[0].x1, v_axes[0].x2),
                height=max(h_bottom.y1, h_bottom.y2) - min(h_top.y1, h_top.y2)
            )
            
            print(f"  ✓ Frame: {frame.width}x{frame.height} pixels")
            return frame
        
        elif len(h_axes) >= 1 and len(v_axes) >= 1:
            # Frame parcial
            print("  ⚠️ Frame parcial detectado")
            h_ax = h_axes[-1]
            v_ax = v_axes[0]
            
            frame = GraphFrame(
                top_left=(min(v_ax.x1, v_ax.x2), int(0.1 * self.h)),
                top_right=(int(0.9 * self.w), int(0.1 * self.h)),
                bottom_left=(min(v_ax.x1, v_ax.x2), max(h_ax.y1, h_ax.y2)),
                bottom_right=(int(0.9 * self.w), max(h_ax.y1, h_ax.y2)),
                width=int(0.9 * self.w) - min(v_ax.x1, v_ax.x2),
                height=max(h_ax.y1, h_ax.y2) - int(0.1 * self.h)
            )
            return frame
        
        return None