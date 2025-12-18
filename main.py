#!/usr/bin/env python3
"""
Script de Raspberry Pi para controlar el sistema Braille via Arduino
"""

import serial
import time
import sys

class BrailleController:
    def __init__(self, puerto='/dev/ttyACM0', baudrate=115200, timeout=2):
        """
        Inicializa la conexión con el Arduino
        
        Args:
            puerto: Puerto serial del Arduino (ej: '/dev/ttyACM0' o '/dev/ttyUSB0')
            baudrate: Velocidad de comunicación (debe coincidir con el Arduino)
            timeout: Tiempo de espera para respuestas
        """
        self.puerto = puerto
        self.baudrate = baudrate
        self.timeout = timeout
        self.arduino = None
        self.conectado = False
        
    def conectar(self):
        """Establece conexión con el Arduino"""
        try:
            self.arduino = serial.Serial(self.puerto, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Esperar a que el Arduino se reinicie
            
            # Esperar señal READY del Arduino
            while True:
                if self.arduino.in_waiting:
                    respuesta = self.arduino.readline().decode('utf-8').strip()
                    if respuesta == "READY":
                        self.conectado = True
                        print(f"✓ Conectado al Arduino en {self.puerto}")
                        return True
                time.sleep(0.1)
                
        except serial.SerialException as e:
            print(f"✗ Error al conectar con Arduino: {e}")
            print(f"  Verifica que el Arduino esté conectado en {self.puerto}")
            return False
    
    def desconectar(self):
        """Cierra la conexión con el Arduino"""
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
            self.conectado = False
            print("✓ Desconectado del Arduino")
    
    def enviar_comando(self, comando):
        """
        Envía un comando al Arduino y espera respuesta
        
        Args:
            comando: String con el comando a enviar
            
        Returns:
            Lista de respuestas del Arduino
        """
        if not self.conectado:
            print("✗ No hay conexión con el Arduino")
            return []
        
        try:
            # Enviar comando
            self.arduino.write(f"{comando}\n".encode('utf-8'))
            self.arduino.flush()
            
            # Esperar y leer respuestas
            respuestas = []
            time.sleep(0.1)
            
            while self.arduino.in_waiting:
                linea = self.arduino.readline().decode('utf-8').strip()
                if linea:
                    respuestas.append(linea)
                    
            return respuestas
            
        except Exception as e:
            print(f"✗ Error al enviar comando: {e}")
            return []
    
    def escribir_texto(self, texto):
        """
        Envía texto al Arduino para convertir a Braille
        
        Args:
            texto: String con el texto a escribir en Braille
            
        Returns:
            True si se completó exitosamente, False en caso contrario
        """
        print(f"Enviando texto: '{texto}'")
        respuestas = self.enviar_comando(f"WRITE:{texto}")
        
        # Procesar respuestas
        for respuesta in respuestas:
            if respuesta == "START":
                print("  → Iniciando escritura...")
            elif respuesta == "DONE":
                print("  ✓ Escritura completada")
                return True
            elif respuesta.startswith("WARN:"):
                print(f"  ⚠ {respuesta}")
            elif respuesta.startswith("ERROR:"):
                print(f"  ✗ {respuesta}")
                return False
        
        return False
    
    def test_solenoides(self):
        """Ejecuta test de solenoides"""
        print("Ejecutando test de solenoides...")
        respuestas = self.enviar_comando("TEST")
        for respuesta in respuestas:
            print(f"  {respuesta}")
        return "OK" in respuestas
    
    def verificar_estado(self):
        """Verifica el estado del Arduino"""
        respuestas = self.enviar_comando("STATUS")
        return "READY" in respuestas
    
    def resetear(self):
        """Apaga todos los solenoides"""
        respuestas = self.enviar_comando("RESET")
        return "OK" in respuestas
    
    def escribir_patron(self, patron):
        """
        Envía un patrón binario directo al Arduino
        
        Args:
            patron: Número entero representando el patrón (0-63)
        """
        respuestas = self.enviar_comando(f"PATTERN:{patron}")
        return "OK" in respuestas


def menu_interactivo(controlador):
    """Menú interactivo para controlar el sistema Braille"""
    while True:
        print("\n" + "="*50)
        print("SISTEMA DE CONTROL BRAILLE")
        print("="*50)
        print("1. Escribir texto")
        print("2. Test de solenoides")
        print("3. Verificar estado")
        print("4. Resetear solenoides")
        print("5. Escribir patrón personalizado")
        print("6. Salir")
        print("="*50)
        
        opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == "1":
            texto = input("Ingresa el texto a escribir en Braille: ")
            controlador.escribir_texto(texto)
            
        elif opcion == "2":
            controlador.test_solenoides()
            
        elif opcion == "3":
            if controlador.verificar_estado():
                print("✓ Arduino listo")
            else:
                print("✗ Arduino no responde")
                
        elif opcion == "4":
            if controlador.resetear():
                print("✓ Solenoides reseteados")
            else:
                print("✗ Error al resetear")
                
        elif opcion == "5":
            patron = input("Ingresa el patrón (0-63): ")
            try:
                valor = int(patron)
                if 0 <= valor <= 63:
                    controlador.escribir_patron(valor)
                else:
                    print("✗ Valor fuera de rango")
            except ValueError:
                print("✗ Valor inválido")
                
        elif opcion == "6":
            print("\n¡Hasta luego!")
            break
            
        else:
            print("✗ Opción inválida")


def main():
    """Función principal"""
    # Configuración del puerto serial
    # En Raspberry Pi típicamente es '/dev/ttyACM0' o '/dev/ttyUSB0'
    # Puedes encontrarlo con: ls /dev/tty*
    puerto = '/dev/ttyACM0'
    
    # Si se pasa el puerto como argumento
    if len(sys.argv) > 1:
        puerto = sys.argv[1]
    
    # Crear controlador
    controlador = BrailleController(puerto=puerto)
    
    # Intentar conectar
    if not controlador.conectar():
        print("\nIntenta con otro puerto, por ejemplo:")
        print("  python3 main.py /dev/ttyUSB0")
        print("  python3 main.py /dev/ttyACM1")
        return
    
    try:
        # Verificar estado inicial
        if controlador.verificar_estado():
            print("✓ Sistema listo para operar\n")
        
        # Modo de operación
        if len(sys.argv) > 2 and sys.argv[2] == "--text":
            # Modo directo: escribir texto desde argumento
            texto = " ".join(sys.argv[3:])
            controlador.escribir_texto(texto)
        else:
            # Modo interactivo
            menu_interactivo(controlador)
        
    except KeyboardInterrupt:
        print("\n\n✓ Programa interrumpido por el usuario")
        
    finally:
        # Resetear y desconectar
        controlador.resetear()
        controlador.desconectar()


if __name__ == "__main__":
    main()
