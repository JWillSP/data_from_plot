# 📊 Data From Plot - Aplicação Streamlit

Aplicação web avançada para extração de dados de gráficos com interface intuitiva.

## 🚀 Recursos

### ✨ Funcionalidades Principais
- ✅ **Upload de imagens** (PNG, JPG, JPEG, BMP)
- ✅ **Colar da área de transferência** (Ctrl+V / Cmd+V)
- ✅ **Detecção automática de eixos** (mesmo parcialmente cobertos)
- ✅ **Calibração inteligente** com OCR
- ✅ **Múltiplos tipos de marcadores**:
  - Pontos preenchidos (●)
  - Quadrados (■ □)
  - Círculos vazios (○)
  - Marcadores X (×)
  - Triângulos (△)
  - Curvas contínuas
- ✅ **Filtragem automática** de cores neutras
- ✅ **Suporte a gráficos simétricos** (valores negativos/positivos)
- ✅ **Exportação múltipla** (Excel, TXT, CSV)
- ✅ **Visualização interativa**

## 📁 Estrutura do Projeto

```
graph_extractor_app/
├── app.py                      # Aplicação Streamlit principal
├── requirements.txt            # Dependências
├── README.md                   # Este arquivo
├── modules/                    # Módulos organizados
│   ├── __init__.py
│   ├── data_types.py          # Classes de dados
│   ├── axis_detector.py       # Detecção de eixos
│   ├── calibrator.py          # Calibração com OCR
│   ├── marker_detector.py     # Detecção de marcadores
│   ├── exporter.py            # Exportação de dados
│   └── graph_extractor.py     # Classe principal
├── assets/                     # Recursos estáticos
└── exports/                    # Diretório de exportação
```

## 🔧 Instalação

### 1. Instalar dependências do sistema

#### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-por
```

#### macOS:
```bash
brew install tesseract tesseract-lang
```

#### Windows:
- Baixe o instalador do Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Adicione ao PATH do sistema

### 2. Instalar dependências Python

```bash
pip install -r requirements.txt
```

## 🚀 Como Executar

### Localmente:
```bash
cd graph_extractor_app
streamlit run app.py
```

A aplicação abrirá automaticamente no navegador em `http://localhost:8501`

### Deploy (Streamlit Cloud):
1. Faça push do código para GitHub
2. Conecte no Streamlit Cloud (streamlit.io/cloud)
3. Deploy automático

## 📖 Como Usar

### Passo 1: Upload da Imagem
- **Opção A**: Clique em "Browse files" e selecione a imagem
- **Opção B**: Use Ctrl+V (Windows/Linux) ou Cmd+V (Mac) para colar da área de transferência

### Passo 2: Processar
1. Vá para a aba "🔍 Processar"
2. Clique em "🚀 Processar Gráfico"
3. Aguarde o processamento (veja o log em tempo real)
4. Visualize o resumo e a detecção de pontos

### Passo 3: Exportar
1. Vá para a aba "💾 Exportar"
2. Escolha o formato desejado:
   - **Excel**: Dados organizados em planilhas por série
   - **TXT**: Formato texto tabular
   - **CSV**: Todos os dados em um arquivo
3. Clique em "Download" para baixar

## 📊 Formatos de Saída

### Excel (.xlsx)
```
📁 graph_data.xlsx
├── Metadata          # Informações gerais
├── Red              # Dados da série vermelha
├── Blue             # Dados da série azul
└── ...              # Outras séries
```

Cada planilha contém:
- **x**: Coordenada X (valor real)
- **y**: Coordenada Y (valor real)
- **type**: Tipo de marcador

### TXT (.txt)
```
# Graph Data Extraction Results
# X Axis: [-4.0, 4.0]
# Y Axis: [0.0, 100.0]

## Red (150 points)
x       y       type
-3.95   45.2    circle
-3.85   46.8    circle
...
```

### CSV (.csv)
```
series,x,y,marker_type
Red,-3.95,45.2,circle
Red,-3.85,46.8,circle
Blue,0.15,98.5,square
...
```

## ⚙️ Configurações Disponíveis

Na sidebar:
- **Mostrar visualização**: Exibe imagem com pontos detectados
- **Exportar automaticamente**: Gera arquivos após processar

## 🎯 Exemplos de Uso

### Gráfico Simétrico
```
Entrada: Gráfico com eixo X de -4 a +4 cm
Resultado:
  ✓ X Range: [-4.0, 4.0]
  ✓ Zero Position: 50%
  ✓ Coordenadas negativas e positivas corretas
```

### Múltiplos Marcadores
```
Entrada: Gráfico com círculos, quadrados e X
Resultado:
  ✓ Red: 50 pontos (circle)
  ✓ Blue: 45 pontos (square)
  ✓ Green: 30 pontos (x)
```

### Curva Contínua
```
Entrada: Linha fina contínua
Resultado:
  ✓ Red: 200 pontos (curve)
  ✓ Amostragem uniforme ao longo da curva
```

## 🔍 Detecção de Problemas

### Eixos não detectados
- Verifique se a imagem tem boa qualidade
- Certifique-se de que os eixos são visíveis
- Tente aumentar o contraste da imagem

### OCR falhou
- Verifique se os números nos eixos estão legíveis
- Certifique-se de que o Tesseract está instalado
- A aplicação usará valores padrão [0, 1] como fallback

### Poucos pontos detectados
- Ajuste o contraste da imagem
- Verifique se os marcadores têm cores distintas
- Evite cores muito próximas do branco/cinza

## 🐛 Troubleshooting

### Erro: "Tesseract not found"
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Instale e adicione ao PATH
```

### Erro de memória com imagens grandes
- Redimensione a imagem antes do upload
- Recomendado: 800-2000 pixels de largura

### Interface não carrega
```bash
# Limpar cache do Streamlit
streamlit cache clear

# Reinstalar dependências
pip install -r requirements.txt --force-reinstall
```

## 📈 Performance

- **Processamento típico**: 5-15 segundos
- **Imagens recomendadas**: 800-2000px
- **Formatos otimizados**: PNG, JPG
- **Limite de pontos**: ~10.000 por série

## 🔐 Privacidade

- Todas as operações são feitas localmente
- Nenhum dado é enviado para servidores externos
- Arquivos temporários são limpos automaticamente

## 🆘 Suporte

### Problemas conhecidos:
1. ❌ Gráficos 3D não são suportados
2. ❌ OCR pode falhar com fontes muito estilizadas
3. ❌ Requer contraste razoável entre marcadores e fundo

### Limitações:
- Máximo 20 séries por gráfico
- Máximo ~10.000 pontos por série
- OCR em português e inglês

## 📝 Changelog

### v2.0 (Atual)
- ✅ Interface Streamlit completa
- ✅ Módulos organizados separadamente
- ✅ Suporte a área de transferência
- ✅ Exportação múltipla (Excel, TXT, CSV)
- ✅ Visualização interativa
- ✅ Melhor tratamento de erros

### v1.0
- Versão notebook do Google Colab

## 📄 Licença

MIT License - use livremente!

## 👥 Contribuindo

Contribuições são bem-vindas! Por favor:
1. Fork o repositório
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 🙏 Agradecimentos

Desenvolvido com:
- [Streamlit](https://streamlit.io/)
- [OpenCV](https://opencv.org/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [scikit-image](https://scikit-image.org/)

---

**Versão:** 2.0  
**Status:** ✅ Pronto para produção  
**Última atualização:** Dezembro 2024
