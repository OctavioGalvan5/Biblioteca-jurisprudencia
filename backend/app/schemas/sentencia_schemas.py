from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class JuezBase(BaseModel):
    nombre: str
    apellido: str
    activo: bool = True


class JuezCreate(JuezBase):
    pass


class JuezResponse(JuezBase):
    id: int
    fecha_alta: datetime
    fecha_baja: Optional[datetime] = None

    class Config:
        from_attributes = True


class SentenciaBase(BaseModel):
    caratula: Optional[str] = None
    nro_expediente: Optional[str] = None
    fecha_sentencia: Optional[date] = None
    instancia: Optional[str] = None
    organo: Optional[str] = None
    jurisdiccion: Optional[str] = Field(None, pattern="^(federal|provincial)$")
    palabras_clave: Optional[List[str]] = None
    contenido: Optional[str] = None
    resumen: Optional[str] = None


class SentenciaCreate(SentenciaBase):
    hash: str
    url_minio: str


class SentenciaUpdate(SentenciaBase):
    """Schema para actualizar sentencia (excluye hash y url_minio)"""
    jueces_ids: Optional[List[int]] = None


class SentenciaResponse(SentenciaBase):
    id: int
    hash: str
    url_minio: str
    created_at: datetime
    updated_at: datetime
    jueces: List[JuezResponse] = []

    class Config:
        from_attributes = True


class JuezPendiente(BaseModel):
    """Juez detectado por IA que necesita revisión del usuario"""
    nombre_extraido: str
    accion: str  # "nuevo" | "sugerencia" | "vinculado"
    juez_sugerido: Optional[JuezResponse] = None
    similitud: Optional[float] = None


class DecisionJuez(BaseModel):
    """Decisión del usuario sobre un juez pendiente"""
    nombre_extraido: str
    tipo: str  # "crear" | "vincular" | "ignorar"
    juez_id: Optional[int] = None      # Para "vincular"
    nombre: Optional[str] = None       # Para "crear"
    apellido: Optional[str] = None     # Para "crear"


class ConfirmarJuecesRequest(BaseModel):
    sentencia_id: int
    decisiones: List[DecisionJuez]


class SentenciaUploadResponse(BaseModel):
    """Respuesta después de subir un PDF"""
    message: str
    sentencia_id: int
    hash: str
    url_minio: str
    extracted_data: dict
    jueces_pendientes: List[JuezPendiente] = []


class SentenciaListResponse(BaseModel):
    """Respuesta de lista de sentencias"""
    total: int
    sentencias: List[SentenciaResponse]
