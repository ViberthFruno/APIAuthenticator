# 📚 Guía de Configuración de Categorías

## 🎯 Resumen del Problema Solucionado

El problema era que las categorías en `config_categorias.json` **no coincidían** con las categorías hardcodeadas en el código. Esto causaba que las palabras clave no se cargaran correctamente en el ejecutable.

### Antes (❌ Problema):
- **config_categorias.json tenía:** Laptop, Desktop, Tablet, Celular, Monitor, Impresora...
- **El código esperaba:** Móviles, Hogar, Cómputo, Accesorios, Transporte, Seguridad, etc.
- **Resultado:** Las palabras clave NO se cargaban porque los nombres no coincidían.

### Después (✅ Solucionado):
- **config_categorias.json ahora tiene:** Móviles, Hogar, Cómputo, Accesorios, Transporte, Seguridad, Entretenimiento, Telecomunicaciones, No encontrado
- **Coincide con el código:** Las categorías ahora coinciden exactamente
- **Resultado:** Las palabras clave se cargan correctamente tanto en PyCharm como en el ejecutable

---

## 📋 Categorías Disponibles

El sistema maneja estas categorías con sus respectivos IDs:

| Categoría | ID | Descripción |
|-----------|----|-----------|
| **Móviles** | 1 | Celulares, smartphones, teléfonos |
| **Hogar** | 3 | Electrodomésticos y productos del hogar |
| **Cómputo** | 4 | Laptops, PCs, tablets, monitores, impresoras |
| **Desconocido** | 5 | Productos sin categoría definida |
| **Accesorios** | 6 | Cables, cargadores, fundas, audífonos |
| **Transporte** | 7 | Scooters, bicicletas eléctricas, hoverboards |
| **Seguridad** | 8 | Cámaras, alarmas, sensores |
| **Entretenimiento** | 10 | TVs, parlantes, consolas, proyectores |
| **Telecomunicaciones** | 11 | Routers, módems, antenas, switches |
| **No encontrado** | 12 | Cuando no se encuentra ninguna coincidencia |

---

## 🔧 Cómo Funciona la Detección de Categorías

1. **Extracción de Descripción:** El sistema extrae la descripción del producto desde el PDF.

2. **Búsqueda de Palabras Clave:** Busca en todas las palabras clave configuradas en `config_categorias.json`.

3. **Priorización:** Las palabras clave **más largas tienen prioridad** (más específicas).
   - Ejemplo: "CABLE USB" se detecta antes que "CABLE"

4. **Coincidencia:** Si la palabra clave está contenida en la descripción (case-insensitive), se asigna esa categoría.

5. **Fallback:** Si no se encuentra ninguna coincidencia, se asigna la categoría "No encontrado" (ID: 12).

---

## ⚙️ Cómo Agregar/Editar Palabras Clave

### Opción 1: Desde la GUI (Recomendado)

1. Abre la aplicación GolloBot
2. Haz clic en el botón **"Editar Categorías"**
3. Selecciona una categoría de la lista izquierda
4. Agrega o elimina palabras clave en el panel derecho
5. Haz clic en **"Guardar Cambios"**

### Opción 2: Editando el JSON directamente

Edita el archivo `config_categorias.json`:

```json
{
  "categorias": {
    "Móviles": {
      "id": 1,
      "palabras_clave": [
        {
          "palabra": "CELULAR",
          "tipo_dispositivo_id": 7
        },
        {
          "palabra": "SMARTPHONE",
          "tipo_dispositivo_id": 7
        }
      ]
    }
  }
}
```

**IMPORTANTE:**
- Las palabras clave deben estar en **MAYÚSCULAS**
- El campo `tipo_dispositivo_id` siempre debe ser `7` (Desconocido)
- El nombre de la categoría debe coincidir **exactamente** con las categorías listadas arriba

---

## 🧪 Cómo Probar que Funciona

### En Desarrollo (PyCharm):

```bash
python test_config_categorias.py
```

Deberías ver:
- ✓ Todas las categorías cargadas correctamente
- ✓ Las palabras clave se importan
- ✓ Las pruebas de detección pasan

### En el Ejecutable:

1. Compila el proyecto:
   ```bash
   build_exe.bat   # En Windows
   ./build_exe.sh  # En Linux
   ```

2. Verifica que `config_categorias.json` esté en el directorio `dist/`

3. Ejecuta el ejecutable y prueba que la detección funcione

4. Opcionalmente, copia `test_config_categorias.py` a `dist/` y ejecútalo para verificar

---

## 🐛 Solución de Problemas

### Problema: Las palabras clave no se cargan en el ejecutable

**Solución:**
1. Verifica que `config_categorias.json` esté en el mismo directorio que el ejecutable
2. Asegúrate de que las categorías en el JSON coincidan exactamente con las del código
3. Verifica que el JSON esté bien formateado (sin errores de sintaxis)

### Problema: La detección asigna la categoría incorrecta

**Posibles causas:**
1. **Palabras ambiguas:** Una palabra clave muy corta (ej: "PC") puede coincidir en muchos productos
   - **Solución:** Usa palabras más específicas o más largas

2. **Orden de prioridad:** Las palabras más largas tienen prioridad
   - **Solución:** Esto es intencional, asegúrate de que tus palabras clave sean lo suficientemente específicas

3. **Case-insensitive:** "LAPTOP", "laptop" y "Laptop" son equivalentes
   - **Solución:** Mantén las palabras en MAYÚSCULAS para consistencia

### Problema: El archivo config_categorias.json no existe

**Solución:**
- El sistema crea automáticamente el archivo con valores por defecto si no existe
- Si necesitas forzar la recreación, elimina el archivo y reinicia la aplicación

---

## 📁 Archivos Relevantes

- `config_categorias.json` - Configuración de categorías y palabras clave (editable por el usuario)
- `config_manager.py` - Gestiona la carga y guardado del archivo JSON
- `api_integration/domain/builders/crear_preingreso_builder.py` - Contiene la lógica de detección de categorías
- `main_gui_integrado.py` - Interfaz gráfica con el editor de categorías
- `test_config_categorias.py` - Script de prueba para verificar la configuración
- `build_exe.bat` / `build_exe.sh` - Scripts de compilación que copian el JSON al ejecutable

---

## ✅ Checklist de Verificación

- [ ] El archivo `config_categorias.json` existe
- [ ] Las categorías coinciden con las del código
- [ ] Todas las palabras clave están en MAYÚSCULAS
- [ ] El JSON está bien formateado
- [ ] Las pruebas con `test_config_categorias.py` pasan en desarrollo
- [ ] El archivo JSON se copia a `dist/` durante la compilación
- [ ] Las pruebas pasan en el ejecutable
- [ ] La detección de categorías funciona correctamente en la aplicación

---

## 🚀 Próximos Pasos

1. **Compila el ejecutable** con `build_exe.bat` o `build_exe.sh`
2. **Prueba la aplicación** con casos reales
3. **Ajusta las palabras clave** según sea necesario
4. **Agrega nuevas palabras clave** para mejorar la detección

---

## 📞 Soporte

Si tienes problemas:
1. Ejecuta `test_config_categorias.py` para diagnóstico
2. Revisa los mensajes de debug en la consola (busca `[DEBUG ConfigManager]` y `[DEBUG CrearPreingresoBuilder]`)
3. Verifica que el archivo JSON esté bien formateado

---

**Última actualización:** 2025-11-18
