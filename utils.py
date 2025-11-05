from typing import Any


def strip_if_string(valor: Any) -> Any:
    if isinstance(valor, str):
        return valor.strip()
    return valor


# Función para formatear valores
def formatear_valor(valor):
    """Convierte valores a string legible"""
    if valor is None:
        return "N/A"
    elif isinstance(valor, bool):
        return "Sí" if valor else "No"
    elif isinstance(valor, list):
        # Si es una lista de diccionarios
        if valor and isinstance(valor[0], dict):
            items = []
            for item in valor:
                items.append(", ".join(f"{k}: {v}" for k, v in item.items()))
            return " | ".join(items)
        return ", ".join(str(v) for v in valor)
    elif isinstance(valor, dict):
        return ", ".join(f"{k}: {v}" for k, v in valor.items())
    else:
        return str(valor)
