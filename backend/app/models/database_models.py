from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, ARRAY, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from ..core.database import Base


class Juez(Base):
    """Modelo de Jueces"""
    __tablename__ = "jueces"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    apellido = Column(String(255), nullable=False)
    activo = Column(Boolean, default=True)
    fecha_alta = Column(DateTime, default=func.now())
    fecha_baja = Column(DateTime, nullable=True)

    # Relación con sentencias
    sentencias = relationship("SentenciaJuez", back_populates="juez")

    def __repr__(self):
        return f"<Juez {self.nombre} {self.apellido}>"


class Sentencia(Base):
    """Modelo de Sentencias"""
    __tablename__ = "sentencias"

    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String(64), unique=True, nullable=False, index=True)
    caratula = Column(Text, nullable=True)
    nro_expediente = Column(String(100), nullable=True, index=True)
    fecha_sentencia = Column(Date, nullable=True, index=True)
    instancia = Column(String(100), nullable=True)
    organo = Column(String(200), nullable=True, index=True)
    jurisdiccion = Column(
        String(20),
        CheckConstraint("jurisdiccion IN ('federal', 'provincial')"),
        nullable=True,
        index=True
    )
    palabras_clave = Column(ARRAY(Text), nullable=True)
    contenido = Column(Text, nullable=True)
    resumen = Column(Text, nullable=True)
    url_minio = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relación con jueces
    jueces = relationship("SentenciaJuez", back_populates="sentencia", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Sentencia {self.nro_expediente}>"


class SentenciaJuez(Base):
    """Tabla de relación muchos a muchos entre Sentencias y Jueces"""
    __tablename__ = "sentencias_jueces"

    id = Column(Integer, primary_key=True, index=True)
    sentencia_id = Column(Integer, ForeignKey("sentencias.id", ondelete="CASCADE"), nullable=False)
    juez_id = Column(Integer, ForeignKey("jueces.id"), nullable=False)

    # Relaciones
    sentencia = relationship("Sentencia", back_populates="jueces")
    juez = relationship("Juez", back_populates="sentencias")

    def __repr__(self):
        return f"<SentenciaJuez sentencia_id={self.sentencia_id} juez_id={self.juez_id}>"


class SentenciaVector(Base):
    """Modelo para almacenar vectores de sentencias (para RAG)"""
    __tablename__ = "sentencias_vectors"

    id = Column(Integer, primary_key=True, index=True)
    sentencia_id = Column(Integer, ForeignKey("sentencias.id", ondelete="CASCADE"), nullable=False, unique=True)
    # El vector se manejará con pgvector
    # embedding = Column(Vector(1536))  # Se configurará cuando instalemos pgvector
    metadata_json = Column(Text, nullable=True)  # JSON con metadata para RAG

    def __repr__(self):
        return f"<SentenciaVector sentencia_id={self.sentencia_id}>"
