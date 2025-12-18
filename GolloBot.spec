# -*- mode: python ; coding: utf-8 -*-
"""
GolloBot - PyInstaller Spec File
=================================

Este archivo spec contiene la configuración completa para generar
el ejecutable de GolloBot usando PyInstaller.

Uso:
    pyinstaller GolloBot.spec

Autor: GolloBot Team
Fecha: 2024
"""

import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

# ================================================================
# CONFIGURACIÓN DE DATOS Y MÓDULOS
# ================================================================

# Recopilar todos los archivos de EasyOCR
easyocr_datas = []
easyocr_binaries = []
easyocr_hiddenimports = []
try:
    tmp = collect_all('easyocr')
    easyocr_datas += tmp[0]
    easyocr_binaries += tmp[1]
    easyocr_hiddenimports += tmp[2]
except:
    pass

# Recopilar todos los archivos de PyTorch
torch_datas = []
torch_binaries = []
torch_hiddenimports = []
try:
    tmp = collect_all('torch')
    torch_datas += tmp[0]
    torch_binaries += tmp[1]
    torch_hiddenimports += tmp[2]
except:
    pass

# Recopilar todos los archivos de TorchVision
torchvision_datas = []
torchvision_binaries = []
torchvision_hiddenimports = []
try:
    tmp = collect_all('torchvision')
    torchvision_datas += tmp[0]
    torchvision_binaries += tmp[1]
    torchvision_hiddenimports += tmp[2]
except:
    pass

# Metadatos
easyocr_metadata = copy_metadata('easyocr') if 'easyocr' in sys.modules or True else []
torch_metadata = copy_metadata('torch') if 'torch' in sys.modules or True else []

# ================================================================
# ARCHIVOS DE DATOS A INCLUIR
# ================================================================

datas = [
    ('config_categorias.json', '.'),  # Archivo de configuración de categorías
]

# Agregar todos los datos recopilados
datas += easyocr_datas
datas += torch_datas
datas += torchvision_datas
datas += easyocr_metadata
datas += torch_metadata

# ================================================================
# MÓDULOS OCULTOS (HIDDEN IMPORTS)
# ================================================================

hiddenimports = [
    # Módulos del proyecto
    'logger',
    'settings',
    'config_manager',
    'email_manager',
    'case_handler',
    'case1',
    'base_case',
    'utils',
    'gui_async_helper',
    'main_gui_integrado',

    # Interfaz gráfica
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.scrolledtext',

    # Procesamiento de imágenes
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'PIL.ImageFont',

    # PDFs
    'pdfplumber',

    # Matemáticas y arrays
    'numpy',
    'numpy.core',
    'numpy.core.multiarray',

    # HTTP y requests
    'httpx',
    'requests',
    'urllib3',

    # Logging estructurado
    'structlog',

    # Reintentos
    'tenacity',

    # Variables de entorno
    'dotenv',

    # Email
    'imaplib',
    'smtplib',
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    'email.mime.base',
    'email.encoders',
]

# Agregar imports ocultos recopilados
hiddenimports += easyocr_hiddenimports
hiddenimports += torch_hiddenimports
hiddenimports += torchvision_hiddenimports

# ================================================================
# BINARIOS
# ================================================================

binaries = []
binaries += easyocr_binaries
binaries += torch_binaries
binaries += torchvision_binaries

# ================================================================
# ANÁLISIS (Analysis)
# ================================================================

a = Analysis(
    ['main.py'],                    # Script principal
    pathex=['.'],                   # Paths adicionales
    binaries=binaries,              # Binarios a incluir
    datas=datas,                    # Archivos de datos
    hiddenimports=hiddenimports,    # Imports ocultos
    hookspath=[],                   # Hooks personalizados
    hooksconfig={},                 # Configuración de hooks
    runtime_hooks=[],               # Runtime hooks
    excludes=[],                    # Módulos a excluir
    noarchive=False,                # Archivar o no
    optimize=0,                     # Nivel de optimización (0, 1, 2)
)

# ================================================================
# PYZ (Python ZIP Archive)
# ================================================================

pyz = PYZ(
    a.pure,                         # Módulos Python puros
    a.zipped_data,                  # Datos zippeados
)

# ================================================================
# EXE (Ejecutable)
# ================================================================

exe = EXE(
    pyz,                            # PYZ archive
    a.scripts,                      # Scripts
    a.binaries,                     # Binarios
    a.datas,                        # Datos
    [],                             # Excludes
    name='GolloBot',                # Nombre del ejecutable
    debug=False,                    # Debug mode (False para producción)
    bootloader_ignore_signals=False,
    strip=False,                    # Strip symbols (solo Linux/Mac)
    upx=True,                       # Usar UPX para comprimir (True si está instalado)
    upx_exclude=[],                 # Archivos a excluir de UPX
    runtime_tmpdir=None,            # Directorio temporal en runtime
    console=True,                   # Mostrar consola (True para ver logs)
    disable_windowed_traceback=False,
    argv_emulation=False,           # Emulación de argv (Mac)
    target_arch=None,               # Arquitectura objetivo
    codesign_identity=None,         # Identidad de firma de código (Mac)
    entitlements_file=None,         # Archivo de entitlements (Mac)
    # icon='icon.ico',              # Descomente y configure si tiene un ícono
)

# ================================================================
# COLLECT (Solo para --onedir, no --onefile)
# ================================================================
# Si desea generar un directorio en lugar de un solo archivo,
# descomente las siguientes líneas y comente el EXE de arriba:

# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='GolloBot',
# )

# ================================================================
# NOTAS DE CONFIGURACIÓN
# ================================================================
"""
OPCIONES CONFIGURABLES:

1. Modo de ejecución:
   - console=True: Muestra la ventana de consola (recomendado para debug)
   - console=False: Oculta la consola (solo para producción)

2. Compresión:
   - upx=True: Comprime el ejecutable (requiere UPX instalado)
   - upx=False: No comprime (ejecutable más grande pero más rápido de generar)

3. Optimización:
   - optimize=0: Sin optimización
   - optimize=1: Optimización básica
   - optimize=2: Optimización máxima

4. Para agregar un ícono:
   - Descomente la línea: # icon='icon.ico'
   - Coloque su archivo icon.ico en el directorio raíz

5. Para modo onedir (directorio en lugar de archivo único):
   - Comente la sección EXE actual
   - Descomente la sección COLLECT

ARCHIVOS ADICIONALES:
   Para incluir archivos adicionales, agregue a la lista 'datas':

   datas = [
       ('archivo.json', '.'),
       ('carpeta/*', 'carpeta'),
   ]

MÓDULOS OCULTOS ADICIONALES:
   Si PyInstaller no detecta algún módulo, agrégelo a 'hiddenimports':

   hiddenimports = [
       'modulo_no_detectado',
   ]

EXCLUSIONES:
   Para excluir módulos no necesarios y reducir tamaño:

   excludes = [
       'matplotlib',
       'pandas',
   ]
"""
