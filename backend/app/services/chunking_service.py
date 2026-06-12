import json
import re
from openai import OpenAI
from ..core.config import settings

CHUNK_PROMPT = """Analiza esta sentencia judicial argentina y dividila en sus secciones principales.
Devolvé un JSON con la clave "secciones" que sea un array de objetos.
Cada objeto debe tener:
- "tipo": "vistos", "considerando", "resuelve" o "general"
- "contenido": el texto exacto de esa sección sin modificar ni resumir

Reglas:
- "vistos": una sola sección con los antecedentes y hechos del caso
- "considerando": cada bloque de razonamiento numerado (I, II, 1., 2., etc.) es una sección separada
- "resuelve": una sola sección con la parte dispositiva
- Reproduci el texto completo distribuido entre las secciones, sin omitir nada
- Si no hay estructura clara, devolvé una sola sección "general" con todo el contenido"""

MAX_INPUT_CHARS = 40000
MAX_OUTPUT_TOKENS = 14000

# Patrones para chunking estructural (fallback sin IA)
_VISTOS = re.compile(r'\bVISTO[S]?\b', re.IGNORECASE)
_CONSIDERANDO = re.compile(r'\bCONSIDERANDO[S]?\b', re.IGNORECASE)
_RESUELVE = re.compile(r'\b(?:SE\s+)?RESUELVE\b|\bFALLA\b|\bPOR\s+(?:TODO\s+)?ELLO\s*[:,]', re.IGNORECASE)
_NUMBERED = re.compile(r'\n\s*(?:[IVX]{1,5}\.|[0-9]{1,2}\.)\s+[A-ZÁÉÍÓÚ]', re.MULTILINE)


class ChunkingService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def chunk_sentencia(self, contenido: str) -> list[dict]:
        if not contenido or len(contenido.strip()) < 200:
            return [{"tipo": "general", "contenido": contenido or ""}]

        # For short-to-medium documents: use GPT
        if len(contenido) <= MAX_INPUT_CHARS:
            result = self._chunk_with_gpt(contenido)
            if result:
                return result

        # For long documents or GPT failure: use structural regex
        result = self._chunk_with_regex(contenido)
        if result:
            return result

        # Final fallback: fixed-size chunks
        return self._fixed_chunks(contenido)

    def _chunk_with_gpt(self, contenido: str) -> list[dict] | None:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": CHUNK_PROMPT},
                    {"role": "user", "content": contenido[:MAX_INPUT_CHARS]},
                ],
                temperature=0,
                max_tokens=MAX_OUTPUT_TOKENS,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)

            # Accept various key names the model might use
            secciones = (
                data.get("secciones")
                or data.get("chunks")
                or data.get("sections")
                or data.get("sectiones")
            )
            if not secciones or not isinstance(secciones, list):
                return None

            result = []
            for s in secciones:
                if isinstance(s, dict) and s.get("contenido", "").strip():
                    result.append({
                        "tipo": s.get("tipo", "general"),
                        "contenido": str(s["contenido"]).strip(),
                    })
            return result if result else None

        except Exception as e:
            print(f"GPT chunking failed: {e}")
            return None

    def _chunk_with_regex(self, contenido: str) -> list[dict] | None:
        """Split by VISTOS / CONSIDERANDO / RESUELVE section headers."""
        boundaries = []

        m = _VISTOS.search(contenido)
        if m:
            boundaries.append((m.start(), "vistos"))

        m = _CONSIDERANDO.search(contenido)
        if m:
            boundaries.append((m.start(), "considerando_block"))

        m = _RESUELVE.search(contenido)
        if m:
            boundaries.append((m.start(), "resuelve"))

        if len(boundaries) < 2:
            return None  # Not enough structure found

        boundaries.sort(key=lambda x: x[0])

        chunks = []
        for i, (start, tipo) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(contenido)
            text = contenido[start:end].strip()
            if not text:
                continue

            if tipo == "considerando_block":
                # Split numbered considerandos within this block
                sub = self._split_numbered_considerandos(text)
                chunks.extend(sub)
            else:
                chunks.append({"tipo": tipo, "contenido": text})

        # Prepend any text before the first boundary
        if boundaries and boundaries[0][0] > 100:
            preamble = contenido[:boundaries[0][0]].strip()
            if preamble:
                chunks.insert(0, {"tipo": "vistos", "contenido": preamble})

        return chunks if chunks else None

    def _split_numbered_considerandos(self, block: str) -> list[dict]:
        """Split a considerandos block into individual numbered sections."""
        matches = list(_NUMBERED.finditer(block))
        if not matches:
            return [{"tipo": "considerando", "contenido": block}]

        result = []
        positions = [m.start() for m in matches] + [len(block)]

        # Text before first numbered section
        if positions[0] > 0:
            pre = block[:positions[0]].strip()
            if pre:
                result.append({"tipo": "considerando", "contenido": pre})

        for i in range(len(matches)):
            text = block[positions[i]:positions[i + 1]].strip()
            if text:
                result.append({"tipo": "considerando", "contenido": text})

        return result

    def _fixed_chunks(self, contenido: str, size: int = 2000) -> list[dict]:
        return [
            {"tipo": "general", "contenido": contenido[i:i + size].strip()}
            for i in range(0, len(contenido), size)
            if contenido[i:i + size].strip()
        ]


chunking_service = ChunkingService()
