"""
🧪 TESTE DO GRAPH EXTRACTOR ULTIMATE
Demonstração de uso via Python (sem Streamlit)
"""

from graph_extractor_ultimate import GraphExtractorUltimate
import sys

def test_graph_extractor(image_path: str, grid_size: int = 100):
    """
    Testa o extrator com uma imagem
    
    Args:
        image_path: Caminho para a imagem do gráfico
        grid_size: Tamanho do grid (50-200, padrão 100)
    """
    
    print("="*70)
    print("🧪 TESTE DO GRAPH EXTRACTOR ULTIMATE")
    print("="*70)
    print(f"Imagem: {image_path}")
    print(f"Grid: {grid_size}x{grid_size}")
    print("")
    
    try:
        # 1. Criar extrator
        extractor = GraphExtractorUltimate(image_path, grid_divisions=grid_size)
        
        # 2. Processar
        data = extractor.process()
        
        # 3. Resumo
        summary = extractor.get_summary()
        
        print("\n" + "="*70)
        print("📊 RESUMO DOS RESULTADOS")
        print("="*70)
        print(f"\nTotal de séries: {summary['total_series']}")
        print(f"Total de pontos: {summary['total_points']}")
        
        print(f"\nCalibrção:")
        print(f"  X: [{summary['calibration']['x_min']:.2f}, {summary['calibration']['x_max']:.2f}]")
        print(f"  Y: [{summary['calibration']['y_min']:.2f}, {summary['calibration']['y_max']:.2f}]")
        
        print(f"\nSéries detectadas:")
        for series_name, info in summary['series'].items():
            print(f"\n  📈 {series_name}:")
            print(f"     Pontos: {info['points']}")
            print(f"     Tipos: {', '.join(info['marker_types'])}")
            print(f"     Range X: [{info['x_range'][0]:.2f}, {info['x_range'][1]:.2f}]")
            print(f"     Range Y: [{info['y_range'][0]:.2f}, {info['y_range'][1]:.2f}]")
        
        # 4. Exportar
        base_name = image_path.replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
        
        print(f"\n" + "="*70)
        print("💾 EXPORTANDO RESULTADOS")
        print("="*70)
        
        excel_path = f"{base_name}_data.xlsx"
        extractor.export_excel(excel_path)
        
        txt_path = f"{base_name}_data.txt"
        extractor.export_txt(txt_path)
        
        csv_path = f"{base_name}_data.csv"
        extractor.export_csv(csv_path)
        
        vis_path = f"{base_name}_visualization.png"
        extractor.visualize(vis_path)
        
        print("\n" + "="*70)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("="*70)
        
        return extractor, summary
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


def test_with_manual_calibration(image_path: str, x_min: float, x_max: float, 
                                 y_min: float, y_max: float, grid_size: int = 100):
    """
    Testa com calibração manual
    
    Args:
        image_path: Caminho para a imagem
        x_min, x_max: Range do eixo X
        y_min, y_max: Range do eixo Y
        grid_size: Tamanho do grid
    """
    
    print("="*70)
    print("🧪 TESTE COM CALIBRAÇÃO MANUAL")
    print("="*70)
    
    try:
        # Criar e processar
        extractor = GraphExtractorUltimate(image_path, grid_divisions=grid_size)
        data = extractor.process()
        
        # Aplicar calibração manual
        print(f"\n🔧 Aplicando calibração manual:")
        print(f"   X: [{x_min}, {x_max}]")
        print(f"   Y: [{y_min}, {y_max}]")
        
        extractor.set_manual_calibration(x_min, x_max, y_min, y_max)
        
        # Resumo
        summary = extractor.get_summary()
        print(f"\n✅ Calibração aplicada!")
        print(f"   Séries: {summary['total_series']}")
        print(f"   Pontos: {summary['total_points']}")
        
        # Exportar
        base_name = image_path.replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
        extractor.export_excel(f"{base_name}_manual_data.xlsx")
        
        return extractor, summary
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    # Exemplo de uso
    
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python test_extractor.py <imagem.png> [grid_size]")
        print("")
        print("Exemplos:")
        print("  python test_extractor.py grafico.png")
        print("  python test_extractor.py grafico.png 150")
        print("")
        sys.exit(1)
    
    image_path = sys.argv[1]
    grid_size = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    # Testar
    extractor, summary = test_graph_extractor(image_path, grid_size)
    
    # Se quiser testar com calibração manual:
    # extractor, summary = test_with_manual_calibration(
    #     image_path,
    #     x_min=0, x_max=12,
    #     y_min=0, y_max=120,
    #     grid_size=100
    # )
