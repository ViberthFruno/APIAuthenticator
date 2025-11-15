# Archivo: case_handler.py
# Ubicación: raíz del proyecto
# Descripción: Manejador principal para cargar y ejecutar casos de respuesta automática

import os
import sys

# ============================================================================
# IMPORTANTE: Para PyInstaller --onefile
# ============================================================================
# Los archivos .py no existen físicamente cuando están empaquetados.
# Por eso debemos importar explícitamente todos los casos aquí.
#
# Para agregar un nuevo caso:
# 1. Crear el archivo caseN.py con la clase Case
# 2. Importarlo explícitamente aquí abajo
# 3. Agregarlo al diccionario AVAILABLE_CASES
# ============================================================================

# Importar casos explícitamente (necesario para PyInstaller)
try:
    import case1
    AVAILABLE_CASES = {
        'case1': case1
    }
    print(f"[DEBUG CaseHandler] ✅ Casos importados explícitamente: {list(AVAILABLE_CASES.keys())}")
except ImportError as e:
    print(f"[DEBUG CaseHandler] ⚠️ Error al importar casos: {e}")
    AVAILABLE_CASES = {}


class CaseHandler:
    def __init__(self):
        """Inicializa el manejador de casos"""
        self.cases = {}
        self.load_cases()

    def load_cases(self):
        """Carga todos los casos desde AVAILABLE_CASES (compatible con PyInstaller)"""
        print(f"[DEBUG CaseHandler] Iniciando carga de casos...")
        print(f"[DEBUG CaseHandler] AVAILABLE_CASES: {list(AVAILABLE_CASES.keys())}")

        try:
            for case_name, case_module in AVAILABLE_CASES.items():
                try:
                    if hasattr(case_module, 'Case'):
                        self.cases[case_name] = case_module.Case()
                        print(f"[DEBUG CaseHandler] ✅ Caso cargado: {case_name}")
                    else:
                        print(f"[DEBUG CaseHandler] ❌ Error: {case_name} no tiene la clase Case")

                except Exception as e:
                    print(f"[DEBUG CaseHandler] ❌ Error al cargar caso {case_name}: {str(e)}")
                    import traceback
                    traceback.print_exc()

            print(f"[DEBUG CaseHandler] Total de casos cargados: {len(self.cases)}")
            print(f"[DEBUG CaseHandler] Casos en self.cases: {list(self.cases.keys())}")

        except Exception as e:
            print(f"[DEBUG CaseHandler] ❌ Error en load_cases: {str(e)}")
            import traceback
            traceback.print_exc()

    def get_available_cases(self):
        """Obtiene la lista de casos disponibles"""
        return list(self.cases.keys())

    def get_case_info(self, case_name, logger=None):
        """Obtiene información de un caso específico"""
        if case_name in self.cases:
            case_obj = self.cases[case_name]
            return {
                'name': case_obj.get_name(),
                'description': case_obj.get_description(),
                'search_keywords': case_obj.get_search_keywords(logger=logger)
            }
        return None

    def execute_case(self, case_name, email_data, logger):
        """Ejecuta un caso específico"""
        if case_name in self.cases:
            try:
                case_obj = self.cases[case_name]
                return case_obj.process_email(email_data, logger)
            except Exception as e:
                logger.exception(f"Error al ejecutar caso {case_name}: {str(e)}")
                return False
        else:
            logger.error(f"Caso no encontrado: {case_name}")
            return False

    def find_matching_case(self, subject, logger):
        """Busca el primer caso que coincida con el asunto del email"""
        print(f"[DEBUG CaseHandler] Buscando caso para asunto: '{subject}'")
        print(f"[DEBUG CaseHandler] Casos disponibles: {list(self.cases.keys())}")

        logger.info(f"🔍 Buscando caso para asunto: '{subject}'")
        logger.info(f"📋 Casos disponibles: {list(self.cases.keys())}")

        for case_name, case_obj in self.cases.items():
            try:
                print(f"[DEBUG CaseHandler] Verificando caso: {case_name}")

                # Pasar el logger a get_search_keywords para mejor debugging
                keywords = case_obj.get_search_keywords(logger=logger)

                print(f"[DEBUG CaseHandler] Keywords para {case_name}: {keywords}")
                logger.info(f"🔑 Palabras clave para {case_name}: {keywords}")

                if not keywords:
                    print(f"[DEBUG CaseHandler] ⚠️ {case_name} sin keywords configuradas")
                    logger.warning(f"⚠️ {case_name} no tiene palabras clave configuradas")
                    continue

                for keyword in keywords:
                    keyword_lower = keyword.lower() if keyword else ""
                    subject_lower = subject.lower()

                    print(f"[DEBUG CaseHandler] ¿'{keyword_lower}' en '{subject_lower}'?")

                    if keyword and keyword_lower in subject_lower:
                        print(f"[DEBUG CaseHandler] ✅ MATCH encontrado!")
                        logger.info(f"✅ Caso encontrado: {case_name} para palabra clave: '{keyword}'")
                        return case_name
                    else:
                        print(f"[DEBUG CaseHandler] ❌ No match")

            except Exception as e:
                print(f"[DEBUG CaseHandler] ❌ Error al verificar {case_name}: {e}")
                logger.exception(f"❌ Error al verificar caso {case_name}: {str(e)}")
                continue

        print(f"[DEBUG CaseHandler] ⚠️ Ningún caso coincide con '{subject}'")
        logger.warning(f"⚠️ No se encontró ningún caso que coincida con el asunto: '{subject}'")
        return None

    def reload_cases(self):
        """Recarga todos los casos disponibles"""
        print(f"[DEBUG CaseHandler] Recargando casos...")
        self.cases.clear()
        self.load_cases()