#!/usr/bin/env python3
"""
Sistema multi-Arduino para escritura Braille paralela
Controla 3 Arduinos, cada uno con 2 módulos de solenoides (6 caracteres simultáneos)
"""

import serial
import time
import threading
from typing import List, Optional


class MultiArduinoBrailleController:
    def __init__(self, puertos=['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyACM2'], 
                 baudrate=115200, timeout=2):
        """
        Inicializa el controlador para múltiples Arduinos
        
        Args:
            puertos: Lista de puertos seriales (uno por Arduino)
            baudrate: Velocidad de comunicación
            timeout: Tiempo de espera para respuestas
        """
        self.puertos = puertos
        self.baudrate = baudrate
        self.timeout = timeout
        self.arduinos = []  # Lista de conexiones serial
        self.conectados = []  # Estados de conexión
        self.locks = []  # Locks para thread-safety
        self.num_modulos = 2  # Módulos por Arduino
        self.num_arduinos = len(puertos)
        self.caracteres_simultaneos = self.num_arduinos * self.num_modulos  # 6 caracteres
        
        # LIMITACIÓN ENERGÉTICA: Solo 1 módulo activo a la vez
        self.display_duration = 2.0  # Segundos que cada carácter permanece visible
        self.module_delay = 0.1  # Pausa entre módulos
        
    def conectar_todos(self):
        """Conecta con todos los Arduinos"""
        print(f"Conectando con {self.num_arduinos} Arduinos...")
        exito_total = True
        
        for i, puerto in enumerate(self.puertos):
            print(f"  Arduino {i+1} ({puerto})...", end=' ')
            if self.conectar_arduino(i, puerto):
                print("✓")
            else:
                print("✗")
                exito_total = False
        
        if exito_total:
            print(f"\n✓ {self.num_arduinos} Arduinos conectados ({self.caracteres_simultaneos} caracteres simultáneos)")
        else:
            print(f"\n⚠️  Algunos Arduinos no conectaron. Caracteres disponibles: {sum(self.conectados) * self.num_modulos}")
        
        return exito_total
    
    def conectar_arduino(self, indice, puerto):
        """
        Conecta con un Arduino específico
        
        Args:
            indice: Índice del Arduino (0-2)
            puerto: Puerto serial del Arduino
            
        Returns:
            True si conectó exitosamente
        """
        try:
            arduino = serial.Serial(puerto, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Esperar reset del Arduino
            
            # Esperar señal READY
            intentos = 0
            while intentos < 10:
                if arduino.in_waiting:
                    respuesta = arduino.readline().decode('utf-8').strip()
                    if respuesta == "READY":
                        # Guardar en las listas
                        if len(self.arduinos) <= indice:
                            self.arduinos.extend([None] * (indice + 1 - len(self.arduinos)))
                            self.conectados.extend([False] * (indice + 1 - len(self.conectados)))
                            self.locks.extend([None] * (indice + 1 - len(self.locks)))
                        
                        self.arduinos[indice] = arduino
                        self.conectados[indice] = True
                        self.locks[indice] = threading.Lock()
                        return True
                time.sleep(0.1)
                intentos += 1
            
            arduino.close()
            return False
            
        except serial.SerialException as e:
            return False
    
    def desconectar_todos(self):
        """Cierra todas las conexiones"""
        for i, arduino in enumerate(self.arduinos):
            if arduino and arduino.is_open:
                try:
                    arduino.close()
                except:
                    pass
        print("✓ Todos los Arduinos desconectados")
    
    def enviar_comando(self, arduino_id, comando):
        """
        Envía comando a un Arduino específico
        
        Args:
            arduino_id: ID del Arduino (0-2)
            comando: Comando a enviar
            
        Returns:
            Lista de respuestas
        """
        if arduino_id >= len(self.arduinos) or not self.conectados[arduino_id]:
            return []
        
        try:
            with self.locks[arduino_id]:
                arduino = self.arduinos[arduino_id]
                arduino.write(f"{comando}\n".encode('utf-8'))
                arduino.flush()
                
                # Leer respuestas
                respuestas = []
                time.sleep(0.1)
                
                while arduino.in_waiting:
                    linea = arduino.readline().decode('utf-8').strip()
                    if linea:
                        respuestas.append(linea)
                
                return respuestas
                
        except Exception as e:
            print(f"✗ Error en Arduino {arduino_id+1}: {e}")
            return []
    
    def escribir_caracter(self, arduino_id, modulo_id, caracter):
        """
        Escribe un carácter en un módulo específico
        
        Args:
            arduino_id: ID del Arduino (0-2)
            modulo_id: ID del módulo en ese Arduino (0-1)
            caracter: Carácter a escribir
            
        Returns:
            True si tuvo éxito
        """
        # El Arduino maneja internamente qué módulo usar
        # Enviamos el ID del módulo junto con el carácter
        comando = f"WRITE_MODULE:{modulo_id}:{caracter}"
        respuestas = self.enviar_comando(arduino_id, comando)
        return "OK" in respuestas or "DONE" in respuestas
    
    def escribir_texto_paralelo(self, texto):
        """
        Escribe texto usando los módulos de forma SECUENCIAL (1 a la vez)
        NOTA: Nombre "paralelo" mantenido por compatibilidad, pero ahora es SECUENCIAL
        debido a limitación energética (solo 1 módulo activo a la vez)
        
        Args:
            texto: Texto a escribir
        """
        texto = texto.lower().replace('\n', ' ').replace('\r', ' ')
        total_chars = len(texto)
        
        print(f"📝 Escribiendo {total_chars} caracteres (modo secuencial - limitación energética)")
        print(f"   ⚡ Solo 1 módulo activo a la vez - 2 segundos por carácter")
        print(f"   ⏱️  Tiempo estimado: {total_chars * self.display_duration:.0f} segundos ({total_chars * self.display_duration / 60:.1f} minutos)")
        
        # Procesar caracteres uno por uno de forma SECUENCIAL
        for i, char in enumerate(texto):
            if char == ' ':
                print(f"  [{i+1}/{total_chars}] (espacio)")
                time.sleep(self.display_duration)  # Pausa equivalente para espacios
                
            elif 'a' <= char <= 'z':
                # Determinar qué Arduino y módulo usar
                arduino_id = (i // self.num_modulos) % len([c for c in self.conectados if c])
                modulo_id = i % self.num_modulos
                
                # Encontrar primer Arduino conectado desde arduino_id
                arduino_real = arduino_id
                intentos = 0
                while intentos < len(self.conectados):
                    if arduino_real < len(self.conectados) and self.conectados[arduino_real]:
                        break
                    arduino_real = (arduino_real + 1) % len(self.conectados)
                    intentos += 1
                
                if arduino_real < len(self.conectados) and self.conectados[arduino_real]:
                    print(f"  [{i+1}/{total_chars}] Arduino{arduino_real+1}.M{modulo_id+1}: '{char}' (2s)")
                    self.escribir_caracter(arduino_real, modulo_id, char)
                    # El Arduino ya maneja el delay de 2 segundos internamente
                else:
                    print(f"  [{i+1}/{total_chars}] ✗ Sin Arduinos disponibles")
            else:
                print(f"  [{i+1}/{total_chars}] '{char}' (no soportado)")
        
        print("\n✓ Escritura completada")
    
    def _escribir_char_thread(self, arduino_id, modulo_id, caracter, pos, total):
        """Thread helper para escritura paralela"""
        if caracter == ' ':
            print(f"  [{pos}/{total}] Arduino{arduino_id+1}.M{modulo_id+1}: (espacio)")
        elif 'a' <= caracter <= 'z':
            print(f"  [{pos}/{total}] Arduino{arduino_id+1}.M{modulo_id+1}: '{caracter}'")
            self.escribir_caracter(arduino_id, modulo_id, caracter)
        else:
            print(f"  [{pos}/{total}] Arduino{arduino_id+1}.M{modulo_id+1}: '{caracter}' (no soportado)")
    
    def escribir_texto_secuencial(self, texto):
        """
        Escribe texto de forma secuencial (un carácter a la vez)
        Ahora IDÉNTICO a escribir_texto_paralelo debido a limitación energética
        
        Args:
            texto: Texto a escribir
        """
        # Redirigir a la función principal (ahora todo es secuencial)
        self.escribir_texto_paralelo(texto)
    
    def test_todos_los_modulos(self):
        """Prueba todos los módulos de todos los Arduinos"""
        print("\n🔧 Test de todos los módulos...")
        
        for i in range(len(self.arduinos)):
            if self.conectados[i]:
                print(f"\nArduino {i+1}:")
                respuestas = self.enviar_comando(i, "TEST")
                for resp in respuestas:
                    print(f"  {resp}")
        
        print("\n✓ Test completado")
    
    def resetear_todos(self):
        """Resetea todos los Arduinos"""
        print("Reseteando todos los Arduinos...")
        for i in range(len(self.arduinos)):
            if self.conectados[i]:
                self.enviar_comando(i, "RESET")
        print("✓ Reset completado")
    
    def verificar_estados(self):
        """Verifica el estado de todos los Arduinos"""
        print("\n📊 Estado de los Arduinos:")
        todos_ok = True
        
        for i in range(len(self.arduinos)):
            if self.conectados[i]:
                respuestas = self.enviar_comando(i, "STATUS")
                estado = "✓ READY" if "READY" in respuestas else "✗ ERROR"
                print(f"  Arduino {i+1}: {estado}")
                if "READY" not in respuestas:
                    todos_ok = False
            else:
                print(f"  Arduino {i+1}: ✗ DESCONECTADO")
                todos_ok = False
        
        return todos_ok
    
    def get_info(self):
        """Retorna información del sistema"""
        conectados = sum(self.conectados)
        return {
            'total_arduinos': self.num_arduinos,
            'arduinos_conectados': conectados,
            'modulos_por_arduino': self.num_modulos,
            'modulos_totales': conectados * self.num_modulos,
            'display_duration': f'{self.display_duration}s por carácter',
            'limitacion_energetica': 'Solo 1 módulo activo a la vez',
            'puertos': [p if c else 'DESCONECTADO' for p, c in zip(self.puertos, self.conectados)]
        }


def menu_interactivo():
    """Menú interactivo para sistema multi-Arduino"""
    print("\n" + "="*70)
    print("SISTEMA MULTI-ARDUINO BRAILLE (6 CARACTERES SIMULTÁNEOS)")
    print("="*70)
    
    # Configurar puertos
    print("\nConfiguración de puertos:")
    puertos = []
    for i in range(3):
        default = f'/dev/ttyACM{i}'
        puerto = input(f"Puerto Arduino {i+1} [{default}]: ").strip()
        puertos.append(puerto if puerto else default)
    
    # Crear controlador
    controlador = MultiArduinoBrailleController(puertos=puertos)
    
    # Conectar
    if not controlador.conectar_todos():
        print("\n⚠️  No todos los Arduinos conectaron, pero puedes continuar")
        continuar = input("¿Continuar de todos modos? (s/n): ").strip().lower()
        if continuar != 's':
            return
    
    # Mostrar información
    info = controlador.get_info()
    print(f"\n📊 Configuración:")
    print(f"   • Arduinos conectados: {info['arduinos_conectados']}/{info['total_arduinos']}")
    print(f"   • Módulos totales: {info['modulos_totales']}")
    print(f"   • Duración por carácter: {info['display_duration']}")
    print(f"   • ⚡ Limitación: {info['limitacion_energetica']}")
    
    # Menú principal
    while True:
        print("\n" + "="*70)
        print("MENÚ PRINCIPAL")
        print("="*70)
        print("1. Escribir texto (los 6 módulos disponibles)")
        print("2. Test de todos los módulos")
        print("3. Verificar estados")
        print("4. Resetear todos")
        print("5. Mostrar información del sistema")
        print("6. Salir")
        print("="*70)
        print("ℹ️  NOTA: Solo 1 módulo activo a la vez (2s por carácter)")
        print("="*70)
        
        opcion = input("\nSelecciona opción: ").strip()
        
        if opcion == "1":
            texto = input("Texto a escribir: ")
            controlador.escribir_texto_paralelo(texto)
            
        elif opcion == "2":
            controlador.test_todos_los_modulos()
            
        elif opcion == "3":
            controlador.verificar_estados()
            
        elif opcion == "4":
            controlador.resetear_todos()
            
        elif opcion == "5":
            info = controlador.get_info()
            print("\n📊 Información del sistema:")
            for key, value in info.items():
                print(f"   • {key}: {value}")
                
        elif opcion == "6":
            break
        else:
            print("✗ Opción inválida")
    
    # Limpiar
    controlador.resetear_todos()
    controlador.desconectar_todos()


if __name__ == "__main__":
    try:
        menu_interactivo()
    except KeyboardInterrupt:
        print("\n\n✓ Programa interrumpido")
