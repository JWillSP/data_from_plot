"""
Módulo de pré-processamento de imagens
Remove legendas, caixas de texto e outros elementos que interferem na detecção
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional


class ImagePreprocessor:
    """Remove automaticamente legendas e caixas de texto do gráfico"""
    
    def __init__(self, img: np.ndarray):
        self.img = img
        self.h, self.w = img.shape[:2]
        self.gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.legend_boxes = []
    
    def remove_legends(self, ask_user: bool = False) -> Tuple[np.ndarray, List[Tuple]]:
        """
        Remove legendas automaticamente usando detecção de caixas de texto
        
        Returns:
            - Imagem limpa
            - Lista de caixas removidas [(x, y, w, h), ...]
        """
        # 1. Detectar caixas de texto (retângulos com texto)
        text_boxes = self._detect_text_boxes()
        
        if len(text_boxes) == 0:
            print("  ℹ️ Nenhuma legenda detectada")
            return self.img, []
        
        print(f"  🔍 Detectadas {len(text_boxes)} possíveis legendas")
        
        # 2. Filtrar apenas as que estão DENTRO do gráfico (não nos eixos)
        legend_boxes = self._filter_internal_boxes(text_boxes)
        
        if len(legend_boxes) == 0:
            print("  ✓ Nenhuma legenda interna ao gráfico")
            return self.img, []
        
        print(f"  ⚠️ {len(legend_boxes)} legenda(s) interna(s) detectada(s)")
        
        # 3. Se ask_user=True, retornar para confirmar
        if ask_user:
            self.legend_boxes = legend_boxes
            return self.img, legend_boxes
        
        # 4. Remover automaticamente
        cleaned = self._inpaint_boxes(self.img, legend_boxes)
        print(f"  ✓ Legendas removidas com inpainting")
        
        return cleaned, legend_boxes
    
    def _detect_text_boxes(self) -> List[Tuple[int, int, int, int]]:
        """Detecta retângulos que provavelmente contêm texto"""
        boxes = []
        
        print(f"    [DEBUG] Tamanho da imagem: {self.w}x{self.h}")
        
        # Estratégia 1: Detectar retângulos COM bordas FORTES
        edges = cv2.Canny(self.gray, 50, 150)
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"    [DEBUG] Estratégia 1 (bordas fortes): {len(contours)} contornos")
        
        count_1 = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            aspect = w / h if h > 0 else 0
            
            if (2000 < area < 50000 and 
                1.5 < aspect < 5 and
                x > 50 and y > 50 and 
                x + w < self.w - 50 and 
                y + h < self.h - 50):
                
                roi = self.gray[y:y+h, x:x+w]
                if roi.size > 0:
                    mean_intensity = np.mean(roi)
                    if mean_intensity > 180:
                        boxes.append((x, y, w, h))
                        count_1 += 1
        
        print(f"    [DEBUG] Estratégia 1: {count_1} caixas detectadas")
        
        # Estratégia 1B: Detectar bordas SUAVES (caixas com contorno fino)
        edges_soft = cv2.Canny(self.gray, 20, 80)  # Thresholds mais baixos
        kernel_soft = np.ones((2, 2), np.uint8)
        edges_soft = cv2.dilate(edges_soft, kernel_soft, iterations=1)
        
        contours_soft, _ = cv2.findContours(edges_soft, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"    [DEBUG] Estratégia 1B (bordas suaves): {len(contours_soft)} contornos")
        
        count_1b = 0
        for cnt in contours_soft:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            aspect = w / h if h > 0 else 0
            
            # Filtros para caixas suaves (legendas com borda fina)
            if (1500 < area < 40000 and 
                1.3 < aspect < 6 and
                x > 50 and y > 50 and 
                x + w < self.w - 50 and 
                y + h < self.h - 50):
                
                roi = self.gray[y:y+h, x:x+w]
                if roi.size > 0:
                    mean_intensity = np.mean(roi)
                    # Verificar se tem fundo claro + texto escuro
                    if mean_intensity > 170:
                        # Verificar se não é duplicata
                        overlap = False
                        for bx, by, bw, bh in boxes:
                            if self._boxes_overlap((x, y, w, h), (bx, by, bw, bh), threshold=0.5):
                                overlap = True
                                break
                        
                        if not overlap:
                            boxes.append((x, y, w, h))
                            count_1b += 1
                            print(f"    [DEBUG] Caixa suave: x={x}, y={y}, w={w}, h={h}, area={area}, aspect={aspect:.2f}, mean={mean_intensity:.1f}")
        
        print(f"    [DEBUG] Estratégia 1B: {count_1b} caixas detectadas")
        
        # Estratégia 2: Detectar regiões de TEXTO SEM CAIXA
        _, binary = cv2.threshold(self.gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        contours_text, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"    [DEBUG] Estratégia 2 (texto): {len(contours_text)} componentes de texto")
        
        text_regions = []
        for cnt in contours_text:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filtrar componentes de texto (letras/símbolos)
            if 3 < w < 80 and 3 < h < 80:  # Aumentado range para pegar símbolos maiores
                text_regions.append((x, y, w, h))
        
        print(f"    [DEBUG] Componentes de texto filtrados: {len(text_regions)}")
        
        # Agrupar regiões próximas em blocos de texto
        if len(text_regions) > 0:
            text_blocks = self._cluster_text_regions(text_regions)
            print(f"    [DEBUG] Blocos de texto agrupados: {len(text_blocks)}")
            
            count_2 = 0
            for block_x, block_y, block_w, block_h in text_blocks:
                area = block_w * block_h
                aspect = block_w / block_h if block_h > 0 else 0
                
                print(f"    [DEBUG] Bloco: x={block_x}, y={block_y}, w={block_w}, h={block_h}, area={area}, aspect={aspect:.2f}")
                
                # Blocos de texto: área moderada, mais largos que altos
                if (800 < area < 30000 and  # Reduzido mínimo para pegar blocos menores
                    1.2 < aspect < 10 and  # Aspect mais permissivo
                    block_x > 50 and block_y > 50 and 
                    block_x + block_w < self.w - 50 and 
                    block_y + block_h < self.h - 50):
                    
                    # Verificar se já não está em boxes
                    overlap = False
                    for bx, by, bw, bh in boxes:
                        if self._boxes_overlap((block_x, block_y, block_w, block_h), (bx, by, bw, bh)):
                            overlap = True
                            break
                    
                    if not overlap:
                        boxes.append((block_x, block_y, block_w, block_h))
                        count_2 += 1
                        print(f"    [DEBUG] ✓ Bloco aceito")
                    else:
                        print(f"    [DEBUG] ✗ Bloco rejeitado (overlap)")
                else:
                    print(f"    [DEBUG] ✗ Bloco rejeitado (filtros)")
            
            print(f"    [DEBUG] Estratégia 2: {count_2} blocos detectados")
        
        print(f"    [DEBUG] TOTAL: {len(boxes)} caixas detectadas")
        return boxes
    
    def _cluster_text_regions(self, regions: List[Tuple]) -> List[Tuple]:
        """Agrupa regiões de texto próximas em blocos - MELHORADO"""
        if not regions:
            return []
        
        # Ordenar por posição
        regions = sorted(regions, key=lambda r: (r[1], r[0]))
        
        blocks = []
        current_block = list(regions[0])  # [x, y, w, h]
        
        for x, y, w, h in regions[1:]:
            # Calcular distâncias
            # Distância horizontal: da direita do bloco atual até o novo elemento
            dist_x = x - (current_block[0] + current_block[2])
            # Distância vertical
            dist_y = abs(y - current_block[1])
            
            # Critérios mais permissivos para capturar linhas múltiplas
            # Se está na mesma linha OU linha abaixo próxima
            if ((dist_x < 50 and dist_y < 25) or  # Mesma linha
                (dist_y < 50 and abs(dist_x) < 100)):  # Linha abaixo, alinhado
                
                # Expandir bloco atual
                new_x = min(current_block[0], x)
                new_y = min(current_block[1], y)
                new_x2 = max(current_block[0] + current_block[2], x + w)
                new_y2 = max(current_block[1] + current_block[3], y + h)
                current_block = [new_x, new_y, new_x2 - new_x, new_y2 - new_y]
            else:
                # Salvar bloco atual e começar novo
                blocks.append(tuple(current_block))
                current_block = [x, y, w, h]
        
        # Adicionar último bloco
        blocks.append(tuple(current_block))
        
        # Expandir blocos em 10px em todas direções (margem)
        expanded_blocks = []
        for x, y, w, h in blocks:
            exp_x = max(0, x - 10)
            exp_y = max(0, y - 10)
            exp_w = min(self.w - exp_x, w + 20)
            exp_h = min(self.h - exp_y, h + 20)
            expanded_blocks.append((exp_x, exp_y, exp_w, exp_h))
        
        return expanded_blocks
    
    def _boxes_overlap(self, box1: Tuple, box2: Tuple, threshold: float = 0.3) -> bool:
        """Verifica se duas caixas se sobrepõem"""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        # Calcular interseção
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        
        if xi2 > xi1 and yi2 > yi1:
            inter_area = (xi2 - xi1) * (yi2 - yi1)
            box1_area = w1 * h1
            box2_area = w2 * h2
            
            # Se interseção > 30% de qualquer caixa
            if inter_area > threshold * min(box1_area, box2_area):
                return True
        
        return False
    
    def _filter_internal_boxes(self, boxes: List[Tuple]) -> List[Tuple]:
        """Filtra apenas caixas que estão DENTRO do gráfico (não nos eixos)"""
        # Estimar região do gráfico (área central, excluindo margens)
        margin_x = int(0.15 * self.w)  # 15% de margem lateral
        margin_y_top = int(0.1 * self.h)  # 10% margem superior
        margin_y_bottom = int(0.2 * self.h)  # 20% margem inferior
        
        internal_boxes = []
        
        for x, y, w, h in boxes:
            cx = x + w // 2  # Centro da caixa
            cy = y + h // 2
            
            # Verificar se está na área central (dentro do gráfico)
            if (margin_x < cx < self.w - margin_x and
                margin_y_top < cy < self.h - margin_y_bottom):
                internal_boxes.append((x, y, w, h))
        
        return internal_boxes
    
    def _inpaint_boxes(self, img: np.ndarray, boxes: List[Tuple]) -> np.ndarray:
        """Remove caixas usando inpainting (preenchimento inteligente)"""
        cleaned = img.copy()
        
        # Criar máscara de regiões a serem removidas
        mask = np.zeros((self.h, self.w), dtype=np.uint8)
        
        for x, y, w, h in boxes:
            # Expandir um pouco a área (margem de 5px)
            x1 = max(0, x - 5)
            y1 = max(0, y - 5)
            x2 = min(self.w, x + w + 5)
            y2 = min(self.h, y + h + 5)
            
            mask[y1:y2, x1:x2] = 255
        
        # Inpainting: preenche a região com base no entorno
        cleaned = cv2.inpaint(cleaned, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
        
        return cleaned
    
    def visualize_detected_boxes(self, boxes: List[Tuple]) -> np.ndarray:
        """Cria visualização das caixas detectadas (para debug/confirmação)"""
        vis = self.img.copy()
        
        for x, y, w, h in boxes:
            cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv2.putText(vis, "Legenda?", (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        return vis


def preprocess_image(img: np.ndarray, remove_legends: bool = True, 
                     ask_user: bool = False) -> Tuple[np.ndarray, dict]:
    """
    Função helper para pré-processar imagem
    
    Args:
        img: Imagem original
        remove_legends: Se True, remove legendas automaticamente
        ask_user: Se True, retorna info para confirmar com usuário
        
    Returns:
        - Imagem processada
        - Dict com informações: {'legend_boxes': [...], 'cleaned': bool}
    """
    preprocessor = ImagePreprocessor(img)
    
    if remove_legends:
        cleaned_img, boxes = preprocessor.remove_legends(ask_user=ask_user)
        
        info = {
            'legend_boxes': boxes,
            'cleaned': len(boxes) > 0,
            'visualizer': preprocessor.visualize_detected_boxes(boxes) if boxes else None
        }
        
        return cleaned_img, info
    
    return img, {'legend_boxes': [], 'cleaned': False}