import subprocess
import threading
import webrtcvad
import numpy as np
import asyncio
import edge_tts
import time
import collections

class TranslatorEngine:
    def __init__(self):
        self.input_srt = "srt://127.0.0.1:8888?mode=listener"
        self.output_srt = "srt://127.0.0.1:9999?mode=caller"
        self.model_size = "small"
        self.vad_aggressiveness = 3
        self.is_running = False
        
        self.process_in = None
        self.process_out = None
        self.model = None
        self.thread = None
        self.out_thread = None
        self.model_lock = threading.Lock()
        
        self.logs_buffer = collections.deque(maxlen=200) # Keep last 200 log lines
        self.tts_queue = collections.deque()
        
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        self.logs_buffer.append(formatted)
        
    def get_logs(self):
        return list(self.logs_buffer)
        
    def update_config(self, input_srt, output_srt, model_size, vad_aggressiveness):
        self.input_srt = input_srt
        self.output_srt = output_srt
        self.model_size = model_size
        self.vad_aggressiveness = vad_aggressiveness
        
    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.log("Arrancando el motor de traducción...")
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.log("Deteniendo procesos FFmpeg y cerrando hilos...")
        if self.process_in:
            try:
                self.process_in.terminate()
            except:
                pass
        if self.process_out:
            try:
                self.process_out.terminate()
            except:
                pass
            
    def _run(self):
        from faster_whisper import WhisperModel
        import platform
        
        system = platform.system()
        self.log(f"Sistema detectado: {system}")
        
        # Auto-detect best device
        device = "cuda" if system == "Windows" else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        self.log(f"Cargando modelo Faster-Whisper: {self.model_size} ({device})")
        try:
            # En Mac/Linux sin CUDA, forzamos CPU. En Windows intentamos CUDA.
            self.model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
            self.log(f"Modelo cargado exitosamente en {device}.")
        except Exception as e:
            self.log(f"Error cargando {device} ({e}). Reintentando con CPU pura...")
            try:
                self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                self.log("Modelo cargado en CPU (Nota: Latencia superior a GPU).")
            except Exception as e2:
                self.log(f"Error crítico cargando modelo: {e2}")
                self.is_running = False
                return
            
        self.log(f"Configurando Receptor SRT: {self.input_srt}")
        self.log(f"Configurando Emisor SRT: {self.output_srt}")
        
        # FFmpeg Input: Read from SRT, output raw PCM 16kHz, 1 channel, 16-bit
        cmd_in = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-i', self.input_srt,
            '-f', 's16le', '-ac', '1', '-ar', '16000', '-'
        ]
        
        # FFmpeg Output: Read raw PCM 24kHz, 1 channel, 16-bit from stdin, output to SRT
        # We use -re to simulate real-time consumption so FFmpeg doesn't buffer silence infinitely
        cmd_out = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-re', '-f', 's16le', '-ac', '1', '-ar', '24000', '-i', '-',
            '-c:a', 'aac', '-f', 'mpegts', self.output_srt
        ]
        
        try:
            self.process_in = subprocess.Popen(cmd_in, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.process_out = subprocess.Popen(cmd_out, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log("Procesos FFmpeg iniciados en segundo plano.")
            
            # Verificar si ffmpeg falló de inmediato (ej. no se puede conectar al servidor SRT)
            import time
            time.sleep(0.5)
            if self.process_out.poll() is not None:
                err = self.process_out.stderr.read().decode('utf-8', errors='ignore')
                self.log(f"Error fatal: El proceso de salida falló al iniciar. Asegúrate de que haya un servidor (ej. OBS, VLC) escuchando en la dirección de salida. Detalles: {err.strip()[-200:]}")
                self.is_running = False
                return
        except Exception as e:
            self.log(f"No se pudo iniciar FFmpeg. Asegúrate de tenerlo instalado: {e}")
            self.is_running = False
            return
            
        # Startup output stream thread
        self.out_thread = threading.Thread(target=self._out_stream_worker, daemon=True)
        self.out_thread.start()
        
        try:
            vad = webrtcvad.Vad(self.vad_aggressiveness)
        except Exception as e:
            self.log(f"Error VAD: {e}")
            self.is_running = False
            return
            
        sample_rate = 16000
        frame_duration_ms = 30 # WebRTC VAD requires 10, 20 or 30ms frames
        frame_size = int(sample_rate * frame_duration_ms / 1000) * 2 # 960 bytes
        
        
        audio_buffer = bytearray()
        silence_frames = 0
        max_silence_frames = int(600 / frame_duration_ms) # 600ms of silence
        
        self.log("Escuchando audio en tiempo real...")
        
        frames_received_count = 0
        speech_detected_count = 0
        
        while self.is_running:
            try:
                frame = self.process_in.stdout.read(frame_size)
                if not frame:
                    # EOF or closed
                    self.log("Stream SRT de entrada cerrado o finalizado.")
                    break
                
                if len(frame) < frame_size:
                    continue
                    
                frames_received_count += 1
                if frames_received_count == 330: # Approx 10 sec
                    self.log(f"[DEBUG] Recibiendo datos constantemente. Habla detectada: {speech_detected_count}/330 frames.")
                    frames_received_count = 0
                    speech_detected_count = 0
                    
                is_speech = vad.is_speech(frame, sample_rate)
                
                if is_speech:
                    speech_detected_count += 1
                    audio_buffer.extend(frame)
                    silence_frames = 0
                else:
                    if len(audio_buffer) > 0:
                        silence_frames += 1
                        audio_buffer.extend(frame)
                        
                    if silence_frames > max_silence_frames:
                        # Terminate phrase
                        audio_data_np = np.frombuffer(audio_buffer, np.int16).astype(np.float32) / 32768.0
                        audio_buffer = bytearray()
                        silence_frames = 0
                        
                        # Only translate if audio length is at least ~0.3 seconds to avoid noise triggering translation
                        if len(audio_data_np) > sample_rate * 0.3:
                            self.log(f"[DEBUG] Frase detectada de {len(audio_data_np)/sample_rate:.2f}s, enviando a traducir...")
                            threading.Thread(target=self._process_chunk, args=(audio_data_np,), daemon=True).start()
                            
            except Exception as e:
                self.log(f"Error crítico en el bucle principal de lectura: {e}")
                break
                
        self.stop()
        
    def _out_stream_worker(self):
        # Generate 100ms of silence at 24000 Hz, 16 bit (2 bytes), 1 ch
        # 100ms = 2400 samples = 4800 bytes
        silence_chunk = b'\x00' * 4800 
        
        self.log("Transmisión de salida activada.")
        while self.is_running:
            try:
                if len(self.tts_queue) > 0:
                    pcm_data = self.tts_queue.popleft()
                    self.log(f"[DEBUG] Enviando audio traducido al stream de salida ({len(pcm_data)} bytes)")
                    self.process_out.stdin.write(pcm_data)
                    self.process_out.stdin.flush()
                else:
                    # Write silence
                    self.process_out.stdin.write(silence_chunk)
                    self.process_out.stdin.flush()
            except Exception as e:
                self.log(f"Error escribiendo en el stream de salida: {e}")
                if self.process_out and self.process_out.poll() is not None:
                    err = self.process_out.stderr.read().decode('utf-8', errors='ignore')
                    self.log(f"El proceso de transmisión de salida finalizó inesperadamente. Detalles: {err.strip()[-200:]}")
                self.stop()
                break
                
    def _process_chunk(self, audio_data):
        from faster_whisper import WhisperModel
        try:
            with self.model_lock:
                if self.model is None:
                    return
                self.log("[DEBUG] Procesando fragmento Whisper...")
                try:
                    # beam_size = 5 gives good accuracy, can be reduced to 1 for max speed
                    segments, info = self.model.transcribe(audio_data, language="es", task="translate", beam_size=1)
                    # Convert to list to force execution and catch errors here
                    segments = list(segments)
                except Exception as e:
                    if "cublas" in str(e).lower() or "cudnn" in str(e).lower():
                        self.log(f"Error de librerías CUDA detectado durante la transcripción: {e}")
                        self.log("Cambiando automáticamente a modo CPU para continuar...")
                        self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                        segments, info = self.model.transcribe(audio_data, language="es", task="translate", beam_size=1)
                        segments = list(segments)
                    else:
                        raise e
            
            text = " ".join([segment.text for segment in segments]).strip()
            self.log(f"[DEBUG] Whisper devolvió: '{text}'")
            
            if text and len(text) > 1:
                self.log(f"Traducido: {text}")
                asyncio.run(self._synthesize_tts_queue(text))
            else:
                self.log("[DEBUG] Texto ignorado por Whisper (vacío o ruido interno)")
        except Exception as e:
            self.log(f"Error crítico traduciendo fragmento Whisper: {e}")
            
    async def _synthesize_tts_queue(self, text):
        try:
            # We use Edge TTS (Neural english voice)
            communicate = edge_tts.Communicate(text, "en-US-AriaNeural", rate="+10%")
            # Edge-TTS normally outputs mp3. We stream to mp3 buffer.
            mp3_buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_buffer.extend(chunk["data"])
                    
            if len(mp3_buffer) > 0:
                # Convert MP3 bytearray to raw PCM 24kHz using a quick FFmpeg call
                cmd_decode = [
                    'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                    '-i', 'pipe:0', 
                    '-f', 's16le', '-ac', '1', '-ar', '24000', 'pipe:1'
                ]
                proc = subprocess.Popen(cmd_decode, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                pcm_data, cmd_err = proc.communicate(input=bytes(mp3_buffer))
                
                if pcm_data:
                    self.log(f"[DEBUG] TTS sintetizado exitosamente y decodificado a PCM ({len(pcm_data)} bytes). Agregando a la cola.")
                    self.tts_queue.append(pcm_data)
                else:
                    self.log(f"Error al decodificar TTS con ffmpeg: {cmd_err.decode()}")
            else:
                self.log("[DEBUG] El buffer mp3 de TTS retornó vacío.")
        except Exception as e:
            self.log(f"Error sintetizando voz TTS: {e}")
