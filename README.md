## Instalación

### Dependencias Python

```bash
# Instalar dependencias
pip install -r requirements.txt
```

### Sistema de Extracción de PDFs Robusto y Multiplataforma

Este proyecto utiliza **PyMuPDF + PaddleOCR** para extraer texto de PDFs:

#### 🎯 Ventajas del Sistema

✅ **Sin dependencias del sistema operativo** - No requiere instalaciones externas (Tesseract, Poppler, etc.)
✅ **Multiplataforma** - Funciona en Windows, Linux y macOS sin configuración adicional
✅ **Robusto y preciso** - PaddleOCR es un motor OCR de última generación
✅ **Híbrido inteligente** - Extrae texto nativo primero, luego usa OCR si es necesario

#### 📋 Estrategia de Extracción

1. **Paso 1 (Rápido)**: Extracción de texto nativo usando **PyMuPDF**
   - Funciona con PDFs generados digitalmente (Oracle Reports, Word, etc.)
   - Muy rápido y eficiente
   - No requiere procesamiento de imágenes

2. **Paso 2 (Preciso)**: OCR usando **PaddleOCR**
   - Se activa automáticamente si el texto nativo es insuficiente
   - Funciona con PDFs escaneados o imágenes
   - Soporta español e inglés
   - Detecta automáticamente la orientación del texto
   - No requiere Tesseract ni instalaciones del sistema

#### 🔧 Características Técnicas

- 🚀 **Alto rendimiento**: Renderiza páginas a 2x zoom (144 DPI) para mejor calidad OCR
- 🔄 **Fallback automático**: Si el texto nativo es insuficiente, usa OCR sin intervención
- 🛡️ **Manejo robusto de errores**: Procesa cada página independientemente
- 🌐 **Multilenguaje**: Soporta español (primario) e inglés
- 📊 **Logging detallado**: Información completa del proceso de extracción

#### 📦 Instalación de Dependencias

Todas las dependencias se instalan automáticamente con:

```bash
pip install -r requirements.txt
```

**Nota**: No se requiere ninguna instalación adicional del sistema operativo

### Ejecución

```bash
python main.py
```

El sistema detectará automáticamente qué método de extracción usar para cada PDF.
