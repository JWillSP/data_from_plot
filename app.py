"""
Graph Extractor - Aplicação Streamlit
Fluxo contínuo e simplificado
"""
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
import os
import sys
from pathlib import Path
import tempfile
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent))


# Fallback para versão antiga
from modules import GraphExtractor
from modules.data_types import AxisCalibration
print("⚠️  Usando GraphExtractor antigo (fallback)")

st.set_page_config(
    page_title="Data From Plot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)


def save_uploaded_file(uploaded_file):
    """Salva arquivo temporário"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name


def plot_series(data_points, x_calib, y_calib):
    """Cria gráficos interativos com Plotly"""
    color_map = {
        'Red': '#FF0000', 'Blue': '#0000FF', 'Green': '#00FF00',
        'Black': '#000000', 'Yellow': '#FFFF00', 'Purple': '#800080',
        'Orange': '#FF8C00'
    }
    
    figs = []
    
    for color, points in data_points.items():
        if not points:
            continue
        
        df = pd.DataFrame(points).sort_values('x')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['x'],
            y=df['y'],
            mode='lines+markers',
            name=color,
            line=dict(color=color_map.get(color, '#000000'), width=2),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title=f'{color} - {len(points)} pontos',
            xaxis_title=f'X ({x_calib.min_value:.1f} a {x_calib.max_value:.1f})',
            yaxis_title=f'Y ({y_calib.min_value:.1f} a {y_calib.max_value:.1f})',
            height=400,
            showlegend=True
        )
        
        figs.append((color, fig, df))
    
    return figs


def main():
    # Cabeçalho
    st.markdown('<div class="main-header">📊 Data From Plot</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("ℹ️ Sobre")
        st.markdown("""
        ### Recursos
        ✅ Múltiplos tipos de marcadores  
        ✅ Calibração automática (OCR)  
        ✅ Calibração manual  
        ✅ Gráficos interativos  
        ✅ Exportação Excel  
        """)
        
        st.divider()
        
        st.header("📏 Calibração Manual")
        use_manual_calib = st.checkbox("Usar calibração manual", value=False, key="manual_calib_checkbox")
        
        if use_manual_calib:
            x_min = st.number_input("X mínimo", value=0.0, step=0.1, key="x_min_input")
            x_max = st.number_input("X máximo", value=9.0, step=0.1, key="x_max_input")
            y_min = st.number_input("Y mínimo", value=0.0, step=0.1, key="y_min_input")
            y_max = st.number_input("Y máximo", value=10.0, step=0.1, key="y_max_input")
            
            manual_calib = {
                'x_min': x_min, 'x_max': x_max,
                'y_min': y_min, 'y_max': y_max
            }
        else:
            manual_calib = None
        
        st.divider()
        
        st.header("⚙️ Configurações Avançadas")
        grid_size = st.slider(
            "Tamanho do grid (curvas finas)",
            min_value=50,
            max_value=200,
            value=100,
            step=10,
            help="Grid NxN para detectar curvas contínuas. Maior = mais pontos",
            key="grid_size_slider"
        )
        st.caption(f"📊 {grid_size}x{grid_size} = {grid_size**2:,} células")
    
    # Inicializar session state
    if 'processed' not in st.session_state:
        st.session_state.processed = False
    if 'extractor' not in st.session_state:
        st.session_state.extractor = None
    
    # Upload de imagem
    st.header("📤 1. Carregar Imagem")
    uploaded_file = st.file_uploader(
        "Escolha uma imagem do gráfico",
        type=['png', 'jpg', 'jpeg', 'bmp'],
        key="file_uploader"
    )
    
    if uploaded_file is not None:
        # Mostrar preview
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Imagem Original")
            image = Image.open(uploaded_file)
            st.image(image, caption="Imagem carregada", use_container_width=True)
        
        # Processar automaticamente
        st.header("🔍 2. Processamento")
        
        with st.spinner("Processando gráfico..."):
            try:
                # Salvar arquivo
                temp_path = save_uploaded_file(uploaded_file)
                
                # Criar extrator com grid_size
                extractor = GraphExtractor(temp_path, grid_divisions=grid_size)
                
                # Processar
                with st.expander("📋 Log de Processamento", expanded=False):
                    data = extractor.process()
                
                # Aplicar calibração manual se habilitada
                if manual_calib:
                    extractor.x_calibration = AxisCalibration(
                        manual_calib['x_min'], 
                        manual_calib['x_max']
                    )
                    extractor.y_calibration = AxisCalibration(
                        manual_calib['y_min'], 
                        manual_calib['y_max']
                    )
                    
                    # Recalcular pontos
                    for color_key in list(extractor.data_points.keys()):
                        points = extractor.data_points[color_key]
                        new_points = []
                        
                        for pt in points:
                            # Normalizar (assumindo que veio de 0-1)
                            norm_x = pt['x']
                            norm_y = pt['y']
                            
                            # Aplicar nova calibração
                            real_x = manual_calib['x_min'] + norm_x * (manual_calib['x_max'] - manual_calib['x_min'])
                            real_y = manual_calib['y_min'] + norm_y * (manual_calib['y_max'] - manual_calib['y_min'])
                            
                            new_points.append({
                                'x': real_x,
                                'y': real_y,
                                'type': pt['type']
                            })
                        
                        extractor.data_points[color_key] = new_points
                    
                    st.success(f"✅ Calibração manual: X[{manual_calib['x_min']}, {manual_calib['x_max']}], Y[{manual_calib['y_min']}, {manual_calib['y_max']}]")
                
                st.session_state.extractor = extractor
                st.session_state.processed = True
                
                # Resumo
                summary = extractor.get_summary()
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Séries Detectadas", summary['total_series'])
                with col_b:
                    st.metric("Total de Pontos", summary['total_points'])
                with col_c:
                    st.metric("Calibração", "Manual" if manual_calib else "Automática")
                
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
                st.exception(e)
                st.session_state.processed = False
        
        # Visualização
        if st.session_state.processed and st.session_state.extractor:
            extractor = st.session_state.extractor
            
            with col2:
                st.subheader("Detecção de Pontos")
                vis_path = os.path.join(tempfile.gettempdir(), 'visualization.png')
                vis = extractor.visualize(vis_path)
                vis_rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
                st.image(vis_rgb, caption="Pontos detectados", use_container_width=True)
            
            # Gráficos interativos
            st.header("📊 3. Gráficos Extraídos")



            with st.expander("🎯 Filtrar Séries", expanded=False):
                available_series = list(extractor.data_points.keys())
                if available_series:
                    series_to_keep = st.multiselect(
                        "Selecione as séries para manter:",
                        options=available_series,
                        default=available_series,
                        key="series_filter"
                    )
                    
                    if st.button("Aplicar Filtro", key="apply_filter"):
                        # Remover séries não selecionadas
                        for series in list(extractor.data_points.keys()):
                            if series not in series_to_keep:
                                del extractor.data_points[series]
                        st.success(f"✅ {len(series_to_keep)} série(s) mantida(s)")
                        st.rerun()


            
            figs = plot_series(
                extractor.data_points,
                extractor.x_calibration,
                extractor.y_calibration
            )
            
            if figs:
                # Mostrar cada gráfico
                for color, fig, df in figs:
                    with st.expander(f"📈 {color} ({len(df)} pontos)", expanded=True):
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Mostrar preview dos dados
                        st.dataframe(df.head(10), use_container_width=True)
            else:
                st.warning("⚠️ Nenhum ponto detectado")
            
            # Exportação
            st.header("💾 4. Exportar Dados")
            
            col_x, col_y, col_z = st.columns(3)
            
            with col_x:
                if st.button("📊 Exportar Excel", use_container_width=True, key="export_excel_btn"):
                    try:
                        excel_path = os.path.join(tempfile.gettempdir(), 'graph_data.xlsx')
                        extractor.export_excel(excel_path)
                        
                        with open(excel_path, 'rb') as f:
                            st.download_button(
                                label="⬇️ Download Excel",
                                data=f,
                                file_name='graph_data.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                use_container_width=True,
                                key="download_excel_btn"
                            )
                    except Exception as e:
                        st.error(f"Erro: {e}")
            
            with col_y:
                if st.button("📄 Exportar CSV", use_container_width=True, key="export_csv_btn"):
                    try:
                        csv_path = os.path.join(tempfile.gettempdir(), 'graph_data.csv')
                        extractor.export_csv(csv_path)
                        
                        with open(csv_path, 'r', encoding='utf-8') as f:
                            st.download_button(
                                label="⬇️ Download CSV",
                                data=f,
                                file_name='graph_data.csv',
                                mime='text/csv',
                                use_container_width=True,
                                key="download_csv_btn"
                            )
                    except Exception as e:
                        st.error(f"Erro: {e}")
            
            with col_z:
                if st.button("🖼️ Exportar Visualização", use_container_width=True, key="export_vis_btn"):
                    try:
                        with open(vis_path, 'rb') as f:
                            st.download_button(
                                label="⬇️ Download PNG",
                                data=f,
                                file_name='visualization.png',
                                mime='image/png',
                                use_container_width=True,
                                key="download_vis_btn"
                            )
                    except Exception as e:
                        st.error(f"Erro: {e}")
    
    else:
        st.info("👆 Faça upload de uma imagem para começar")
    
    # Rodapé
    st.divider()
    st.markdown("""
        <div style="text-align: center; color: #666; padding: 1rem;">
            📊 Data From Plot v3.2 | Desenvolvido com IA
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()