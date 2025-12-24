"""
Classe principal do Graph Extractor
"""
import cv2
import numpy as np
from typing import Dict, Optional
from .axis_detector import AxisDetector
from .calibrator import AxisCalibrator
from .marker_detector import MarkerDetector
from .exporter import DataExporter
from .data_types import GraphFrame, AxisCalibration


class GraphExtractor:
    """Classe principal para extração de dados de gráficos"""
    
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.img = cv2.imread(image_path)
        
        if self.img is None:
            raise ValueError(f"Erro ao carregar imagem: {image_path}")
        
        self.frame: Optional[GraphFrame] = None
        self.x_calibration: Optional[AxisCalibration] = None
        self.y_calibration: Optional[AxisCalibration] = None
        self.data_points: Dict = {}
        
        print(f"📸 Imagem carregada: {self.img.shape[1]}x{self.img.shape[0]} pixels")
    
    def process(self) -> Dict:
        """Executa pipeline completo de extração"""
        print("\n" + "="*60)
        print("🚀 INICIANDO EXTRAÇÃO DE DADOS DO GRÁFICO")
        print("="*60)
        
        try:
            # 1. Detectar eixos
            print("\n📐 Passo 1: Detectando eixos...")
            detector = AxisDetector(self.img)
            axes = detector.detect_axes()
            
            # 2. Encontrar frame
            print("\n🖼️  Passo 2: Encontrando frame do gráfico...")
            self.frame = detector.find_frame(axes)
            if not self.frame:
                raise ValueError("Não foi possível detectar o frame do gráfico")
            
            # 3. Calibrar eixos
            print("\n📏 Passo 3: Calibrando eixos...")
            calibrator = AxisCalibrator(self.img, self.frame)
            self.x_calibration = calibrator.calibrate_x_axis()
            self.y_calibration = calibrator.calibrate_y_axis()
            
            print(f"  ✓ Eixo X: [{self.x_calibration.min_value:.2f}, {self.x_calibration.max_value:.2f}]")
            if self.x_calibration.zero_position:
                print(f"    Zero em: {self.x_calibration.zero_position:.2%}")
            print(f"  ✓ Eixo Y: [{self.y_calibration.min_value:.2f}, {self.y_calibration.max_value:.2f}]")
            
            # 4. Detectar marcadores
            print("\n🎯 Passo 4: Detectando marcadores...")
            marker_det = MarkerDetector(self.img, self.frame)
            self.data_points = marker_det.detect_all(self.x_calibration, self.y_calibration)
            
            print("\n" + "="*60)
            print("✅ EXTRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("="*60)
            
            return self.data_points
            
        except Exception as e:
            print(f"\n❌ ERRO: {str(e)}")
            raise
    
    def export_excel(self, output_path: str):
        """Exporta para Excel"""
        if not self.data_points:
            raise ValueError("Nenhum dado para exportar. Execute process() primeiro.")
        
        if not self.frame:
            raise ValueError("Frame não detectado.")
        
        if not self.x_calibration or not self.y_calibration:
            raise ValueError("Calibração dos eixos não realizada.")
        
        exporter = DataExporter(
            self.image_path, self.frame,
            self.x_calibration, self.y_calibration,
            self.data_points
        )
        exporter.to_excel(output_path)
        print(f"  ✓ Excel salvo: {output_path}")
    
    def export_txt(self, output_path: str):
        """Exporta para TXT"""
        if not self.data_points:
            raise ValueError("Nenhum dado para exportar. Execute process() primeiro.")
        
        exporter = DataExporter(
            self.image_path, self.frame,
            self.x_calibration, self.y_calibration,
            self.data_points
        )
        exporter.to_txt(output_path)
        print(f"  ✓ TXT salvo: {output_path}")
    
    def export_csv(self, output_path: str):
        """Exporta para CSV"""
        if not self.data_points:
            raise ValueError("Nenhum dado para exportar. Execute process() primeiro.")
        
        exporter = DataExporter(
            self.image_path, self.frame,
            self.x_calibration, self.y_calibration,
            self.data_points
        )
        exporter.to_csv(output_path)
        print(f"  ✓ CSV salvo: {output_path}")
    
    def visualize(self, save_path: Optional[str] = None) -> np.ndarray:
        """Cria visualização dos pontos detectados"""
        if not self.data_points:
            raise ValueError("Nenhum dado para visualizar. Execute process() primeiro.")
        
        exporter = DataExporter(
            self.image_path, self.frame,
            self.x_calibration, self.y_calibration,
            self.data_points
        )
        vis = exporter.visualize(self.img)
        
        if save_path:
            cv2.imwrite(save_path, vis)
            print(f"  ✓ Visualização salva: {save_path}")
        
        return vis
    
    def get_summary(self) -> Dict:
        """Retorna resumo dos dados extraídos"""
        if not self.data_points:
            return {}
        
        summary = {
            'total_series': len(self.data_points),
            'total_points': sum(len(pts) for pts in self.data_points.values()),
            'series': {}
        }
        
        for color, points in self.data_points.items():
            marker_types = set(pt['type'] for pt in points)
            summary['series'][color] = {
                'points': len(points),
                'marker_types': list(marker_types)
            }
        
        return summary
    
    def _recalibrate_points(self):
        """Recalcula coordenadas dos pontos com nova calibração"""
        if not self.data_points or not self.frame:
            return
        
        # Armazenar pontos em coordenadas de pixel
        pixel_points = {}
        
        for color, points in self.data_points.items():
            pixel_points[color] = []
            for pt in points:
                # Converter de volta para normalizado (0-1)
                norm_x = (pt['x'] - 0) / (1 - 0)  # Estava em [0,1]
                norm_y = (pt['y'] - 0) / (1 - 0)
                
                # Aplicar nova calibração
                real_x = self.x_calibration.min_value + norm_x * (self.x_calibration.max_value - self.x_calibration.min_value)
                real_y = self.y_calibration.min_value + norm_y * (self.y_calibration.max_value - self.y_calibration.min_value)
                
                pixel_points[color].append({
                    'x': real_x,
                    'y': real_y,
                    'type': pt['type']
                })
        
        self.data_points = pixel_points