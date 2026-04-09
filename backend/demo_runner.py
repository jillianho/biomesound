"""
demo_runner.py
Demo day runner for Gut Radio. Two modes:

  1. ARDUINO MODE  — reads pH from serial, POSTs to /api/sensor
  2. SLIDER MODE   — serves a browser UI with sliders, no hardware needed

Usage:
    # Mode 1: Arduino connected
    python demo_runner.py --mode arduino --port /dev/ttyUSB0

    # Mode 2: Browser sliders (fallback, no hardware)
    python demo_runner.py --mode slider

    # Mode 3: Run through preset gut states automatically (good for unattended demo)
    python demo_runner.py --mode auto

Assumes the FastAPI backend is already running:
    cd backend && uvicorn main:app --reload --port 8000
"""

import argparse
import time
import json
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import requests

API_BASE = "http://localhost:8000"

# ── preset gut states for auto/demo mode ─────────────────────────────────
DEMO_SEQUENCE = [
    {"name": "Fasted morning",        "ph": 7.0,  "h2": 0.8,  "ch4": 0.5,  "temp": 37.0, "hold": 8},
    {"name": "Breakfast (oats+fiber)","ph": 6.5,  "h2": 4.5,  "ch4": 0.8,  "temp": 37.0, "hold": 10},
    {"name": "Peak fermentation",     "ph": 6.2,  "h2": 11.0, "ch4": 1.1,  "temp": 37.0, "hold": 10},
    {"name": "Sugar spike",           "ph": 7.7,  "h2": 0.6,  "ch4": 0.3,  "temp": 37.4, "hold": 8},
    {"name": "Inflammation signal",   "ph": 8.0,  "h2": 0.4,  "ch4": 0.2,  "temp": 38.1, "hold": 8},
    {"name": "Recovery (dinner)",     "ph": 6.4,  "h2": 8.0,  "ch4": 1.0,  "temp": 37.0, "hold": 10},
]


# ── Arduino serial reader ─────────────────────────────────────────────────

def run_arduino_mode(port: str, baud: int = 9600):
    try:
        import serial
    except ImportError:
        print("[error] pyserial not installed. Run: pip install pyserial --break-system-packages")
        return

    print(f"[arduino] connecting to {port}...")
    with serial.Serial(port, baud, timeout=2) as ser:
        time.sleep(2)
        ser.flushInput()
        print("[arduino] connected. reading...\n")

        while True:
            try:
                raw = ser.readline().decode("utf-8", errors="ignore").strip()
                if not raw:
                    continue

                # Parse: single float (pH) or "ph,h2,ch4,temp"
                parts = raw.split(",")
                ph   = float(parts[0])
                h2   = float(parts[1]) if len(parts) > 1 else 3.5
                ch4  = float(parts[2]) if len(parts) > 2 else 0.8
                temp = float(parts[3]) if len(parts) > 3 else 37.0

                _post_sensor(ph, h2, ch4, temp)

            except (ValueError, IndexError) as e:
                print(f"[parse error] {e}")
            except KeyboardInterrupt:
                print("\n[arduino] stopped.")
                break
            time.sleep(0.5)


# ── Auto demo sequence ────────────────────────────────────────────────────

def run_auto_mode():
    print("[auto demo] cycling through preset gut states...\n")
    while True:
        for step in DEMO_SEQUENCE:
            print(f"\n  ► {step['name']}")
            print(f"    pH {step['ph']} | H₂ {step['h2']} ppm | CH₄ {step['ch4']} ppm | {step['temp']}°C")

            # Gradually transition to the target state over the hold period
            steps = max(2, step["hold"] // 2)
            for i in range(steps):
                # Add slight random jitter to look like live sensor data
                import random
                ph_jitter   = step["ph"]   + random.uniform(-0.08, 0.08)
                h2_jitter   = step["h2"]   + random.uniform(-0.3, 0.3)
                ch4_jitter  = step["ch4"]  + random.uniform(-0.1, 0.1)
                temp_jitter = step["temp"] + random.uniform(-0.05, 0.05)

                result = _post_sensor(ph_jitter, h2_jitter, ch4_jitter, temp_jitter)
                if result:
                    print(f"    score: {result.get('score','?')}  |  mood: {result.get('mood','?')}")

                time.sleep(step["hold"] / steps)


# ── Slider UI server ──────────────────────────────────────────────────────

SLIDER_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Gut Radio — Demo Controls</title>
<style>
  body { font-family: monospace; background: #0a0c0f; color: #e0e8f0; padding: 2rem; max-width: 500px; margin: 0 auto; }
  h2 { color: #00e5a0; font-size: 18px; margin-bottom: 1.5rem; letter-spacing: 0.1em; }
  .row { display: grid; grid-template-columns: 80px 1fr 60px; gap: 12px; align-items: center; margin-bottom: 16px; }
  label { font-size: 13px; color: rgba(224,232,240,0.6); }
  input[type=range] { width: 100%; accent-color: #00e5a0; }
  .val { font-size: 14px; font-weight: bold; text-align: right; color: #00e5a0; }
  .presets { display: flex; flex-wrap: wrap; gap: 8px; margin: 1.5rem 0; }
  button { font-family: monospace; font-size: 11px; padding: 6px 12px; border: 1px solid rgba(0,229,160,0.3); background: transparent; color: #00e5a0; cursor: pointer; border-radius: 4px; letter-spacing: 0.05em; }
  button:hover { background: rgba(0,229,160,0.1); }
  #status { margin-top: 1rem; font-size: 12px; color: rgba(224,232,240,0.5); min-height: 40px; line-height: 1.6; }
  .score-big { font-size: 48px; font-weight: bold; color: #00e5a0; text-align: center; margin: 1rem 0; transition: color 0.5s; }
  .mood-big { font-size: 16px; text-align: center; color: rgba(224,232,240,0.7); margin-bottom: 1.5rem; }
</style>
</head>
<body>
<h2>GUT / RADIO — sensor demo</h2>
<div class="score-big" id="score">--</div>
<div class="mood-big" id="mood">awaiting input</div>

<div class="row"><label>pH</label><input type="range" id="ph" min="4" max="9" step="0.1" value="6.5" oninput="update()"><span class="val" id="ph-v">6.5</span></div>
<div class="row"><label>H₂ ppm</label><input type="range" id="h2" min="0" max="20" step="0.5" value="4" oninput="update()"><span class="val" id="h2-v">4.0</span></div>
<div class="row"><label>CH₄ ppm</label><input type="range" id="ch4" min="0" max="10" step="0.5" value="1" oninput="update()"><span class="val" id="ch4-v">1.0</span></div>
<div class="row"><label>Temp °C</label><input type="range" id="temp" min="35" max="39" step="0.1" value="37" oninput="update()"><span class="val" id="temp-v">37.0</span></div>

<div class="presets">
  <button onclick="preset(6.5,4,1,37)">healthy</button>
  <button onclick="preset(6.2,12,1.2,37)">peak</button>
  <button onclick="preset(7.8,0.5,0.3,37.5)">sugar spike</button>
  <button onclick="preset(8.1,0.3,0.2,38.3)">inflamed</button>
  <button onclick="preset(6.8,1,7.5,36.9)">methanogen</button>
  <button onclick="preset(7.0,0.8,0.5,37)">fasted</button>
</div>

<div id="status">slide to generate sound</div>
<audio id="player" controls style="width:100%; margin-top:1rem;"></audio>

<script>
const API = 'http://localhost:8049';
let debounce = null;

function val(id) { return parseFloat(document.getElementById(id).value); }

function preset(ph, h2, ch4, temp) {
  document.getElementById('ph').value = ph;
  document.getElementById('h2').value = h2;
  document.getElementById('ch4').value = ch4;
  document.getElementById('temp').value = temp;
  update();
}

function update() {
  document.getElementById('ph-v').textContent   = val('ph').toFixed(1);
  document.getElementById('h2-v').textContent   = val('h2').toFixed(1);
  document.getElementById('ch4-v').textContent  = val('ch4').toFixed(1);
  document.getElementById('temp-v').textContent = val('temp').toFixed(1);

  clearTimeout(debounce);
  debounce = setTimeout(sendToAPI, 400);
}

async function sendToAPI() {
  const body = { ph: val('ph'), h2_ppm: val('h2'), ch4_ppm: val('ch4'), temp_c: val('temp') };
  document.getElementById('status').textContent = 'generating...';
  try {
    const r = await fetch(API + '/api/sensor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await r.json();

    const score = data.score;
    const scoreEl = document.getElementById('score');
    scoreEl.textContent = score;
    scoreEl.style.color = score > 70 ? '#00e5a0' : score > 40 ? '#f5a623' : '#ff4c4c';
    document.getElementById('mood').textContent = data.mood;
    document.getElementById('status').textContent =
      `state: ${data.state} | diversity: ${data.biome.diversity_index.toFixed(2)} | inflammation: ${data.biome.inflammation_score.toFixed(2)}`;

    // Play the generated audio
    const player = document.getElementById('player');
    player.src = API + data.audio_url;
    player.load();
    player.play().catch(() => {});
  } catch(e) {
    document.getElementById('status').textContent = 'error: ' + e.message + ' (is the backend running?)';
  }
}

update();
</script>
</body>
</html>"""


class SliderHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(SLIDER_HTML.encode())

    def log_message(self, *args):
        pass  # suppress request logging


def run_slider_mode():
    port = 8080
    server = HTTPServer(("", port), SliderHandler)
    url = f"http://localhost:{port}"
    print(f"[slider] opening demo controls at {url}")
    print("[slider] make sure the FastAPI backend is running: uvicorn main:app --port 8000")
    threading.Thread(target=lambda: (time.sleep(0.5), webbrowser.open(url)), daemon=True).start()
    server.serve_forever()


# ── shared helper ─────────────────────────────────────────────────────────

def _post_sensor(ph, h2, ch4, temp) -> dict | None:
    try:
        r = requests.post(
            f"{API_BASE}/api/sensor",
            json={"ph": round(ph, 2), "h2_ppm": round(h2, 2),
                  "ch4_ppm": round(ch4, 2), "temp_c": round(temp, 2)},
            timeout=15,
        )
        return r.json()
    except Exception as e:
        print(f"[api error] {e}")
        return None


# ── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gut Radio demo runner")
    parser.add_argument("--mode",  choices=["arduino", "slider", "auto"], default="slider")
    parser.add_argument("--port",  default="/dev/ttyUSB0", help="Serial port (arduino mode)")
    parser.add_argument("--baud",  default=9600, type=int)
    args = parser.parse_args()

    if args.mode == "arduino":
        run_arduino_mode(args.port, args.baud)
    elif args.mode == "auto":
        run_auto_mode()
    else:
        run_slider_mode()
