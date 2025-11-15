# Archivo: case_handler.py
# Ubicación: raíz del proyecto
# Descripción: Manejador principal para cargar y ejecutar casos de respuesta automática

import sys

# Importar casos explícitamente (necesario para PyInstaller)
try:
    import case1

    AVAILABLE_CASES = {
        'case1': case1
    }
    print("[DEBUG CaseHandler] Casos importados explícitamente:", list(AVAILABLE_CASES.keys()))
except ImportError as e:
    print(f"[DEBUG CaseHandler] ⚠️ Error al importar casos: {e}")
    AVAILABLE_CASES = {}


class CaseHandler:
    def __init__(self):
        """Inicializa el manejador de casos"""
        self.cases = {}
        self.load_cases()

    def load_cases(self):
        """Carga todos los casos disponibles desde imports explícitos"""
        try:
            print(f"[DEBUG CaseHandler] Iniciando carga de casos...")
            print(f"[DEBUG CaseHandler] AVAILABLE_CASES: {list(AVAILABLE_CASES.keys())}")

            for case_name, case_module in AVAILABLE_CASES.items():
                try:
                    if hasattr(case_module, 'Case'):
                        self.cases[case_name] = case_module.Case()
                        print(f"[DEBUG CaseHandler] ✓ Caso cargado: {case_name}")
                    else:
                        print(f"[DEBUG CaseHandler] ❌ Error: {case_name} no tiene la clase Case")

                except Exception as e:
                    print(f"[DEBUG CaseHandler] ❌ Error al cargar caso {case_name}: {str(e)}")
                    import traceback
                    traceback.print_exc()

            print(f"[DEBUG CaseHandler] Total de casos cargados: {len(self.cases)}")
            print(f"[DEBUG CaseHandler] Casos en self.cases: {list(self.cases.keys())}")

        except Exception as e:
            print(f"[DEBUG CaseHandler] ❌ Error al cargar casos: {str(e)}")
            import traceback
            traceback.print_exc()

    def get_available_cases(self):
        """Obtiene la lista de casos disponibles"""
        return list(self.cases.keys())

    def get_case_info(self, case_name):
        """Obtiene información de un caso específico"""
        if case_name in self.cases:
            case_obj = self.cases[case_name]
            return {
                'name': case_obj.get_name(),
                'description': case_obj.get_description(),
                'search_keywords': case_obj.get_search_keywords()
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

    def find_matching_case(self, subject, sender, allowed_domains, logger):
        """
        Busca el primer caso que coincida con el asunto O dominio del email (lógica OR)

        Args:
            subject: Asunto del correo
            sender: Remitente del correo (puede incluir nombre y email)
            allowed_domains: String con dominios permitidos separados por comas o None
            logger: Logger para mensajes

        Returns:
            Nombre del caso si coincide, None si no
        """
        print(f"[DEBUG CaseHandler] Buscando caso para asunto: '{subject}'")
        print(f"[DEBUG CaseHandler] Sender: '{sender}'")
        print(f"[DEBUG CaseHandler] Dominios permitidos: '{allowed_domains}'")
        print(f"[DEBUG CaseHandler] Casos disponibles: {list(self.cases.keys())}")

        # Extraer dominio del sender
        sender_domain = None
        if sender and '@' in sender:
            # El sender puede venir como "Nombre <email@domain.com>" o "email@domain.com"
            import re
            email_match = re.search(r'[\w\.-]+@[\w\.-]+', sender)
            if email_match:
                email_address = email_match.group(0)
                sender_domain = '@' + email_address.split('@')[1]
                print(f"[DEBUG CaseHandler] Dominio extraído del sender: '{sender_domain}'")

        # Parsear dominios permitidos
        domains_list = []
        if allowed_domains and allowed_domains.strip():
            # Separar por comas y limpiar espacios
            domains_list = [d.strip() for d in allowed_domains.split(',') if d.strip()]
            print(f"[DEBUG CaseHandler] Dominios parseados: {domains_list}")

        for case_name, case_obj in self.cases.items():
            try:
                print(f"[DEBUG CaseHandler] Verificando caso: {case_name}")
                keywords = case_obj.get_search_keywords()
                print(f"[DEBUG CaseHandler] Keywords para {case_name}: {keywords}")

                # VERIFICACIÓN 1: Buscar por palabra clave en el asunto
                keyword_match = False
                for keyword in keywords:
                    print(f"[DEBUG CaseHandler] ¿'{keyword.lower()}' en '{subject.lower()}'?")
                    if keyword.lower() in subject.lower():
                        keyword_match = True
                        logger.info(f"✓ Caso encontrado por PALABRA CLAVE: {case_name} ('{keyword}')")
                        print(f"[DEBUG CaseHandler] ✓ MATCH por palabra clave!")
                        return case_name

                # VERIFICACIÓN 2: Buscar por dominio del remitente (si hay dominios configurados)
                domain_match = False
                if sender_domain and domains_list:
                    for allowed_domain in domains_list:
                        # Normalizar para comparación (case insensitive)
                        if sender_domain.lower() == allowed_domain.lower():
                            domain_match = True
                            logger.info(f"✓ Caso encontrado por DOMINIO: {case_name} ('{sender_domain}')")
                            print(f"[DEBUG CaseHandler] ✓ MATCH por dominio!")
                            return case_name

                # Si no hubo match ni por keyword ni por dominio
                if not keyword_match and not domain_match:
                    print(f"[DEBUG CaseHandler] ✗ No coincide (ni keyword ni dominio)")

            except Exception as e:
                logger.exception(f"Error al verificar caso {case_name}: {str(e)}")
                print(f"[DEBUG CaseHandler] ❌ Error en caso {case_name}: {e}")
                continue

        print(f"[DEBUG CaseHandler] ❌ No se encontró ningún caso que coincida")
        return None

    def reload_cases(self):
        """Recarga todos los casos disponibles"""
        self.cases.clear()
        self.load_cases()