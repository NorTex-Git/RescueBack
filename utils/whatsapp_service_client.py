import requests
import json
from core.config import Config

class WhatsAppServiceClient:
    """
    Cliente para consumir el servicio de WhatsApp
    """
    
    def __init__(self):
        self.api_base_url = Config.WHATSAPP_SERVICE_URL
        self.broadcast_endpoint = f"{self.api_base_url}/send-broadcast-template"
        self.send_message_endpoint = f"{self.api_base_url}/send-message"
        self.send_reaction_endpoint = f"{self.api_base_url}/send-reaction"
        self.timeout = Config.WHATSAPP_SERVICE_TIMEOUT

    def send_reaction(self, phone, wa_message_id, emoji):
        """Envía (o quita, con emoji='') una reacción a un mensaje por su wamid."""
        if not self.api_base_url or not phone or not wa_message_id:
            return {"success": False, "error": "phone y wa_message_id requeridos"}
        try:
            response = requests.post(
                self.send_reaction_endpoint,
                headers={"Content-Type": "application/json"},
                json={"phone": phone, "message_id": wa_message_id, "emoji": emoji or ""},
                timeout=self.timeout,
            )
            try:
                result = response.json()
            except json.JSONDecodeError:
                return {"success": False, "error": f"Respuesta no válida ({response.status_code})"}
            if 200 <= response.status_code < 300 and result.get("success"):
                return {"success": True, "data": result.get("data")}
            return {"success": False, "error": result.get("error", f"HTTP {response.status_code}")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_text_message(self, phone, message, use_queue=False, context_message_id=None):
        """Envía un mensaje de texto libre a un número vía el servicio de WhatsApp.

        `context_message_id`: wamid del mensaje que se está respondiendo (para que
        WhatsApp muestre la cita).
        Nota: WhatsApp sólo permite texto libre dentro de la ventana de 24h de la
        conversación; fuera de ella el servicio responderá error (requiere plantilla).
        """
        if not self.api_base_url:
            return {"success": False, "error": "WHATSAPP_SERVICE_URL no configurado", "data": None}
        if not phone or not message:
            return {"success": False, "error": "phone y message son requeridos", "data": None}

        payload = {"phone": phone, "message": message, "use_queue": use_queue}
        if context_message_id:
            payload["context_message_id"] = context_message_id
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(
                self.send_message_endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            try:
                result = response.json()
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": f"Respuesta no válida del servicio. Status: {response.status_code}",
                    "data": None,
                }
            if 200 <= response.status_code < 300 and result.get("success"):
                return {"success": True, "data": result.get("data", result), "error": None}
            return {
                "success": False,
                "error": result.get("error", f"Error HTTP {response.status_code}"),
                "data": None,
            }
        except requests.exceptions.Timeout:
            return {"success": False, "error": f"Timeout al conectar con el servicio de WhatsApp (>{self.timeout}s)", "data": None}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Error de conexión con el servicio de WhatsApp", "data": None}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Error en la petición: {str(e)}", "data": None}
        except Exception as e:
            return {"success": False, "error": f"Error inesperado: {str(e)}", "data": None}
    
    def enviar_broadcast_plantilla(self, phones, template_name, language="es_CO", parameters=None, use_queue=False):
        """
        Envía una plantilla de WhatsApp a múltiples números
        
        Args:
            phones (list): Lista de números de teléfono
            template_name (str): Nombre de la plantilla
            language (str): Código de idioma
            parameters (list): Parámetros de la plantilla
            use_queue (bool): Si usar cola para el envío
        
        Returns:
            dict: Respuesta de la API
        """
        
        payload = {
            "phones": phones,
            "template_name": template_name,
            "language": language,
            "parameters": parameters or [],
            "use_queue": use_queue
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.broadcast_endpoint, 
                headers=headers, 
                json=payload,
                timeout=self.timeout
            )
            
            try:
                result = response.json()
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": f"Respuesta no válida del servicio. Status: {response.status_code}",
                    "data": None
                }
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": result.get('data', result),
                    "debug_info": result.get('debug_info'),
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', f'Error HTTP {response.status_code}'),
                    "data": None,
                    "debug_info": result.get('debug_info')
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Timeout al conectar con el servicio de WhatsApp (>{self.timeout}s)",
                "data": None
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Error de conexión con el servicio de WhatsApp",
                "data": None
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Error en la petición: {str(e)}",
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error inesperado: {str(e)}",
                "data": None
            }

    def delete_number(self, phone):
        """
        Elimina un numero del servicio de WhatsApp.
        """
        if not self.api_base_url:
            return {
                "success": False,
                "error": "WHATSAPP_SERVICE_URL no configurado",
                "data": None
            }
        if not phone:
            return {
                "success": False,
                "error": "Numero de telefono faltante",
                "data": None
            }

        endpoint = f"{self.api_base_url}/numbers/{phone}"
        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.delete(
                endpoint,
                headers=headers,
                timeout=self.timeout
            )

            try:
                result = response.json()
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": f"Respuesta no valida del servicio. Status: {response.status_code}",
                    "data": None
                }

            if 200 <= response.status_code < 300:
                return {
                    "success": True,
                    "data": result.get("data", result),
                    "error": None
                }

            return {
                "success": False,
                "error": result.get("error", f"Error HTTP {response.status_code}"),
                "data": None
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Timeout al conectar con el servicio de WhatsApp (>{self.timeout}s)",
                "data": None
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Error de conexion con el servicio de WhatsApp",
                "data": None
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Error en la peticion: {str(e)}",
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error inesperado: {str(e)}",
                "data": None
            }


# Instancia global del cliente
whatsapp_client = WhatsAppServiceClient()
