"""
Tipos de dados para o Graph Extractor
"""
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class Point:
    """Representa um ponto detectado no gráfico"""
    x: float
    y: float
    color: Tuple[int, int, int]
    marker_type: str = 'point'  # 'point', 'square', 'circle', 'x', 'triangle', 'hollow', 'curve'


@dataclass
class GraphAxis:
    """Representa um eixo do gráfico"""
    x1: int
    y1: int
    x2: int
    y2: int
    is_horizontal: bool
    
    def length(self) -> float:
        """Calcula o comprimento do eixo"""
        return ((self.x2 - self.x1)**2 + (self.y2 - self.y1)**2)**0.5


@dataclass
class GraphFrame:
    """Representa a moldura/frame do gráfico"""
    top_left: Tuple[int, int]
    top_right: Tuple[int, int]
    bottom_left: Tuple[int, int]
    bottom_right: Tuple[int, int]
    width: int
    height: int


@dataclass
class AxisCalibration:
    """Armazena calibração dos eixos com valores mín, máx e zero"""
    min_value: float
    max_value: float
    zero_position: Optional[float] = None  # Posição do zero (0 a 1)
    unit: str = ''
    is_symmetric: bool = False
