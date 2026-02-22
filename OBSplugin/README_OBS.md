# OBS Audio Translator Plugin Mode

Este proyecto permite usar el traductor de audio en tiempo real directamente dentro de OBS Studio como un panel (Dock).

## Instrucciones de Uso

1. **Instalar Dependencias:**
   - **PC:** Ejecuta `run_windows.bat`. Se creará un entorno virtual e instalará todo lo necesario.
   - **Mac:** Ejecuta `./run_mac.sh` desde la terminal.
   
2. **Configurar en OBS:**
   - Abre OBS Studio.
   - Ve al menú superior: **Vista** -> **Paneles (Docks)** -> **Paneles de navegador personalizados**.
   - En "Nombre del panel" pon: `Traductor`.
   - En "URL" pon: `http://localhost:8000`.
   - Haz clic en **Aplicar**.
   - Se abrirá una ventana que puedes arrastrar y anclar en cualquier parte de tu OBS.

## Compatibilidad
- **Windows:** Utiliza aceleración NVIDIA CUDA si está disponible (muy rápido).
- **Mac (Intel/M1/M2):** Utiliza la CPU. Se recomienda usar el modelo `tiny` o `base` en Mac para evitar retrasos excesivos, a menos que tengas un procesador muy potente.

## Requisitos
- **FFmpeg:** Debe estar instalado en el sistema.
- **Python 3.8+**
