document.addEventListener('DOMContentLoaded', () => {
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    const dot = document.getElementById('status-indicator');
    const terminal = document.getElementById('terminal-window');

    const inputSrt = document.getElementById('input-srt');
    const outputSrt = document.getElementById('output-srt');
    const modelSize = document.getElementById('model-size');
    const vadLevel = document.getElementById('vad-aggressiveness');

    let isRunning = false;
    let pollInterval = null;

    // Helper to log in terminal locally
    const uiLog = (msg) => {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        line.innerHTML = `<span style="color:#64748b;">[UI]</span> ${msg}`;
        terminal.appendChild(line);
        terminal.scrollTop = terminal.scrollHeight;
    };

    // Render server logs
    const renderLogs = (logs) => {
        terminal.innerHTML = '';
        logs.forEach(logLine => {
            const line = document.createElement('div');
            line.className = 'terminal-line';
            line.textContent = logLine;
            terminal.appendChild(line);
        });
        terminal.scrollTop = terminal.scrollHeight;
    };

    // Update UI State
    const setUIState = (running) => {
        isRunning = running;
        if (running) {
            dot.classList.add('running');
            btnStart.disabled = true;
            btnStop.disabled = false;

            // disable inputs
            inputSrt.disabled = true;
            outputSrt.disabled = true;
            modelSize.disabled = true;
            vadLevel.disabled = true;
        } else {
            dot.classList.remove('running');
            btnStart.disabled = false;
            btnStop.disabled = true;

            // enable inputs
            inputSrt.disabled = false;
            outputSrt.disabled = false;
            modelSize.disabled = false;
            vadLevel.disabled = false;
        }
    };

    const fetchStatus = async () => {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();

            if (data.is_running !== isRunning) {
                setUIState(data.is_running);
            }

            // Render logs if there's any change
            // An optimal way is appending only new logs, but for simplicity we re-render
            renderLogs(data.logs || []);

        } catch (e) {
            console.error("No se pudo obtener el estado:", e);
        }
    };

    btnStart.addEventListener('click', async () => {
        uiLog("Solicitando inicio al servidor...");
        btnStart.disabled = true; // prevent double click
        try {
            const config = {
                input_srt: inputSrt.value.trim(),
                output_srt: outputSrt.value.trim(),
                model_size: modelSize.value,
                vad_aggressiveness: parseInt(vadLevel.value)
            };

            const res = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            const data = await res.json();
            uiLog(data.message || data.detail || JSON.stringify(data));
            if (res.ok) fetchStatus();
        } catch (e) {
            uiLog("Error al iniciar: " + e.message);
            btnStart.disabled = false;
        }
    });

    btnStop.addEventListener('click', async () => {
        uiLog("Solicitando detención al servidor...");
        btnStop.disabled = true;
        try {
            const res = await fetch('/api/stop', { method: 'POST' });
            const data = await res.json();
            uiLog(data.message || data.detail || JSON.stringify(data));
            if (res.ok) fetchStatus();
        } catch (e) {
            uiLog("Error al detener: " + e.message);
            btnStop.disabled = false;
        }
    });

    // Empezar a hacer polling cada segundo
    fetchStatus();
    pollInterval = setInterval(fetchStatus, 1000);
});
