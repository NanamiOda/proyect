#!/usr/bin/env python3
"""
Sistema de lectura de PDFs a Braille
Soporta lectura directa de texto y OCR para PDFs escaneados
"""

import os
import sys
from pathlib import Path
from PIL import Image
import pytesseract
import PyPDF2
import pdf2image
from multi_arduino_controller import MultiArduinoBrailleController


class PDFToBraille:
    def __init__(self, controlador_braille):
        """
        Inicializa el sistema de lectura de PDFs
        
        Args:
            controlador_braille: Instancia de MultiArduinoBrailleController
        """
        self.controlador = controlador_braille
        self.modo_ocr = False
        
        # Configurar Tesseract para español
        pytesseract.pytesseract.tesseract_cmd = self._encontrar_tesseract()
        
    def _encontrar_tesseract(self):
        """Intenta encontrar el ejecutable de Tesseract"""
        # Rutas comunes en diferentes sistemas
        rutas_posibles = [
            '/usr/bin/tesseract',  # Linux
            '/usr/local/bin/tesseract',  # Linux/Mac
            'C:\\Program Files\\Tesseract-OCR\\tesseract.exe',  # Windows
            'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe',  # Windows
            'tesseract'  # En PATH
        ]
        
        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                return ruta
        
        return 'tesseract'  # Por defecto, asumir que está en PATH
    
    def detectar_tipo_pdf(self, ruta_pdf):
        """
        Detecta si el PDF contiene texto extraíble o es escaneo
        
        Args:
            ruta_pdf: Ruta al archivo PDF
            
        Returns:
            'texto' si tiene texto extraíble, 'escaneo' si requiere OCR
        """
        try:
            with open(ruta_pdf, 'rb') as archivo:
                lector = PyPDF2.PdfReader(archivo)
                
                # Revisar primeras 3 páginas
                paginas_revisar = min(3, len(lector.pages))
                texto_total = ""
                
                for i in range(paginas_revisar):
                    texto = lector.pages[i].extract_text()
                    texto_total += texto
                
                # Si hay suficiente texto extraíble, es PDF de texto
                if len(texto_total.strip()) > 50:
                    return 'texto'
                else:
                    return 'escaneo'
                    
        except Exception as e:
            print(f"⚠️  Error al analizar PDF: {e}")
            return 'escaneo'  # En caso de duda, usar OCR
    
    def leer_pdf_texto(self, ruta_pdf, pagina_inicio=None, pagina_fin=None):
        """
        Lee texto directamente del PDF
        
        Args:
            ruta_pdf: Ruta al archivo PDF
            pagina_inicio: Página inicial (None para comenzar desde la primera)
            pagina_fin: Página final (None para leer hasta el final)
            
        Returns:
            Texto extraído del PDF
        """
        try:
            print(f"📄 Leyendo PDF (modo texto directo): {os.path.basename(ruta_pdf)}")
            
            with open(ruta_pdf, 'rb') as archivo:
                lector = PyPDF2.PdfReader(archivo)
                total_paginas = len(lector.pages)
                
                # Determinar rango de páginas
                inicio = pagina_inicio if pagina_inicio else 0
                fin = pagina_fin if pagina_fin else total_paginas
                
                print(f"   Páginas: {inicio+1} a {fin} de {total_paginas}")
                
                texto_completo = ""
                
                for i in range(inicio, min(fin, total_paginas)):
                    print(f"   Procesando página {i+1}...", end=' ')
                    texto_pagina = lector.pages[i].extract_text()
                    texto_completo += texto_pagina + "\n"
                    print(f"✓ ({len(texto_pagina)} caracteres)")
                
                return texto_completo
                
        except Exception as e:
            print(f"✗ Error al leer PDF: {e}")
            return None
    
    def leer_pdf_ocr(self, ruta_pdf, pagina_inicio=None, pagina_fin=None, dpi=300):
        """
        Lee PDF usando OCR (para PDFs escaneados o imágenes)
        
        Args:
            ruta_pdf: Ruta al archivo PDF
            pagina_inicio: Página inicial (None para todas)
            pagina_fin: Página final (None para todas)
            dpi: Resolución para conversión a imagen
            
        Returns:
            Texto extraído mediante OCR
        """
        try:
            print(f"📄 Leyendo PDF (modo OCR): {os.path.basename(ruta_pdf)}")
            print(f"   Resolución: {dpi} DPI")
            print("   ⚠️  Este proceso puede tardar varios minutos...")
            
            # Convertir PDF a imágenes
            print("   Convirtiendo PDF a imágenes...")
            imagenes = pdf2image.convert_from_path(
                ruta_pdf,
                dpi=dpi,
                first_page=pagina_inicio+1 if pagina_inicio else None,
                last_page=pagina_fin if pagina_fin else None
            )
            
            print(f"   ✓ {len(imagenes)} páginas convertidas")
            
            texto_completo = ""
            
            # Aplicar OCR a cada imagen
            for i, imagen in enumerate(imagenes):
                num_pagina = (pagina_inicio if pagina_inicio else 0) + i + 1
                print(f"   Aplicando OCR a página {num_pagina}...", end=' ')
                
                # OCR con Tesseract en español
                texto_pagina = pytesseract.image_to_string(
                    imagen,
                    lang='spa',  # Idioma español
                    config='--psm 6'  # Page segmentation mode: Assume uniform block of text
                )
                
                texto_completo += texto_pagina + "\n"
                print(f"✓ ({len(texto_pagina)} caracteres)")
            
            return texto_completo
            
        except Exception as e:
            print(f"✗ Error en OCR: {e}")
            print("\n💡 Asegúrate de tener instalado:")
            print("   - Tesseract OCR")
            print("   - Datos de idioma español para Tesseract")
            return None
    
    def procesar_pdf(self, ruta_pdf, modo='auto', pagina_inicio=None, 
                     pagina_fin=None):
        """
        Procesa un PDF completo y lo escribe en Braille
        
        Args:
            ruta_pdf: Ruta al archivo PDF
            modo: 'auto', 'texto', o 'ocr'
            pagina_inicio: Página inicial (1-based, None para todas)
            pagina_fin: Página final (1-based, None para todas)
        """
        if not os.path.exists(ruta_pdf):
            print(f"✗ Archivo no encontrado: {ruta_pdf}")
            return
        
        # Ajustar índices (convertir de 1-based a 0-based)
        inicio_0 = (pagina_inicio - 1) if pagina_inicio else None
        fin_0 = pagina_fin if pagina_fin else None
        
        print("\n" + "="*70)
        print(f"PROCESANDO PDF: {os.path.basename(ruta_pdf)}")
        print("="*70)
        
        # Detectar modo si es 'auto'
        if modo == 'auto':
            print("\n🔍 Detectando tipo de PDF...")
            tipo = self.detectar_tipo_pdf(ruta_pdf)
            print(f"   Tipo detectado: {tipo.upper()}")
            modo = tipo
        
        # Leer texto según el modo
        if modo == 'texto':
            texto = self.leer_pdf_texto(ruta_pdf, inicio_0, fin_0)
        elif modo == 'ocr':
            texto = self.leer_pdf_ocr(ruta_pdf, inicio_0, fin_0)
        else:
            print(f"✗ Modo no válido: {modo}")
            return
        
        if not texto:
            print("✗ No se pudo extraer texto del PDF")
            return
        
        # Limpiar texto
        texto = self._limpiar_texto(texto)
        
        print(f"\n📊 Estadísticas del texto:")
        print(f"   • Caracteres totales: {len(texto)}")
        print(f"   • Palabras: {len(texto.split())}")
        print(f"   • Caracteres válidos (a-z): {sum(1 for c in texto.lower() if 'a' <= c <= 'z')}")
        print(f"   • Tiempo estimado: {len(texto) * 2:.0f} segundos ({len(texto) * 2 / 60:.1f} minutos)")
        
        # Preguntar si continuar
        print(f"\n⚠️  Se escribirán {len(texto)} caracteres en Braille (2s por carácter)")
        confirmacion = input("¿Continuar? (s/n): ").strip().lower()
        
        if confirmacion != 's':
            print("❌ Operación cancelada")
            return
        
        # Escribir en Braille
        print("\n" + "="*70)
        print("ESCRIBIENDO EN BRAILLE")
        print("="*70)
        
        self.controlador.escribir_texto_paralelo(texto)
        
        print("\n✅ PDF procesado completamente")
    
    def _limpiar_texto(self, texto):
        """
        Limpia el texto extraído del PDF
        
        Args:
            texto: Texto a limpiar
            
        Returns:
            Texto limpio
        """
        # Reemplazar saltos de línea múltiples
        import re
        texto = re.sub(r'\n{3,}', '\n\n', texto)
        
        # Eliminar espacios múltiples
        texto = re.sub(r' {2,}', ' ', texto)
        
        # Eliminar espacios al inicio/fin de líneas
        lineas = [linea.strip() for linea in texto.split('\n')]
        texto = '\n'.join(lineas)
        
        return texto
    
    def extraer_muestra(self, ruta_pdf, num_caracteres=200):
        """
        Extrae una muestra del PDF para preview
        
        Args:
            ruta_pdf: Ruta al PDF
            num_caracteres: Número de caracteres a extraer
            
        Returns:
            Muestra de texto
        """
        tipo = self.detectar_tipo_pdf(ruta_pdf)
        
        if tipo == 'texto':
            texto = self.leer_pdf_texto(ruta_pdf, 0, 1)
        else:
            texto = self.leer_pdf_ocr(ruta_pdf, 0, 1)
        
        if texto:
            return texto[:num_caracteres] + "..." if len(texto) > num_caracteres else texto
        return None


def menu_pdf():
    """Menú interactivo para procesamiento de PDFs"""
    print("\n" + "="*70)
    print("SISTEMA PDF A BRAILLE")
    print("="*70)
    
    # Conectar Arduinos
    print("\n📡 Configurando conexión con Arduinos...")
    puertos = []
    for i in range(3):
        default = f'/dev/ttyACM{i}'
        puerto = input(f"Puerto Arduino {i+1} [{default}]: ").strip()
        puertos.append(puerto if puerto else default)
    
    controlador = MultiArduinoBrailleController(puertos=puertos)
    
    if not controlador.conectar_todos():
        print("\n⚠️  No todos los Arduinos conectaron")
        continuar = input("¿Continuar de todos modos? (s/n): ").strip().lower()
        if continuar != 's':
            return
    
    # Crear procesador de PDF
    pdf_processor = PDFToBraille(controlador)
    
    # Menú principal
    while True:
        print("\n" + "="*70)
        print("MENÚ PDF A BRAILLE")
        print("="*70)
        print("1. Procesar PDF (modo automático)")
        print("2. Procesar PDF (modo texto directo)")
        print("3. Procesar PDF (modo OCR)")
        print("4. Vista previa de PDF")
        print("5. Test de Arduinos")
        print("6. Información del sistema")
        print("7. Salir")
        print("="*70)
        
        opcion = input("\nSelecciona opción: ").strip()
        
        if opcion in ['1', '2', '3']:
            ruta_pdf = input("\nRuta del archivo PDF: ").strip()
            
            if not os.path.exists(ruta_pdf):
                print("✗ Archivo no encontrado")
                continue
            
            # Opciones de páginas
            print("\nRango de páginas (Enter para todas):")
            pag_inicio = input("  Página inicial: ").strip()
            pag_fin = input("  Página final: ").strip()
            
            pagina_inicio = int(pag_inicio) if pag_inicio else None
            pagina_fin = int(pag_fin) if pag_fin else None
            
            # Procesar
            if opcion == '1':
                pdf_processor.procesar_pdf(ruta_pdf, 'auto', pagina_inicio, pagina_fin)
            elif opcion == '2':
                pdf_processor.procesar_pdf(ruta_pdf, 'texto', pagina_inicio, pagina_fin)
            elif opcion == '3':
                pdf_processor.procesar_pdf(ruta_pdf, 'ocr', pagina_inicio, pagina_fin)
        
        elif opcion == '4':
            ruta_pdf = input("\nRuta del archivo PDF: ").strip()
            
            if os.path.exists(ruta_pdf):
                print("\n📄 Vista previa:")
                print("-" * 70)
                muestra = pdf_processor.extraer_muestra(ruta_pdf, 300)
                if muestra:
                    print(muestra)
                print("-" * 70)
            else:
                print("✗ Archivo no encontrado")
        
        elif opcion == '5':
            controlador.test_todos_los_modulos()
        
        elif opcion == '6':
            info = controlador.get_info()
            print("\n📊 Información del sistema:")
            for key, value in info.items():
                print(f"   • {key}: {value}")
        
        elif opcion == '7':
            break
        
        else:
            print("✗ Opción inválida")
    
    # Limpiar
    controlador.resetear_todos()
    controlador.desconectar_todos()


if __name__ == "__main__":
    try:
        menu_pdf()
    except KeyboardInterrupt:
        print("\n\n✓ Programa interrumpido")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
