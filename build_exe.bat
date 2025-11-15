@echo off
REM ================================================================
REM Script de Build para GolloBot
REM Crea el ejecutable con PyInstaller incluyendo todos los recursos
REM ================================================================

echo.
echo ================================================================
echo         BUILD GOLLOBOT - PYINSTALLER
echo ================================================================
echo.

REM Limpiar builds anteriores
echo [1/4] Limpiando builds anteriores...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "GolloBot.spec" del /q GolloBot.spec
echo     ✓ Limpieza completada
echo.

REM Ejecutar PyInstaller
echo [2/4] Ejecutando PyInstaller...
pyinstaller --onefile --console ^
  --name="GolloBot" ^
  --paths=. ^
  --hidden-import=logger ^
  --hidden-import=settings ^
  --hidden-import=config_manager ^
  --hidden-import=email_manager ^
  --hidden-import=case_handler ^
  --hidden-import=case1 ^
  --hidden-import=base_case ^
  --hidden-import=utils ^
  --hidden-import=gui_async_helper ^
  --hidden-import=main_gui_integrado ^
  --hidden-import=tkinter ^
  --hidden-import=tkinter.ttk ^
  --hidden-import=PIL ^
  --hidden-import=pdfplumber ^
  --hidden-import=numpy ^
  --hidden-import=httpx ^
  --hidden-import=structlog ^
  --hidden-import=tenacity ^
  --hidden-import=dotenv ^
  --hidden-import=imaplib ^
  --hidden-import=smtplib ^
  --hidden-import=requests ^
  --collect-all=easyocr ^
  --collect-all=torch ^
  --collect-all=torchvision ^
  --collect-data=easyocr ^
  --collect-data=torch ^
  --copy-metadata=easyocr ^
  --copy-metadata=torch ^
  main.py

if errorlevel 1 (
    echo.
    echo ❌ ERROR: PyInstaller falló
    pause
    exit /b 1
)

echo     ✓ Build completado
echo.

REM Copiar archivos de configuración al directorio dist
echo [3/4] Copiando archivos de configuración...
if exist "config.json" (
    copy /y "config.json" "dist\config.json"
    echo     ✓ config.json copiado a dist\
) else (
    echo     ⚠️  config.json no encontrado - crear manualmente
)
if exist "config_categorias.json" (
    copy /y "config_categorias.json" "dist\config_categorias.json"
    echo     ✓ config_categorias.json copiado a dist\
) else (
    echo     ⚠️  config_categorias.json no encontrado - se creará automáticamente
)
echo.

REM Mostrar resultados
echo [4/4] Build finalizado exitosamente
echo.
echo ================================================================
echo                    BUILD COMPLETADO
echo ================================================================
echo.
echo 📁 Ubicación del ejecutable:
echo    dist\GolloBot.exe
echo.
echo 📋 Archivos necesarios para distribución:
echo    - dist\GolloBot.exe          (ejecutable)
echo    - dist\config.json           (configuración editable)
echo    - dist\config_categorias.json (palabras clave categorías - editable)
echo.
echo 💡 Instrucciones:
echo    1. Copie los archivos de dist\ al directorio de destino
echo    2. Configure config.json con los parámetros del usuario
echo    3. Configure config_categorias.json con las palabras clave (opcional)
echo    4. Ejecute GolloBot.exe
echo.
echo ================================================================
echo.

pause
