# Aplicación de Debug para Sistema Braille

## Descripción

Aplicación web Flask para debugging y monitoreo en tiempo real del sistema Braille. Permite visualizar comandos enviados al Arduino, palabras procesadas y estadísticas del sistema.

## Características

- **Monitoreo en Tiempo Real**: WebSocket para actualizaciones instantáneas
- **Multi-Arduino**: Conecta y monitorea múltiples Arduinos simultáneamente
- **Visualización de Palabras**: Muestra la palabra actual siendo procesada en grande
- **Historial de Palabras**: Registro de todas las palabras procesadas con timestamps
- **Console Log**: Logs detallados de todos los comandos (SENT/RECV/ERROR/INFO)
- **Controles de Prueba**: Enviar caracteres de prueba a módulos específicos
- **Estadísticas**: Comandos enviados, palabras procesadas, errores, tiempo activo
- **Interfaz Responsive**: Diseño adaptable para diferentes dispositivos

## Requisitos

```bash
pip install flask flask-socketio pyserial
```

O instalar desde requirements.txt:

```bash
pip install -r requirements.txt
```

## Uso

### 1. Iniciar la aplicación en Raspberry Pi

```bash
python3 debug_app.py
```

### 2. Acceder a la interfaz web

Desde el mismo Raspberry Pi:
```
http://localhost:5000
```

Desde otro dispositivo en la red:
```
http://[IP-DEL-RASPBERRY]:5000
```

### 3. Conectar Arduinos

1. La aplicación detectará automáticamente los puertos disponibles
2. Selecciona un puerto del dropdown
3. Asigna un nombre al dispositivo (opcional)
4. Haz clic en "Conectar"

### 4. Monitorear el sistema

- **Panel de Logs**: Muestra todos los mensajes en tiempo real
- **Palabras Procesadas**: Historial de palabras completadas
- **Palabra Actual**: Visualización grande de la palabra en proceso
- **Estadísticas**: Métricas del sistema actualizadas cada 2 segundos

### 5. Controles de Prueba

Para cada Arduino conectado puedes:
- Enviar carácter a módulo específico (0-1)
- Ejecutar comando personalizado
- Test de todos los módulos
- Reset de solenoides

## Comandos Disponibles

### Comandos Estándar del Arduino

```
WRITE_MODULE:0:a    - Escribir 'a' en módulo 0
WRITE_MODULE:1:z    - Escribir 'z' en módulo 1
TEST                - Probar todos los módulos
RESET               - Apagar todos los solenoides
STATUS              - Verificar estado del Arduino
```

### API REST

- `GET /api/ports` - Listar puertos disponibles
- `POST /api/connect` - Conectar a Arduino
- `POST /api/disconnect` - Desconectar Arduino
- `POST /api/send` - Enviar comando
- `GET /api/status` - Estado del sistema
- `GET /api/logs` - Obtener logs
- `GET /api/words` - Obtener palabras procesadas

## Interfaz

### Secciones Principales

1. **Header con Estadísticas**
   - Dispositivos conectados
   - Comandos enviados
   - Palabras procesadas
   - Errores
   - Tiempo activo

2. **Panel de Conexiones**
   - Gestión de múltiples Arduinos
   - Información de cada dispositivo
   - Controles individuales

3. **Palabra Actual (Grande)**
   - Visualización destacada de la palabra en proceso
   - Actualización en tiempo real

4. **Console Log**
   - Logs con código de colores:
     - INFO (Verde)
     - ERROR (Rojo)
     - SENT (Azul)
     - RECV (Naranja)

5. **Historial de Palabras**
   - Lista de palabras completadas
   - Timestamp de cada palabra

6. **Controles de Prueba**
   - Envío de caracteres individuales
   - Comandos personalizados por Arduino

## Seguridad

Para uso en producción considera:

1. Agregar autenticación:
```python
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()
```

2. Configurar HTTPS
3. Limitar acceso por IP
4. Usar contraseñas para WebSocket

## Debugging

### Puertos no detectados

```bash
# Listar puertos en Linux
ls /dev/tty*

# Dar permisos
sudo chmod 666 /dev/ttyACM0
```

### Error de conexión WebSocket

Verificar firewall:
```bash
sudo ufw allow 5000
```

### Ver logs del servidor

La aplicación muestra logs en la terminal donde se ejecuta.

## Acceso Remoto

Para acceder desde cualquier dispositivo en la red local:

1. Obtener IP del Raspberry:
```bash
hostname -I
```

2. Acceder desde navegador:
```
http://192.168.X.X:5000
```

## Configuración Avanzada

### Cambiar puerto del servidor

```python
socketio.run(app, host='0.0.0.0', port=8080)
```

### Ajustar tamaño del log

```python
log_queue = queue.Queue(maxsize=500)  # Más logs
```

### Modificar frecuencia de actualización

En debug.html:
```javascript
setInterval(loadStatus, 5000);  // Cada 5 segundos
```

## Integración con Sistema Principal

La aplicación de debug puede correr en paralelo con el sistema principal:

```bash
# Terminal 1: Sistema principal
python3 main.py

# Terminal 2: Debug web
python3 debug_app.py
```

Ambos pueden conectarse a los mismos Arduinos si se configuran correctamente.

## Notas

- Los logs se mantienen en memoria (máximo 200 entradas)
- Las palabras procesadas se mantienen en memoria (últimas 50)
- Al reiniciar la aplicación se pierden logs y historial
- Los WebSocket permiten actualizaciones sin recargar la página

## Soporte

Para problemas o mejoras, consultar la documentación del sistema principal en README.md.
