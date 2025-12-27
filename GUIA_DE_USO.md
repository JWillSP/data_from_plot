# 📘 GUIA DE USO - Graph Extractor V3

## 🚀 Início Rápido (5 minutos)

### 1. Instalação de Dependências

```bash
pip install opencv-python numpy pytesseract pillow pandas openpyxl xlsxwriter scikit-image
sudo apt-get install tesseract-ocr  # Linux
# ou
brew install tesseract  # macOS
```

### 2. Estrutura de Diretórios

```
seu_projeto/
├── modules_v3/          ← Copiar esta pasta
│   ├── __init__.py
│   ├── graph_extractor_v3.py
│   ├── marker_detector_v3.py
│   ├── calibrator_v3.py
│   ├── axis_detector.py
│   ├── exporter.py
│   └── data_types.py
└── seu_script.py        ← Seu código
```

### 3. Exemplo Básico

```python
import sys
sys.path.append('modules_v3')

from graph_extractor_v3 import GraphExtractor

# Processar gráfico
extractor = GraphExtractor('meu_grafico.png')
data = extractor.process()

# Exportar resultados
extractor.export_excel('resultados.xlsx')
extractor.visualize('visualizacao.png')

print(f"✅ Detectadas {len(data)} séries")
```

---

## 📊 Exemplos de Uso

### Exemplo 1: Processamento Automático Completo

```python
from graph_extractor_v3 import GraphExtractor

# 1. Criar extrator
extractor = GraphExtractor('grafico_experimental.png')

# 2. Processar (tudo automático)
try:
    data = extractor.process()
    
    # 3. Ver resumo
    summary = extractor.get_summary()
    print(f"\n📊 Resumo:")
    print(f"   Séries: {summary['total_series']}")
    print(f"   Pontos: {summary['total_points']}")
    
    for series_name, info in summary['series'].items():
        print(f"\n   {series_name}:")
        print(f"     - Pontos: {info['points']}")
        print(f"     - Tipos: {info['marker_types']}")
    
    # 4. Exportar em múltiplos formatos
    extractor.export_excel('dados.xlsx')
    extractor.export_csv('dados.csv')
    extractor.export_txt('dados.txt')
    extractor.visualize('resultado.png')
    
    print("\n✅ Processamento concluído!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
```

**Saída esperada:**
```
📸 Imagem carregada: 1200x900 pixels

============================================================
🚀 INICIANDO EXTRAÇÃO DE DADOS DO GRÁFICO
============================================================

🔍 Passo 1: Detectando eixos...
  Eixos detectados: 2 horizontal, 2 vertical

🖼️ Passo 2: Encontrando frame do gráfico...
  ✓ Frame: 1000x700 pixels

📏 Passo 3: Calibrando eixos...
  ✓ Eixo X: [0, 12] cm
  ✓ Eixo Y: [0, 120] %

🎯 Passo 4: Detectando pontos (HSV + Grid 100x100)...
  Camada 1: Detectando marcadores destacados (HSV)...
    ✓ 18 marcadores destacados
  Camada 2: Detectando curvas via grid 100x100...
    ✓ 120 pontos em curvas
  🎯 Total: 138 pontos em 2 séries

============================================================
✅ EXTRAÇÃO CONCLUÍDA COM SUCESSO!
============================================================

📊 Resumo:
   Séries: 2
   Pontos: 138
   
   Orange_points:
     - Pontos: 18
     - Tipos: ['marker']
   
   Black_line:
     - Pontos: 120
     - Tipos: ['curve']

✅ Processamento concluído!
```

---

### Exemplo 2: Com Calibração Manual (OCR Falhou)

```python
from graph_extractor_v3 import GraphExtractor

extractor = GraphExtractor('grafico_dificil.png')

# 1. Processar (OCR pode falhar)
data = extractor.process()

# 2. Verificar se OCR funcionou
if extractor.x_calibration.min_value == 0 and extractor.x_calibration.max_value == 1:
    print("⚠️ OCR falhou, aplicando calibração manual...")
    
    # 3. Definir valores manualmente
    extractor.set_manual_calibration(
        x_min=0,    # Valor mínimo do eixo X
        x_max=12,   # Valor máximo do eixo X
        y_min=0,    # Valor mínimo do eixo Y
        y_max=120   # Valor máximo do eixo Y
    )
    
    # 4. Os pontos são recalculados automaticamente!
    print("✅ Calibração manual aplicada")

# 5. Exportar com valores corretos
extractor.export_excel('dados_calibrados.xlsx')
```

---

### Exemplo 3: Processar Múltiplos Gráficos

```python
import os
from graph_extractor_v3 import GraphExtractor

# Pasta com gráficos
input_folder = 'graficos/'
output_folder = 'resultados/'

os.makedirs(output_folder, exist_ok=True)

# Lista de imagens
images = [f for f in os.listdir(input_folder) if f.endswith('.png')]

print(f"📊 Processando {len(images)} gráficos...\n")

for i, image_file in enumerate(images, 1):
    print(f"[{i}/{len(images)}] {image_file}")
    
    try:
        # Processar
        extractor = GraphExtractor(os.path.join(input_folder, image_file))
        data = extractor.process()
        
        # Nome base sem extensão
        base_name = os.path.splitext(image_file)[0]
        
        # Exportar
        extractor.export_excel(os.path.join(output_folder, f'{base_name}.xlsx'))
        extractor.visualize(os.path.join(output_folder, f'{base_name}_vis.png'))
        
        print(f"  ✅ Concluído: {len(data)} séries\n")
        
    except Exception as e:
        print(f"  ❌ Erro: {e}\n")

print("✅ Processamento em lote concluído!")
```

---

### Exemplo 4: Acessar Dados Programaticamente

```python
from graph_extractor_v3 import GraphExtractor
import matplotlib.pyplot as plt

extractor = GraphExtractor('grafico.png')
data = extractor.process()

# Dados estão em extractor.data_points
# Formato: {series_name: [{'x': ..., 'y': ..., 'type': ...}, ...]}

# Plotar com matplotlib
fig, ax = plt.subplots(figsize=(10, 6))

for series_name, points in data.items():
    # Extrair coordenadas
    xs = [pt['x'] for pt in points]
    ys = [pt['y'] for pt in points]
    
    # Plotar
    if '_line' in series_name:
        ax.plot(xs, ys, label=series_name, linewidth=2)
    else:  # _points
        ax.scatter(xs, ys, label=series_name, s=50)

ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.legend()
ax.grid(True, alpha=0.3)
plt.savefig('replot.png', dpi=150)
plt.show()

print("✅ Gráfico recriado com matplotlib")
```

---

### Exemplo 5: Integração com Pandas

```python
from graph_extractor_v3 import GraphExtractor
import pandas as pd

extractor = GraphExtractor('dados_experimentais.png')
data = extractor.process()

# Converter para DataFrame
dfs = {}

for series_name, points in data.items():
    df = pd.DataFrame(points)
    df['series'] = series_name
    dfs[series_name] = df

# Combinar tudo
all_data = pd.concat(dfs.values(), ignore_index=True)

print(all_data.head(10))

# Análise estatística
print("\n📊 Estatísticas:")
print(all_data.groupby('series')['y'].describe())

# Salvar
all_data.to_csv('dados_completos.csv', index=False)
```

---

## 🔧 Configurações Avançadas

### Ajustar Sensibilidade de Detecção

#### Marcadores Grandes
```python
# Editar: modules_v3/marker_detector_v3.py, linha ~60
# Aumentar área máxima para círculos muito grandes
if 10 < area < 2000:  # Era 1000
    detected.append(Point(...))
```

#### Curvas Finas
```python
# Editar: modules_v3/marker_detector_v3.py, linha ~110
# Aumentar resolução do grid
curves = self._detect_curves_with_grid(roi, x1, y1, grid_size=150)  # Era 100
```

#### Cores
```python
# Editar: modules_v3/marker_detector_v3.py, linhas 38-45
# Adicionar novo range de cor
color_ranges = {
    'blue': ([100, 50, 50], [130, 255, 255]),
    # ... outros
    'purple': ([130, 50, 50], [160, 255, 255]),  # NOVO
}
```

---

## 🐛 Troubleshooting

### Problema 1: OCR sempre retorna [0, 1]

**Causa**: Tesseract não instalado ou imagem muito pequena

**Solução**:
```bash
# Verificar instalação
tesseract --version

# Se não instalado (Linux)
sudo apt-get install tesseract-ocr tesseract-ocr-por

# Se não instalado (macOS)
brew install tesseract

# Alternativa: usar calibração manual
extractor.set_manual_calibration(x_min=..., x_max=..., y_min=..., y_max=...)
```

---

### Problema 2: Poucos pontos detectados

**Causa**: Marcadores muito pequenos ou cores não suportadas

**Diagnóstico**:
```python
# Ver imagem de debug
import cv2

extractor = GraphExtractor('grafico.png')
extractor.process()

# Visualizar detecções
vis = extractor.visualize()
cv2.imshow('Detectado', vis)
cv2.waitKey(0)
```

**Solução**: Ajustar ranges HSV (ver seção Configurações Avançadas)

---

### Problema 3: Muitos pontos de ruído

**Causa**: Grid detectando bordas/texto

**Solução**:
```python
# Editar: modules_v3/marker_detector_v3.py, linha ~165
# Tornar filtro de cor mais restritivo
if avg > 180 and max(abs(r - avg), ...) < 20:  # Era 200 e 15
    return True  # Filtrar
```

---

### Problema 4: Séries não separadas

**Causa**: Cores muito similares sendo agrupadas

**Diagnóstico**:
```python
# Ver cores detectadas
for series, points in data.items():
    if points:
        print(f"{series}: {points[0]['type']}, cor exemplo: {points[0].get('color', 'N/A')}")
```

**Solução**: Verificar `_classify_color()` e ajustar thresholds

---

## 📁 Estrutura de Saída

### Excel (.xlsx)
```
📊 dados.xlsx
├── Sheet "Metadata"
│   ├── Arquivo: caminho/imagem.png
│   ├── Data: 2024-12-27 14:30
│   ├── Frame: 1000x700 pixels
│   ├── Eixo X: [0, 12]
│   ├── Eixo Y: [0, 120]
│   └── Estatísticas
│
├── Sheet "Orange_points"
│   ├── # | X    | Y
│   ├── 1 | 0.50 | 35.2
│   ├── 2 | 1.20 | 38.5
│   └── ... (+ gráfico embutido)
│
└── Sheet "Black_line"
    ├── # | X    | Y
    ├── 1 | 0.00 | 34.0
    └── ... (+ gráfico embutido)
```

### CSV (.csv)
```csv
series,x,y,marker_type
Orange_points,0.50,35.2,marker
Orange_points,1.20,38.5,marker
Black_line,0.00,34.0,curve
Black_line,0.10,34.1,curve
...
```

### TXT (.txt)
```
# Eixo X: [0, 12]
# Eixo Y: [0, 120]

## Orange_points: 18 pontos
0.500000, 35.200000
1.200000, 38.500000
...

## Black_line: 120 pontos
0.000000, 34.000000
0.100000, 34.100000
...
```

---

## 🎯 Casos de Uso

### Caso 1: Tese de Doutorado
```python
# Extrair dados de 50 gráficos publicados
# Para comparar com simulações

for paper_fig in paper_figures:
    extractor = GraphExtractor(paper_fig)
    data = extractor.process()
    
    # Comparar com simulação
    compare_with_simulation(data, simulation_results)
```

### Caso 2: Validação Experimental
```python
# Extrair curva experimental
experimental = GraphExtractor('exp_curve.png').process()

# Comparar com teoria
theoretical = load_theoretical_data()

plot_comparison(experimental, theoretical)
```

### Caso 3: Digitalização de Gráficos Antigos
```python
# Digitalizar gráficos de papers de 1980
old_graph = GraphExtractor('scan_1980_fig3.png')
old_graph.process()

# Calibração manual (OCR pode falhar em scans)
old_graph.set_manual_calibration(x_min=0, x_max=100, y_min=0, y_max=1)

old_graph.export_csv('digitalized_1980_fig3.csv')
```

---

## 🚀 Performance

### Tempos Típicos (Intel i5, 8GB RAM)

| Tamanho Imagem | Tempo | Pontos |
|----------------|-------|--------|
| 800x600 | ~2s | 100-200 |
| 1200x900 | ~4s | 150-300 |
| 1920x1080 | ~7s | 200-500 |
| 4K (3840x2160) | ~20s | 500-1000 |

### Otimizações

```python
# Para processar muitas imagens
import multiprocessing as mp

def process_image(img_path):
    extractor = GraphExtractor(img_path)
    return extractor.process()

# Processar em paralelo
with mp.Pool(4) as pool:
    results = pool.map(process_image, image_list)
```

---

## 📞 Suporte

**Problemas comuns**: Ver seção Troubleshooting acima  
**Documentação**: README_V3.md e CORRECOES_DETALHADAS.md  
**Testes**: test_modules_v3.py

---

**Versão**: 3.0 Hybrid  
**Última atualização**: Dezembro 2024  
**Status**: ✅ Produção
