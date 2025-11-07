## Instalación

### Dependencias del Sistema

El bot utiliza OCR para procesar imágenes y PDFs escaneados. Necesitas instalar Tesseract OCR:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils
```

**macOS:**
```bash
brew install tesseract tesseract-lang poppler
```

**Windows:**
1. Descargar Tesseract desde: https://github.com/UB-Mannheim/tesseract/wiki
2. Instalar y agregar al PATH del sistema
3. Descargar paquete de idioma español (spa.traineddata)

### Dependencias de Python

```bash
# Instalar dependencias de Python
pip install -r requirements.txt

# Ejecutar el bot
python main.py
```

## Formatos Soportados

El bot puede procesar los siguientes formatos de archivo:
- **PDF** (con texto extraíble o escaneados)
- **Imágenes**: JPG, JPEG, PNG, GIF

Los archivos escaneados y las imágenes son procesados usando OCR (Reconocimiento Óptico de Caracteres) con Tesseract.
