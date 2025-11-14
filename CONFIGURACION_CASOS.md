# Configuración de Casos - Bot de Correo

## 📋 Descripción

El bot ahora soporta detección flexible de correos mediante **palabras clave** (keywords) y **dominios de remitente** (senders).

## 🎯 Lógica de Detección

El bot evalúa cada correo de la siguiente manera:

1. **Si el caso tiene keywords Y senders**: Valida que AMBOS coincidan (AND)
2. **Si solo tiene keywords**: Valida solo las palabras clave en el asunto
3. **Si solo tiene senders**: Valida solo el dominio del remitente
4. **Si no tiene ninguno**: El caso no se activará

## 📝 Formato de Configuración

### Formato Nuevo (Recomendado)

```json
{
    "search_params": {
        "caso1": {
            "keywords": ["Gollo", "Factura", "Boleta"],
            "senders": ["@fruno.com", "@gollo.com"]
        }
    }
}
```

### Formato Antiguo (Retrocompatible)

```json
{
    "search_params": {
        "caso1": "Gollo"
    }
}
```

## 💡 Ejemplos de Uso

### Ejemplo 1: Solo Palabras Clave
**Caso de uso**: Procesar correos que contengan "Gollo" en el asunto, sin importar el remitente.

```json
{
    "search_params": {
        "caso1": {
            "keywords": ["Gollo"]
        }
    }
}
```

✅ Detectará:
- `Asunto: "Boleta de Gollo" | Remitente: cualquiera@ejemplo.com`
- `Asunto: "GOLLO - Reparación" | Remitente: otro@gmail.com`

❌ NO detectará:
- `Asunto: "Factura de compra" | Remitente: cualquiera@ejemplo.com`

---

### Ejemplo 2: Solo Dominios de Remitente
**Caso de uso**: Procesar todos los correos de @fruno.com, sin importar el asunto.

```json
{
    "search_params": {
        "caso1": {
            "senders": ["@fruno.com"]
        }
    }
}
```

✅ Detectará:
- `Asunto: cualquier cosa | Remitente: usuario@fruno.com`
- `Asunto: sin palabras clave | Remitente: otro.usuario@fruno.com`

❌ NO detectará:
- `Asunto: cualquier cosa | Remitente: externo@gmail.com`

---

### Ejemplo 3: Palabras Clave + Dominios (AND)
**Caso de uso**: Procesar correos que contengan "Gollo" en el asunto Y vengan de @fruno.com.

```json
{
    "search_params": {
        "caso1": {
            "keywords": ["Gollo"],
            "senders": ["@fruno.com"]
        }
    }
}
```

✅ Detectará:
- `Asunto: "Boleta de Gollo" | Remitente: viberth@fruno.com` ✅

❌ NO detectará:
- `Asunto: "Boleta de Gollo" | Remitente: externo@gmail.com` (falta dominio)
- `Asunto: "Otra cosa" | Remitente: usuario@fruno.com` (falta keyword)

---

### Ejemplo 4: Múltiples Palabras Clave
**Caso de uso**: Procesar correos con diferentes palabras clave.

```json
{
    "search_params": {
        "caso1": {
            "keywords": ["Gollo", "Factura", "Boleta", "Reparación"]
        }
    }
}
```

✅ Detectará cualquier correo que contenga AL MENOS UNA de estas palabras:
- `Asunto: "Gollo - Reparación"`
- `Asunto: "Factura de compra"`
- `Asunto: "Boleta #12345"`

---

### Ejemplo 5: Múltiples Dominios
**Caso de uso**: Procesar correos de diferentes dominios autorizados.

```json
{
    "search_params": {
        "caso1": {
            "keywords": ["Gollo"],
            "senders": ["@fruno.com", "@gollo.com", "@proveedor.com"]
        }
    }
}
```

✅ Detectará correos con "Gollo" en el asunto que vengan de CUALQUIERA de estos dominios:
- `Asunto: "Gollo" | Remitente: usuario@fruno.com`
- `Asunto: "Gollo" | Remitente: admin@gollo.com`
- `Asunto: "Gollo" | Remitente: ventas@proveedor.com`

❌ NO detectará:
- `Asunto: "Gollo" | Remitente: externo@gmail.com`

---

### Ejemplo 6: Múltiples Casos Diferentes

```json
{
    "search_params": {
        "caso1": {
            "keywords": ["Gollo"],
            "senders": ["@fruno.com"]
        },
        "caso2": {
            "keywords": ["Factura", "Invoice"]
        },
        "caso3": {
            "senders": ["@proveedor.com", "@distribuidor.com"]
        }
    }
}
```

**Comportamiento**:
- **Caso 1**: Solo correos con "Gollo" en asunto Y de @fruno.com
- **Caso 2**: Correos con "Factura" o "Invoice" de cualquier remitente
- **Caso 3**: Todos los correos de @proveedor.com o @distribuidor.com

---

## 🔍 Búsqueda Case-Insensitive

La búsqueda NO distingue entre mayúsculas y minúsculas:

```json
"keywords": ["gollo", "GOLLO", "Gollo"]  // Todos detectan lo mismo
```

## 📧 Formato de Remitentes Aceptados

El campo `senders` acepta:
- Dominios completos: `"@fruno.com"`
- Correos específicos: `"viberth.gonzalez@fruno.com"`
- Subcadenas: `"@gmail.com"`, `"fruno"`

**Recomendación**: Usar `@dominio.com` para validar todos los correos de ese dominio.

## ⚠️ Notas Importantes

1. **Orden de evaluación**: El bot evalúa los casos en el orden que aparecen en `search_params`
2. **Primer match gana**: Se ejecuta el PRIMER caso que coincida
3. **Compatibilidad**: El formato antiguo (string simple) sigue funcionando
4. **Listas vacías**: `"keywords": []` o `"senders": []` se ignoran
5. **Substring match**: Las keywords y senders buscan coincidencias parciales, no exactas

## 🚀 Migración desde Formato Antiguo

### Antes:
```json
{
    "search_params": {
        "caso1": "Gollo"
    }
}
```

### Después (equivalente):
```json
{
    "search_params": {
        "caso1": {
            "keywords": ["Gollo"]
        }
    }
}
```

### Después (mejorado con validación de dominio):
```json
{
    "search_params": {
        "caso1": {
            "keywords": ["Gollo"],
            "senders": ["@fruno.com"]
        }
    }
}
```

## 📊 Logs de Detección

El bot genera logs informativos cuando detecta un caso:

```
INFO: Caso encontrado: caso1 | Keyword: 'Gollo' | Sender: '@fruno.com'
INFO: Caso encontrado: caso2 | Keyword: 'Factura'
INFO: Caso encontrado: caso3 | Sender: '@proveedor.com'
```

---

**Última actualización**: 2025-11-14
**Versión**: 2.0 - Sistema de detección flexible
