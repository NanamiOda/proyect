// Sistema con 2 módulos Braille (12 solenoides totales)
// Cada módulo tiene 6 puntos Braille
// Patrón Braille estándar:
//  1 • • 4
//  2 • • 5
//  3 • • 6

// MÓDULO 1 - Pines 2-7
const int MOD1_PIN1 = 2;
const int MOD1_PIN2 = 3;
const int MOD1_PIN3 = 4;
const int MOD1_PIN4 = 5;
const int MOD1_PIN5 = 6;
const int MOD1_PIN6 = 7;

// MÓDULO 2 - Pines 8-13
const int MOD2_PIN1 = 8;
const int MOD2_PIN2 = 9;
const int MOD2_PIN3 = 10;
const int MOD2_PIN4 = 11;
const int MOD2_PIN5 = 12;
const int MOD2_PIN6 = 13;

// Arrays de pines por módulo
const int MODULO_1_PINS[] = {MOD1_PIN1, MOD1_PIN2, MOD1_PIN3, MOD1_PIN4, MOD1_PIN5, MOD1_PIN6};
const int MODULO_2_PINS[] = {MOD2_PIN1, MOD2_PIN2, MOD2_PIN3, MOD2_PIN4, MOD2_PIN5, MOD2_PIN6};

const int NUM_MODULOS = 2;
const int PINES_POR_MODULO = 6;

// Tiempos de control - LIMITACIÓN ENERGÉTICA
// Solo se puede activar 1 módulo a la vez
const int DISPLAY_DURATION = 2000;  // Duración que el módulo permanece activo (2 segundos)
const int MODULE_DELAY = 100;        // Pequeña pausa entre módulos (ms)

// Configuración PWM para MOSFET D4184 075N03L
const int PWM_FREQUENCY = 700;      // Frecuencia 700Hz
const int PWM_DUTY_CYCLE = 60;      // Duty cycle 60%
const int PWM_VALUE = (255 * PWM_DUTY_CYCLE) / 100;  // Valor PWM (153 para 60%)

// Array de caracteres Braille (a-z)
const byte braille[] = {
  B000001, // 97 a
  B000011, // 98 b
  B001001, // 99 c
  B011001, // 100 d
  B010001, // 101 e
  B001011, // 102 f
  B011011, // 103 g
  B010011, // 104 h
  B001010, // 105 i
  B011010, // 106 j
  B000101, // 107 k
  B000111, // 108 l
  B001101, // 109 m
  B011101, // 110 n
  B010101, // 111 o
  B001111, // 112 p
  B011111, // 113 q
  B010111, // 114 r
  B001110, // 115 s
  B011110, // 116 t
  B100101, // 117 u
  B100111, // 118 v
  B111010, // 119 w
  B101101, // 120 x
  B111101, // 121 y
  B110101  // 122 z
};

// Función para escribir en un pin con PWM
void escribirPinPWM(int pin, bool estado) {
  if (estado) {
    // Activar con PWM según si el pin lo soporta
    if (pin == 3 || pin == 5 || pin == 6 || pin == 9 || pin == 10 || pin == 11) {
      // Pines con capacidad PWM - usar duty cycle de 60%
      analogWrite(pin, PWM_VALUE);
      
      // Habilitar PWM en el timer correspondiente
      if (pin == 9 || pin == 10) {
        // Timer 1
        if (pin == 9) {
          TCCR1A |= _BV(COM1A1);  // Habilitar PWM en OC1A (pin 9)
        } else {
          TCCR1A |= _BV(COM1B1);  // Habilitar PWM en OC1B (pin 10)
        }
      } else if (pin == 3 || pin == 11) {
        // Timer 2
        if (pin == 11) {
          TCCR2A |= _BV(COM2A1);  // Habilitar PWM en OC2A (pin 11)
        } else {
          TCCR2A |= _BV(COM2B1);  // Habilitar PWM en OC2B (pin 3)
        }
      } else {
        // Pines 5 y 6 (Timer 0) - usar analogWrite estándar
        analogWrite(pin, PWM_VALUE);
      }
    } else {
      // Pines digitales sin PWM - usar digitalWrite
      digitalWrite(pin, HIGH);
    }
  } else {
    // Desactivar pin
    if (pin == 3 || pin == 5 || pin == 6 || pin == 9 || pin == 10 || pin == 11) {
      analogWrite(pin, 0);
    } else {
      digitalWrite(pin, LOW);
    }
  }
}

void setup() {
  // Inicializar comunicación serial para Raspberry Pi
  Serial.begin(115200);  // Mayor velocidad para comunicación con Raspberry
  
  // Configurar PWM a 700Hz para pines PWM (3, 5, 6, 9, 10, 11)
  // Timer 0 (pines 5 y 6) - usado por delay(), evitar modificar
  // Timer 1 (pines 9 y 10) - 16 bits
  // Timer 2 (pines 3 y 11) - 8 bits
  
  // Configurar Timer 1 para 700Hz (pines 9 y 10)
  TCCR1A = 0;
  TCCR1B = 0;
  TCCR1A = _BV(WGM11);  // Fast PWM mode con ICR1 como TOP
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS11);  // Prescaler 8
  ICR1 = 2857;  // 16MHz / (8 * 700Hz) = 2857 para 700Hz
  
  // Configurar Timer 2 para aproximadamente 700Hz (pines 3 y 11)
  TCCR2A = _BV(WGM21) | _BV(WGM20);  // Fast PWM
  TCCR2B = _BV(WGM22) | _BV(CS22);   // Prescaler 64
  OCR2A = 89;  // 16MHz / (64 * 700Hz) ≈ 89 (~714Hz)
  
  // Configurar pines del MÓDULO 1
  for (int i = 0; i < PINES_POR_MODULO; i++) {
    pinMode(MODULO_1_PINS[i], OUTPUT);
    digitalWrite(MODULO_1_PINS[i], LOW);
  }
  
  // Configurar pines del MÓDULO 2
  for (int i = 0; i < PINES_POR_MODULO; i++) {
    pinMode(MODULO_2_PINS[i], OUTPUT);
    digitalWrite(MODULO_2_PINS[i], LOW);
  }
  
  // Esperar a que el serial esté listo
  while (!Serial) {
    ; // Esperar a que se conecte el puerto serial
  }
  
  // Enviar señal de inicio al Raspberry
  Serial.println("READY");
}

void loop() {
  // Esperar comandos del Raspberry Pi
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();  // Eliminar espacios y saltos de línea
    
    // Procesar comando
    if (comando.startsWith("WRITE_MODULE:")) {
      // Comando: WRITE_MODULE:modulo_id:caracter
      // Ejemplo: WRITE_MODULE:0:a  (módulo 0, letra a)
      int primer_separador = comando.indexOf(':', 13);
      if (primer_separador > 0) {
        String modulo_str = comando.substring(13, primer_separador);
        String caracter_str = comando.substring(primer_separador + 1);
        
        int modulo_id = modulo_str.toInt();
        char caracter = caracter_str.charAt(0);
        
        if (modulo_id >= 0 && modulo_id < NUM_MODULOS) {
          escribirCaracterModulo(modulo_id, caracter);
          Serial.println("OK");
        } else {
          Serial.println("ERROR:INVALID_MODULE");
        }
      }
      
    } else if (comando.startsWith("WRITE:")) {
      // Comando legacy para compatibilidad - usa módulo 0
      String texto = comando.substring(6);
      escribirTexto(texto);
      
    } else if (comando == "TEST") {
      // Comando para probar ambos módulos
      testModulos();
      Serial.println("OK");
      
    } else if (comando == "STATUS") {
      // Comando para verificar estado
      Serial.println("READY");
      
    } else if (comando == "RESET") {
      // Comando para resetear/apagar todos los solenoides
      apagarTodosModulos();
      Serial.println("OK");
      
    } else if (comando.startsWith("PATTERN:")) {
      // Comando para escribir patrón en módulo 0
      String patron = comando.substring(8);
      byte valorPatron = (byte)patron.toInt();
      escribirPatronModulo(0, valorPatron);
      Serial.println("OK");
      
    } else {
      // Comando no reconocido
      Serial.println("ERROR:UNKNOWN_COMMAND");
    }
  }
}

// Función para escribir texto completo
void escribirTexto(String texto) {
  texto.toLowerCase();  // Convertir a minúsculas
  
  Serial.println("START");
  
  // Procesar cada carácter
  for (int i = 0; i < texto.length(); i++) {
    char c = texto.charAt(i);
    
    if (c == ' ') {
      // Espacio - pausa sin solenoides
      apagarSolenoides();
      delay(CHAR_DELAY);
      
    } else if (c >= 'a' && c <= 'z') {
      // Letra válida
      escribirCaracter(c);
      
    } else {
      // Carácter no soportado, enviar advertencia
      Serial.print("WARN:UNSUPPORTED_CHAR:");
      Serial.println(c);
    }
  }
  
  apagarTodosModulos();
  Serial.println("DONE");
}

// Función para escribir un carácter en un módulo específico
// IMPORTANTE: Solo se activa 1 módulo a la vez por limitación energética
void escribirCaracterModulo(int modulo_id, char c) {
  if (c < 'a' || c > 'z') {
    return;  // Carácter no válido
  }
  
  // CRÍTICO: Apagar TODOS los módulos antes de activar uno nuevo
  apagarTodosModulos();
  delay(MODULE_DELAY);  // Pausa de seguridad
  
  // Obtener el patrón Braille
  int indice = c - 'a';
  byte patron = braille[indice];
  
  // Seleccionar pines del módulo
  const int* pines = (modulo_id == 0) ? MODULO_1_PINS : MODULO_2_PINS;
  
  // Activar solenoides según el patrón
  for (int i = 0; i < PINES_POR_MODULO; i++) {
    if (patron & (1 << i)) {
      escribirPinPWM(pines[i], true);
    } else {
      escribirPinPWM(pines[i], false);
    }
  }
  
  // Mantener activo por 2 segundos (lectura del usuario)
  delay(DISPLAY_DURATION);
  
  // Apagar solenoides del módulo
  apagarModulo(modulo_id);
  
  // Pequeña pausa antes del siguiente
  delay(MODULE_DELAY);
}

// Función para escribir un carácter (legacy - usa módulo 0)
void escribirCaracter(char c) {
  escribirCaracterModulo(0, c);
}

// Función para apagar un módulo específico
void apagarModulo(int modulo_id) {
  const int* pines = (modulo_id == 0) ? MODULO_1_PINS : MODULO_2_PINS;
  for (int i = 0; i < PINES_POR_MODULO; i++) {
    escribirPinPWM(pines[i], false);
  }
}

// Función para apagar todos los módulos
void apagarTodosModulos() {
  apagarModulo(0);
  apagarModulo(1);
}

// Función legacy
void apagarSolenoides() {
  apagarTodosModulos();
}

// Función para probar todos los módulos
void testModulos() {
  Serial.println("Probando MÓDULO 1...");
  for (int i = 0; i < PINES_POR_MODULO; i++) {
    Serial.print("Solenoide M1-");
    Serial.print(i + 1);
    Serial.println(" activado");
    
    escribirPinPWM(MODULO_1_PINS[i], true);
    delay(300);
    escribirPinPWM(MODULO_1_PINS[i], false);
    delay(200);
  }
  
  Serial.println("Probando MÓDULO 2...");
  for (int i = 0; i < PINES_POR_MODULO; i++) {
    Serial.print("Solenoide M2-");
    Serial.print(i + 1);
    Serial.println(" activado");
    
    escribirPinPWM(MODULO_2_PINS[i], true);
    delay(300);
    escribirPinPWM(MODULO_2_PINS[i], false);
    delay(200);
  }
  
  Serial.println("Test completado");
}

// Función legacy
void testSolenoides() {
  testModulos();
}

// Función para escribir un patrón en un módulo específico
void escribirPatronModulo(int modulo_id, byte patron) {
  // CRÍTICO: Apagar todos los módulos primero
  apagarTodosModulos();
  delay(MODULE_DELAY);
  
  const int* pines = (modulo_id == 0) ? MODULO_1_PINS : MODULO_2_PINS;
  
  for (int i = 0; i < PINES_POR_MODULO; i++) {
    if (patron & (1 << i)) {
      escribirPinPWM(pines[i], true);
    } else {
      escribirPinPWM(pines[i], false);
    }
  }
  
  // Mantener activo 2 segundos
  delay(DISPLAY_DURATION);
  apagarModulo(modulo_id);
  delay(MODULE_DELAY);
}

// Función legacy
void escribirPatron(byte patron) {
  escribirPatronModulo(0, patron);
}
