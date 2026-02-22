import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from engine import TranslatorEngine

app = FastAPI(title="Live Audio Translator")

# Initialize static directory if not exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

engine = TranslatorEngine()

class ConfigUpdate(BaseModel):
    input_srt: str
    output_srt: str
    model_size: str
    vad_aggressiveness: int

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/start")
def start_processing(config: ConfigUpdate):
    if engine.is_running:
        raise HTTPException(status_code=400, detail="Ya se está ejecutando el motor de traducción.")
    engine.update_config(config.input_srt, config.output_srt, config.model_size, config.vad_aggressiveness)
    engine.start()
    return {"status": "started", "message": "Motor de traducción iniciado exitosamente."}

@app.post("/api/stop")
def stop_processing():
    if not engine.is_running:
        raise HTTPException(status_code=400, detail="El motor no se estaba ejecutando.")
    engine.stop()
    return {"status": "stopped", "message": "Motor detenido."}

@app.get("/api/status")
def get_status():
    return {
        "is_running": engine.is_running,
        "input_srt": engine.input_srt,
        "output_srt": engine.output_srt,
        "model_size": engine.model_size,
        "vad_aggressiveness": engine.vad_aggressiveness,
        "logs": engine.get_logs()
    }

if __name__ == "__main__":
    print("Servidor iniciado. Abre el navegador en http://localhost:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
