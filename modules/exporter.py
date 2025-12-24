"""
Módulo de exportação de dados
"""
import cv2
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List
from .data_types import GraphFrame, AxisCalibration


class DataExporter:
    """Exporta dados para múltiplos formatos"""
    
    def __init__(self, image_path: str, frame: GraphFrame, 
                 x_calib: AxisCalibration, y_calib: AxisCalibration,
                 data_points: Dict):
        self.image_path = image_path
        self.frame = frame
        self.x_calib = x_calib
        self.y_calib = y_calib
        self.data_points = data_points
    
    def to_excel(self, output_path: str):
        """Exporta para Excel com gráficos"""
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Metadata
            metadata = pd.DataFrame({
                'Property': [
                    'Image', 'Timestamp', 'Frame Size',
                    'X Range', 'Y Range', 'X Zero Position', 'Total Points'
                ],
                'Value': [
                    self.image_path,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    f"{self.frame.width}x{self.frame.height}",
                    f"[{self.x_calib.min_value:.2f}, {self.x_calib.max_value:.2f}]",
                    f"[{self.y_calib.min_value:.2f}, {self.y_calib.max_value:.2f}]",
                    f"{self.x_calib.zero_position:.2%}" if self.x_calib.zero_position else 'N/A',
                    sum(len(pts) for pts in self.data_points.values())
                ]
            })
            metadata.to_excel(writer, sheet_name='Metadata', index=False)
            
            # Dados por cor com gráficos
            color_map = {'Red': '#FF0000', 'Blue': '#0000FF', 'Green': '#00FF00', 
                        'Black': '#000000', 'Yellow': '#FFFF00', 'Purple': '#800080'}
            
            for idx, (color, points) in enumerate(self.data_points.items()):
                if not color or not points:
                    continue
                    
                df = pd.DataFrame(points)
                df = df.sort_values('x')
                
                sheet_name = str(color)[:31]  # Garantir que é string
                df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
                
                worksheet = writer.sheets[sheet_name]
                
                # Criar gráfico
                chart = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
                
                max_row = len(df) + 1
                chart.add_series({
                    'name': color,
                    'categories': [sheet_name, 2, 0, max_row, 0],  # coluna x
                    'values': [sheet_name, 2, 1, max_row, 1],      # coluna y
                    'line': {'color': color_map.get(color, '#000000'), 'width': 2},
                    'marker': {'type': 'circle', 'size': 5}
                })
                
                chart.set_x_axis({'name': 'X'})
                chart.set_y_axis({'name': 'Y'})
                chart.set_title({'name': f'{color} - {len(points)} pontos'})
                chart.set_size({'width': 720, 'height': 480})
                
                worksheet.insert_chart('E2', chart)
    
    def to_txt(self, output_path: str):
        """Exporta para TXT"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Graph Data Extraction Results\n")
            f.write(f"# Image: {self.image_path}\n")
            f.write(f"# Timestamp: {datetime.now()}\n\n")
            
            f.write(f"# X Axis: [{self.x_calib.min_value:.2f}, {self.x_calib.max_value:.2f}]\n")
            f.write(f"# Y Axis: [{self.y_calib.min_value:.2f}, {self.y_calib.max_value:.2f}]\n\n")
            
            for color, points in self.data_points.items():
                f.write(f"\n## {color} ({len(points)} points)\n")
                f.write("x\ty\ttype\n")
                
                for pt in sorted(points, key=lambda p: p['x']):
                    f.write(f"{pt['x']:.6f}\t{pt['y']:.6f}\t{pt['type']}\n")
    
    def to_csv(self, output_path: str):
        """Exporta para CSV (todos os dados em um arquivo)"""
        all_data = []
        
        for color, points in self.data_points.items():
            for pt in points:
                all_data.append({
                    'series': color,
                    'x': pt['x'],
                    'y': pt['y'],
                    'marker_type': pt['type']
                })
        
        df = pd.DataFrame(all_data)
        df = df.sort_values(['series', 'x'])
        df.to_csv(output_path, index=False)
    
    def visualize(self, img: np.ndarray) -> np.ndarray:
        """Cria visualização dos pontos detectados"""
        vis = img.copy()
        
        # Desenhar frame
        cv2.rectangle(vis, self.frame.top_left, self.frame.bottom_right, (0, 255, 0), 2)
        
        # Desenhar pontos
        for color_name, points in self.data_points.items():
            for pt in points:
                # Converter de volta para pixel
                norm_x = (pt['x'] - self.x_calib.min_value) / (self.x_calib.max_value - self.x_calib.min_value)
                norm_y = (pt['y'] - self.y_calib.min_value) / (self.y_calib.max_value - self.y_calib.min_value)
                
                px = int(self.frame.bottom_left[0] + norm_x * self.frame.width)
                py = int(self.frame.top_left[1] + (1.0 - norm_y) * self.frame.height)
                
                # Desenhar marcador apropriado
                if pt['type'] == 'square':
                    cv2.rectangle(vis, (px-3, py-3), (px+3, py+3), (0, 255, 255), 1)
                elif pt['type'] == 'x':
                    cv2.line(vis, (px-3, py-3), (px+3, py+3), (0, 255, 255), 1)
                    cv2.line(vis, (px-3, py+3), (px+3, py-3), (0, 255, 255), 1)
                else:
                    cv2.circle(vis, (px, py), 3, (0, 255, 255), 1)
        
        return vis
