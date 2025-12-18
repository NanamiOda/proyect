#!/bin/bash
# Script de instalación automática para Raspberry Pi
# Sistema Multi-Arduino de Voz y PDF a Braille

echo "======================================================================"
echo "INSTALACIÓN: Sistema Multi-Arduino de Voz y PDF a Braille"
echo "======================================================================"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Verificar si se ejecuta como root
if [ "$EUID" -eq 0 ]; then 
    print_warning "No ejecutes este script como root. Usará sudo cuando sea necesario."
    exit 1
fi

echo "Paso 1/6: Actualizando sistema..."
echo "----------------------------------------------------------------------"
sudo apt-get update -qq
if [ $? -eq 0 ]; then
    print_success "Sistema actualizado"
else
    print_error "Error al actualizar. Continuando..."
fi
echo ""

echo "Paso 2/6: Instalando dependencias del sistema..."
echo "----------------------------------------------------------------------"
PACKAGES="python3-pip python3-pyaudio portaudio19-dev tesseract-ocr tesseract-ocr-spa poppler-utils"
print_info "Paquetes a instalar: $PACKAGES"
sudo apt-get install -y $PACKAGES

if [ $? -eq 0 ]; then
    print_success "Dependencias del sistema instaladas"
else
    print_error "Error al instalar dependencias del sistema"
    exit 1
fi
echo ""

echo "Paso 3/6: Instalando dependencias Python..."
echo "----------------------------------------------------------------------"
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --user
    if [ $? -eq 0 ]; then
        print_success "Dependencias Python instaladas"
    else
        print_error "Error al instalar dependencias Python"
        exit 1
    fi
else
    print_error "No se encontró requirements.txt"
    exit 1
fi
echo ""

echo "Paso 4/6: Descargando modelo Vosk español..."
echo "----------------------------------------------------------------------"
if [ -d "vosk-model-small-es-0.42" ]; then
    print_warning "Modelo ya existe. Omitiendo descarga."
else
    print_info "Descargando modelo (puede tardar varios minutos)..."
    wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
    
    if [ $? -eq 0 ]; then
        print_info "Descomprimiendo modelo..."
        unzip -q vosk-model-small-es-0.42.zip
        
        if [ $? -eq 0 ]; then
            print_success "Modelo Vosk instalado"
            rm vosk-model-small-es-0.42.zip
        else
            print_error "Error al descomprimir modelo"
            exit 1
        fi
    else
        print_error "Error al descargar modelo"
        exit 1
    fi
fi
echo ""

echo "Paso 5/6: Configurando permisos USB..."
echo "----------------------------------------------------------------------"
print_info "Añadiendo usuario al grupo 'dialout'..."
sudo usermod -a -G dialout $USER

if [ $? -eq 0 ]; then
    print_success "Usuario añadido al grupo dialout"
    print_warning "IMPORTANTE: Debes cerrar sesión y volver a entrar para que los cambios surtan efecto"
else
    print_warning "No se pudo añadir al grupo dialout. Puede que necesites permisos sudo."
fi

# Dar permisos a puertos USB actuales
print_info "Dando permisos a puertos USB existentes..."
for port in /dev/ttyACM* /dev/ttyUSB*; do
    if [ -e "$port" ]; then
        sudo chmod 666 "$port" 2>/dev/null
        print_success "Permisos configurados para $port"
    fi
done
echo ""

echo "Paso 6/6: Verificando instalación..."
echo "----------------------------------------------------------------------"

# Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    print_success "Python: $PYTHON_VERSION"
else
    print_error "Python3 no encontrado"
fi

# Verificar Tesseract
if command -v tesseract &> /dev/null; then
    TESSERACT_VERSION=$(tesseract --version 2>&1 | head -n 1)
    print_success "Tesseract: $TESSERACT_VERSION"
    
    # Verificar idioma español
    if tesseract --list-langs 2>&1 | grep -q "spa"; then
        print_success "Tesseract: Idioma español instalado"
    else
        print_error "Tesseract: Idioma español NO instalado"
    fi
else
    print_error "Tesseract no encontrado"
fi

# Verificar modelo Vosk
if [ -d "vosk-model-small-es-0.42" ]; then
    print_success "Modelo Vosk español presente"
else
    print_error "Modelo Vosk NO encontrado"
fi

# Verificar archivos Python
PYTHON_FILES=("multi_arduino_controller.py" "voice_to_braille.py" "pdf_to_braille.py" "main.py")
for file in "${PYTHON_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "Script: $file"
    else
        print_error "Script NO encontrado: $file"
    fi
done

# Verificar Arduino
echo ""
print_info "Detectando Arduinos..."
ARDUINO_COUNT=0
for port in /dev/ttyACM* /dev/ttyUSB*; do
    if [ -e "$port" ]; then
        print_success "Arduino detectado en: $port"
        ((ARDUINO_COUNT++))
    fi
done

if [ $ARDUINO_COUNT -eq 0 ]; then
    print_warning "No se detectaron Arduinos. Conéctalos y vuelve a verificar."
elif [ $ARDUINO_COUNT -lt 3 ]; then
    print_warning "Se detectaron $ARDUINO_COUNT Arduinos. Se recomiendan 3 para máximo rendimiento."
else
    print_success "Se detectaron $ARDUINO_COUNT Arduinos"
fi

echo ""
echo "======================================================================"
echo "INSTALACIÓN COMPLETADA"
echo "======================================================================"
echo ""
print_success "Sistema instalado correctamente"
echo ""
echo "📝 Próximos pasos:"
echo ""
echo "1. Cargar braille.ino en cada Arduino usando Arduino IDE"
echo "2. Conectar los 3 Arduinos al Raspberry Pi"
echo "3. Cerrar sesión y volver a entrar (para permisos USB)"
echo ""
echo "🚀 Para ejecutar el sistema:"
echo ""
echo "   Voz a Braille:     python3 voice_to_braille.py"
echo "   PDF a Braille:     python3 pdf_to_braille.py"
echo "   Control directo:   python3 multi_arduino_controller.py"
echo ""
echo "📖 Para más información, consulta el README.md"
echo ""
