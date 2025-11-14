# 📦 Instrucciones de Build y Distribución - GolloBot

## 🔨 Crear el Ejecutable

### Windows
```cmd
build_exe.bat
```

### Linux/Mac
```bash
./build_exe.sh
```

---

## 📁 Estructura de Archivos

Después del build, encontrarás en la carpeta `dist/`:

```
dist/
├── GolloBot.exe         # Ejecutable principal (Windows)
│   o GolloBot           # Ejecutable principal (Linux/Mac)
└── config.json          # Archivo de configuración (editable por usuario)
```

---

## 🚀 Distribución al Usuario Final

### 1. Archivos a entregar:

- ✅ `GolloBot.exe` (o `GolloBot` en Linux/Mac)
- ✅ `config.json`

### 2. Instrucciones para el usuario:

1. **Copiar ambos archivos** al mismo directorio
2. **Editar `config.json`** con sus credenciales y parámetros:

```json
{
    "search_params": {
        "caso1": "Gollo",
        "titular_correo": "@fruno.com"
    },
    "provider": "Gmail",
    "email": "tu-email@ejemplo.com",
    "password": "tu contraseña de aplicación",
    "cc_users": [
        "usuario1@ejemplo.com",
        "usuario2@ejemplo.com"
    ]
}
```

3. **Ejecutar el programa**:
   - Windows: Doble clic en `GolloBot.exe`
   - Linux/Mac: `./GolloBot` desde terminal

---

## 🔧 Configuración de `config.json`

### Parámetros principales:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `search_params.caso1` | Palabra clave para detectar emails del Caso 1 | `"Gollo"` |
| `search_params.titular_correo` | Dominio de correos válidos | `"@fruno.com"` |
| `provider` | Proveedor de email (Gmail, Outlook, etc.) | `"Gmail"` |
| `email` | Correo electrónico del bot | `"bot@ejemplo.com"` |
| `password` | Contraseña de aplicación (no la contraseña normal) | `"abcd efgh ijkl mnop"` |
| `cc_users` | Lista de correos en copia (CC) | `["user@ejemplo.com"]` |

---

## ⚠️ IMPORTANTE: Archivos Empaquetados vs Externos

### 📦 Archivos DENTRO del ejecutable:
- `config_categorias.json` - Configuración de categorías de productos (NO editable por usuario)
- Todos los módulos Python y dependencias
- Modelos de EasyOCR y PyTorch

### 📝 Archivos EXTERNOS (al lado del .exe):
- `config.json` - Configuración del bot (EDITABLE por usuario)
- Este archivo DEBE estar en el mismo directorio que el ejecutable

---

## 🐛 Solución de Problemas

### Error: "Email no coincide con ningún caso"

**Causa**: El archivo `config.json` no está en el mismo directorio que el ejecutable.

**Solución**:
1. Verifica que `config.json` esté en el mismo directorio que `GolloBot.exe`
2. Verifica que `search_params.caso1` tenga el valor correcto (ej: `"Gollo"`)
3. Asegúrate de que el asunto del email contenga esa palabra

### Error: "Archivo de configuración no encontrado"

**Causa**: El bot no puede encontrar `config.json`

**Solución**:
```
✓ Estructura correcta:
C:\Bot\
  ├── GolloBot.exe
  └── config.json

✗ Estructura incorrecta:
C:\Bot\
  ├── GolloBot.exe
C:\OtraCarpeta\
  └── config.json
```

### El bot lee correos pero no los procesa

**Causa**: Las palabras clave en `config.json` no coinciden con los asuntos

**Solución**:
- Verifica que el asunto del email contenga la palabra clave exacta definida en `search_params.caso1`
- Ejemplo: Si `caso1: "Gollo"`, el asunto debe contener "Gollo" (no case-sensitive)

---

## 📋 Checklist de Distribución

Antes de entregar al usuario:

- [ ] Ejecutable compilado correctamente
- [ ] `config.json` incluido con valores de ejemplo
- [ ] Instrucciones de configuración proporcionadas
- [ ] Usuario sabe cómo obtener contraseña de aplicación (si usa Gmail)
- [ ] Ambos archivos en el mismo directorio
- [ ] Probado en entorno similar al del usuario

---

## 🔐 Obtener Contraseña de Aplicación (Gmail)

Para usar Gmail, el usuario necesita una **contraseña de aplicación**:

1. Ir a https://myaccount.google.com/security
2. Activar "Verificación en 2 pasos" (si no está activada)
3. Ir a "Contraseñas de aplicaciones"
4. Generar nueva contraseña para "Correo"
5. Copiar la contraseña generada (formato: `xxxx xxxx xxxx xxxx`)
6. Usar esa contraseña en `config.json`

---

## 📞 Soporte

Si el usuario experimenta problemas:

1. Verificar que `config.json` esté correctamente configurado
2. Verificar que ambos archivos estén en el mismo directorio
3. Revisar los logs del bot para mensajes de error específicos
4. Contactar al equipo de desarrollo con los logs
