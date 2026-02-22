@echo off
echo Iniciando OBS Audio Translator para Windows...

:: Verificar si el entorno virtual existe
if not exist venv (
    echo Creando entorno virtual...
    python -m venv venv
)

:: Activar entorno virtual e instalar dependencias
call venv\Scripts\activate
echo Instalando/Actualizando dependencias (esto puede tardar la primera vez)...
pip install -r requirements.txt

:: Verificar FFmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] FFmpeg no detectado en el PATH. Asegurate de instalarlo.
)

echo.
echo Servidor iniciado. En OBS:
echo 1. Ve a Vista - Paneles - Paneles de navegador personalizados.
echo 2. Agrega una con URL: http://localhost:8000
echo.

python main.py
pause
