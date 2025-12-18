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
        self.sample_rate = self._get_valid_sample_rate(sample_rate)
        self.modelo = None
        self.recognizer = None
        self.audio_queue = queue.Queue()
        self.escuchando = False
    
    def _get_valid_sample_rate(self, desired_rate=16000):
        """
        Obtiene una tasa de muestreo válida para el dispositivo
        
        Args:
            desired_rate: Tasa deseada (16000 Hz para Vosk)
            
        Returns:
            Tasa de muestreo válida
        """
        try:
            # Intentar obtener el dispositivo por defecto
            device_info = sd.query_devices(kind='input')
            default_rate = int(device_info['default_samplerate'])
            
            # Lista de tasas compatibles con Vosk en orden de preferencia
            vosk_rates = [16000, 8000, 32000, 44100, 48000]
            
            # Si la tasa por defecto es compatible con Vosk, usarla
            if default_rate in vosk_rates:
                print(f"[INFO] Usando sample rate: {default_rate} Hz")
                return default_rate
            
            # Probar tasas de muestreo compatibles con Vosk
            for rate in vosk_rates:
                try:
                    sd.check_input_settings(
                        device=None,
                        channels=1,
                        samplerate=rate
                    )
                    print(f"[INFO] Sample rate ajustado a: {rate} Hz (compatible con dispositivo)")
                    return rate
                except Exception:
                    continue
            
            # Si ninguna funciona, usar la por defecto del dispositivo
            print(f"[WARNING] Usando sample rate del dispositivo: {default_rate} Hz")
            return default_rate
            
        except Exception as e:
            print(f"[WARNING] No se pudo detectar sample rate automático: {e}")
            print(f"[INFO] Usando sample rate por defecto: {desired_rate} Hz")
            return desired_rate
        
    def cargar_modelo(self):
        """Carga el modelo Vosk"""
        print("Cargando modelo de reconocimiento de voz...")
        
        if not os.path.exists(self.modelo_path):
            print(f"[ERROR] No se encontro el modelo en '{self.modelo_path}'")
            print("\nPara descargar el modelo:")
            print("1. Visita: https://alphacephei.com/vosk/models")
            print("2. Descarga: vosk-model-small-es-0.42")
            print("3. Descomprime en este directorio")
            return False
        
        try:
            self.modelo = Model(self.modelo_path)
            self.recognizer = KaldiRecognizer(self.modelo, self.sample_rate)
            self.recognizer.SetWords(True)
            print(f"[OK] Modelo cargado exitosamente")
            print(f"[INFO] Sample rate configurado: {self.sample_rate} Hz")
            return True
        except Exception as e:
            print(f"[ERROR] Error al cargar modelo: {e}")
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
                
                # Probar tasas de muestreo comunes
                compatible_rates = []
                for rate in [8000, 16000, 22050, 32000, 44100, 48000]:
                    try:
                        sd.check_input_settings(device=i, channels=1, samplerate=rate)
                        compatible_rates.append(rate)
                    except:
                        pass
                
                    if compatible_rates:
                        print(f"   Tasas compatibles: {', '.join(map(str, compatible_rates))} Hz")
        
        def escuchar_continuo(self, controlador_braille, device=None):
            """
            Escucha la voz y envía a Braille en tiempo real
            
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
                    while True:
                        try:
                            data = self.audio_queue.get(timeout=0.5)
                        except queue.Empty:
                            continue
                        
                        if self.recognizer.AcceptWaveform(data):
                            resultado = json.loads(self.recognizer.Result())
                            texto = resultado.get('text', '')
                            if texto:
                                print(f"\n[RECONOCIDO] '{texto}'")
                                print("[INFO] Escribiendo en Braille (2s por caracter)...")
                                controlador_braille.escribir_texto_paralelo(texto)
                                print()
                        else:
                            # Resultado parcial (mientras habla)
                            resultado_parcial = json.loads(self.recognizer.PartialResult())
                            texto_parcial = resultado_parcial.get('partial', '')
                            if texto_parcial:
                                print(f"\r[PARCIAL] {texto_parcial}", end='', flush=True)
            
            except KeyboardInterrupt:
                print("\n\n✓ Escucha detenida")
            except Exception as e:
                print(f"\n✗ Error durante la escucha: {e}")
        
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
                    import time
                    inicio = time.time()
                    texto_final = None
                    
                    while (time.time() - inicio) < timeout:
                        try:
                            data = self.audio_queue.get(timeout=0.5)
                        except queue.Empty:
                            continue
                        
                        if self.recognizer.AcceptWaveform(data):
                            resultado = json.loads(self.recognizer.Result())
                            texto_final = resultado.get('text', '')
                            if texto_final:
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
            print("[ERROR] Modelo no cargado")
            return
        
        print(f"\n[INFO] Probando microfono durante {duracion} segundos...")
        print("[INFO] Sample rate: {} Hz".format(self.sample_rate))
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
                            print(f"[OK] Reconocido: '{texto}'")
                    else:
                        resultado_parcial = json.loads(self.recognizer.PartialResult())
                        texto_parcial = resultado_parcial.get('partial', '')
                        if texto_parcial:
                            print(f"\r[PARCIAL] {texto_parcial}", end='', flush=True)
                
                print("\n\n[OK] Test completado")
                
        except Exception as e:
            print(f"\n[ERROR] Error durante el test: {e}")
            print(f"[INFO] Verifica el sample rate del dispositivo con opcion 4")


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
        print("\n[WARNING] No todos los Arduinos conectaron")
        continuar = input("¿Continuar de todos modos? (s/n): ").strip().lower()
        if continuar != 's':
            return
    
    # Verificar estados
    if not controlador.verificar_estados():
        print("[WARNING] Algunos Arduinos no responden correctamente")
    
    # Configurar sistema de voz
    print("\n2. Inicializando reconocimiento de voz...")
    modelo_path = input("Ruta del modelo Vosk [vosk-model-small-es-0.42]: ").strip()
    if not modelo_path:
        modelo_path = "vosk-model-small-es-0.42"
    
    voz = VoiceToBraille(modelo_path=modelo_path)
    if not voz.cargar_modelo():
        controlador.desconectar()
        return
    
    print("\n[OK] Sistema inicializado correctamente\n")
    
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
        print("[INFO] Limitación energética: 2 segundos por carácter")
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
            print("\n[INFO] Información del sistema:")
            for key, value in info.items():
                print(f"   - {key}: {value}")
        
        elif opcion == "8":
            print("\n[OK] Saliendo del sistema...")
            break
            
        else:
            print("[ERROR] Opción inválida")
    controlador.resetear_todos()
    controlador.desconectar_todos()


def main():
    """Función principal"""
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n[OK] Programa interrumpido por el usuario")
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Verificar dependencias
    try:
        import vosk
        import sounddevice
    except ImportError as e:
        print("[ERROR] Faltan dependencias")
        print("\nInstala las dependencias necesarias:")
        print("  pip3 install vosk sounddevice")
        print("\nEn Raspberry Pi también necesitas:")
        print("  sudo apt-get install python3-pyaudio portaudio19-dev")
        sys.exit(1)
    
    main()

