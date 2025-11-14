#!/bin/bash
# ================================================================
# Script de Build para GolloBot
# Crea el ejecutable con PyInstaller incluyendo todos los recursos
# ================================================================

echo ""
echo "================================================================"
echo "         BUILD GOLLOBOT - PYINSTALLER"
echo "================================================================"
echo ""

# Limpiar builds anteriores
echo "[1/4] Limpiando builds anteriores..."
rm -rf dist build GolloBot.spec
echo "    ✓ Limpieza completada"
echo ""

# Ejecutar PyInstaller
echo "[2/4] Ejecutando PyInstaller..."
pyinstaller --onefile --console \
  --name="GolloBot" \
  --paths=. \
  --add-data "config_categorias.json:." \
  --hidden-import=logger \
  --hidden-import=settings \
  --hidden-import=config_manager \
  --hidden-import=email_manager \
  --hidden-import=case_handler \
  --hidden-import=case1 \
  --hidden-import=base_case \
  --hidden-import=utils \
  --hidden-import=gui_async_helper \
  --hidden-import=main_gui_integrado \
  --hidden-import=tkinter \
  --hidden-import=tkinter.ttk \
  --hidden-import=PIL \
  --hidden-import=pdfplumber \
  --hidden-import=numpy \
  --hidden-import=httpx \
  --hidden-import=structlog \
  --hidden-import=tenacity \
  --hidden-import=dotenv \
  --hidden-import=imaplib \
  --hidden-import=smtplib \
  --hidden-import=requests \
  --collect-all=easyocr \
  --collect-all=torch \
  --collect-all=torchvision \
  --collect-data=easyocr \
  --collect-data=torch \
  --copy-metadata=easyocr \
  --copy-metadata=torch \
  main.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ERROR: PyInstaller falló"
    exit 1
fi

echo "    ✓ Build completado"
echo ""

# Copiar config.json de ejemplo al directorio dist
echo "[3/4] Copiando archivo de configuración..."
if [ -f "config.json" ]; then
    cp config.json dist/config.json
    echo "    ✓ config.json copiado a dist/"
else
    echo "    ⚠️  config.json no encontrado - crear manualmente"
fi
echo ""

# Dar permisos de ejecución
chmod +x dist/GolloBot

# Mostrar resultados
echo "[4/4] Build finalizado exitosamente"
echo ""
echo "================================================================"
echo "                    BUILD COMPLETADO"
echo "================================================================"
echo ""
echo "📁 Ubicación del ejecutable:"
echo "   dist/GolloBot"
echo ""
echo "📋 Archivos necesarios para distribución:"
echo "   - dist/GolloBot          (ejecutable)"
echo "   - dist/config.json       (configuración editable)"
echo ""
echo "💡 Instrucciones:"
echo "   1. Copie GolloBot y config.json al directorio de destino"
echo "   2. Configure config.json con los parámetros del usuario"
echo "   3. Ejecute ./GolloBot"
echo ""
echo "================================================================"
echo ""
