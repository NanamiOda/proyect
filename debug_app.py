#!/usr/bin/env python3
"""
Aplicación Flask para debugging del sistema Braille
Muestra en tiempo real las palabras y comandos procesados
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import serial
import serial.tools.list_ports
import threading
import time
from datetime import datetime
import queue
import os
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'braille-debug-2025'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Variables globales para monitoreo
log_queue = queue.Queue(maxsize=200)
arduino_connections = {}  # {port: serial_connection}
monitoring_threads = {}
is_monitoring = False
processed_words = []  # Historial de palabras procesadas
current_word = ""  # Palabra actual siendo procesada
stats = {
    'total_commands': 0,
    'total_words': 0,
    'errors': 0,
    'start_time': None
}

class ArduinoMonitor:
    """Monitor individual para cada Arduino"""
    def __init__(self, port, name):
        self.port = port
        self.name = name
        self.serial_conn = None
        self.running = False
        self.thread = None
        
    def connect(self, baudrate=115200):
        """Conectar al Arduino"""
        try:
            self.serial_conn = serial.Serial(self.port, baudrate, timeout=1)
            time.sleep(2)
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            add_log("INFO", f"{self.name} conectado en {self.port}", self.name)
            return True
        except Exception as e:
            add_log("ERROR", f"Error al conectar {self.name}: {str(e)}", self.name)
            return False
    
    def disconnect(self):
        """Desconectar del Arduino"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        add_log("INFO", f"{self.name} desconectado", self.name)
    
    def send_command(self, command):
        """Enviar comando al Arduino"""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(f"{command}\n".encode())
                add_log("SENT", command, self.name)
                stats['total_commands'] += 1
                
                # Detectar palabras en comandos
                if command.startswith("WRITE_MODULE:"):
                    parts = command.split(":")
                    if len(parts) >= 3:
                        char = parts[2]
                        update_current_word(char)
                        
                return True
            except Exception as e:
                add_log("ERROR", f"Error al enviar: {str(e)}", self.name)
                stats['errors'] += 1
                return False
        return False
    
    def _monitor_loop(self):
        """Bucle de monitoreo continuo"""
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    if self.serial_conn.in_waiting:
                        line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            add_log("RECV", line, self.name)
                            # Emitir via WebSocket
                            socketio.emit('arduino_message', {
                                'type': 'RECV',
                                'message': line,
                                'source': self.name,
                                'timestamp': get_timestamp()
                            })
            except Exception as e:
                if self.running:
                    add_log("ERROR", f"Error en monitor: {str(e)}", self.name)
                    stats['errors'] += 1
                time.sleep(0.5)
            time.sleep(0.01)

def add_log(log_type, message, source="SYSTEM"):
    """Agregar entrada al log"""
    log_entry = {
        'type': log_type,
        'message': message,
        'source': source,
        'timestamp': get_timestamp()
    }
    
    try:
        log_queue.put_nowait(log_entry)
    except queue.Full:
        # Remover el más antiguo si está lleno
        try:
            log_queue.get_nowait()
            log_queue.put_nowait(log_entry)
        except:
            pass

def get_timestamp():
    """Obtener timestamp formateado"""
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]

def update_current_word(char):
    """Actualizar palabra actual siendo procesada"""
    global current_word
    if char == ' ' or char == '\n':
        if current_word:
            processed_words.append({
                'word': current_word,
                'timestamp': get_timestamp()
            })
            stats['total_words'] += 1
            socketio.emit('word_processed', {
                'word': current_word,
                'timestamp': get_timestamp()
            })
            current_word = ""
    else:
        current_word += char
    
    socketio.emit('current_word_update', {
        'word': current_word,
        'timestamp': get_timestamp()
    })

def get_available_ports():
    """Obtener puertos seriales disponibles"""
    ports = serial.tools.list_ports.comports()
    return [{
        'port': port.device,
        'description': port.description,
        'hwid': port.hwid
    } for port in ports]

@app.route('/')
def index():
    """Página principal de debugging"""
    return render_template('debug.html')

@app.route('/api/ports')
def api_ports():
    """Listar puertos disponibles"""
    return jsonify(get_available_ports())

@app.route('/api/connect', methods=['POST'])
def api_connect():
    """Conectar a un Arduino"""
    data = request.json
    port = data.get('port')
    name = data.get('name', f'Arduino-{len(arduino_connections)+1}')
    
    if not port:
        return jsonify({'success': False, 'error': 'Puerto no especificado'})
    
    if port in arduino_connections:
        return jsonify({'success': False, 'error': 'Puerto ya conectado'})
    
    monitor = ArduinoMonitor(port, name)
    if monitor.connect():
        arduino_connections[port] = monitor
        stats['start_time'] = datetime.now()
        return jsonify({'success': True, 'name': name})
    
    return jsonify({'success': False, 'error': 'No se pudo conectar'})

@app.route('/api/disconnect', methods=['POST'])
def api_disconnect():
    """Desconectar un Arduino"""
    data = request.json
    port = data.get('port')
    
    if port in arduino_connections:
        arduino_connections[port].disconnect()
        del arduino_connections[port]
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Puerto no conectado'})

@app.route('/api/disconnect_all', methods=['POST'])
def api_disconnect_all():
    """Desconectar todos los Arduinos"""
    for monitor in list(arduino_connections.values()):
        monitor.disconnect()
    arduino_connections.clear()
    return jsonify({'success': True})

@app.route('/api/send', methods=['POST'])
def api_send():
    """Enviar comando a un Arduino específico"""
    data = request.json
    port = data.get('port')
    command = data.get('command')
    
    if not port or not command:
        return jsonify({'success': False, 'error': 'Faltan parámetros'})
    
    if port not in arduino_connections:
        return jsonify({'success': False, 'error': 'Puerto no conectado'})
    
    success = arduino_connections[port].send_command(command)
    return jsonify({'success': success})

@app.route('/api/send_all', methods=['POST'])
def api_send_all():
    """Enviar comando a todos los Arduinos"""
    data = request.json
    command = data.get('command')
    
    if not command:
        return jsonify({'success': False, 'error': 'Comando vacío'})
    
    results = {}
    for port, monitor in arduino_connections.items():
        results[port] = monitor.send_command(command)
    
    return jsonify({'success': all(results.values()), 'results': results})

@app.route('/api/status')
def api_status():
    """Estado del sistema"""
    uptime = None
    if stats['start_time']:
        delta = datetime.now() - stats['start_time']
        uptime = str(delta).split('.')[0]
    
    return jsonify({
        'connected_devices': len(arduino_connections),
        'devices': [{'port': port, 'name': m.name} for port, m in arduino_connections.items()],
        'stats': {
            'total_commands': stats['total_commands'],
            'total_words': stats['total_words'],
            'errors': stats['errors'],
            'uptime': uptime
        },
        'current_word': current_word
    })

@app.route('/api/logs')
def api_logs():
    """Obtener logs recientes"""
    logs = []
    temp_queue = queue.Queue()
    
    while not log_queue.empty():
        try:
            log = log_queue.get_nowait()
            logs.append(log)
            temp_queue.put(log)
        except queue.Empty:
            break
    
    while not temp_queue.empty():
        try:
            log_queue.put_nowait(temp_queue.get_nowait())
        except (queue.Full, queue.Empty):
            break
    
    return jsonify(logs)

@app.route('/api/words')
def api_words():
    """Obtener palabras procesadas"""
    return jsonify({
        'current': current_word,
        'history': processed_words[-50:]  # Últimas 50 palabras
    })

@app.route('/api/clear_logs', methods=['POST'])
def api_clear_logs():
    """Limpiar logs"""
    global log_queue
    log_queue = queue.Queue(maxsize=200)
    return jsonify({'success': True})

@app.route('/api/clear_words', methods=['POST'])
def api_clear_words():
    """Limpiar historial de palabras"""
    global processed_words, current_word
    processed_words = []
    current_word = ""
    return jsonify({'success': True})

@app.route('/api/test/char', methods=['POST'])
def api_test_char():
    """Enviar carácter de prueba"""
    data = request.json
    port = data.get('port')
    module = data.get('module', 0)
    char = data.get('char', 'a')
    
    if port not in arduino_connections:
        return jsonify({'success': False, 'error': 'Puerto no conectado'})
    
    command = f"WRITE_MODULE:{module}:{char}"
    success = arduino_connections[port].send_command(command)
    return jsonify({'success': success})

@app.route('/api/test/modules', methods=['POST'])
def api_test_modules():
    """Probar todos los módulos de un Arduino"""
    data = request.json
    port = data.get('port')
    
    if port not in arduino_connections:
        return jsonify({'success': False, 'error': 'Puerto no conectado'})
    
    success = arduino_connections[port].send_command('TEST')
    return jsonify({'success': success})

@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reset de todos los solenoides de un Arduino"""
    data = request.json
    port = data.get('port')
    
    if port not in arduino_connections:
        return jsonify({'success': False, 'error': 'Puerto no conectado'})
    
    success = arduino_connections[port].send_command('RESET')
    return jsonify({'success': success})

@socketio.on('connect')
def handle_connect():
    """Cliente WebSocket conectado"""
    emit('connection_status', {
        'connected': len(arduino_connections) > 0,
        'devices': [{'port': p, 'name': m.name} for p, m in arduino_connections.items()]
    })

@socketio.on('request_update')
def handle_request_update():
    """Cliente solicita actualización de estado"""
    emit('status_update', {
        'stats': stats,
        'current_word': current_word,
        'connected_devices': len(arduino_connections)
    })

if __name__ == '__main__':
    print("=" * 70)
    print("  SISTEMA DE DEBUG BRAILLE - Interfaz Web")
    print("=" * 70)
    print(f"\n[INFO] Servidor iniciado en: http://localhost:5000")
    print(f"[INFO] También accesible desde red en: http://{os.popen('hostname -I').read().strip().split()[0] if os.name != 'nt' else 'IP-LOCAL'}:5000")
    print("\n[INFO] Puertos disponibles:")
    for port_info in get_available_ports():
        print(f"   • {port_info['port']}: {port_info['description']}")
    print("\n[INFO] Presiona Ctrl+C para detener el servidor")
    print("=" * 70 + "\n")
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n\n[INFO] Cerrando servidor...")
        for monitor in arduino_connections.values():
            monitor.disconnect()
        print("[OK] Servidor cerrado correctamente")
