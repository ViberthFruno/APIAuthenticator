# 📝 Cómo Agregar Nuevos Casos al Bot

## 🎯 Contexto

El bot utiliza un sistema de casos para procesar diferentes tipos de correos. Cada caso es un módulo Python independiente que hereda de `BaseCase`.

---

## ⚠️ Importante para PyInstaller

Debido a que usamos PyInstaller con `--onefile`, **NO podemos cargar casos dinámicamente**. Debemos importarlos explícitamente en `case_handler.py`.

---

## 📋 Pasos para Agregar un Nuevo Caso

### 1. Crear el archivo del caso

Crea un nuevo archivo `case2.py` (o `case3.py`, etc.) en la raíz del proyecto:

```python
# case2.py
from base_case import BaseCase

class Case(BaseCase):
    def __init__(self):
        super().__init__(
            name="Caso 2",
            description="Descripción del caso 2",
            config_key="caso2",  # ← Importante: debe coincidir con config.json
            response_message="Mensaje de respuesta automática",
        )

    def process_email(self, email_data, logger):
        """Procesa el email según la lógica del caso"""
        try:
            sender = email_data.get('sender', '')
            subject = email_data.get('subject', '')
            attachments = email_data.get('attachments', [])

            logger.info(f"Procesando {self._config_key} para {sender}")

            # Tu lógica personalizada aquí
            # ...

            response = {
                'recipient': sender,
                'subject': f"Re: {subject}",
                'body': self._response_message
            }

            return response

        except Exception as e:
            logger.exception(f"Error al procesar {self._config_key}: {str(e)}")
            return None
```

### 2. Registrar el caso en `case_handler.py`

**IMPORTANTE:** Abre `case_handler.py` y agrega el import:

```python
# Importar casos explícitamente (necesario para PyInstaller)
try:
    import case1
    import case2  # ← AGREGAR AQUÍ
    AVAILABLE_CASES = {
        'case1': case1,
        'case2': case2  # ← AGREGAR AQUÍ
    }
    print("[DEBUG CaseHandler] Casos importados explícitamente:", list(AVAILABLE_CASES.keys()))
except ImportError as e:
    print(f"[DEBUG CaseHandler] ⚠️ Error al importar casos: {e}")
    AVAILABLE_CASES = {}
```

### 3. Configurar en `config.json`

Agrega la palabra clave del nuevo caso en `search_params`:

```json
{
    "search_params": {
        "caso1": "Gollo",
        "caso2": "MiPalabraClave"
    },
    "provider": "Gmail",
    "email": "tu-email@ejemplo.com",
    "password": "tu contraseña",
    "cc_users": []
}
```

### 4. Actualizar PyInstaller (si es necesario)

Si el nuevo caso tiene dependencias especiales, agrégalas en `build_exe.bat` / `build_exe.sh`:

```bash
--hidden-import=case2 \
```

### 5. Recompilar

Ejecuta el script de build:

```bash
# Windows
build_exe.bat

# Linux/Mac
./build_exe.sh
```

---

## 📚 Estructura de un Caso

### Métodos heredados de `BaseCase`:

- `get_name()` - Retorna el nombre del caso
- `get_description()` - Retorna la descripción
- `get_search_keywords()` - Obtiene las palabras clave desde config.json
- `get_response_message()` - Retorna el mensaje de respuesta
- `process_email(email_data, logger)` - **DEBE ser implementado** (lógica del caso)

### Datos disponibles en `email_data`:

```python
{
    'sender': 'remitente@ejemplo.com',
    'subject': 'Asunto del correo',
    'msg_id': '12345',
    'attachments': [
        {
            'filename': 'archivo.pdf',
            'data': b'...',  # bytes del archivo
            'content_type': 'application/pdf'
        }
    ],
    'body_text': 'Texto del cuerpo del correo',
    'garantia_correo': {
        'encontrada': True,
        'garantia': 'Normal'  # o 'No', 'C.S.R', etc.
    },
    'proveedor_correo': {
        'encontrado': True,
        'distribuidor_id': 'uuid...',
        'distribuidor_nombre': 'MobilePro'
    }
}
```

### Estructura del response:

```python
{
    'recipient': 'destinatario@ejemplo.com',
    'subject': 'Re: Asunto',
    'body': 'Cuerpo del mensaje',
    'attachments': [  # Opcional
        {
            'filename': 'respuesta.txt',
            'data': b'...'
        }
    ],
    'extracted_data': {  # Opcional - para correos CC
        'numero_boleta': '123',
        'nombre_cliente': 'Juan Pérez',
        # ... más datos
    },
    'pdf_original': {  # Opcional - para correos CC
        'filename': 'original.pdf',
        'data': b'...'
    }
}
```

---

## ✅ Checklist de Implementación

Antes de considerar el caso completo:

- [ ] Archivo `caseN.py` creado con clase `Case`
- [ ] Caso importado en `case_handler.py`
- [ ] `config_key` agregado en `config.json`
- [ ] Lógica de `process_email()` implementada
- [ ] Probado en desarrollo (PyCharm)
- [ ] Compilado con PyInstaller
- [ ] Probado como ejecutable
- [ ] Documentación actualizada

---

## 🐛 Debugging

Si el caso no se carga:

1. Verifica que aparezca en los logs:
   ```
   [DEBUG CaseHandler] Casos importados explícitamente: ['case1', 'case2']
   [DEBUG CaseHandler] ✓ Caso cargado: case2
   ```

2. Verifica que la palabra clave esté en config.json:
   ```
   [DEBUG caso2] Keyword para 'caso2': 'MiPalabraClave'
   ```

3. Verifica que haga match:
   ```
   [DEBUG CaseHandler] Keywords para case2: ['MiPalabraClave']
   [DEBUG CaseHandler] ✓ MATCH encontrado!
   ```

---

## 🔄 Ejemplo Completo: Caso Simple

```python
# case_simple.py
from base_case import BaseCase

class Case(BaseCase):
    def __init__(self):
        super().__init__(
            name="Caso Simple",
            description="Responde con un mensaje simple",
            config_key="caso_simple",
            response_message="Gracias por tu correo. Lo procesaremos pronto.",
        )

    def process_email(self, email_data, logger):
        """Solo responde con el mensaje predefinido"""
        sender = email_data.get('sender', '')
        subject = email_data.get('subject', '')

        logger.info(f"Procesando caso simple para {sender}")

        return {
            'recipient': sender,
            'subject': f"Re: {subject}",
            'body': self._response_message
        }
```

Luego registrar en `case_handler.py` y en `config.json` con `"caso_simple": "Consulta"`.

---

## 📞 Soporte

Si tienes problemas al agregar un caso:

1. Revisa los logs de debugging
2. Verifica que el import funcione en Python normal
3. Asegúrate de recompilar con PyInstaller
4. Verifica que config.json tenga la entrada correcta
