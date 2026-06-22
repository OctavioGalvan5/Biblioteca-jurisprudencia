import hashlib
import io
import base64
from typing import Optional
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
from PIL import Image


MIN_TEXT_CHARS = 300  # Below this total → likely a scanned PDF


class PDFProcessor:

    @staticmethod
    def calculate_hash(file_data: bytes) -> str:
        return hashlib.sha256(file_data).hexdigest()

    @staticmethod
    def extract_text(file_data: bytes) -> str:
        """
        Extract text from PDF with automatic OCR fallback.
        Strategy: native extraction → Tesseract → GPT-4o Vision
        """
        text = PDFProcessor._extract_text_native(file_data)
        if len(text.strip()) >= MIN_TEXT_CHARS:
            return text

        print(f"Texto insuficiente ({len(text)} chars) - intentando OCR con Tesseract...")
        try:
            ocr_text = PDFProcessor._extract_text_tesseract(file_data)
            if len(ocr_text.strip()) >= MIN_TEXT_CHARS:
                print(f"Tesseract OK: {len(ocr_text)} chars")
                return ocr_text
            print(f"Tesseract insuficiente ({len(ocr_text)} chars) - probando Vision...")
        except Exception as e:
            print(f"Tesseract no disponible: {e}")

        try:
            from ..core.config import settings
            vision_text = PDFProcessor._extract_text_vision(file_data, settings.OPENAI_API_KEY)
            if vision_text.strip():
                print(f"GPT-4o Vision OK: {len(vision_text)} chars")
                return vision_text
        except Exception as e:
            print(f"GPT-4o Vision fallo: {e}")

        # Return whatever we have even if short
        return text

    @staticmethod
    def _extract_text_native(file_data: bytes) -> str:
        text_parts = []
        try:
            with pdfplumber.open(io.BytesIO(file_data)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
        except Exception as e:
            print(f"pdfplumber fallo: {e} — intentando PyPDF2...")
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(file_data))
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            except Exception as e2:
                print(f"PyPDF2 fallo: {e2}")

        return "\n\n".join(text_parts).strip()

    @staticmethod
    def _render_pages(file_data: bytes, dpi_scale: float = 2.0):
        """Yield (page_num, PIL Image) for each page using PyMuPDF."""
        doc = fitz.open(stream=file_data, filetype="pdf")
        mat = fitz.Matrix(dpi_scale, dpi_scale)
        try:
            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                yield i, img
        finally:
            doc.close()

    @staticmethod
    def _extract_text_tesseract(file_data: bytes) -> str:
        import pytesseract  # optional dep — ImportError caught by caller

        parts = []
        for _, img in PDFProcessor._render_pages(file_data):
            text = pytesseract.image_to_string(img, lang="spa+eng", config="--psm 1")
            if text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts)

    @staticmethod
    def _extract_text_vision(file_data: bytes, api_key: str, max_pages: int = 30) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        parts = []

        for i, img in PDFProcessor._render_pages(file_data):
            if i >= max_pages:
                break
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extrae todo el texto de esta página de una sentencia judicial argentina. "
                                "Devuelve solo el texto tal como aparece, sin comentarios ni explicaciones."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }],
                max_tokens=4000,
            )
            text = resp.choices[0].message.content
            if text and text.strip():
                parts.append(text.strip())

        return "\n\n".join(parts)

    FIRMA_KEYWORDS = ["digitally signed", "firmado digitalmente", "firmado por", "fdo:"]

    @staticmethod
    def convert_last_page_to_image(file_data: bytes) -> Optional[str]:
        """Convert the signature page to base64 PNG for judge extraction."""
        try:
            doc = fitz.open(stream=file_data, filetype="pdf")
            if len(doc) == 0:
                doc.close()
                return None

            n = len(doc)
            firma_page = None

            # Solo buscamos en la última (n-1) y penúltima (n-2) página
            for i in range(n - 1, max(n - 3, -1), -1):
                page = doc[i]
                text = page.get_text().lower()
                if any(kw in text for kw in PDFProcessor.FIRMA_KEYWORDS):
                    firma_page = page
                    print(f"Pagina de firmas detectada: pagina {i + 1} de {n}")
                    break

            if firma_page is None:
                firma_page = doc[-1]
                print(f"Sin pagina de firmas detectada, usando ultima pagina ({n})")

            mat = fitz.Matrix(3, 3)  # 3x zoom ≈ 225 DPI — mejor legibilidad para Vision
            pix = firma_page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            doc.close()

            img_base64 = base64.b64encode(img_bytes).decode()
            print(f"Pagina de firmas convertida ({pix.width}x{pix.height}px)")
            return img_base64

        except Exception as e:
            print(f"Error al convertir pagina a imagen: {e}")
            return None

    @staticmethod
    def get_pdf_metadata(file_data: bytes) -> dict:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_data))
            meta = reader.metadata
            return {
                "num_pages": len(reader.pages),
                "author": meta.get("/Author") if meta else None,
                "creator": meta.get("/Creator") if meta else None,
                "producer": meta.get("/Producer") if meta else None,
                "subject": meta.get("/Subject") if meta else None,
                "title": meta.get("/Title") if meta else None,
            }
        except Exception as e:
            print(f"Error al extraer metadata: {e}")
            return {"num_pages": 0}


pdf_processor = PDFProcessor()
