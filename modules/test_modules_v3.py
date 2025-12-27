#!/usr/bin/env python3
"""
Script de teste para Graph Extractor V3 - HÍBRIDO
"""
import sys
import os

# Adicionar pasta dos módulos ao path
sys.path.insert(0, '/mnt/user-data/outputs/modules_v3')

# Tentar importar módulos
print("="*70)
print("TESTE DOS MÓDULOS V3 - HÍBRIDO")
print("="*70)

print("\n1️⃣ Testando imports...")
try:
    from data_types import Point, GraphAxis, GraphFrame, AxisCalibration
    print("  ✓ data_types OK")
except Exception as e:
    print(f"  ❌ data_types: {e}")
    sys.exit(1)

try:
    from axis_detector import AxisDetector
    print("  ✓ axis_detector OK")
except Exception as e:
    print(f"  ❌ axis_detector: {e}")
    sys.exit(1)

try:
    from calibrator_v3 import AxisCalibratorV3
    print("  ✓ calibrator_v3 OK")
except Exception as e:
    print(f"  ❌ calibrator_v3: {e}")
    sys.exit(1)

try:
    from marker_detector_v3 import MarkerDetectorV3
    print("  ✓ marker_detector_v3 OK")
except Exception as e:
    print(f"  ❌ marker_detector_v3: {e}")
    sys.exit(1)

try:
    from exporter import DataExporter
    print("  ✓ exporter OK")
except Exception as e:
    print(f"  ❌ exporter: {e}")
    sys.exit(1)

try:
    from graph_extractor_v3 import GraphExtractor
    print("  ✓ graph_extractor_v3 OK")
except Exception as e:
    print(f"  ❌ graph_extractor_v3: {e}")
    sys.exit(1)

print("\n2️⃣ Testando estrutura das classes...")
print(f"  ✓ GraphExtractor: {len(dir(GraphExtractor))} métodos/atributos")
print(f"  ✓ MarkerDetectorV3: {len(dir(MarkerDetectorV3))} métodos/atributos")
print(f"  ✓ AxisCalibratorV3: {len(dir(AxisCalibratorV3))} métodos/atributos")

print("\n" + "="*70)
print("✅ TODOS OS MÓDULOS V3 FORAM IMPORTADOS COM SUCESSO!")
print("="*70)

print("\n📝 Resumo das melhorias V3:")
print("  • Detecção HSV robusta (da versão antiga que funcionava)")
print("  • Grid 100x100 = 10.000 células para curvas finas")
print("  • OCR multi-estratégia para eixos")
print("  • Separação clara: marcadores vs curvas")
print("  • Classificação de cores melhorada")
print("\nPronto para testar com imagens reais!")
