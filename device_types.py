# device_types.py
# Constantes de tipos de dispositivo con sus IDs
# Estos IDs corresponden a los tipos de dispositivo en la API

# Lista de todos los tipos de dispositivo disponibles
TIPOS_DISPOSITIVO = {
    1: "Celulares y Tablets",
    2: "Monitores",
    3: "Cocinas",
    4: "Refrigeradoras",
    6: "Licuadoras",
    7: "Desconocido",
    8: "Audífonos",
    9: "Relojes",
    10: "Cable USB",
    11: "Cubo",
    13: "Proyector",
    15: "Parlante",
    16: "Mouse",
    17: "Scooter",
    18: "Robot de Limpieza",
    19: "Pantallas",
    20: "Impresora",
    21: "Laptop",
    23: "Cámaras de seguridad",
    24: "Router",
    25: "Drones",
    26: "Baterías",
    27: "Gamming",
    28: "Teclado",
    29: "Estuches",
    32: "Audio/video",
    33: "Internet Satelital",
    34: "Tarjeta de memoria externa",
    36: "No encontrado"  # Se pondrá automáticamente si no encuentra en el PDF
}

# IDs especiales
TIPO_DISPOSITIVO_DESCONOCIDO = 7
TIPO_DISPOSITIVO_NO_ENCONTRADO = 36

def get_tipo_dispositivo_nombre(tipo_id):
    """Obtiene el nombre del tipo de dispositivo por su ID"""
    return TIPOS_DISPOSITIVO.get(tipo_id, "Desconocido")

def get_tipos_dispositivo_ordenados():
    """Retorna una lista de tuplas (id, nombre) ordenada alfabéticamente por nombre"""
    return sorted(TIPOS_DISPOSITIVO.items(), key=lambda x: x[1])

def get_tipos_dispositivo_para_dropdown():
    """Retorna una lista de strings formateados para dropdown: 'Nombre (ID: XX)'"""
    return [f"{nombre} (ID: {id_tipo})" for id_tipo, nombre in get_tipos_dispositivo_ordenados()]
