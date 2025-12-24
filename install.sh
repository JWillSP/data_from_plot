#!/bin/bash

# Script de instalação rápida do Graph Extractor

echo "📊 Graph Data Extractor - Instalação"
echo "===================================="
echo ""

# Detectar sistema operacional
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Detectado: Linux"
    echo "Instalando Tesseract OCR..."
    sudo apt-get update
    sudo apt-get install -y tesseract-ocr tesseract-ocr-por
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Detectado: macOS"
    echo "Instalando Tesseract OCR..."
    brew install tesseract tesseract-lang
else
    echo "⚠️  Windows detectado"
    echo "Por favor, instale o Tesseract manualmente:"
    echo "https://github.com/UB-Mannheim/tesseract/wiki"
    echo ""
    read -p "Pressione Enter após instalar o Tesseract..."
fi

echo ""
echo "📦 Instalando dependências Python..."
pip install -r requirements.txt

echo ""
echo "✅ Instalação concluída!"
echo ""
echo "Para executar a aplicação:"
echo "  streamlit run app.py"
echo ""
