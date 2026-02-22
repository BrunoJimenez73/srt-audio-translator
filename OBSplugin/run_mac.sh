#!/bin/bash
echo "Iniciando OBS Audio Translator para Mac..."

# Verificar si el entorno virtual existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual e instalar dependencias
source venv/bin/activate
echo "Instalando/Actualizando dependencias (esto puede tardar la primera vez)..."
pip install -r requirements.txt

# Verificar FFmpeg
if ! command -v ffmpeg &> /dev/null
then
    echo "[ADVERTENCIA] FFmpeg no detectado. Puedes instalarlo con 'brew install ffmpeg'"
fi

echo ""
echo "Servidor iniciado. En OBS:"
echo "1. Ve a Vista - Paneles - Paneles de navegador personalizados."
echo "2. Agrega una con URL: http://localhost:8000"
echo ""

python3 main.py
