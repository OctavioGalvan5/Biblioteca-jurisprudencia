from typing import Dict, Any, Optional, List
import json
import anthropic
from openai import OpenAI
from ..core.config import settings


class AIExtractor:
    """Servicio para extraer información de sentencias usando IA"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._claude = None

    @property
    def claude(self):
        if self._claude is None:
            self._claude = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._claude

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

        prompt = f"""Analizá esta imagen de una página de una sentencia judicial argentina. Tu tarea es identificar los nombres completos de los firmantes (jueces, vocales, secretarios) que aparecen en esta página.

Buscá estos formatos habituales en documentos judiciales argentinos:
- "Digitally signed by NOMBRE APELLIDO" (firma digital PDF)
- "Firmado Digitalmente por NOMBRE Apellido"
- Nombres en mayúsculas junto a cargos: "Dr. APELLIDO, NOMBRE - JUEZ FEDERAL"
- Texto bajo una firma o sello: "DRES FERRO - TAZZA - JIMENEZ, JUECES DE CÁMARA"
- Nombres precedidos de "Ante mí:", "Por su orden:", "Fdo.:"

Firmantes ya registrados en el sistema (priorizá coincidencias con estos):
{judges_list}

Respondé ÚNICAMENTE con este JSON:
{{"firmantes": ["Nombre Apellido", ...]}}

Si no encontrás ningún firmante, devolvé {{"firmantes": []}}."""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }],
            )

            text = response.content[0].text.strip()
            # Extract JSON even if model adds surrounding text
            start = text.find('{')
            end = text.rfind('}') + 1
            result = json.loads(text[start:end])
            return result.get("firmantes", result.get("jueces", []))

        except Exception as e:
            print(f"Error al extraer firmantes con Claude Vision: {e}")
            return []


# Instancia global
ai_extractor = AIExtractor()
