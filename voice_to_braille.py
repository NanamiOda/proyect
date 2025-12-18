#!/usr/bin/env python3
"""
Sistema de reconocimiento de voz a Braille usando Vosk
Captura audio del micrófono y lo convierte a escritura Braille
"""

import os
import sys
import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from multi_arduino_controller import MultiArduinoBrailleController


class VoiceToBraille:
    def __init__(self, modelo_path="vosk-model-small-es-0.42", sample_rate=16000):
        """
        Inicializa el sistema de reconocimiento de voz
        
        Args:
            modelo_path: Ruta al modelo Vosk español
            sample_rate: Frecuencia de muestreo de audio (Hz)
        """
        self.modelo_path = modelo_path
        self.sample_rate = sample_rate
        self.modelo = None
        self.recognizer = None
        self.audio_queue = queue.Queue()
        self.escuchando = False
        
    def cargar_modelo(self):
        """Carga el modelo Vosk"""
        print("Cargando modelo de reconocimiento de voz...")
        
        if not os.path.exists(self.modelo_path):
            print(f"✗ Error: No se encontró el modelo en '{self.modelo_path}'")
            print("\nPara descargar el modelo:")
            print("1. Visita: https://alphacephei.com/vosk/models")
            print("2. Descarga: vosk-model-small-es-0.42")
            print("3. Descomprime en este directorio")
            return False
        
        try:
            self.modelo = Model(self.modelo_path)
            self.recognizer = KaldiRecognizer(self.modelo, self.sample_rate)
            self.recognizer.SetWords(True)
            print(f"✓ Modelo cargado exitosamente desde {self.modelo_path}")
            return True
        except Exception as e:
            print(f"✗ Error al cargar modelo: {e}")
            return False
    
    def audio_callback(self, indata, frames, time, status):
        """Callback para captura de audio en tiempo real"""
        if status:
            print(f"Estado audio: {status}", file=sys.stderr)
        self.audio_queue.put(bytes(indata))
    
    def listar_microfonos(self):
        """Lista los dispositivos de audio disponibles"""
        print("\n" + "="*60)
        print("DISPOSITIVOS DE AUDIO DISPONIBLES")
        print("="*60)
        dispositivos = sd.query_devices()
        
        for i, device in enumerate(dispositivos):
            if device['max_input_channels'] > 0:
                print(f"{i}: {device['name']}")
                print(f"   Canales entrada: {device['max_input_channels']}")
                print(f"   Sample rate: {device['default_samplerate']} Hz")
                print()
        print("="*60 + "\n")
    
    def escuchar_continuo(self, controlador_braille, device=None):
        """
        Modo de escucha continua - reconoce voz y envía a Braille en tiempo real
        
        Args:
            controlador_braille: Instancia de MultiArduinoBrailleController
            device: ID del dispositivo de audio (None para default)
        """
        if not self.recognizer:
            print("✗ Error: Modelo no cargado")
            return
        
        print("\n" + "="*60)
        print("MODO ESCUCHA CONTINUA")
        print("="*60)
        print("🎤 Escuchando... Habla ahora")
        print("Presiona Ctrl+C para detener")
        print("="*60 + "\n")
        
        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                device=device,
                dtype='int16',
                channels=1,
                callback=self.audio_callback
            ):
                self.escuchando = True
                
                while self.escuchando:
                    data = self.audio_queue.get()
                    
                    if self.recognizer.AcceptWaveform(data):
                        # Resultado completo (frase terminada)
                        resultado = json.loads(self.recognizer.Result())
                        texto = resultado.get('text', '')
                        
                        if texto:
                            print(f"\n🗣️  Reconocido: '{texto}'")
                            print("📝 Escribiendo en Braille (2s por carácter)...")
                            controlador_braille.escribir_texto_paralelo(texto)
                            print()
                    else:
                        # Resultado parcial (mientras habla)
                        resultado_parcial = json.loads(self.recognizer.PartialResult())
                        texto_parcial = resultado_parcial.get('partial', '')
                        if texto_parcial:
                            print(f"\r💬 {texto_parcial}", end='', flush=True)
        
        except KeyboardInterrupt:
            print("\n\n✓ Escucha detenida")
        except Exception as e:
            print(f"\n✗ Error durante la escucha: {e}")
        finally:
            self.escuchando = False
    
    def escuchar_una_frase(self, controlador_braille, device=None, timeout=10):
        """
        Escucha una sola frase y la convierte a Braille
        
        Args:
            controlador_braille: Instancia de MultiArduinoBrailleController
            device: ID del dispositivo de audio
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            Texto reconocido o None
        """
        if not self.recognizer:
            print("✗ Error: Modelo no cargado")
            return None
        
        print("🎤 Escuchando... (habla ahora)")
        
        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                device=device,
                dtype='int16',
                channels=1,
                callback=self.audio_callback
            ):
                inicio = sd.get_stream_time()
                texto_final = None
                
                while (sd.get_stream_time() - inicio) < timeout:
                    try:
                        data = self.audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    
                    if self.recognizer.AcceptWaveform(data):
                        resultado = json.loads(self.recognizer.Result())
                        texto = resultado.get('text', '')
                        
                        if texto:
                            texto_final = texto
                            break
                    else:
                        resultado_parcial = json.loads(self.recognizer.PartialResult())
                        texto_parcial = resultado_parcial.get('partial', '')
                        if texto_parcial:
                            print(f"\r💬 {texto_parcial}", end='', flush=True)
                
                if texto_final:
                    print(f"\n\n🗣️  Reconocido: '{texto_final}'")
                    print("📝 Escribiendo en Braille (2s por carácter)...")
                    controlador_braille.escribir_texto_paralelo(texto_final)
                    return texto_final
                else:
                    print("\n⚠️  No se detectó voz clara")
                    return None
                    
        except Exception as e:
            print(f"\n✗ Error durante la escucha: {e}")
            return None
    
    def test_microfono(self, device=None, duracion=5):
        """
        Prueba el micrófono sin escribir a Braille
        
        Args:
            device: ID del dispositivo de audio
            duracion: Duración de la prueba en segundos
        """
        if not self.recognizer:
            print("✗ Error: Modelo no cargado")
            return
        
        print(f"\n🎤 Probando micrófono durante {duracion} segundos...")
        print("Habla algo para probar el reconocimiento\n")
        
        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                device=device,
                dtype='int16',
                channels=1,
                callback=self.audio_callback
            ):
                import time
                inicio = time.time()
                
                while (time.time() - inicio) < duracion:
                    try:
                        data = self.audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    
                    if self.recognizer.AcceptWaveform(data):
                        resultado = json.loads(self.recognizer.Result())
                        texto = resultado.get('text', '')
                        if texto:
                            print(f"✓ Reconocido: '{texto}'")
                    else:
                        resultado_parcial = json.loads(self.recognizer.PartialResult())
                        texto_parcial = resultado_parcial.get('partial', '')
                        if texto_parcial:
                            print(f"\r💬 {texto_parcial}", end='', flush=True)
                
                print("\n\n✓ Test completado")
                
        except Exception as e:
            print(f"\n✗ Error durante el test: {e}")


def menu_principal():
    """Menú principal del sistema"""
    print("\n" + "="*60)
    print("SISTEMA VOZ A BRAILLE - Vosk + Multi-Arduino")
    print("="*60)
    
    # Configurar puertos Arduino
    print("\nConfiguración de Arduinos:")
    puertos = []
    for i in range(3):
        default = f'/dev/ttyACM{i}'
        puerto = input(f"Puerto Arduino {i+1} [{default}]: ").strip()
        puertos.append(puerto if puerto else default)
    
    # Crear y conectar controlador Braille
    print("\n1. Conectando con Arduinos...")
    controlador = MultiArduinoBrailleController(puertos=puertos)
    if not controlador.conectar_todos():
        print("\n⚠️  No todos los Arduinos conectaron")
        continuar = input("¿Continuar de todos modos? (s/n): ").strip().lower()
        if continuar != 's':
            return
    
    # Verificar estados
    if not controlador.verificar_estados():
        print("⚠️  Algunos Arduinos no responden correctamente")
    
    # Configurar sistema de voz
    print("\n2. Inicializando reconocimiento de voz...")
    modelo_path = input("Ruta del modelo Vosk [vosk-model-small-es-0.42]: ").strip()
    if not modelo_path:
        modelo_path = "vosk-model-small-es-0.42"
    
    voz = VoiceToBraille(modelo_path=modelo_path)
    if not voz.cargar_modelo():
        controlador.desconectar()
        return
    
    print("\n✓ Sistema inicializado correctamente\n")
    
    # Menú de opciones
    while True:
        print("\n" + "="*60)
        print("MENÚ PRINCIPAL")
        print("="*60)
        print("1. Escucha continua")
        print("2. Escuchar una frase")
        print("3. Test de micrófono")
        print("4. Listar micrófonos disponibles")
        print("5. Test de solenoides")
        print("6. Escribir texto manual")
        print("7. Información del sistema")
        print("8. Salir")
        print("="*60)
        print("ℹ️  Limitación energética: 2 segundos por carácter")
        print("="*60)
        
        opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == "1":
            device_input = input("ID del micrófono (Enter para default): ").strip()
            device = int(device_input) if device_input else None
            voz.escuchar_continuo(controlador, device=device)
            
        elif opcion == "2":
            device_input = input("ID del micrófono (Enter para default): ").strip()
            device = int(device_input) if device_input else None
            voz.escuchar_una_frase(controlador, device=device)
            
        elif opcion == "3":
            device_input = input("ID del micrófono (Enter para default): ").strip()
            device = int(device_input) if device_input else None
            duracion = input("Duración del test en segundos [5]: ").strip()
            duracion = int(duracion) if duracion else 5
            voz.test_microfono(device=device, duracion=duracion)
            
        elif opcion == "4":
            voz.listar_microfonos()
            
        elif opcion == "5":
            controlador.test_todos_los_modulos()
            
        elif opcion == "6":
            texto = input("Ingresa el texto: ")
            controlador.escribir_texto_paralelo(texto)
            
        elif opcion == "7":
            info = controlador.get_info()
            print("\n📊 Información del sistema:")
            for key, value in info.items():
                print(f"   • {key}: {value}")
            
        elif opcion == "8":
            print("\n✓ Saliendo del sistema...")
            break
            
        else:
            print("✗ Opción inválida")
    
    # Limpiar y desconectar
    controlador.resetear_todos()
    controlador.desconectar_todos()


def main():
    """Función principal"""
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n✓ Programa interrumpido por el usuario")
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Verificar dependencias
    try:
        import vosk
        import sounddevice
    except ImportError as e:
        print("✗ Error: Faltan dependencias")
        print("\nInstala las dependencias necesarias:")
        print("  pip3 install vosk sounddevice")
        print("\nEn Raspberry Pi también necesitas:")
        print("  sudo apt-get install python3-pyaudio portaudio19-dev")
        sys.exit(1)
    
    main()
