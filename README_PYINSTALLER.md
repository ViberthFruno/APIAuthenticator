# Generación de Ejecutable con PyInstaller - GolloBot

Este documento explica cómo generar el ejecutable de GolloBot usando PyInstaller.

## Tabla de Contenidos

- [Requisitos Previos](#requisitos-previos)
- [Métodos de Compilación](#métodos-de-compilación)
  - [Método 1: Scripts Automatizados (Recomendado)](#método-1-scripts-automatizados-recomendado)
  - [Método 2: Archivo .spec](#método-2-archivo-spec)
  - [Método 3: Comando Directo](#método-3-comando-directo)
- [Archivos de Distribución](#archivos-de-distribución)
- [Solución de Problemas](#solución-de-problemas)
- [Notas Importantes](#notas-importantes)

---

## Requisitos Previos

### 1. Instalar PyInstaller

```bash
pip install pyinstaller
```

### 2. Instalar todas las dependencias del proyecto

```bash
pip install -r requirements.txt
```

### 3. Verificar que la aplicación funcione correctamente

Antes de compilar, asegúrese de que la aplicación se ejecuta sin errores:

```bash
python main.py
```

---

## Métodos de Compilación

### Método 1: Scripts Automatizados (Recomendado)

Este es el método más simple y automatizado. Los scripts limpian builds anteriores, ejecutan PyInstaller y copian los archivos necesarios.

#### En Linux/Mac:

```bash
chmod +x build_exe.sh
./build_exe.sh
```

#### En Windows:

```cmd
build_exe.bat
```

**Ventajas:**
- Limpia automáticamente builds anteriores
- Copia archivos de configuración al directorio `dist/`
- Muestra mensajes de progreso claros
- Maneja errores adecuadamente

---

### Método 2: Archivo .spec

El archivo `.spec` permite una configuración más avanzada y reproducible del build.

#### Generar el ejecutable usando el .spec:

```bash
pyinstaller GolloBot.spec
```

**Ventajas:**
- Configuración centralizada y versionable
- Fácil de modificar y mantener
- Reproducible en diferentes entornos

#### Personalizar el archivo .spec:

Puede editar `GolloBot.spec` para:
- Agregar/quitar módulos ocultos (hidden imports)
- Modificar archivos de datos incluidos
- Cambiar el ícono del ejecutable
- Ajustar opciones de compilación

---

### Método 3: Comando Directo

Si prefiere ejecutar PyInstaller directamente con todas las opciones:

```bash
pyinstaller --onefile --console \
  --name="GolloBot" \
  --paths=. \
  --add-data "config_categorias.json;." \
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
```

#### En Windows, use `;` en lugar de `:` para --add-data:

```cmd
pyinstaller --onefile --console ^
  --name="GolloBot" ^
  --paths=. ^
  --add-data "config_categorias.json;." ^
  ... (resto de opciones igual)
```

---

## Archivos de Distribución

Después de la compilación exitosa, encontrará los siguientes archivos en el directorio `dist/`:

```
dist/
├── GolloBot              # Ejecutable (Linux/Mac)
├── GolloBot.exe          # Ejecutable (Windows)
├── config.json           # Configuración de la aplicación
└── config_categorias.json # Configuración de categorías
```

### Archivos necesarios para la distribución:

1. **GolloBot / GolloBot.exe** - El ejecutable principal
2. **config.json** - Archivo de configuración (editable por el usuario)
3. **config_categorias.json** - Configuración de palabras clave (opcional)
4. **.env** (opcional) - Variables de entorno si se usan

### Distribución a usuarios finales:

```
📦 Carpeta de distribución GolloBot/
├── GolloBot.exe
├── config.json
├── config_categorias.json
└── README.txt (instrucciones de uso)
```

---

## Solución de Problemas

### Error: Module not found

Si PyInstaller no encuentra un módulo:

1. Agregue el módulo a los `--hidden-import`:
   ```bash
   --hidden-import=nombre_del_modulo
   ```

2. O edite el archivo `GolloBot.spec` y agregue en la sección `hiddenimports`:
   ```python
   hiddenimports=['nombre_del_modulo']
   ```

### Error: File not found en el ejecutable

Si el ejecutable no encuentra archivos de datos:

1. Use `--add-data` para incluir archivos:
   ```bash
   --add-data "archivo.json;."
   ```

2. O edite `GolloBot.spec` en la sección `datas`:
   ```python
   datas=[('archivo.json', '.')]
   ```

### El ejecutable es muy grande

El ejecutable puede ser grande debido a PyTorch y EasyOCR. Para reducir el tamaño:

1. **Usar UPX** (compresor de ejecutables):
   ```bash
   pip install pyinstaller[upx]
   pyinstaller --onefile --upx-dir=/path/to/upx ...
   ```

2. **Excluir módulos no utilizados** editando el .spec

3. **Compilar sin PyTorch** si no se usa OCR

### Error al ejecutar en otra máquina

Si el ejecutable no funciona en otra PC:

1. **Windows**: Instale Visual C++ Redistributable
2. **Linux**: Compile en la distribución/versión más antigua posible
3. **Mac**: Considere las restricciones de firma de código de macOS

---

## Notas Importantes

### Opciones del comando PyInstaller explicadas:

- `--onefile`: Genera un solo archivo ejecutable
- `--console`: Muestra la consola (para ver logs)
- `--name="GolloBot"`: Nombre del ejecutable
- `--paths=.`: Agrega el directorio actual al path de Python
- `--add-data`: Incluye archivos de datos en el ejecutable
- `--hidden-import`: Importa módulos que PyInstaller no detecta automáticamente
- `--collect-all`: Recopila todos los archivos de un paquete
- `--collect-data`: Recopila archivos de datos de un paquete
- `--copy-metadata`: Copia metadatos de paquetes

### Para modo ventana (sin consola):

Si quiere ocultar la consola, cambie `--console` por `--windowed`:

```bash
pyinstaller --onefile --windowed ...
```

**Nota**: Esto ocultará los mensajes de error en consola.

### Para agregar un ícono:

```bash
pyinstaller --onefile --console --icon=icon.ico ...
```

### Verificación del build:

Después de compilar, verifique:

1. ✅ El ejecutable se genera en `dist/`
2. ✅ Los archivos de configuración están en `dist/`
3. ✅ El ejecutable se ejecuta sin errores
4. ✅ Todas las funcionalidades funcionan correctamente

---

## Limpieza de archivos temporales

Para limpiar los archivos temporales de PyInstaller:

### Linux/Mac:
```bash
rm -rf build dist *.spec
```

### Windows:
```cmd
rmdir /s /q build dist
del *.spec
```

---

## Recursos Adicionales

- [Documentación oficial de PyInstaller](https://pyinstaller.org/en/stable/)
- [PyInstaller - Opciones](https://pyinstaller.org/en/stable/usage.html)
- [PyInstaller - Spec files](https://pyinstaller.org/en/stable/spec-files.html)

---

## Changelog

- **v1.0.0**: Configuración inicial de PyInstaller para GolloBot
  - Soporte completo para PyTorch y EasyOCR
  - Inclusión de todos los módulos necesarios
  - Scripts automatizados de build

---

## Soporte

Si encuentra problemas durante la compilación:

1. Verifique que todas las dependencias estén instaladas
2. Asegúrese de que la aplicación funcione antes de compilar
3. Revise los logs de PyInstaller para ver errores específicos
4. Consulte la sección de [Solución de Problemas](#solución-de-problemas)

---

**Última actualización**: 2024
**Versión de PyInstaller recomendada**: 6.0+
