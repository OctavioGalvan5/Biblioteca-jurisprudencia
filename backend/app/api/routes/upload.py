from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session

from difflib import SequenceMatcher
import io
from datetime import datetime

from ...core.database import get_db
from ...core.minio_client import minio_client
from ...services.pdf_processor import pdf_processor
from ...services.ai_extractor import ai_extractor
from ...models.database_models import Sentencia, Juez, SentenciaJuez
from ...schemas.sentencia_schemas import (
    SentenciaUploadResponse, JuezPendiente, ConfirmarJuecesRequest
)

router = APIRouter(prefix="/upload", tags=["Upload"])

SIMILITUD_VINCULADO = 0.95   # Match casi exacto → sugerir vincular con alta confianza
SIMILITUD_SUGERENCIA = 0.70  # Match parcial → sugerir con advertencia


def _similitud_nombres(a: str, b: str) -> float:
    return SequenceMatcher(None, a.upper().strip(), b.upper().strip()).ratio()


def _encontrar_coincidencia(nombre_extraido: str, jueces_db: list) -> tuple:
    """Retorna (mejor_juez, similitud) comparando nombre completo y apellido."""
    partes = nombre_extraido.strip().split()
    if len(partes) < 2:
        return None, 0.0

    apellido_extraido = partes[-1].upper()
    nombre_completo_extraido = nombre_extraido.upper()
    mejor_juez = None
    mejor_sim = 0.0

    for juez in jueces_db:
        nombre_completo_db = f"{juez.nombre} {juez.apellido}".upper()
        sim_completo = _similitud_nombres(nombre_completo_extraido, nombre_completo_db)
        sim_apellido = _similitud_nombres(apellido_extraido, juez.apellido.upper())
        sim = max(sim_completo, sim_apellido)
        if sim > mejor_sim:
            mejor_sim = sim
            mejor_juez = juez

    return mejor_juez, mejor_sim


@router.post("/sentencia", response_model=SentenciaUploadResponse)
async def upload_sentencia(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint para subir una sentencia en PDF.

    Flujo:
    1. Validar que sea PDF
    2. Calcular hash
    3. Verificar duplicados
    4. Subir a MinIO
    5. Extraer texto
    6. Procesar con IA para metadata
    7. Extraer jueces con Vision AI (fuzzy matching, sin auto-crear)
    8. Guardar sentencia en BD (sin jueces aún)
    9. Retornar datos + jueces_pendientes para revisión del usuario
    """

    # 1. Validar tipo de archivo
    if not file.content_type == "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un PDF"
        )

    # Leer contenido del archivo
    file_content = await file.read()

    # 2. Calcular hash
    file_hash = pdf_processor.calculate_hash(file_content)

    # 3. Verificar duplicados
    existing = db.query(Sentencia).filter(Sentencia.hash == file_hash).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Esta sentencia ya existe en el sistema (ID: {existing.id})"
        )

    # 4. Subir a MinIO
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"{file_hash}_{timestamp}.pdf"

        file_io = io.BytesIO(file_content)
        minio_url = minio_client.upload_file(
            file_data=file_io,
            object_name=object_name,
            content_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir archivo a MinIO: {str(e)}"
        )

    # 5. Extraer texto del PDF
    try:
        full_text = pdf_processor.extract_text(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al extraer texto del PDF: {str(e)}"
        )

    # 6. Procesar con IA para extraer metadata
    try:
        extracted_metadata = ai_extractor.extract_metadata_from_text(full_text)
    except Exception as e:
        print(f"Error en extracción de metadata: {e}")
        extracted_metadata = {}

    # 7. Extraer jueces con Vision AI
    extracted_judges_names = []
    try:
        last_page_image = pdf_processor.convert_last_page_to_image(file_content)
        if last_page_image:
            known_judges = db.query(Juez).filter(Juez.activo == True).all()
            known_judges_list = [
                {"nombre": j.nombre, "apellido": j.apellido}
                for j in known_judges
            ]
            extracted_judges_names = ai_extractor.extract_judges_from_image(
                last_page_image,
                known_judges_list
            )
    except Exception as e:
        print(f"Error en extracción de jueces: {e}")

    # 8. Guardar sentencia en BD (sin vincular jueces todavía)
    try:
        fecha_sentencia = None
        if extracted_metadata.get("fecha_sentencia"):
            try:
                from datetime import datetime as dt
                fecha_sentencia = dt.strptime(
                    extracted_metadata["fecha_sentencia"],
                    "%Y-%m-%d"
                ).date()
            except:
                pass

        nueva_sentencia = Sentencia(
            hash=file_hash,
            url_minio=minio_url,
            caratula=extracted_metadata.get("caratula"),
            nro_expediente=extracted_metadata.get("nro_expediente"),
            fecha_sentencia=fecha_sentencia,
            instancia=extracted_metadata.get("instancia"),
            organo=extracted_metadata.get("organo"),
            jurisdiccion=extracted_metadata.get("jurisdiccion"),
            palabras_clave=extracted_metadata.get("palabras_clave", []),
            contenido=full_text,
            resumen=extracted_metadata.get("resumen")
        )

        db.add(nueva_sentencia)
        db.commit()
        db.refresh(nueva_sentencia)

    except Exception as e:
        db.rollback()
        try:
            minio_client.delete_file(object_name)
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar en base de datos: {str(e)}"
        )

    # 9. Construir lista de jueces pendientes con fuzzy matching
    jueces_db = db.query(Juez).filter(Juez.activo == True).all()
    jueces_pendientes: list[JuezPendiente] = []

    for nombre_extraido in extracted_judges_names:
        partes = nombre_extraido.strip().split()
        if len(partes) < 2:
            continue

        mejor_juez, similitud = _encontrar_coincidencia(nombre_extraido, jueces_db)

        if similitud >= SIMILITUD_VINCULADO:
            accion = "vinculado"
        elif similitud >= SIMILITUD_SUGERENCIA:
            accion = "sugerencia"
        else:
            accion = "nuevo"
            mejor_juez = None

        juez_sugerido_data = None
        if mejor_juez:
            from ...schemas.sentencia_schemas import JuezResponse
            juez_sugerido_data = JuezResponse(
                id=mejor_juez.id,
                nombre=mejor_juez.nombre,
                apellido=mejor_juez.apellido,
                activo=mejor_juez.activo,
                fecha_alta=mejor_juez.fecha_alta,
                fecha_baja=mejor_juez.fecha_baja,
            )

        jueces_pendientes.append(JuezPendiente(
            nombre_extraido=nombre_extraido,
            accion=accion,
            juez_sugerido=juez_sugerido_data,
            similitud=round(similitud, 2) if similitud > 0 else None,
        ))

    return SentenciaUploadResponse(
        message="Sentencia subida exitosamente",
        sentencia_id=nueva_sentencia.id,
        hash=file_hash,
        url_minio=minio_url,
        extracted_data={
            **extracted_metadata,
            "jueces_extraidos": extracted_judges_names,
        },
        jueces_pendientes=jueces_pendientes,
    )


@router.post("/confirmar-jueces")
async def confirmar_jueces(
    request: ConfirmarJuecesRequest,
    db: Session = Depends(get_db)
):
    """
    Confirma las decisiones del usuario sobre los jueces de una sentencia.

    Para cada juez extraído el usuario puede:
    - "crear": crear un nuevo juez con nombre/apellido editado y vincularlo
    - "vincular": vincular a un juez ya existente en la BD
    - "ignorar": no vincular ningún juez para ese nombre extraído
    """
    sentencia = db.query(Sentencia).filter(Sentencia.id == request.sentencia_id).first()
    if not sentencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sentencia con ID {request.sentencia_id} no encontrada"
        )

    # Eliminar relaciones previas (por si se llama de nuevo)
    db.query(SentenciaJuez).filter(
        SentenciaJuez.sentencia_id == sentencia.id
    ).delete()

    jueces_vinculados_ids = []

    for decision in request.decisiones:
        if decision.tipo == "ignorar":
            continue

        elif decision.tipo == "vincular":
            if not decision.juez_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Decisión 'vincular' requiere juez_id (nombre: {decision.nombre_extraido})"
                )
            juez = db.query(Juez).filter(Juez.id == decision.juez_id).first()
            if not juez:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Juez con ID {decision.juez_id} no encontrado"
                )

        elif decision.tipo == "crear":
            if not decision.nombre or not decision.apellido:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Decisión 'crear' requiere nombre y apellido (extraído: {decision.nombre_extraido})"
                )
            juez = Juez(
                nombre=decision.nombre.strip().title(),
                apellido=decision.apellido.strip().title(),
                activo=True
            )
            db.add(juez)
            db.flush()
            print(f"✅ Juez creado: {juez.nombre} {juez.apellido}")

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de decisión inválido: {decision.tipo}"
            )

        if juez.id not in jueces_vinculados_ids:
            jueces_vinculados_ids.append(juez.id)
            db.add(SentenciaJuez(
                sentencia_id=sentencia.id,
                juez_id=juez.id
            ))

    db.commit()

    return {
        "message": "Jueces confirmados correctamente",
        "sentencia_id": sentencia.id,
        "jueces_ids": jueces_vinculados_ids,
    }
