
# app.py (All-in-One Flask Server and Webpage with wide calibration)
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from gpiozero import DigitalInputDevice
from w1thermsensor import W1ThermSensor
import logging

# --- Configuration ---
SOIL_SENSOR_PIN = 17
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__)
CORS(app)
state = {'calibration_offset': 0.0}

# --- HTML & JavaScript for the Webpage ---
HTML_DOCUMENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plant Monitor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        #tempFill { transition: width 0.5s ease-in-out; }
    </style>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen">
    <div class="w-full max-w-md bg-white rounded-2xl shadow-lg p-6 md:p-8 space-y-6">
        <h1 class="text-2xl font-bold text-gray-800 text-center">Plant Health Monitor</h1>
        <div id="status" class="text-center font-semibold text-yellow-600">Fetching data...</div>
        <!-- Temperature Section -->
        <div class="space-y-3">
            <div class="flex justify-between items-baseline">
                <label class="text-lg font-semibold text-gray-700">Temperature</label>
                <span id="tempValue" class="text-xl font-bold text-indigo-600">--.-°C</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-6">
                <div id="tempFill" class="bg-gradient-to-r from-blue-500 to-red-500 h-full rounded-full w-0"></div>
            </div>
        </div>
        <!-- Soil Moisture Section -->
        <div class="space-y-3">
            <label class="text-lg font-semibold text-gray-700">Soil Moisture</label>
            <div id="moistureBox" class="flex items-center p-4 rounded-lg border-2">
                <span id="moistureStatus" class="text-xl font-bold text-gray-500">Waiting...</span>
            </div>
        </div>
        <!-- Calibration Section -->
        <div class="space-y-3 pt-2">
            <div class="flex justify-between items-baseline">
                <label for="calSlider" class="text-lg font-semibold text-gray-700">Calibration</label>
                <span id="calValue" class="text-xl font-bold text-gray-600">0.0°C</span>
            </div>
            <!-- *** CHANGE 1: Updated slider min and max values *** -->
            <input id="calSlider" type="range" min="-10.0" max="10.0" step="0.1" value="0.0" class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer">
            <button id="resetButton" class="w-full mt-2 px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700">Reset</button>
        </div>
    </div>
    <script>
        const PI_IP_ADDRESS = window.location.hostname || '10.15.138.87';
        const PI_PORT = 5000;
        const API_BASE_URL = `http://${PI_IP_ADDRESS}:${PI_PORT}`;

        async function fetchSensorData() {
            try {
                const response = await fetch(`${API_BASE_URL}/data`);
                const data = await response.json();
                updateUI(data);
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').className = 'text-center font-semibold text-green-600';
            } catch (error) {
                document.getElementById('status').textContent = 'Connection Error';
                document.getElementById('status').className = 'text-center font-semibold text-red-500';
            }
        }

        function updateUI(data) {
            const tempValue = document.getElementById('tempValue');
            const tempFill = document.getElementById('tempFill');
            const moistureBox = document.getElementById('moistureBox');
            const moistureStatus = document.getElementById('moistureStatus');
            const calValue = document.getElementById('calValue');
            const calSlider = document.getElementById('calSlider');
            
            if (data.temperature !== null) {
                tempValue.textContent = `${data.temperature.toFixed(1)}°C`;
                const percentage = ((data.temperature - -10) / (80 - -10)) * 100;
                tempFill.style.width = `${Math.max(0, Math.min(100, percentage))}%`;
            }
            
            moistureBox.classList.remove('border-green-500', 'bg-green-50', 'border-red-500', 'bg-red-50');
            if (data.is_wet) {
                moistureStatus.textContent = 'Wet';
                moistureStatus.className = 'text-xl font-bold text-green-600';
                moistureBox.classList.add('border-green-500', 'bg-green-50');
            } else {
                moistureStatus.textContent = 'Dry';
                moistureStatus.className = 'text-xl font-bold text-red-600';
                moistureBox.classList.add('border-red-500', 'bg-red-50');
            }
            
            calValue.textContent = `${data.calibration_offset.toFixed(1)}°C`;
            calSlider.value = data.calibration_offset;
        }
        
        async function sendCalibrationUpdate(offset) {
            console.log(`Sending POST calibration update: ${offset}`);
            try {
                await fetch(`${API_BASE_URL}/calibrate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ offset: offset }),
                });
            } catch (error) {
                console.error('Calibration POST Error:', error);
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            const calSlider = document.getElementById('calSlider');
            const calValue = document.getElementById('calValue');
            const resetButton = document.getElementById('resetButton');

            calSlider.addEventListener('input', () => {
                 calValue.textContent = `${parseFloat(calSlider.value).toFixed(1)}°C`;
            });
            calSlider.addEventListener('change', () => sendCalibrationUpdate(calSlider.value));
            resetButton.addEventListener('click', () => {
                calSlider.value = 0.0;
                sendCalibrationUpdate(0.0);
            });
            
            setInterval(fetchSensorData, 2000);
            fetchSensorData();
        });
    </script>
</body>
</html>
"""

# --- Sensor Initialization ---
try:
    temp_sensor = W1ThermSensor()
    soil_sensor = DigitalInputDevice(SOIL_SENSOR_PIN)
    print("✅ Sensors initialized successfully.")
except Exception as e:
    print(f"❌ FATAL: Could not initialize sensors: {e}")
    temp_sensor = None
    soil_sensor = None

# --- API Routes ---
@app.route('/data')
def get_sensor_data():
    if temp_sensor and soil_sensor:
        try:
            raw_temp = temp_sensor.get_temperature()
            calibrated_temp = raw_temp + state['calibration_offset']
        except: calibrated_temp = None
        try:
            is_wet = not soil_sensor.is_active
        except: is_wet = None
    else:
        calibrated_temp, is_wet = 20.0, False
    return jsonify({
        "temperature": calibrated_temp,
        "is_wet": is_wet,
        "calibration_offset": state['calibration_offset']
    })

@app.route('/calibrate', methods=['POST'])
def set_calibration():
    data = request.get_json()
    offset = data.get('offset')
    if offset is not None:
        print(f"✅ Received calibration request. New offset: {offset}")
        # --- CHANGE 2: Updated server-side limit ---
        state['calibration_offset'] = max(-10.0, min(10.0, float(offset)))
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/')
def index():
    return Response(HTML_DOCUMENT, mimetype='text/html')

# --- Main Execution ---
if __name__ == "__main__":
    print("==============================================")
    print("    RUNNING ALL-IN-ONE SERVER    ")
    print("==============================================")
    print(f"🌍 Starting server. Open your browser to http://<YOUR_PI_IP>:5000")
    app.run(host='0.0.0.0', port=5000)
