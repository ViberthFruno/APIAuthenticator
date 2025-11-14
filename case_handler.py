# Archivo: case_handler.py
# Ubicación: raíz del proyecto
# Descripción: Manejador principal para cargar y ejecutar casos de respuesta automática

import os
import sys
import importlib.util


class CaseHandler:
    def __init__(self):
        """Inicializa el manejador de casos"""
        self.cases = {}
        self.load_cases()

    def load_cases(self):
        """Carga todos los archivos de casos disponibles"""
        try:
            if getattr(sys, 'frozen', False):
                current_dir = sys._MEIPASS
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))

            case_files = [f for f in os.listdir(current_dir) if
                          f.startswith('case') and f.endswith('.py') and f != 'case_handler.py']

            for case_file in case_files:
                try:
                    case_name = case_file[:-3]
                    case_path = os.path.join(current_dir, case_file)
                    spec = importlib.util.spec_from_file_location(case_name, case_path)
                    case_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(case_module)

                    if hasattr(case_module, 'Case'):
                        self.cases[case_name] = case_module.Case()
                        print(f"Caso cargado: {case_name}")
                    else:
                        print(f"Error: {case_file} no tiene la clase Case")

                except Exception as e:
                    print(f"Error al cargar caso {case_file}: {str(e)}")

        except Exception as e:
            print(f"Error al cargar casos: {str(e)}")

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

    def find_matching_case(self, subject, sender, logger):
        """
        Busca el primer caso que coincida con el asunto y/o remitente del email.

        Lógica de coincidencia:
        - Si el caso tiene keywords Y senders: valida AMBOS (AND)
        - Si solo tiene keywords: valida solo keywords
        - Si solo tiene senders: valida solo senders
        - Si no tiene ninguno: no coincide
        """
        for case_name, case_obj in self.cases.items():
            try:
                keywords = case_obj.get_search_keywords()
                senders = case_obj.get_search_senders() if hasattr(case_obj, 'get_search_senders') else []

                # Validar si coincide con alguna keyword
                keyword_match = False
                matched_keyword = None
                if keywords:
                    for keyword in keywords:
                        if keyword and keyword.lower() in subject.lower():
                            keyword_match = True
                            matched_keyword = keyword
                            break

                # Validar si coincide con algún sender/dominio
                sender_match = False
                matched_sender = None
                if senders:
                    for allowed_sender in senders:
                        if allowed_sender and allowed_sender.lower() in sender.lower():
                            sender_match = True
                            matched_sender = allowed_sender
                            break

                # Determinar si el caso coincide
                has_keywords = bool(keywords)
                has_senders = bool(senders)

                if has_keywords and has_senders:
                    # Ambos configurados: validar AMBOS (AND)
                    if keyword_match and sender_match:
                        logger.info(f"Caso encontrado: {case_name} | Keyword: '{matched_keyword}' | Sender: '{matched_sender}'")
                        return case_name
                elif has_keywords:
                    # Solo keywords: validar solo keywords
                    if keyword_match:
                        logger.info(f"Caso encontrado: {case_name} | Keyword: '{matched_keyword}'")
                        return case_name
                elif has_senders:
                    # Solo senders: validar solo senders
                    if sender_match:
                        logger.info(f"Caso encontrado: {case_name} | Sender: '{matched_sender}'")
                        return case_name

            except Exception as e:
                logger.exception(f"Error al verificar caso {case_name}: {str(e)}")
                continue

        return None

    def reload_cases(self):
        """Recarga todos los casos disponibles"""
        self.cases.clear()
        self.load_cases()