import hashlib
import io
import json
from typing import BinaryIO, Dict, Any, List, Optional
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import base64


class PDFProcessor:
    """Servicio para procesar archivos PDF"""

    @staticmethod
    def calculate_hash(file_data: bytes) -> str:
        """
        Calcular hash SHA256 del archivo

        Args:
            file_data: Contenido del archivo en bytes

        Returns:
            Hash SHA256 en hexadecimal
        """
        return hashlib.sha256(file_data).hexdigest()

    @staticmethod
    def extract_text(file_data: bytes) -> str:
        """
        Extraer texto completo del PDF

        Args:
            file_data: Contenido del PDF en bytes

        Returns:
            Texto extraído del PDF
        """
        text_parts = []

        try:
            # Intentar con pdfplumber (mejor para tablas y texto complejo)
            with pdfplumber.open(io.BytesIO(file_data)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

        except Exception as e:
            print(f"Error con pdfplumber: {e}. Intentando con PyPDF2...")

            # Fallback a PyPDF2
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data))
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            except Exception as e2:
                print(f"Error con PyPDF2: {e2}")
                raise Exception("No se pudo extraer texto del PDF")

        full_text = "\n\n".join(text_parts)
        return full_text.strip()

    # Palabras clave para detectar la página de firmas
    FIRMA_KEYWORDS = ["digitally signed", "firmado digitalmente", "firma"]

    @staticmethod
    def convert_last_page_to_image(file_data: bytes) -> Optional[str]:
        """
        Convertir la página de firmas del PDF a imagen (para extraer jueces).
        Escanea las últimas páginas buscando la que contiene firmas digitales,
        en lugar de asumir siempre que es la última página.

        Args:
            file_data: Contenido del PDF en bytes

        Returns:
            Imagen de la página de firmas en base64
        """
        try:
            doc = fitz.open(stream=file_data, filetype="pdf")

            if len(doc) == 0:
                doc.close()
                return None

            n = len(doc)
            firma_page = None

            # Buscar en las últimas 5 páginas (de atrás hacia adelante)
            for i in range(n - 1, max(n - 6, -1), -1):
                page = doc[i]
                text = page.get_text().lower()
                if any(kw in text for kw in PDFProcessor.FIRMA_KEYWORDS):
                    firma_page = page
                    print(f"✅ Página de firmas detectada: página {i + 1} de {n}")
                    break

            # Fallback a última página si no se encontró ninguna con firmas
            if firma_page is None:
                firma_page = doc[-1]
                print(f"⚠️ Sin página de firmas detectada, usando última página ({n})")

            # Renderizar a imagen con buena resolución (2x zoom = ~200 DPI)
            mat = fitz.Matrix(2, 2)
            pix = firma_page.get_pixmap(matrix=mat)

            # Convertir a bytes PNG
            img_bytes = pix.tobytes("png")
            doc.close()

            # Convertir a base64
            img_base64 = base64.b64encode(img_bytes).decode()

            print(f"✅ Página de firmas convertida a imagen ({pix.width}x{pix.height}px)")
            return img_base64

        except Exception as e:
            print(f"❌ Error al convertir página a imagen: {e}")
            return None

    @staticmethod
    def get_pdf_metadata(file_data: bytes) -> Dict[str, Any]:
        """
        Extraer metadata del PDF

        Args:
            file_data: Contenido del PDF en bytes

        Returns:
            Diccionario con metadata
        """
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data))
            metadata = pdf_reader.metadata

            return {
                "num_pages": len(pdf_reader.pages),
                "author": metadata.get("/Author", None) if metadata else None,
                "creator": metadata.get("/Creator", None) if metadata else None,
                "producer": metadata.get("/Producer", None) if metadata else None,
                "subject": metadata.get("/Subject", None) if metadata else None,
                "title": metadata.get("/Title", None) if metadata else None,
            }
        except Exception as e:
            print(f"Error al extraer metadata: {e}")
            return {"num_pages": 0}


# Instancia global
pdf_processor = PDFProcessor()

