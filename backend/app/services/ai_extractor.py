from typing import Dict, Any, Optional, List
import json
from openai import OpenAI
from ..core.config import settings


class AIExtractor:
    """Servicio para extraer información de sentencias usando IA"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def extract_metadata_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extraer metadata de una sentencia usando GPT

        Args:
            text: Texto completo de la sentencia

        Returns:
            Diccionario con metadata extraída
        """
        prompt = f"""
Eres un asistente experto en análisis de sentencias judiciales argentinas.

Analiza el siguiente texto de una sentencia y extrae la siguiente información en formato JSON:

1. **caratula**: La carátula del expediente (ej: "LASCURAIN, IGNACIO ROQUE c/ ANSES s/ EJECUCIÓN PREVISIONAL")
2. **nro_expediente**: Número de expediente (ej: "FRO 23011341/2010")
3. **fecha_sentencia**: Fecha de la sentencia en formato YYYY-MM-DD
4. **instancia**: Instancia judicial (ej: "Primera Instancia", "Cámara de Apelaciones", etc.)
5. **organo**: Órgano judicial (ej: "CAMARA FEDERAL DE ROSARIO - SALA A", "Juzgado Federal Nº 2")
6. **jurisdiccion**: "federal" o "provincial"
7. **palabras_clave**: Array de palabras clave relevantes (máximo 10)
8. **resumen**: Resumen conciso de la sentencia (máximo 300 palabras)

Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional.

TEXTO DE LA SENTENCIA:
{text[:8000]}

JSON:
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un experto en análisis de documentos judiciales. Respondes solo en formato JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Validar y normalizar jurisdicción
            if result.get("jurisdiccion"):
                result["jurisdiccion"] = result["jurisdiccion"].lower()
                if result["jurisdiccion"] not in ["federal", "provincial"]:
                    result["jurisdiccion"] = None

            return result

        except Exception as e:
            print(f"Error al extraer metadata con IA: {e}")
            return {
                "caratula": None,
                "nro_expediente": None,
                "fecha_sentencia": None,
                "instancia": None,
                "organo": None,
                "jurisdiccion": None,
                "palabras_clave": [],
                "resumen": None
            }

    def extract_judges_from_image(self, image_base64: str, known_judges: List[Dict[str, str]]) -> List[str]:
        """
        Extraer nombres de jueces de la imagen de firmas usando Vision AI

        Args:
            image_base64: Imagen en base64
            known_judges: Lista de jueces conocidos [{"nombre": "...", "apellido": "..."}]

        Returns:
            Lista de nombres completos de jueces extraídos
        """
        judges_list = "\n".join([f"- {j['nombre']} {j['apellido']}" for j in known_judges[:50]])

        prompt = f"""
Esta es una página de una sentencia judicial argentina que contiene las firmas de los jueces.

INSTRUCCIONES:
1. Identifica los nombres completos de los jueces que firmaron la sentencia
2. Busca los siguientes formatos de firma digital (ambos son válidos):
   - "Digitally signed by NOMBRE APELLIDO" (firma digital estilo PDF)
   - "Firmado Digitalmente por NOMBRE Apellido" (formato usado en la Corte Suprema argentina)
   También considerá nombres en mayúsculas asociados a firmas o sellos.
3. Compara con esta lista de jueces conocidos en el sistema:

{judges_list}

4. Devuelve un JSON con formato:
{{"jueces": ["NOMBRE COMPLETO APELLIDO", ...]}}

Responde ÚNICAMENTE con el JSON, sin texto adicional.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("jueces", [])

        except Exception as e:
            print(f"Error al extraer jueces con Vision AI: {e}")
            return []


# Instancia global
ai_extractor = AIExtractor()
