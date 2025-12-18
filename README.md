# Sistema Multi-Arduino de Voz y PDF a Braille

Sistema completo para convertir voz y PDFs a escritura Braille usando 3 Arduinos y Raspberry Pi.

**⚡ LIMITACIÓN ENERGÉTICA: Solo 1 módulo activo a la vez (2 segundos por carácter)**

## 📋 Componentes

### Hardware
- **3 Arduinos** (Uno, Mega, Nano, etc.)
- **12 Solenoides** totales (6 por cada 2 Arduinos = 2 módulos Braille por Arduino)
- **Raspberry Pi** (cualquier modelo con 3+ puertos USB)
- **Micrófono USB** o micrófono incorporado
- **Fuente de alimentación suficiente** para los solenoides

### Software
- `braille.ino` - Código Arduino para 2 módulos de solenoides (12 solenoides)
- `multi_arduino_controller.py` - Controlador para 3 Arduinos con gestión secuencial
- `voice_to_braille.py` - Sistema de reconocimiento de voz con Vosk
- `pdf_to_braille.py` - Lector de PDFs con OCR
- `main.py` - Controlador legacy para un solo Arduino
- Modelo Vosk: `vosk-model-small-es-0.42`
- Tesseract OCR con datos en español

## ⚡ Limitación Energética Importante

**Solo se puede activar 1 módulo (6 solenoides) a la vez debido a restricciones de alimentación.**

- Cada carácter permanece visible durante **2 segundos**
- Los módulos se activan **secuencialmente**
- Tiempo total = número de caracteres × 2 segundos
- Ejemplo: "HOLA" = 4 caracteres × 2s = 8 segundos

## 🚀 Instalación

### 1. Arduino (x3)

```bash
# Cargar braille.ino a cada uno de los 3 Arduinos usando Arduino IDE
# Cada Arduino controla 2 módulos (12 solenoides)
```

**Conexiones por Arduino:**

**Módulo 1:**
- Pin 2 → Solenoide M1-1 (punto Braille 1)
- Pin 3 → Solenoide M1-2 (punto Braille 2)
- Pin 4 → Solenoide M1-3 (punto Braille 3)
- Pin 5 → Solenoide M1-4 (punto Braille 4)
- Pin 6 → Solenoide M1-5 (punto Braille 5)
- Pin 7 → Solenoide M1-6 (punto Braille 6)

**Módulo 2:**
- Pin 8 → Solenoide M2-1 (punto Braille 1)
- Pin 9 → Solenoide M2-2 (punto Braille 2)
- Pin 10 → Solenoide M2-3 (punto Braille 3)
- Pin 11 → Solenoide M2-4 (punto Braille 4)
- Pin 12 → Solenoide M2-5 (punto Braille 5)
- Pin 13 → Solenoide M2-6 (punto Braille 6)

**Nota:** Repetir estas conexiones en los 3 Arduinos

### 2. Raspberry Pi

```bash
# Actualizar sistema
sudo apt-get update
sudo apt-get upgrade

# Instalar dependencias del sistema
sudo apt-get install python3-pip python3-pyaudio portaudio19-dev

# Instalar Tesseract OCR y datos en español
sudo apt-get install tesseract-ocr tesseract-ocr-spa

# Instalar poppler-utils para pdf2image
sudo apt-get install poppler-utils

# Instalar dependencias Python
pip3 install -r requirements.txt

# Descargar modelo Vosk español
wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
unzip vosk-model-small-es-0.42.zip
```

### 3. Verificar puertos Arduino

```bash
# Listar puertos USB
ls /dev/tty*

# Típicamente serán /dev/ttyACM0, /dev/ttyACM1, /dev/ttyACM2
# O /dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyUSB2
```

## 📖 Uso

### Modo 1: Sistema completo con voz (Multi-Arduino)

```bash
python3 voice_to_braille.py
```

**Opciones del menú:**
1. **Escucha continua** - Reconoce voz y escribe en Braille automáticamente
2. **Escuchar una frase** - Captura una sola frase
3. **Test de micrófono** - Prueba reconocimiento sin escribir
4. **Listar micrófonos** - Muestra dispositivos disponibles
5. **Test de solenoides** - Prueba todos los módulos
6. **Escribir texto manual** - Escribe texto sin usar voz
7. **Información del sistema** - Estado de Arduinos
8. **Salir**

**Nota:** Cada carácter permanece visible 2 segundos para lectura táctil.

### Modo 2: Lectura de PDFs

```bash
python3 pdf_to_braille.py
```

**Opciones del menú:**
1. **Procesar PDF (modo automático)** - Detecta si es texto o imagen
2. **Procesar PDF (modo texto directo)** - Para PDFs con texto seleccionable
3. **Procesar PDF (modo OCR)** - Para PDFs escaneados o imágenes
4. **Vista previa de PDF** - Muestra primeros 300 caracteres
5. **Test de Arduinos** - Prueba todos los módulos
6. **Información del sistema** - Estado de Arduinos
7. **Salir**

**Características PDF:**
- ✅ Lectura directa de texto PDF
- ✅ OCR para PDFs escaneados (Tesseract)
- ✅ Selección de rango de páginas
- ✅ Vista previa antes de procesar
- ✅ Estimación de tiempo (2s por carácter)
- ✅ Limpieza automática de texto

**⚠️ Importante:** PDFs largos requieren mucho tiempo de procesamiento.

### Modo 3: Control directo Multi-Arduino

```bash
python3 multi_arduino_controller.py
```

**Opciones:**
1. Escribir texto (6 módulos disponibles)
2. Test de todos los módulos
3. Verificar estados
4. Resetear todos
5. Mostrar información del sistema
6. Salir

**Nota:** Solo 1 módulo activo a la vez (2s por carácter)

### Modo 4: Solo control Braille simple (legacy - 1 Arduino)

```bash
# Modo interactivo
python3 main.py

# Modo directo
python3 main.py /dev/ttyACM0 --text "hola mundo"
```

## 🎤 Configuración del micrófono

### Verificar micrófono en Raspberry Pi

```bash
# Listar dispositivos de audio
arecord -l

# Probar grabación (5 segundos)
arecord -d 5 test.wav

# Reproducir
aplay test.wav
```

### Ajustar volumen

```bash
# Abrir mezclador de audio
alsamixer

# O usar comandos
amixer set Capture 80%
```

## 🔧 Protocolo de comunicación Arduino-Raspberry

### Comandos enviados al Arduino:
- `WRITE_MODULE:modulo_id:caracter` - Escribe carácter en módulo específico (0 o 1)
- `WRITE:texto` - Convierte texto a Braille (legacy, usa módulo 0)
- `TEST` - Prueba todos los solenoides de ambos módulos
- `STATUS` - Verifica estado del sistema
- `RESET` - Apaga todos los solenoides
- `PATTERN:n` - Escribe patrón binario (0-63) en módulo 0

### Respuestas del Arduino:
- `READY` - Sistema listo
- `START` - Iniciando escritura
- `DONE` - Escritura completada
- `OK` - Comando ejecutado
- `ERROR:mensaje` - Error con descripción
- `WARN:mensaje` - Advertencia

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────┐
│   Raspberry Pi      │
│                     │
│  ┌──────────────┐   │
│  │ Vosk ASR     │   │  Reconocimiento de voz
│  │ (español)    │   │
│  └──────┬───────┘   │
│         │           │
│  ┌──────▼───────┐   │
│  │ PDF Reader   │   │  Lectura de PDFs
│  │ + OCR        │   │
│  └──────┬───────┘   │
│         │           │
│  ┌──────▼───────────┐
│  │ Multi-Arduino    │  Control secuencial
│  │ Controller       │  (1 módulo a la vez)
│  └──┬───┬───┬───────┘
│     │   │   │       │
└─────┼───┼───┼───────┘
      │   │   │
   USB│USB│USB│
      ▼   ▼   ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ Arduino 1  │  │ Arduino 2  │  │ Arduino 3  │
   │            │  │            │  │            │
   │ 2 módulos  │  │ 2 módulos  │  │ 2 módulos  │
   │ (12 pines) │  │ (12 pines) │  │ (12 pines) │
   └─┬────────┬─┘  └─┬────────┬─┘  └─┬────────┬─┘
     │        │      │        │      │        │
   ┌─▼─┐    ┌─▼─┐  ┌─▼─┐    ┌─▼─┐  ┌─▼─┐    ┌─▼─┐
   │M1 │    │M2 │  │M1 │    │M2 │  │M1 │    │M2 │
   │(6)│    │(6)│  │(6)│    │(6)│  │(6)│    │(6)│
   └───┘    └───┘  └───┘    └───┘  └───┘    └───┘
   
   ⚡ SECUENCIAL: Solo 1 módulo activo a la vez (2s cada uno)
```

## 🐛 Solución de problemas

### Arduinos no conectan
```bash
# Verificar puertos
ls -l /dev/ttyACM*

# Dar permisos
sudo chmod 666 /dev/ttyACM0
sudo chmod 666 /dev/ttyACM1
sudo chmod 666 /dev/ttyACM2

# O añadir usuario al grupo dialout (permanente)
sudo usermod -a -G dialout $USER
# Luego reiniciar sesión
```

### Solo conectan algunos Arduinos
- El sistema puede funcionar con 1, 2 o 3 Arduinos
- Caracteres simultáneos = Arduinos conectados × 2
- Verifica las conexiones USB
- Usa un hub USB con alimentación si es necesario

### Micrófono no funciona
```bash
# Verificar que está conectado
arecord -l

# Probar con otro ID de dispositivo
# En voice_to_braille.py usar opción 6 para listar
```

### Modelo Vosk no encontrado
```bash
# Verificar que está descomprimido correctamente
ls -la vosk-model-small-es-0.42/

# Debe contener archivos como:
# - am/
# - conf/
# - graph/
# - ivector/
```

### Tesseract OCR no funciona
```bash
# Verificar instalación
tesseract --version

# Verificar idioma español
tesseract --list-langs
# Debe aparecer 'spa'

# Si falta, instalar:
sudo apt-get install tesseract-ocr-spa
```

### PDF no se procesa (OCR)
```bash
# Verificar poppler-utils
which pdftoppm

# Si no está instalado:
sudo apt-get install poppler-utils
```

### Error de permisos en Raspberry Pi
```bash
# Ejecutar con permisos necesarios
sudo python3 voice_to_braille.py
sudo python3 pdf_to_braille.py
```

## 📊 Características del sistema

✅ Reconocimiento de voz en español
✅ Conversión automática a Braille
✅ **Sistema secuencial con tiempo de lectura**
✅ **6 módulos disponibles (rotación automática)**
✅ **2 segundos por carácter (lectura táctil)**
✅ **Lectura de PDFs con texto directo**
✅ **OCR para PDFs escaneados (Tesseract)**
✅ Soporte para letras a-z
✅ Modo de escucha continua
✅ Test de hardware integrado
✅ Comunicación serial robusta
✅ Manejo de errores completo
✅ Interfaz de menú intuitiva
✅ Control de 3 Arduinos simultáneos
✅ Selección de páginas PDF
✅ Vista previa de PDFs
✅ Estimación de tiempo de procesamiento

## 🎯 Mejoras futuras

- [ ] Soporte para números y puntuación
- [ ] Mayúsculas y caracteres especiales
- [ ] Control de velocidad ajustable por módulo
- [ ] Guardado de historial
- [ ] Interfaz web
- [ ] Soporte para otros idiomas
- [ ] Feedback táctil adicional
- [ ] Procesamiento de imágenes directas (sin PDF)
- [ ] Modo braille grado 2 (abreviado)
- [ ] Cache de OCR para PDFs procesados

## 📝 Notas técnicas

### Patrón Braille
```
1 • • 4
2 • • 5
3 • • 6
```

Los bytes representan los puntos activos (bit 1 = punto activo)

### Ejemplo: letra "a"
```
Binario: 000001
Puntos: solo punto 1
```

### Ejemplo: letra "w"
```
Binario: 111010
Puntos: 2, 4, 5, 6
```

## 📄 Licencia

Proyecto educativo para tesis universitaria.

## 👥 Soporte

Para dudas o problemas, revisar la documentación de:
- [Vosk API](https://alphacephei.com/vosk/)
- [Arduino Reference](https://www.arduino.cc/reference/)
- [PySerial Documentation](https://pyserial.readthedocs.io/)
