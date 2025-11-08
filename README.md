## Instalación

### Dependencias Python

```bash
# Instalar dependencias
pip install -r requirements.txt
```

### Sistema de Extracción Híbrido de PDFs

Este proyecto utiliza un **sistema híbrido inteligente** para extraer texto de PDFs:

1. **Método Primario (Rápido)**: Extracción de texto nativo usando `pdfplumber`
   - Funciona con PDFs generados digitalmente (ej: Oracle Reports, Word, etc.)
   - Muy rápido y eficiente
   - No requiere dependencias del sistema

2. **Método de Respaldo (Robusto)**: OCR usando `pytesseract` y `pdf2image`
   - Se activa automáticamente si el método primario falla o no encuentra texto
   - Funciona con PDFs escaneados, imágenes, o PDFs sin texto embebido
   - Requiere Tesseract OCR instalado en el sistema

### Instalación de Tesseract OCR (Requerido para OCR)

El sistema funciona sin Tesseract usando solo extracción nativa, pero para máxima compatibilidad se recomienda instalarlo:

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils
```

#### macOS
```bash
brew install tesseract tesseract-lang poppler
```

#### Windows
1. Descargar el instalador desde: https://github.com/UB-Mannheim/tesseract/wiki
2. Instalar y agregar Tesseract al PATH del sistema
3. Descargar paquete de idioma español si es necesario

#### Verificar Instalación
```bash
tesseract --version
```

### Ejecución

```bash
python main.py
```

El sistema detectará automáticamente qué método de extracción usar para cada PDF.
